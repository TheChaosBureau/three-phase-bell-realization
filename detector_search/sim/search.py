from __future__ import annotations

import csv
import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from detector_search.config import DEFAULT_SEARCH_CONFIG, SearchConfig
from detector_search.models.base import DetectorModel, ParamGridValue

from .metrics import (
    branch_asymmetry_metrics,
    fit_rate_vs_power,
    race_error_metric,
    waiting_time_metrics,
)
from .race import simulate_many_races
from .single_branch import simulate_many_trials


def _sample_param_value(spec: ParamGridValue, rng) -> float:
    if isinstance(spec, list):
        return float(rng.choice(spec))
    if isinstance(spec, tuple):
        if len(spec) == 3 and spec[2] == "log":
            low, high, _ = spec
            return float(np.exp(rng.uniform(np.log(low), np.log(high))))
        if len(spec) == 2:
            low, high = spec
            return float(rng.uniform(low, high))
        return float(rng.choice(spec))
    raise TypeError(f"Unsupported parameter grid specification: {spec!r}")


def sample_param_sets(
    param_grid: Mapping[str, ParamGridValue],
    n_samples: int,
    rng,
) -> list[dict[str, float]]:
    """
    Draw parameter sets from simple uniform, log-uniform, or discrete ranges.
    """
    param_sets: list[dict[str, float]] = []
    for _ in range(n_samples):
        params = {name: _sample_param_value(spec, rng) for name, spec in param_grid.items()}
        param_sets.append(params)
    return param_sets


def _seed_for(base_seed: int, *parts: Any) -> int:
    payload = "|".join([str(base_seed), *(str(part) for part in parts)]).encode("utf-8")
    digest = hashlib.blake2s(payload, digest_size=4).digest()
    return int.from_bytes(digest, byteorder="big", signed=False)


def perturb_params(params: Mapping[str, float], level: float, sign: float) -> dict[str, float]:
    """
    Apply a simple multiplicative mismatch to numeric parameters.
    """
    perturbed: dict[str, float] = {}
    factor = 1.0 + sign * level
    probability_like = {"p_trig"}
    non_negative_like = {
        "lambda_dark",
        "alpha",
        "dead_time",
        "eps_event",
        "gain_P",
        "leak",
        "sigma",
        "threshold",
    }

    for name, value in params.items():
        new_value = value * factor if value != 0.0 else value
        if name in probability_like:
            new_value = min(max(new_value, 0.0), 1.0)
        elif name in non_negative_like:
            new_value = max(new_value, 0.0)
        perturbed[name] = new_value
    return perturbed


def dark_count_penalty(lambda_dark_fit: float) -> float:
    return max(lambda_dark_fit, 0.0)


def composite_score(metrics: Mapping[str, float], weights: Mapping[str, float] | None = None) -> float:
    active_weights = DEFAULT_SEARCH_CONFIG.score_weights if weights is None else weights
    return float(
        active_weights["linearity_rms_rel"] * metrics["linearity_rms_rel"]
        + active_weights["race_rms_error"] * metrics["race_rms_error"]
        + active_weights["dark_penalty"] * metrics["dark_penalty"]
        + active_weights["waiting_time_penalty"] * metrics["waiting_time_penalty"]
        + active_weights["mismatch_penalty"] * metrics["mismatch_penalty"]
    )


def evaluate_candidate(
    model: DetectorModel,
    params: dict[str, float],
    config: SearchConfig = DEFAULT_SEARCH_CONFIG,
) -> dict[str, Any]:
    """
    Run rate, race, waiting-time, and mismatch scans for one candidate.
    """
    rate_rows: list[dict[str, Any]] = []
    for index, power in enumerate(config.p_scan):
        row = simulate_many_trials(
            model,
            params=params,
            P_abs=power,
            n_trials=config.n_rate_trials,
            dt=config.dt,
            t_max=config.t_max,
            seed=_seed_for(config.seed, model.name, "rate", index, power, tuple(sorted(params.items()))),
        )
        rate_rows.append({"power": power, **row})

    rate_fit = fit_rate_vs_power(
        [row["power"] for row in rate_rows],
        [float(row["rate_estimate"]) for row in rate_rows],
    )

    waiting_rows: list[dict[str, Any]] = []
    for index, power in enumerate(config.waiting_time_powers):
        row = simulate_many_trials(
            model,
            params=params,
            P_abs=power,
            n_trials=config.n_rate_trials,
            dt=config.dt,
            t_max=config.t_max,
            seed=_seed_for(config.seed, model.name, "waiting", index, power, tuple(sorted(params.items()))),
        )
        metrics = waiting_time_metrics(row["click_times"])
        waiting_rows.append({"power": power, **metrics, "n_clicks": row["n_clicks"]})

    waiting_penalty = float(np.mean([row["waiting_time_penalty"] for row in waiting_rows]))

    race_rows: list[dict[str, Any]] = []
    target_probs: list[float] = []
    empirical_probs: list[float] = []
    for index, (P1, P2) in enumerate(config.race_pairs):
        row = simulate_many_races(
            model,
            params1=params,
            params2=params,
            P1=P1,
            P2=P2,
            n_trials=config.n_race_trials,
            dt=config.dt,
            t_max=config.t_max,
            seed=_seed_for(config.seed, model.name, "race", index, P1, P2, tuple(sorted(params.items()))),
        )
        target = P1 / (P1 + P2)
        empirical = float(row["p1_win"])
        target_probs.append(target)
        empirical_probs.append(empirical)
        race_rows.append({"P1": P1, "P2": P2, "target_p1": target, "empirical_p1": empirical, **row})

    race_metrics = race_error_metric(target_probs, empirical_probs)
    asymmetry_metrics = branch_asymmetry_metrics(target_probs, empirical_probs)

    mismatch_rows: list[dict[str, Any]] = []
    mismatch_errors: list[float] = []
    for level in config.mismatch_levels:
        params_low = perturb_params(params, level=level, sign=-1.0)
        params_high = perturb_params(params, level=level, sign=1.0)
        level_errors: list[float] = []
        for index, (P1, P2) in enumerate(config.race_pairs):
            row = simulate_many_races(
                model,
                params1=params_high,
                params2=params_low,
                P1=P1,
                P2=P2,
                n_trials=config.n_race_trials,
                dt=config.dt,
                t_max=config.t_max,
                seed=_seed_for(config.seed, model.name, "mismatch", level, index, P1, P2, tuple(sorted(params.items()))),
            )
            target = P1 / (P1 + P2)
            error = abs(float(row["p1_win"]) - target)
            level_errors.append(error)
        mismatch_error = max(level_errors) if level_errors else math.inf
        mismatch_rows.append({"level": level, "worst_error": mismatch_error})
        mismatch_errors.append(mismatch_error)

    mismatch_penalty = max(mismatch_errors) if mismatch_errors else math.inf
    dark_penalty = dark_count_penalty(float(rate_fit["lambda_dark_fit"]))

    summary_metrics = {
        "linearity_rms_rel": float(rate_fit["linearity_rms_rel"]),
        "linearity_max_rel": float(rate_fit["linearity_max_rel"]),
        "lambda_dark_fit": float(rate_fit["lambda_dark_fit"]),
        "alpha_fit": float(rate_fit["alpha_fit"]),
        "race_rms_error": float(race_metrics["race_rms_error"]),
        "race_max_error": float(race_metrics["race_max_error"]),
        "branch_asymmetry_amplification": float(asymmetry_metrics["branch_asymmetry_amplification"]),
        "branch_asymmetry_worst": float(asymmetry_metrics["branch_asymmetry_worst"]),
        "dark_penalty": dark_penalty,
        "waiting_time_penalty": waiting_penalty,
        "mismatch_penalty": mismatch_penalty,
    }
    summary_metrics["score"] = composite_score(summary_metrics, weights=config.score_weights)

    return {
        "model": model.name,
        "params": dict(params),
        "metrics": summary_metrics,
        "rate_scan": rate_rows,
        "waiting_time_rows": waiting_rows,
        "race_rows": race_rows,
        "mismatch_rows": mismatch_rows,
    }


def rank_candidates(results: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """
    Sort candidate evaluations by composite score.
    """
    return sorted(results, key=lambda row: float(row["metrics"]["score"]))


def search_model_family(
    model: DetectorModel,
    n_samples: int,
    config: SearchConfig = DEFAULT_SEARCH_CONFIG,
) -> list[dict[str, Any]]:
    """
    Sample and evaluate candidates for one model family.
    """
    rng = np.random.default_rng(config.seed)
    candidates = sample_param_sets(model.default_param_grid(), n_samples=n_samples, rng=rng)
    results = [evaluate_candidate(model, params=params, config=config) for params in candidates]
    return [dict(result) for result in rank_candidates(results)]


def save_results_jsonl(results: Sequence[Mapping[str, Any]], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in results:
            handle.write(json.dumps(row, default=_json_default))
            handle.write("\n")


def save_results_csv(results: Sequence[Mapping[str, Any]], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "model",
        "score",
        "lambda_dark_fit",
        "alpha_fit",
        "linearity_rms_rel",
        "race_rms_error",
        "waiting_time_penalty",
        "mismatch_penalty",
        "params_json",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            metrics = row["metrics"]
            writer.writerow(
                {
                    "model": row["model"],
                    "score": metrics["score"],
                    "lambda_dark_fit": metrics["lambda_dark_fit"],
                    "alpha_fit": metrics["alpha_fit"],
                    "linearity_rms_rel": metrics["linearity_rms_rel"],
                    "race_rms_error": metrics["race_rms_error"],
                    "waiting_time_penalty": metrics["waiting_time_penalty"],
                    "mismatch_penalty": metrics["mismatch_penalty"],
                    "params_json": json.dumps(row["params"], sort_keys=True),
                }
            )


def _json_default(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.integer):
        return int(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
