from __future__ import annotations

import argparse
from pathlib import Path

from detector_search.config import DEFAULT_SEARCH_CONFIG, SearchConfig
from detector_search.models import (
    AccumulatorBadControlModel,
    MetastableEscapeModel,
    PoissonLinearModel,
    ShotTriggerModel,
)
from detector_search.plots import (
    plot_race_law,
    plot_rate_residuals,
    plot_rate_scan,
    plot_robustness,
    plot_score_histogram,
    plot_waiting_time_histogram,
)
from detector_search.sim.search import (
    evaluate_candidate,
    save_results_csv,
    save_results_jsonl,
    search_model_family,
)
from detector_search.sim.single_branch import simulate_many_trials


MODEL_FACTORIES = {
    "poisson_linear": PoissonLinearModel,
    "shot_trigger": ShotTriggerModel,
    "metastable_escape": MetastableEscapeModel,
    "accumulator_bad_control": AccumulatorBadControlModel,
}


def _save_global_search_plots(
    model_name: str,
    model,
    results: list[dict],
    outdir: str,
    config: SearchConfig = DEFAULT_SEARCH_CONFIG,
) -> list[str]:
    outpath = Path(outdir)
    outpath.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    score_path = outpath / f"{model_name}_score_histogram.png"
    plot_score_histogram(results).savefig(score_path)
    written.append(str(score_path))

    if not results:
        return written

    top = results[0]
    metrics = top["metrics"]

    rate_path = outpath / f"{model_name}_top_rate_scan.png"
    fit_values = [
        metrics["lambda_dark_fit"] + metrics["alpha_fit"] * row["power"]
        for row in top["rate_scan"]
    ]
    plot_rate_scan(top["rate_scan"], fit_values).savefig(rate_path)
    written.append(str(rate_path))

    residual_path = outpath / f"{model_name}_top_rate_residuals.png"
    plot_rate_residuals(top["rate_scan"], fit_values).savefig(residual_path)
    written.append(str(residual_path))

    race_path = outpath / f"{model_name}_top_race_law.png"
    plot_race_law(top["race_rows"]).savefig(race_path)
    written.append(str(race_path))

    robustness_path = outpath / f"{model_name}_top_robustness.png"
    plot_robustness(top["mismatch_rows"]).savefig(robustness_path)
    written.append(str(robustness_path))

    waiting_power = max(config.waiting_time_powers)
    waiting_row = simulate_many_trials(
        model,
        params=top["params"],
        P_abs=waiting_power,
        n_trials=config.n_rate_trials,
        dt=config.dt,
        t_max=config.t_max,
        seed=config.seed + 99_001,
    )
    if int(waiting_row["n_clicks"]) > 0:
        waiting_path = outpath / f"{model_name}_top_waiting_time_hist.png"
        plot_waiting_time_histogram(waiting_row["click_times"], float(waiting_row["click_times"].mean())).savefig(waiting_path)
        written.append(str(waiting_path))

    summary_path = outpath / f"{model_name}_top_candidate.txt"
    summary_path.write_text(
        "\n".join(
            [
                f"model={top['model']}",
                f"score={metrics['score']}",
                f"params={top['params']}",
                f"metrics={metrics}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    written.append(str(summary_path))

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a global detector-model parameter search.")
    parser.add_argument("model", choices=sorted(MODEL_FACTORIES))
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--jsonl", default="detector_search_results/results.jsonl")
    parser.add_argument("--csv", default="detector_search_results/results.csv")
    parser.add_argument("--outdir", help="Directory where PNG plots and top-candidate summaries should be written.")
    args = parser.parse_args()

    model = MODEL_FACTORIES[args.model]()
    results = search_model_family(model, n_samples=args.samples)
    save_results_jsonl(results, args.jsonl)
    save_results_csv(results, args.csv)
    message = f"Saved {len(results)} results to {args.jsonl} and {args.csv}"
    if args.outdir:
        written = _save_global_search_plots(args.model, model, results, args.outdir)
        message += f"; wrote {len(written)} plot artifacts to {args.outdir}"
    print(message)


if __name__ == "__main__":
    main()
