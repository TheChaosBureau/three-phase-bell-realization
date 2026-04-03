from __future__ import annotations

from typing import Any

import numpy as np

from detector_integration.frontends.four_branch import four_branch_weights
from src.benchmarks import theory_correlator
from src.shared_4tank_core import singlet_state

from .export_interface import branch_waveforms_from_power, resolve_envelope_config
from .metrics import fraction_error_metrics, surrogate_correlator_metrics

BRANCH_LABELS = ["++", "+-", "-+", "--"]


def benchmark_four_branch_cases() -> list[tuple[str, float, float]]:
    return [
        ("case_a", 0.0, 0.0),
        ("case_c", 0.0, 45.0),
        ("a0b0", 0.0, 22.5),
        ("a0b1", 0.0, -22.5),
        ("a1b0", 45.0, 22.5),
        ("a1b1", 45.0, -22.5),
    ]


def simulate_four_branch_surrogate(
    state4: np.ndarray | None = None,
    *,
    a_deg: float,
    b_deg: float,
    envelope_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved = resolve_envelope_config(envelope_config)
    state = singlet_state() if state4 is None else np.asarray(state4, dtype=np.complex128)
    exact = four_branch_weights(state, a_deg=a_deg, b_deg=b_deg)
    export = branch_waveforms_from_power(BRANCH_LABELS, exact, config=resolved)
    surrogate = np.array([export["branch_energy_fraction"][label] for label in BRANCH_LABELS], dtype=float)
    metrics = fraction_error_metrics(exact, surrogate)
    correlator = surrogate_correlator_metrics(exact, surrogate)
    return {
        **export,
        "a_deg": float(a_deg),
        "b_deg": float(b_deg),
        "exact_weight": {label: float(value) for label, value in zip(BRANCH_LABELS, exact, strict=True)},
        "surrogate_fraction": {label: float(value) for label, value in zip(BRANCH_LABELS, surrogate, strict=True)},
        "metrics": {**metrics, **correlator, "theory_correlator": float(theory_correlator(a_deg, b_deg))},
    }
