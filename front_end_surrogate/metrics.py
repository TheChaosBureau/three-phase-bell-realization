from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np


def fraction_error_metrics(exact: Sequence[float], surrogate: Sequence[float]) -> dict[str, float | np.ndarray]:
    exact_values = np.asarray(exact, dtype=float)
    surrogate_values = np.asarray(surrogate, dtype=float)
    errors = surrogate_values - exact_values
    return {
        "errors": errors,
        "rms_error": float(np.sqrt(np.mean(errors**2))),
        "max_abs_error": float(np.max(np.abs(errors))),
    }


def correlator_from_fractions(fractions: Sequence[float]) -> float:
    values = np.asarray(fractions, dtype=float).reshape(4)
    return float(values[0] - values[1] - values[2] + values[3])


def surrogate_correlator_metrics(exact: Sequence[float], surrogate: Sequence[float]) -> dict[str, float]:
    exact_corr = correlator_from_fractions(exact)
    surrogate_corr = correlator_from_fractions(surrogate)
    return {
        "correlator_exact": exact_corr,
        "correlator_surrogate": surrogate_corr,
        "correlator_error": abs(surrogate_corr - exact_corr),
    }


def chsh_value(correlators: Mapping[str, float]) -> float:
    return float(correlators["a0b0"] + correlators["a0b1"] + correlators["a1b0"] - correlators["a1b1"])


def chsh_metrics(exact_correlators: Mapping[str, float], surrogate_correlators: Mapping[str, float]) -> dict[str, float]:
    exact_s = chsh_value(exact_correlators)
    surrogate_s = chsh_value(surrogate_correlators)
    return {
        "exact_s": exact_s,
        "surrogate_s": surrogate_s,
        "abs_error": abs(surrogate_s - exact_s),
    }
