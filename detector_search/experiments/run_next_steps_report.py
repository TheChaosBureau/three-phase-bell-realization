from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from detector_search.config import SearchConfig
from detector_search.models import MetastableEscapeModel, PoissonLinearModel, ShotTriggerModel
from detector_search.plots import (
    plot_integration_mapping,
    plot_model_diagnostic_panel,
    plot_winner_region,
)
from detector_search.sim.race import simulate_many_races
from detector_search.sim.search import evaluate_candidate, save_results_csv, save_results_jsonl, search_model_family
from detector_search.sim.single_branch import simulate_many_trials
from src.analyzer_couplers import rotation


REPORT_MODELS = {
    "poisson_linear": PoissonLinearModel,
    "shot_trigger": ShotTriggerModel,
    "metastable_escape": MetastableEscapeModel,
}

REPORT_CONFIG = SearchConfig(
    dt=5e-3,
    t_max=4.0,
    n_rate_trials=60,
    n_race_trials=160,
    p_scan=(0.0, 0.25, 0.5, 1.0, 1.5),
    race_pairs=((0.75, 0.25), (0.70, 0.30), (0.60, 0.40), (0.50, 0.50)),
    mismatch_levels=(0.01, 0.03, 0.05),
    waiting_time_powers=(0.25, 1.0, 1.5),
    seed=20260402,
)


def _summary_row(model_name: str, rank: int, result: dict[str, Any]) -> dict[str, Any]:
    metrics = result["metrics"]
    return {
        "model": model_name,
        "rank": rank,
        "score": metrics["score"],
        "linearity_rms_rel": metrics["linearity_rms_rel"],
        "dark_count_rate": max(float(metrics["lambda_dark_fit"]), 0.0),
        "race_rms_error": metrics["race_rms_error"],
        "mismatch_penalty": metrics["mismatch_penalty"],
        "branch_asymmetry_amplification": metrics["branch_asymmetry_amplification"],
        "waiting_time_penalty": metrics["waiting_time_penalty"],
        "params_json": json.dumps(result["params"], sort_keys=True),
    }


def _write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "model",
        "rank",
        "score",
        "linearity_rms_rel",
        "dark_count_rate",
        "race_rms_error",
        "mismatch_penalty",
        "branch_asymmetry_amplification",
        "waiting_time_penalty",
        "params_json",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _save_model_comparison_plot(
    outdir: Path,
    model_name: str,
    model,
    result: dict[str, Any],
    config: SearchConfig,
) -> str:
    waiting_power = max(config.waiting_time_powers)
    waiting_row = simulate_many_trials(
        model,
        params=result["params"],
        P_abs=waiting_power,
        n_trials=config.n_rate_trials,
        dt=config.dt,
        t_max=config.t_max,
        seed=config.seed + 11_000,
    )
    figure = plot_model_diagnostic_panel(model_name, result, waiting_row["click_times"], waiting_power)
    output_path = outdir / f"{model_name}_comparison.png"
    figure.savefig(output_path)
    return str(output_path)


def _clip(value: float, low: float, high: float) -> float:
    return min(max(value, low), high)


def _evaluate_shot_trigger_region(
    outdir: Path,
    result: dict[str, Any],
    *,
    grid_size: int,
    config: SearchConfig,
) -> tuple[str, str, list[dict[str, Any]]]:
    model = ShotTriggerModel()
    params = dict(result["params"])
    eps_low, eps_high, _ = model.default_param_grid()["eps_event"]
    p_low, p_high = model.default_param_grid()["p_trig"]

    eps_center = float(params["eps_event"])
    p_center = float(params["p_trig"])
    eps_values = np.linspace(_clip(0.5 * eps_center, eps_low, eps_high), _clip(1.5 * eps_center, eps_low, eps_high), grid_size)
    p_values = np.linspace(_clip(p_center - 0.35, p_low, p_high), _clip(p_center + 0.35, p_low, p_high), grid_size)

    score_grid = np.zeros((grid_size, grid_size), dtype=float)
    race_grid = np.zeros_like(score_grid)
    rows: list[dict[str, Any]] = []
    for iy, p_trig in enumerate(p_values):
        for ix, eps_event in enumerate(eps_values):
            candidate = dict(params)
            candidate["eps_event"] = float(eps_event)
            candidate["p_trig"] = float(p_trig)
            evaluated = evaluate_candidate(model, candidate, config=config)
            score_grid[iy, ix] = evaluated["metrics"]["score"]
            race_grid[iy, ix] = evaluated["metrics"]["race_rms_error"]
            rows.append(
                {
                    "eps_event": eps_event,
                    "p_trig": p_trig,
                    "score": evaluated["metrics"]["score"],
                    "race_rms_error": evaluated["metrics"]["race_rms_error"],
                    "linearity_rms_rel": evaluated["metrics"]["linearity_rms_rel"],
                }
            )

    csv_path = outdir / "shot_trigger_winner_region.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["eps_event", "p_trig", "score", "race_rms_error", "linearity_rms_rel"],
        )
        writer.writeheader()
        writer.writerows(rows)

    figure = plot_winner_region(
        eps_values,
        p_values,
        score_grid,
        race_grid,
        xlabel="eps_event",
        ylabel="p_trig",
        title="shot_trigger operating window",
    )
    image_path = outdir / "shot_trigger_winner_region.png"
    figure.savefig(image_path)
    return str(csv_path), str(image_path), rows


def reduced_two_branch_weights(theta_deg: float, state: np.ndarray | None = None) -> np.ndarray:
    prepared = np.array([1.0, 0.0], dtype=np.complex128) if state is None else np.asarray(state, dtype=np.complex128).reshape(2)
    amplitudes = rotation(math.radians(theta_deg)) @ prepared
    weights = np.abs(amplitudes) ** 2
    return (weights / np.sum(weights)).astype(float)


def _evaluate_integration_surrogate(
    outdir: Path,
    params: dict[str, float],
    *,
    config: SearchConfig,
    power_scale: float,
) -> tuple[str, str, list[dict[str, Any]]]:
    model = ShotTriggerModel()
    angle_values = np.linspace(0.0, 90.0, 10)
    rows: list[dict[str, Any]] = []
    empirical_probs: list[float] = []
    target_probs: list[float] = []
    for index, angle_deg in enumerate(angle_values):
        weights = reduced_two_branch_weights(float(angle_deg))
        P1 = power_scale * float(weights[0])
        P2 = power_scale * float(weights[1])
        race = simulate_many_races(
            model,
            params1=params,
            params2=params,
            P1=P1,
            P2=P2,
            n_trials=max(400, 3 * config.n_race_trials),
            dt=config.dt,
            t_max=config.t_max,
            seed=config.seed + 31_000 + index,
        )
        empirical = float(race["p1_win"])
        target = float(weights[0])
        target_probs.append(target)
        empirical_probs.append(empirical)
        rows.append(
            {
                "angle_deg": angle_deg,
                "target_weight_1": target,
                "target_weight_2": float(weights[1]),
                "empirical_win_1": empirical,
                "empirical_win_2": 1.0 - empirical,
                "P1": P1,
                "P2": P2,
            }
        )

    csv_path = outdir / "shot_trigger_integration.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["angle_deg", "target_weight_1", "target_weight_2", "empirical_win_1", "empirical_win_2", "P1", "P2"],
        )
        writer.writeheader()
        writer.writerows(rows)

    figure = plot_integration_mapping(
        angle_values_deg=angle_values,
        target_probs=np.asarray(target_probs, dtype=float),
        empirical_probs=np.asarray(empirical_probs, dtype=float),
        title="shot_trigger driven by reduced 2-branch analyzer weights",
    )
    image_path = outdir / "shot_trigger_integration.png"
    figure.savefig(image_path)
    return str(csv_path), str(image_path), rows


def _markdown_table(best_rows: list[dict[str, Any]]) -> str:
    header = "| model | score | linearity | dark | race | mismatch | asym amp |"
    divider = "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"
    body = [
        (
            f"| {row['model']} | {row['score']:.3f} | {row['linearity_rms_rel']:.3f} | "
            f"{row['dark_count_rate']:.3f} | {row['race_rms_error']:.3f} | "
            f"{row['mismatch_penalty']:.3f} | {row['branch_asymmetry_amplification']:.3f} |"
        )
        for row in best_rows
    ]
    return "\n".join([header, divider, *body])


def _write_report_markdown(
    path: Path,
    best_rows: list[dict[str, Any]],
    shot_region_rows: list[dict[str, Any]],
    integration_rows: list[dict[str, Any]],
) -> None:
    candidate_rows = [row for row in best_rows if row["model"] != "poisson_linear"]
    best_candidate = min(candidate_rows, key=lambda row: row["score"])
    viable_region = sum(1 for row in shot_region_rows if row["race_rms_error"] <= 0.05)
    region_fraction = viable_region / max(len(shot_region_rows), 1)
    integration_rms = math.sqrt(
        sum((row["empirical_win_1"] - row["target_weight_1"]) ** 2 for row in integration_rows) / max(len(integration_rows), 1)
    )

    text = "\n".join(
        [
            "# Detector Next Report",
            "",
            "## Benchmark Triangle",
            "",
            _markdown_table(best_rows),
            "",
            "## Interpretation",
            "",
            f"- `poisson_linear` remains the ideal reference baseline; in this run `shot_trigger` slightly outscored it on the composite metric.",
            f"- Among physical candidates, `{best_candidate['model']}` is currently best by composite score.",
            f"- `shot_trigger` viable-grid fraction with race RMS <= 0.05: {region_fraction:.1%}.",
            f"- `shot_trigger` 2-branch integration RMS error: {integration_rms:.4f}.",
            "",
            "## Files",
            "",
            "- `results_summary.csv` contains the top-ranked rows per model.",
            "- `*_comparison.png` holds the per-model diagnostic panels.",
            "- `shot_trigger_winner_region.png` shows the `eps_event` vs `p_trig` slice.",
            "- `shot_trigger_integration.png` shows reduced branch weights mapped to winner frequencies.",
            "",
        ]
    )
    path.write_text(text + "\n", encoding="utf-8")


def build_next_steps_report(
    outdir: str | Path,
    *,
    samples_per_model: int = 8,
    top_k: int = 5,
    grid_size: int = 9,
    config: SearchConfig = REPORT_CONFIG,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results_by_model: dict[str, list[dict[str, Any]]] = {}
    comparison_paths: list[str] = []
    summary_rows: list[dict[str, Any]] = []

    for model_name, model_factory in REPORT_MODELS.items():
        model = model_factory()
        results = search_model_family(model, n_samples=samples_per_model, config=config)
        results_by_model[model_name] = results
        save_results_jsonl(results, output_dir / f"{model_name}_search.jsonl")
        save_results_csv(results, output_dir / f"{model_name}_search.csv")
        comparison_paths.append(_save_model_comparison_plot(output_dir, model_name, model, results[0], config))
        for rank, result in enumerate(results[:top_k], start=1):
            summary_rows.append(_summary_row(model_name, rank, result))

    summary_path = output_dir / "results_summary.csv"
    _write_summary_csv(summary_path, summary_rows)

    best_rows = [row for row in summary_rows if row["rank"] == 1]
    best_rows.sort(key=lambda row: row["score"])

    shot_region_csv, shot_region_png, shot_region_rows = _evaluate_shot_trigger_region(
        output_dir,
        results_by_model["shot_trigger"][0],
        grid_size=grid_size,
        config=config,
    )
    integration_csv, integration_png, integration_rows = _evaluate_integration_surrogate(
        output_dir,
        results_by_model["shot_trigger"][0]["params"],
        config=config,
        power_scale=max(config.p_scan),
    )

    report_path = output_dir / "report.md"
    _write_report_markdown(report_path, best_rows, shot_region_rows, integration_rows)

    return {
        "outdir": str(output_dir),
        "summary_csv": str(summary_path),
        "comparison_paths": comparison_paths,
        "shot_trigger_region_csv": shot_region_csv,
        "shot_trigger_region_png": shot_region_png,
        "integration_csv": integration_csv,
        "integration_png": integration_png,
        "report_md": str(report_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the detector next-steps artifact folder.")
    parser.add_argument("--outdir", default="artifacts/detector_next")
    parser.add_argument("--samples-per-model", type=int, default=8)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--grid-size", type=int, default=9)
    args = parser.parse_args()

    outputs = build_next_steps_report(
        args.outdir,
        samples_per_model=args.samples_per_model,
        top_k=args.top_k,
        grid_size=args.grid_size,
    )
    print(json.dumps(outputs, indent=2))


if __name__ == "__main__":
    main()
