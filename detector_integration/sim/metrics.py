from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np

from detector_search.sim.metrics import race_error_metric


def winner_frequency_summary(winners: Sequence[int], n_branches: int) -> dict[str, np.ndarray | int | float]:
    values = np.asarray(winners, dtype=int).reshape(-1)
    timeout_count = int(np.sum(values < 0))
    decisive = values[values >= 0]
    counts = np.bincount(decisive, minlength=n_branches).astype(int)
    decisive_count = int(np.sum(counts))
    frequencies = counts.astype(float) / decisive_count if decisive_count else np.zeros(n_branches, dtype=float)
    total_trials = int(values.size)
    return {
        "counts": counts,
        "frequencies": frequencies,
        "decisive_count": decisive_count,
        "timeout_count": timeout_count,
        "decisive_fraction": decisive_count / max(total_trials, 1),
        "timeout_fraction": timeout_count / max(total_trials, 1),
    }


def two_branch_metrics(exact_weights: Sequence[float], empirical_frequencies: Sequence[float]) -> dict[str, float | np.ndarray]:
    exact = np.asarray(exact_weights, dtype=float).reshape(2)
    empirical = np.asarray(empirical_frequencies, dtype=float).reshape(2)
    errors = empirical - exact
    race_metrics = race_error_metric(exact, empirical)
    return {
        "errors": errors,
        "rms_error": float(np.sqrt(np.mean(errors**2))),
        "max_abs_error": float(np.max(np.abs(errors))),
        "winner_law_error": float(race_metrics["race_rms_error"]),
        "race_rms_error": float(race_metrics["race_rms_error"]),
        "race_max_error": float(race_metrics["race_max_error"]),
    }


def correlator_from_frequencies(frequencies: Sequence[float]) -> float:
    values = np.asarray(frequencies, dtype=float).reshape(4)
    return float(values[0] - values[1] - values[2] + values[3])


def four_branch_metrics(exact_weights: Sequence[float], empirical_frequencies: Sequence[float]) -> dict[str, float | np.ndarray]:
    exact = np.asarray(exact_weights, dtype=float).reshape(4)
    empirical = np.asarray(empirical_frequencies, dtype=float).reshape(4)
    errors = empirical - exact
    correlator_exact = correlator_from_frequencies(exact)
    correlator_empirical = correlator_from_frequencies(empirical)
    return {
        "errors": errors,
        "rms_error": float(np.sqrt(np.mean(errors**2))),
        "max_abs_error": float(np.max(np.abs(errors))),
        "correlator_exact": correlator_exact,
        "correlator_empirical": correlator_empirical,
        "correlator_error": abs(correlator_empirical - correlator_exact),
    }


def chsh_value(correlators: Mapping[str, float]) -> float:
    return float(correlators["a0b0"] + correlators["a0b1"] + correlators["a1b0"] - correlators["a1b1"])


def chsh_metrics(exact_correlators: Mapping[str, float], empirical_correlators: Mapping[str, float]) -> dict[str, float]:
    exact_s = chsh_value(exact_correlators)
    empirical_s = chsh_value(empirical_correlators)
    return {
        "exact_s": exact_s,
        "empirical_s": empirical_s,
        "abs_error": abs(empirical_s - exact_s),
    }
