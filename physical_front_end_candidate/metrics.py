from __future__ import annotations

from collections.abc import Sequence

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
