from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np


def fraction_error_metrics(exact: Sequence[float], realized: Sequence[float]) -> dict[str, float | np.ndarray]:
    exact_values = np.asarray(exact, dtype=float)
    realized_values = np.asarray(realized, dtype=float)
    errors = realized_values - exact_values
    return {
        "errors": errors,
        "rms_error": float(np.sqrt(np.mean(errors**2))),
        "max_abs_error": float(np.max(np.abs(errors))),
    }


def finite_export_metrics(branch_powers: Sequence[Sequence[float]]) -> dict[str, bool | float]:
    concatenated = np.concatenate([np.asarray(values, dtype=float).reshape(-1) for values in branch_powers])
    min_power = float(np.min(concatenated)) if concatenated.size else 0.0
    return {
        "finite": bool(np.all(np.isfinite(concatenated))),
        "min_power_w": min_power,
        "nonnegative_with_tolerance": min_power >= -1e-12,
    }


def common_envelope_fidelity_metrics(
    branch_labels: Sequence[str],
    branch_powers: Mapping[str, Sequence[float]],
    exact_weight: Mapping[str, float],
) -> dict[str, float | dict[str, np.ndarray]]:
    gamma: dict[str, np.ndarray] = {}
    valid_labels = [label for label in branch_labels if abs(float(exact_weight[label])) > 1e-12]
    for label in valid_labels:
        gamma[label] = np.asarray(branch_powers[label], dtype=float) / float(exact_weight[label])
    if len(valid_labels) < 2:
        return {
            "gamma": gamma,
            "rms_difference": 0.0,
            "max_abs_difference": 0.0,
        }
    reference = gamma[valid_labels[0]]
    differences = [gamma[label] - reference for label in valid_labels[1:]]
    stacked = np.vstack(differences)
    return {
        "gamma": gamma,
        "rms_difference": float(np.sqrt(np.mean(stacked**2))),
        "max_abs_difference": float(np.max(np.abs(stacked))),
    }


def energy_preservation_metrics(
    time_s: Sequence[float],
    reference_power: Sequence[float],
    candidate_power: Sequence[float],
) -> dict[str, float]:
    values_t = np.asarray(time_s, dtype=float)
    reference = np.asarray(reference_power, dtype=float)
    candidate = np.asarray(candidate_power, dtype=float)
    reference_energy = float(np.trapezoid(reference, x=values_t))
    candidate_energy = float(np.trapezoid(candidate, x=values_t))
    error = candidate_energy - reference_energy
    return {
        "reference_energy": reference_energy,
        "candidate_energy": candidate_energy,
        "abs_error": abs(error),
        "rel_error": abs(error) / max(abs(reference_energy), 1e-18),
    }
