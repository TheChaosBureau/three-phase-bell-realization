from __future__ import annotations

from collections.abc import Mapping
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


def resolve_envelope_config(config: Mapping[str, Any] | None) -> PhysicalEnvelopeConfig:
    if config is None:
        return PhysicalEnvelopeConfig()
    return PhysicalEnvelopeConfig(**dict(config))


def build_time_axis(config: PhysicalEnvelopeConfig) -> np.ndarray:
    return np.arange(0.0, config.duration_s + config.dt_s, config.dt_s, dtype=float)


def amplitude_envelope(config: PhysicalEnvelopeConfig) -> np.ndarray:
    time_s = build_time_axis(config)
    if config.kind == "constant":
        return np.full_like(time_s, config.peak_drive_v, dtype=float)
    if config.kind == "exp_decay":
        return config.peak_drive_v * np.exp(-0.5 * time_s / max(config.decay_tau_s, config.dt_s))
    raise ValueError(f"Unsupported physical envelope kind: {config.kind}")


def detector_export_from_power(
    branch_power_w: Mapping[str, list[float]],
    *,
    branch_labels: list[str],
    envelope_config: PhysicalEnvelopeConfig,
) -> list[dict[str, Any]]:
    detector_dt = max(float(envelope_config.dt_s), 5e-3)
    if envelope_config.kind == "exp_decay":
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
    if envelope_config.kind == "constant":
        mean_power = {label: float(np.mean(branch_power_w[label])) for label in branch_labels}
        return [
            {
                "kind": "constant",
                "power_scale": mean_power[label],
                "dt": detector_dt,
                "t_max": float(envelope_config.duration_s),
            }
            for label in branch_labels
        ]

    time_s = build_time_axis(envelope_config).tolist()
    return [
        {
            "kind": "sampled",
            "time_s": time_s,
            "power_w": list(branch_power_w[label]),
            "dt": float(time_s[1] - time_s[0]) if len(time_s) > 1 else detector_dt,
            "t_max": float(time_s[-1]) if time_s else 0.0,
        }
        for label in branch_labels
    ]


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
