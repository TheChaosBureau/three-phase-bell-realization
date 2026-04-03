from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from detector_integration.sim.metrics import two_branch_metrics

from .boundary_calibration import calibrated_trace, resolved_calibrated_boundary_config
from .boundary_diagnosis import run_trace_handoff


@dataclass(frozen=True)
class ReproCheckConfig:
    min_trials_per_case: int = 500
    target_decisive_count: int = 100
    max_trials_per_case: int = 20_000
    batch_trials: int = 500
    gain: float = 4.0
    exposure_s: float = 5.0


PRIOR_DIAGNOSIS_REFERENCE = {
    "export_mode": "piecewise:linear:20.0ms",
    "gain": 4.0,
    "exposure_s": 5.0,
    "winner_rms_error": 0.0,
    "winner_max_error": 0.0,
    "decisive_fraction": 0.08333333333333333,
}


def resolved_repro_check_config(config: Mapping[str, Any] | None = None) -> ReproCheckConfig:
    if config is None:
        return ReproCheckConfig()
    return ReproCheckConfig(**dict(config))


def _binomial_ci95(p: float, n: int) -> float:
    if n <= 0:
        return float("nan")
    return 1.96 * float(np.sqrt(max(p * (1.0 - p), 0.0) / n))


def rerun_frozen_boundary_case(
    state: np.ndarray,
    analyzer,
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    seed: int,
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repro_config = resolved_repro_check_config(config)
    boundary_config = resolved_calibrated_boundary_config({"gain": repro_config.gain, "exposure_s": repro_config.exposure_s})
    trace = calibrated_trace(state, analyzer, config={"gain": boundary_config.gain, "exposure_s": boundary_config.exposure_s})

    total_trials = 0
    decisive_count = 0
    timeout_count = 0
    winner_counts = np.zeros(2, dtype=int)
    exact_weights = np.array([trace["candidate"]["exact_weight"][label] for label in trace["branch_labels"]], dtype=float)

    batch_index = 0
    while total_trials < repro_config.max_trials_per_case:
        batch_trials = min(int(repro_config.batch_trials), repro_config.max_trials_per_case - total_trials)
        if batch_trials <= 0:
            break
        run = run_trace_handoff(trace, detector_spec, n_trials=batch_trials, seed=seed + 10_003 * batch_index)
        winner_counts += np.asarray(run["winner_counts"], dtype=int)
        batch_decisive = int(np.sum(run["winner_counts"]))
        decisive_count += batch_decisive
        timeout_count += int(batch_trials - batch_decisive)
        total_trials += batch_trials
        batch_index += 1
        if total_trials >= repro_config.min_trials_per_case and decisive_count >= repro_config.target_decisive_count:
            break

    empirical_frequencies = winner_counts.astype(float) / decisive_count if decisive_count else np.zeros_like(exact_weights)
    metrics = two_branch_metrics(exact_weights, empirical_frequencies)
    p1 = float(empirical_frequencies[0]) if decisive_count else 0.0
    decisive_fraction = decisive_count / max(total_trials, 1)
    return {
        "trace": trace,
        "total_trials": int(total_trials),
        "decisive_count": int(decisive_count),
        "timeout_count": int(timeout_count),
        "decisive_fraction": float(decisive_fraction),
        "decisive_fraction_ci95": _binomial_ci95(decisive_fraction, total_trials),
        "winner_counts": winner_counts,
        "empirical_frequencies": empirical_frequencies,
        "exact_weights": exact_weights,
        "metrics": metrics,
        "p1_ci95": _binomial_ci95(p1, decisive_count),
        "winner_rms_error_ci95": _binomial_ci95(p1, decisive_count),
        "sufficient_evidence": bool(decisive_count >= repro_config.target_decisive_count and total_trials >= repro_config.min_trials_per_case),
        "config": repro_config,
    }


def classify_reproducibility(result_rows: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    if not result_rows:
        return {
            "outcome": "inconclusive",
            "next_ticket": "Further trial scaling is needed before the frozen regime can be evaluated.",
        }
    sufficient = all(bool(row["sufficient_evidence"]) for row in result_rows)
    rms_error = float(np.sqrt(np.mean([float(row["rms_error"]) ** 2 for row in result_rows])))
    max_error = float(np.max([float(row["max_abs_error"]) for row in result_rows]))
    if sufficient and rms_error < 0.03 and max_error < 0.05:
        return {
            "outcome": "reproducible",
            "next_ticket": "Keep the frozen calibrated boundary and extend the calibrated physical/SPICE front-end candidate toward the next physical front-end phase.",
        }
    if sufficient:
        return {
            "outcome": "not reproducible",
            "next_ticket": "Treat the earlier best-regime result as a low-statistics fluke and revisit boundary calibration assumptions before scaling.",
        }
    return {
        "outcome": "inconclusive",
        "next_ticket": "Increase total trials or recover a higher-decisive operating point before making a boundary decision.",
    }
