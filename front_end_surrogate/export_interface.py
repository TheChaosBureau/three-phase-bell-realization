from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class SurrogateEnvelopeConfig:
    """Behavioral common-envelope configuration for the front-end surrogate."""

    kind: str = "exp_decay"
    duration_s: float = 5.0
    dt_s: float = 1e-4
    peak_power_w: float = 4.0
    decay_tau_s: float = 1.25
    drive_phase_deg: float = 0.0
    load_resistance_ohm: float = 50.0


def resolve_envelope_config(config: Mapping[str, Any] | None) -> SurrogateEnvelopeConfig:
    if config is None:
        return SurrogateEnvelopeConfig()
    return SurrogateEnvelopeConfig(**dict(config))


def build_time_axis(config: SurrogateEnvelopeConfig) -> np.ndarray:
    return np.arange(0.0, config.duration_s + config.dt_s, config.dt_s, dtype=float)


def common_envelope_power(config: SurrogateEnvelopeConfig) -> np.ndarray:
    time_s = build_time_axis(config)
    if config.kind == "constant":
        return np.full_like(time_s, config.peak_power_w, dtype=float)
    if config.kind == "exp_decay":
        return config.peak_power_w * np.exp(-time_s / max(config.decay_tau_s, config.dt_s))
    raise ValueError(f"Unsupported surrogate envelope kind: {config.kind}")


def branch_waveforms_from_power(
    branch_labels: list[str],
    fractions: np.ndarray,
    *,
    config: SurrogateEnvelopeConfig,
) -> dict[str, Any]:
    time_s = build_time_axis(config)
    gamma_t = common_envelope_power(config)
    load = float(config.load_resistance_ohm)
    phase = np.deg2rad(config.drive_phase_deg)
    phase_signs = np.array([1.0 if index % 2 == 0 else -1.0 for index in range(len(branch_labels))], dtype=float)

    branch_voltage_v: dict[str, list[float]] = {}
    branch_current_a: dict[str, list[float]] = {}
    branch_power_w: dict[str, list[float]] = {}
    branch_energy_j: dict[str, float] = {}
    branch_energy_fraction: dict[str, float] = {}

    powers = np.outer(np.asarray(fractions, dtype=float), gamma_t)
    voltages = np.sqrt(np.maximum(powers, 0.0) * load) * np.cos(phase * phase_signs[:, None])
    currents = np.divide(voltages, load, dtype=float)
    energies = np.trapezoid(powers, x=time_s, axis=1)
    total_energy = float(np.sum(energies))

    for index, label in enumerate(branch_labels):
        branch_voltage_v[label] = voltages[index].tolist()
        branch_current_a[label] = currents[index].tolist()
        branch_power_w[label] = powers[index].tolist()
        branch_energy_j[label] = float(energies[index])
        branch_energy_fraction[label] = float(energies[index] / max(total_energy, 1e-18))

    return {
        "branch_labels": branch_labels,
        "time_s": time_s.tolist(),
        "branch_voltage_v": branch_voltage_v,
        "branch_current_a": branch_current_a,
        "branch_power_w": branch_power_w,
        "branch_energy_j": branch_energy_j,
        "branch_energy_fraction": branch_energy_fraction,
        "envelope_config": asdict(config),
    }


def detector_envelope_sequence(surrogate_run: Mapping[str, Any]) -> list[dict[str, Any]]:
    envelope_config = dict(surrogate_run.get("envelope_config", {}))
    if envelope_config:
        detector_dt = max(float(envelope_config["dt_s"]), 5e-3)
        kind = envelope_config["kind"]
        if kind == "constant":
            return [
                {
                    "kind": "constant",
                    "power_scale": float(envelope_config["peak_power_w"]) * float(surrogate_run["branch_energy_fraction"][label]),
                    "dt": detector_dt,
                    "t_max": float(envelope_config["duration_s"]),
                }
                for label in surrogate_run["branch_labels"]
            ]
        if kind == "exp_decay":
            return [
                {
                    "kind": "exp_decay",
                    "power_scale": float(envelope_config["peak_power_w"]) * float(surrogate_run["branch_energy_fraction"][label]),
                    "decay_tau": float(envelope_config["decay_tau_s"]),
                    "dt": detector_dt,
                    "t_max": float(envelope_config["duration_s"]),
                }
                for label in surrogate_run["branch_labels"]
            ]

    time_s = list(surrogate_run["time_s"])
    return [
        {
            "kind": "sampled",
            "time_s": time_s,
            "power_w": list(surrogate_run["branch_power_w"][label]),
            "dt": float(time_s[1] - time_s[0]) if len(time_s) > 1 else 1.0,
            "t_max": float(time_s[-1]) if time_s else 0.0,
        }
        for label in surrogate_run["branch_labels"]
    ]
