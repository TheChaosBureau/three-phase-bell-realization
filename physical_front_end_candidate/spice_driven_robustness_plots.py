from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np
from matplotlib.figure import Figure


def plot_robustness_metric_sweep(
    rows: list[dict[str, Any]],
    *,
    metric_key: str,
    title: str,
    ylabel: str,
) -> Figure:
    figure = Figure(figsize=(8.4, 4.8), dpi=120)
    axis = figure.subplots()
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["parameter_name"])].append(row)
    for parameter_name, parameter_rows in grouped.items():
        sorted_rows = sorted(parameter_rows, key=lambda row: float(row["level"]))
        axis.plot(
            [float(row["level"]) * 100.0 for row in sorted_rows],
            [float(row[metric_key]) for row in sorted_rows],
            marker="o",
            label=parameter_name.replace("_", " "),
        )
    axis.set_xlabel("Perturbation level (%)")
    axis.set_ylabel(ylabel)
    axis.set_title(title)
    axis.legend(fontsize=8)
    return figure


def plot_boundary_metric_heatmap(
    rows: list[dict[str, Any]],
    *,
    metric_key: str,
    title: str,
) -> Figure:
    gains = sorted({float(row["gain"]) for row in rows})
    exposures = sorted({float(row["exposure_s"]) for row in rows})
    grid = np.full((len(exposures), len(gains)), np.nan, dtype=float)
    for row in rows:
        exposure_index = exposures.index(float(row["exposure_s"]))
        gain_index = gains.index(float(row["gain"]))
        grid[exposure_index, gain_index] = float(row[metric_key])
    figure = Figure(figsize=(6.8, 5.0), dpi=120)
    axis = figure.subplots()
    image = axis.imshow(grid, aspect="auto", origin="lower", cmap="viridis")
    axis.set_xticks(np.arange(len(gains)), [f"{gain:.1f}" for gain in gains])
    axis.set_yticks(np.arange(len(exposures)), [f"{exposure:.1f}" for exposure in exposures])
    axis.set_xlabel("Boundary gain (x)")
    axis.set_ylabel("Boundary exposure (s)")
    axis.set_title(title)
    figure.colorbar(image, ax=axis, shrink=0.9)
    return figure


def plot_sensitivity_ranking(rows: list[dict[str, Any]]) -> Figure:
    figure = Figure(figsize=(8.8, 4.8), dpi=120)
    axes = figure.subplots(1, 2)
    labels = [str(row["class_key"]) for row in rows]
    axes[0].bar(labels, [float(row["worst_damage_score"]) for row in rows], color="#4c78a8")
    axes[0].set_title("Worst-case damage score")
    axes[0].tick_params(axis="x", rotation=20)
    axes[1].bar(labels, [float(row["pass_rate"]) for row in rows], color="#54a24b")
    axes[1].set_title("Pass rate")
    axes[1].tick_params(axis="x", rotation=20)
    figure.suptitle("SPICE-Driven Robustness Sensitivity Ranking")
    figure.tight_layout()
    return figure


def plot_baseline_vs_class_worst_case(
    baseline_metrics: dict[str, Any],
    class_rows: list[dict[str, Any]],
) -> Figure:
    labels = ["baseline"] + [str(row["class_key"]) for row in class_rows]
    winner = [float(baseline_metrics["winner_law_rms_error"])] + [float(row["worst_winner_law_rms_error"]) for row in class_rows]
    pre_click = [float(baseline_metrics["pre_click_transparency_rms_shift"])] + [
        float(row["worst_pre_click_transparency_max_shift"]) for row in class_rows
    ]
    figure = Figure(figsize=(9.2, 4.8), dpi=120)
    axes = figure.subplots(1, 2)
    axes[0].bar(labels, winner, color="#4c78a8")
    axes[0].set_title("Winner-law RMS / class worst case")
    axes[0].tick_params(axis="x", rotation=20)
    axes[1].bar(labels, pre_click, color="#e45756")
    axes[1].set_title("Pre-click shift / class worst case")
    axes[1].tick_params(axis="x", rotation=20)
    figure.tight_layout()
    return figure


def plot_safe_window_pass_counts(rows: list[dict[str, Any]]) -> Figure:
    figure = Figure(figsize=(8.4, 4.8), dpi=120)
    axis = figure.subplots()
    labels = [f"{row['class_key']}:{row['parameter_name']}" for row in rows]
    axis.bar(labels, [int(row["pass_count"]) for row in rows], color="#72b7b2")
    axis.set_ylabel("Passing configurations")
    axis.set_title("Safe operating window counts")
    axis.tick_params(axis="x", rotation=25)
    figure.tight_layout()
    return figure


__all__ = [
    "plot_baseline_vs_class_worst_case",
    "plot_boundary_metric_heatmap",
    "plot_robustness_metric_sweep",
    "plot_safe_window_pass_counts",
    "plot_sensitivity_ranking",
]
