from __future__ import annotations

from typing import Any

import numpy as np

from detector_integration.frontends.two_branch import two_branch_weights
from .export_interface import branch_waveforms_from_power, resolve_envelope_config
from .metrics import fraction_error_metrics


def representative_two_branch_cases() -> list[dict[str, Any]]:
    return [
        {"case": "pole_plus_30", "state": np.array([1.0, 0.0], dtype=np.complex128), "analyzer": 30.0},
        {"case": "equator_x_45", "state": np.array([1.0, 1.0], dtype=np.complex128) / np.sqrt(2.0), "analyzer": 45.0},
        {"case": "phase_y_22_5", "state": np.array([1.0, 1.0j], dtype=np.complex128) / np.sqrt(2.0), "analyzer": 22.5},
    ]


def simulate_two_branch_surrogate(
    state: np.ndarray,
    analyzer,
    *,
    envelope_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved = resolve_envelope_config(envelope_config)
    branch_labels = ["branch_1", "branch_2"]
    exact = two_branch_weights(np.asarray(state, dtype=np.complex128), analyzer)
    export = branch_waveforms_from_power(branch_labels, exact, config=resolved)
    surrogate = np.array([export["branch_energy_fraction"][label] for label in branch_labels], dtype=float)
    metrics = fraction_error_metrics(exact, surrogate)
    return {
        **export,
        "exact_weight": {label: float(value) for label, value in zip(branch_labels, exact, strict=True)},
        "surrogate_fraction": {label: float(value) for label, value in zip(branch_labels, surrogate, strict=True)},
        "metrics": metrics,
    }
