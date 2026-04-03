from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from detector_integration.detectors import latch_first_event, resolve_branch_detector_params, simulate_branch_nucleation, validated_latch_arbiter_config
from detector_integration.sim.metrics import chsh_metrics, four_branch_metrics, two_branch_metrics, winner_frequency_summary

from .export_interface import detector_envelope_sequence
from .four_branch_surrogate import benchmark_four_branch_cases, simulate_four_branch_surrogate
from .two_branch_surrogate import representative_two_branch_cases, simulate_two_branch_surrogate


def _run_handoff_trials(
    surrogate_run: Mapping[str, Any],
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    seed: int,
) -> dict[str, Any]:
    branch_labels = list(surrogate_run["branch_labels"])
    n_branches = len(branch_labels)
    exact_weights = np.array([float(surrogate_run["exact_weight"][label]) for label in branch_labels], dtype=float)
    envelopes = detector_envelope_sequence(surrogate_run)
    rng = np.random.default_rng(seed)
    latch_config = validated_latch_arbiter_config(n_branches)
    winners: list[int] = []
    event_time_rows: list[np.ndarray] = []

    n_trials = int(surrogate_run.get("_n_trials", 0))
    if n_trials <= 0:
        raise ValueError("Surrogate handoff run requires '_n_trials' to be set.")

    for _ in range(n_trials):
        event_times = np.full(n_branches, np.inf, dtype=float)
        for branch_index in range(n_branches):
            branch_rng = np.random.default_rng(int(rng.integers(0, 2**32 - 1)))
            branch_detector = resolve_branch_detector_params(detector_spec, branch_index)
            click_time = simulate_branch_nucleation(branch_detector, 1.0, envelopes[branch_index], branch_rng)
            if click_time is not None:
                event_times[branch_index] = click_time
        latch_result = latch_first_event(event_times, config=latch_config, rng=rng)
        winners.append(int(latch_result["winner_index"]))
        event_time_rows.append(event_times)

    frequency_summary = winner_frequency_summary(winners, n_branches=n_branches)
    metrics = two_branch_metrics(exact_weights, frequency_summary["frequencies"]) if n_branches == 2 else four_branch_metrics(exact_weights, frequency_summary["frequencies"])
    return {
        "exact_weights": exact_weights,
        "empirical_frequencies": frequency_summary["frequencies"],
        "winner_counts": frequency_summary["counts"],
        "decisive_fraction": frequency_summary["decisive_fraction"],
        "timeout_fraction": frequency_summary["timeout_fraction"],
        "metrics": metrics,
        "event_times": np.asarray(event_time_rows, dtype=float),
    }


def run_two_branch_surrogate_handoff(
    state: np.ndarray,
    analyzer,
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    n_trials: int,
    seed: int,
    envelope_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    surrogate = simulate_two_branch_surrogate(state, analyzer, envelope_config=envelope_config)
    surrogate["_n_trials"] = n_trials
    result = _run_handoff_trials(surrogate, detector_spec, seed=seed)
    return {
        "surrogate": surrogate,
        **result,
    }


def run_four_branch_surrogate_handoff(
    *,
    a_deg: float,
    b_deg: float,
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    n_trials: int,
    seed: int,
    state4: np.ndarray | None = None,
    envelope_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    surrogate = simulate_four_branch_surrogate(state4, a_deg=a_deg, b_deg=b_deg, envelope_config=envelope_config)
    surrogate["_n_trials"] = n_trials
    result = _run_handoff_trials(surrogate, detector_spec, seed=seed)
    return {
        "surrogate": surrogate,
        **result,
    }


def run_surrogate_chsh_handoff(
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    n_trials: int,
    seed: int,
    envelope_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    exact_correlators: dict[str, float] = {}
    empirical_correlators: dict[str, float] = {}
    rows: list[dict[str, Any]] = []
    settings = {
        "a0b0": (0.0, 22.5),
        "a0b1": (0.0, -22.5),
        "a1b0": (45.0, 22.5),
        "a1b1": (45.0, -22.5),
    }
    for index, (label, (a_deg, b_deg)) in enumerate(settings.items()):
        result = run_four_branch_surrogate_handoff(
            a_deg=a_deg,
            b_deg=b_deg,
            detector_spec=detector_spec,
            n_trials=n_trials,
            seed=seed + 1_013 * index,
            envelope_config=envelope_config,
        )
        exact_correlators[label] = float(result["metrics"]["correlator_exact"])
        empirical_correlators[label] = float(result["metrics"]["correlator_empirical"])
        rows.append(
            {
                "label": label,
                "a_deg": a_deg,
                "b_deg": b_deg,
                "correlator_exact": result["metrics"]["correlator_exact"],
                "correlator_empirical": result["metrics"]["correlator_empirical"],
                "correlator_error": result["metrics"]["correlator_error"],
                "rms_error": result["metrics"]["rms_error"],
            }
        )
    return {"rows": rows, **chsh_metrics(exact_correlators, empirical_correlators)}


def representative_two_branch_handoff_rows(
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    n_trials: int,
    seed: int,
    envelope_config: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, case in enumerate(representative_two_branch_cases()):
        result = run_two_branch_surrogate_handoff(
            case["state"],
            case["analyzer"],
            detector_spec,
            n_trials=n_trials,
            seed=seed + 97 * index,
            envelope_config=envelope_config,
        )
        rows.append(
            {
                "mode": "two_branch",
                "case": case["case"],
                "exact_weights": result["exact_weights"].tolist(),
                "empirical_frequencies": result["empirical_frequencies"].tolist(),
                "rms_error": float(result["metrics"]["rms_error"]),
                "max_abs_error": float(result["metrics"]["max_abs_error"]),
                "decisive_fraction": float(result["decisive_fraction"]),
            }
        )
    return rows


def benchmark_four_branch_handoff_rows(
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    n_trials: int,
    seed: int,
    envelope_config: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, (label, a_deg, b_deg) in enumerate(benchmark_four_branch_cases()):
        result = run_four_branch_surrogate_handoff(
            a_deg=a_deg,
            b_deg=b_deg,
            detector_spec=detector_spec,
            n_trials=n_trials,
            seed=seed + 131 * index,
            envelope_config=envelope_config,
        )
        rows.append(
            {
                "mode": "four_branch",
                "case": label,
                "exact_weights": result["exact_weights"].tolist(),
                "empirical_frequencies": result["empirical_frequencies"].tolist(),
                "rms_error": float(result["metrics"]["rms_error"]),
                "max_abs_error": float(result["metrics"]["max_abs_error"]),
                "correlator_error": float(result["metrics"]["correlator_error"]),
                "decisive_fraction": float(result["decisive_fraction"]),
            }
        )
    return rows
