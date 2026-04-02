from __future__ import annotations

import math
from typing import Sequence

import numpy as np
from scipy import stats


def fit_rate_vs_power(P_values: Sequence[float], rate_values: Sequence[float]) -> dict[str, float | np.ndarray]:
    """
    Fit lambda(P) = lambda_dark + alpha * P and return residual metrics.
    """
    power = np.asarray(P_values, dtype=float)
    rates = np.asarray(rate_values, dtype=float)
    design = np.column_stack([np.ones_like(power), power])
    coeffs, *_ = np.linalg.lstsq(design, rates, rcond=None)
    fit = design @ coeffs
    scale_floor = 0.1 * max(float(np.max(np.abs(rates))), float(np.max(np.abs(fit))), 1e-9)
    denom = np.maximum(np.maximum(np.abs(rates), np.abs(fit)), scale_floor)
    rel_residuals = (rates - fit) / denom
    return {
        "lambda_dark_fit": float(coeffs[0]),
        "alpha_fit": float(coeffs[1]),
        "fit_values": fit,
        "residuals": rates - fit,
        "relative_residuals": rel_residuals,
        "linearity_rms_rel": float(np.sqrt(np.mean(rel_residuals**2))),
        "linearity_max_rel": float(np.max(np.abs(rel_residuals))),
    }


def waiting_time_metrics(click_times: Sequence[float]) -> dict[str, float]:
    """
    Compare observed waiting times to an exponential distribution with matched mean.
    """
    times = np.asarray(click_times, dtype=float)
    if times.size == 0:
        return {
            "mean": math.inf,
            "variance": math.inf,
            "coefficient_of_variation": math.inf,
            "ks_distance": 1.0,
            "waiting_time_penalty": 10.0,
        }

    mean = float(np.mean(times))
    variance = float(np.var(times))
    std = float(np.std(times))
    coefficient_of_variation = std / max(mean, 1e-12)
    ks_distance = float(stats.kstest(times, stats.expon(scale=mean).cdf).statistic)
    penalty = abs(coefficient_of_variation - 1.0) + ks_distance
    return {
        "mean": mean,
        "variance": variance,
        "coefficient_of_variation": coefficient_of_variation,
        "ks_distance": ks_distance,
        "waiting_time_penalty": penalty,
    }


def race_error_metric(target_probs: Sequence[float], empirical_probs: Sequence[float]) -> dict[str, float | np.ndarray]:
    """
    Measure winner-probability deviation from the race-law target.
    """
    target = np.asarray(target_probs, dtype=float)
    empirical = np.asarray(empirical_probs, dtype=float)
    errors = empirical - target
    return {
        "errors": errors,
        "race_rms_error": float(np.sqrt(np.mean(errors**2))),
        "race_max_error": float(np.max(np.abs(errors))),
    }
