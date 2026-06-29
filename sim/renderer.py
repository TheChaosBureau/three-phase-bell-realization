from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import imageio.v2 as imageio
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Circle
import numpy as np
import pandas as pd

from .config import BRANCHES
from .geometry import CircularBasinGeometry, default_geometry
from .modes import annular_mode, build_basin_grid, gaussian_mode, oriented_local_mode, shared_modes


def _sample_frame_indices(times: np.ndarray, sample_interval: float) -> list[int]:
    if len(times) == 0:
        return []
    if sample_interval <= 0.0:
        return list(range(len(times)))

    indices = [0]
    next_sample = float(times[0]) + sample_interval
    for idx in range(1, len(times)):
        if times[idx] + 1e-12 < next_sample:
            continue
        indices.append(idx)
        while next_sample <= times[idx] + 1e-12:
            next_sample += sample_interval
    if indices[-1] != len(times) - 1:
        indices.append(len(times) - 1)
    return indices


def _compose_field(
    row: pd.Series,
    geometry: CircularBasinGeometry,
    playback_mode: str,
    summary: dict[str, Any],
    x: np.ndarray,
    y: np.ndarray,
    radius: np.ndarray,
    mask: np.ndarray,
) -> np.ndarray:
    phi_x, phi_y = shared_modes(x, y, radius)
    field = row["c_x"] * phi_x + row["c_y"] * phi_y

    analyzer_scale = 0.32 if playback_mode == "truth_preserving" else 0.48
    field += analyzer_scale * oriented_local_mode(
        x,
        y,
        geometry.analyzer_positions["A"],
        float(summary["angle_a"]),
        geometry.analyzer_radius,
        row["alpha_a"],
        row["beta_a"],
    )
    field += analyzer_scale * oriented_local_mode(
        x,
        y,
        geometry.analyzer_positions["B"],
        float(summary["angle_b"]),
        geometry.analyzer_radius,
        row["alpha_b"],
        row["beta_b"],
    )

    q_values = np.array([row["q1"], row["q2"], row["q3"], row["q4"]], dtype=float)
    q_scale = float(np.max(np.abs(q_values))) or 1.0
    for q_name, q_value in zip(("q1", "q2", "q3", "q4"), q_values, strict=True):
        field += 0.18 * (q_value / q_scale) * gaussian_mode(
            x,
            y,
            geometry.bay_positions[q_name],
            geometry.bay_radius,
        )

    field += 0.16 * row["o_real"] * annular_mode(x, y, radius, 0.34, 0.05, 1, phase=0.0)
    field += 0.16 * row["o_imag"] * annular_mode(x, y, radius, 0.34, 0.05, 1, phase=math.pi / 2.0)
    field += 0.16 * row["s_real"] * annular_mode(x, y, radius, 0.42, 0.05, 2, phase=math.pi / 4.0)
    field += 0.16 * row["s_imag"] * annular_mode(x, y, radius, 0.42, 0.05, 2, phase=3.0 * math.pi / 4.0)

    detector_scale = 0.30 if playback_mode == "truth_preserving" else 0.42
    for branch in BRANCHES:
        detector_mode = gaussian_mode(x, y, geometry.detector_positions[branch], geometry.detector_radius)
        field += detector_scale * math.sqrt(max(row[f"z_{branch}_abs2"], 0.0)) * detector_mode

    winner = row["winner_so_far"]
    if winner != "none":
        field += 0.12 * row["h"] * annular_mode(x, y, radius, 0.72, 0.04, 1, phase=0.0)
        field += 0.24 * row[f"g_{winner}"] * gaussian_mode(
            x,
            y,
            geometry.detector_positions[winner],
            geometry.detector_radius * 1.2,
        )

    field = np.where(mask, field, np.nan)
    return field


def _frame_image(
    row: pd.Series,
    summary: dict[str, Any],
    geometry: CircularBasinGeometry,
    playback_mode: str,
    x: np.ndarray,
    y: np.ndarray,
    radius: np.ndarray,
    mask: np.ndarray,
) -> np.ndarray:
    field = _compose_field(row, geometry, playback_mode, summary, x, y, radius, mask)

    figure = Figure(figsize=(4.4, 4.8), dpi=96)
    canvas = FigureCanvasAgg(figure)
    ax = figure.subplots()
    ax.set_facecolor("#f4f1e8")
    ax.imshow(
        field,
        extent=(-1.05, 1.05, -1.05, 1.05),
        origin="lower",
        cmap="coolwarm",
        vmin=-1.2,
        vmax=1.2,
    )
    ax.add_patch(Circle((0.0, 0.0), geometry.basin_radius, fill=False, linewidth=2.0, edgecolor="#113355"))

    for label, center in geometry.analyzer_positions.items():
        ax.add_patch(
            Circle(
                center,
                geometry.analyzer_radius,
                fill=False,
                linewidth=1.4,
                edgecolor="#2b6f77",
            )
        )
        ax.text(center[0], center[1] + 0.22, label, ha="center", va="center", fontsize=9, color="#18434a")

    for label, center in geometry.bay_positions.items():
        ax.add_patch(
            Circle(
                center,
                geometry.bay_radius,
                fill=False,
                linewidth=1.0,
                edgecolor="#8a5a44",
            )
        )
        ax.text(center[0], center[1], label.upper(), ha="center", va="center", fontsize=7, color="#6f4330")

    winner = row["winner_so_far"]
    for branch in BRANCHES:
        branch_center = geometry.detector_positions[branch]
        intensity = max(float(row[f"z_{branch}_abs2"]), 0.0)
        face_alpha = min(0.18 + 1.4 * math.sqrt(intensity), 0.92)
        facecolor = "#e16b5b" if branch == winner else "#3c7dcf"
        edgecolor = "#f6c453" if branch == winner else "#163a68"
        ax.add_patch(
            Circle(
                branch_center,
                geometry.detector_radius,
                facecolor=facecolor,
                alpha=face_alpha,
                linewidth=2.0 if branch == winner else 1.2,
                edgecolor=edgecolor,
            )
        )
        ax.text(branch_center[0], branch_center[1], branch.upper(), ha="center", va="center", fontsize=8, color="white")

    ax.text(
        -1.02,
        -1.16,
        (
            f"t={row['t']:.3f}s  winner={winner}  inhibit={row['h']:.3f}\n"
            f"mode={summary['detector_mode']}  trigger={summary['trigger_time'] if math.isfinite(summary['trigger_time']) else float('nan'):.3f}s"
        ),
        ha="left",
        va="top",
        fontsize=8,
        color="#24303f",
    )
    ax.set_xlim(-1.05, 1.05)
    ax.set_ylim(-1.24, 1.05)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("Wavepool Entanglement Playback", fontsize=11, color="#24303f")
    figure.tight_layout(pad=0.35)

    canvas.draw()
    frame = np.asarray(canvas.buffer_rgba())[:, :, :3].copy()
    return frame


def render_playback(
    timeseries: pd.DataFrame,
    summary: dict[str, Any],
    output_path: str | Path,
    playback_mode: str = "truth_preserving",
    fps: int = 30,
    sample_interval: float = 0.01,
) -> dict[str, Any]:
    if playback_mode not in {"truth_preserving", "stylized_explanatory"}:
        raise ValueError(f"unknown playback mode: {playback_mode}")
    if timeseries.empty:
        raise ValueError("cannot render playback for an empty timeseries")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    geometry = default_geometry()
    x, y, radius, mask = build_basin_grid(size=128)
    sampled_indices = _sample_frame_indices(timeseries["t"].to_numpy(dtype=float), sample_interval)

    with imageio.get_writer(
        output,
        fps=fps,
        codec="libx264",
        format="FFMPEG",
        macro_block_size=None,
        pixelformat="yuv420p",
    ) as writer:
        for idx in sampled_indices:
            row = timeseries.iloc[idx]
            writer.append_data(
                _frame_image(
                    row=row,
                    summary=summary,
                    geometry=geometry,
                    playback_mode=playback_mode,
                    x=x,
                    y=y,
                    radius=radius,
                    mask=mask,
                )
            )

    return {
        "winner": summary["winner"],
        "detector_mode": summary["detector_mode"],
        "fps": fps,
        "frame_count": len(sampled_indices),
        "sample_interval": sample_interval,
        "source_rows": int(len(timeseries)),
        "source_duration": float(timeseries["t"].iloc[-1] - timeseries["t"].iloc[0]),
        "playback_mode": playback_mode,
        "output_path": str(output),
    }
