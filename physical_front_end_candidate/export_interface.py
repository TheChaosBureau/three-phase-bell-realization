from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class PhysicalEnvelopeConfig:
    """Common envelope configuration for the physical two-branch candidate."""

    kind: str = "exp_decay"
    duration_s: float = 5.0
    dt_s: float = 1e-4
    peak_drive_v: float = 1.0
    decay_tau_s: float = 1.25


@dataclass(frozen=True)
class HandoffExportConfig:
    """Detector-facing export configuration for physical front-end traces."""

    mode: str = "exponential_fit"
    piecewise_bin_width_s: float = 5e-3
    piecewise_mode: str = "constant"


def resolve_envelope_config(config: Mapping[str, Any] | None) -> PhysicalEnvelopeConfig:
    if config is None:
        return PhysicalEnvelopeConfig()
    return PhysicalEnvelopeConfig(**dict(config))


def resolve_handoff_export_config(config: Mapping[str, Any] | None) -> HandoffExportConfig:
    if config is None:
        return HandoffExportConfig()
    return HandoffExportConfig(**dict(config))


def build_time_axis(config: PhysicalEnvelopeConfig) -> np.ndarray:
    return np.arange(0.0, config.duration_s + config.dt_s, config.dt_s, dtype=float)


def amplitude_envelope(config: PhysicalEnvelopeConfig) -> np.ndarray:
    time_s = build_time_axis(config)
    if config.kind == "constant":
        return np.full_like(time_s, config.peak_drive_v, dtype=float)
    if config.kind == "exp_decay":
        return config.peak_drive_v * np.exp(-0.5 * time_s / max(config.decay_tau_s, config.dt_s))
    raise ValueError(f"Unsupported physical envelope kind: {config.kind}")


def _sampled_envelope(time_s: Sequence[float], power_w: Sequence[float], *, dt: float) -> dict[str, Any]:
    values_t = np.asarray(time_s, dtype=float).reshape(-1)
    values_p = np.asarray(power_w, dtype=float).reshape(-1)
    if values_t.size != values_p.size:
        raise ValueError("time_s and power_w must have matching lengths.")
    return {
        "kind": "sampled",
        "time_s": values_t.tolist(),
        "power_w": values_p.tolist(),
        "dt": float(dt),
        "t_max": float(values_t[-1]) if values_t.size else 0.0,
    }


def _sampled_linear_envelope(time_s: Sequence[float], power_w: Sequence[float], *, dt: float) -> dict[str, Any]:
    values_t = np.asarray(time_s, dtype=float).reshape(-1)
    values_p = np.asarray(power_w, dtype=float).reshape(-1)
    if values_t.size != values_p.size:
        raise ValueError("time_s and power_w must have matching lengths.")
    return {
        "kind": "sampled_linear",
        "time_s": values_t.tolist(),
        "power_w": values_p.tolist(),
        "dt": float(dt),
        "t_max": float(values_t[-1]) if values_t.size else 0.0,
    }


def _piecewise_edges(time_s: np.ndarray, bin_width_s: float) -> np.ndarray:
    width = max(float(bin_width_s), 1e-12)
    start = float(time_s[0])
    end = float(time_s[-1])
    edges = np.arange(start, end + width, width, dtype=float)
    if edges.size < 2 or edges[-1] < end:
        edges = np.append(edges, end)
    else:
        edges[-1] = end
    return edges


def _piecewise_constant_segments(time_s: np.ndarray, power_w: np.ndarray, bin_width_s: float) -> tuple[np.ndarray, np.ndarray]:
    edges = _piecewise_edges(time_s, bin_width_s)
    segment_times: list[float] = []
    segment_powers: list[float] = []
    for start, end in zip(edges[:-1], edges[1:], strict=True):
        start_idx = int(np.searchsorted(time_s, start, side="left"))
        end_idx = int(np.searchsorted(time_s, end, side="left"))
        if end_idx <= start_idx:
            end_idx = min(start_idx + 1, time_s.size)
        segment_times.append(float(start))
        segment_powers.append(float(np.mean(power_w[start_idx:end_idx])))
    return np.asarray(segment_times, dtype=float), np.asarray(segment_powers, dtype=float)


def _piecewise_linear_knots(time_s: np.ndarray, power_w: np.ndarray, bin_width_s: float) -> tuple[np.ndarray, np.ndarray]:
    edges = _piecewise_edges(time_s, bin_width_s)
    centers = 0.5 * (edges[:-1] + edges[1:])
    knot_powers = []
    for start, end in zip(edges[:-1], edges[1:], strict=True):
        start_idx = int(np.searchsorted(time_s, start, side="left"))
        end_idx = int(np.searchsorted(time_s, end, side="left"))
        if end_idx <= start_idx:
            end_idx = min(start_idx + 1, time_s.size)
        knot_powers.append(float(np.mean(power_w[start_idx:end_idx])))
    knot_times = np.concatenate(([float(time_s[0])], centers, [float(time_s[-1])]))
    knot_values = np.concatenate(([float(power_w[0])], np.asarray(knot_powers, dtype=float), [float(power_w[-1])]))
    return knot_times, knot_values


def export_mode_slug(config: HandoffExportConfig) -> str:
    if config.mode != "piecewise_envelope":
        return config.mode
    bin_ms = 1_000.0 * float(config.piecewise_bin_width_s)
    return f"{config.mode}_{config.piecewise_mode}_{bin_ms:.3f}ms".replace(".", "p")


def build_detector_handoff_envelopes(
    branch_power_w: Mapping[str, Sequence[float]],
    *,
    time_s: Sequence[float],
    branch_labels: list[str],
    envelope_config: PhysicalEnvelopeConfig,
    export_config: HandoffExportConfig | Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    resolved_export = resolve_handoff_export_config(export_config if isinstance(export_config, Mapping) else asdict(export_config) if export_config is not None else None)
    sampled_time = np.asarray(time_s, dtype=float).reshape(-1)
    detector_dt = max(float(envelope_config.dt_s), 5e-3)

    if resolved_export.mode == "direct_trace":
        return [
            _sampled_envelope(sampled_time, branch_power_w[label], dt=float(sampled_time[1] - sampled_time[0]) if sampled_time.size > 1 else detector_dt)
            for label in branch_labels
        ]

    if resolved_export.mode == "piecewise_envelope":
        envelopes: list[dict[str, Any]] = []
        for label in branch_labels:
            branch_values = np.asarray(branch_power_w[label], dtype=float).reshape(-1)
            if resolved_export.piecewise_mode == "constant":
                piece_time, piece_power = _piecewise_constant_segments(sampled_time, branch_values, resolved_export.piecewise_bin_width_s)
                envelopes.append(_sampled_envelope(piece_time, piece_power, dt=max(float(resolved_export.piecewise_bin_width_s), detector_dt)))
            elif resolved_export.piecewise_mode == "linear":
                knot_time, knot_power = _piecewise_linear_knots(sampled_time, branch_values, resolved_export.piecewise_bin_width_s)
                envelopes.append(
                    _sampled_linear_envelope(
                        knot_time,
                        knot_power,
                        dt=max(min(float(resolved_export.piecewise_bin_width_s) / 8.0, detector_dt), float(envelope_config.dt_s)),
                    )
                )
            else:
                raise ValueError(f"Unsupported piecewise mode: {resolved_export.piecewise_mode}")
        return envelopes

    if resolved_export.mode == "exponential_fit":
        peak_power = {label: float(np.max(branch_power_w[label])) for label in branch_labels}
        return [
            {
                "kind": "exp_decay",
                "power_scale": peak_power[label],
                "decay_tau": float(envelope_config.decay_tau_s),
                "dt": detector_dt,
                "t_max": float(envelope_config.duration_s),
            }
            for label in branch_labels
        ]

    raise ValueError(f"Unsupported handoff export mode: {resolved_export.mode}")


def detector_export_from_power(
    branch_power_w: Mapping[str, Sequence[float]],
    *,
    branch_labels: list[str],
    envelope_config: PhysicalEnvelopeConfig,
) -> list[dict[str, Any]]:
    return build_detector_handoff_envelopes(
        branch_power_w,
        time_s=build_time_axis(envelope_config),
        branch_labels=branch_labels,
        envelope_config=envelope_config,
        export_config=HandoffExportConfig(mode="exponential_fit"),
    )


def render_envelope_trace(envelope: Mapping[str, Any], sample_time_s: Sequence[float]) -> np.ndarray:
    sample_time = np.asarray(sample_time_s, dtype=float).reshape(-1)
    kind = str(envelope["kind"])
    if kind == "constant":
        return np.full_like(sample_time, float(envelope["power_scale"]), dtype=float)
    if kind == "exp_decay":
        tau = max(float(envelope["decay_tau"]), 1e-12)
        return float(envelope["power_scale"]) * np.exp(-sample_time / tau)
    if kind == "sampled":
        knot_time = np.asarray(envelope["time_s"], dtype=float).reshape(-1)
        knot_power = np.asarray(envelope["power_w"], dtype=float).reshape(-1)
        indices = np.searchsorted(knot_time, sample_time, side="right") - 1
        indices = np.clip(indices, 0, knot_power.size - 1)
        return knot_power[indices]
    if kind == "sampled_linear":
        knot_time = np.asarray(envelope["time_s"], dtype=float).reshape(-1)
        knot_power = np.asarray(envelope["power_w"], dtype=float).reshape(-1)
        return np.interp(sample_time, knot_time, knot_power)
    raise ValueError(f"Unsupported detector envelope kind: {kind}")


def render_envelope_traces(
    detector_envelopes: Sequence[Mapping[str, Any]],
    *,
    sample_time_s: Sequence[float],
    branch_labels: list[str],
) -> dict[str, list[float]]:
    return {
        label: render_envelope_trace(detector_envelopes[index], sample_time_s).tolist()
        for index, label in enumerate(branch_labels)
    }


def export_contract(
    *,
    branch_labels: list[str],
    time_s: np.ndarray,
    branch_voltage_v: dict[str, np.ndarray],
    branch_current_a: dict[str, np.ndarray],
    branch_power_w: dict[str, np.ndarray],
    branch_energy_j: dict[str, float],
    branch_energy_fraction: dict[str, float],
    exact_weight: dict[str, float],
    envelope_config: PhysicalEnvelopeConfig,
) -> dict[str, Any]:
    return {
        "branch_labels": branch_labels,
        "time_s": time_s.tolist(),
        "branch_voltage_v": {label: branch_voltage_v[label].tolist() for label in branch_labels},
        "branch_current_a": {label: branch_current_a[label].tolist() for label in branch_labels},
        "branch_power_w": {label: branch_power_w[label].tolist() for label in branch_labels},
        "branch_energy_j": branch_energy_j,
        "branch_energy_fraction": branch_energy_fraction,
        "exact_weight": exact_weight,
        "envelope_config": asdict(envelope_config),
    }
