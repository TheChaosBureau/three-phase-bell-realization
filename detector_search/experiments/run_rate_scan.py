from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from detector_search.config import DEFAULT_SEARCH_CONFIG
from detector_search.models import (
    AccumulatorBadControlModel,
    MetastableEscapeModel,
    PoissonLinearModel,
    ShotTriggerModel,
)
from detector_search.plots import plot_rate_residuals, plot_rate_scan, plot_waiting_time_histogram
from detector_search.sim.metrics import fit_rate_vs_power
from detector_search.sim.single_branch import simulate_many_trials


MODEL_FACTORIES = {
    "poisson_linear": PoissonLinearModel,
    "shot_trigger": ShotTriggerModel,
    "metastable_escape": MetastableEscapeModel,
    "accumulator_bad_control": AccumulatorBadControlModel,
}


def _json_default(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _save_rate_plots(model_name: str, rows: list[dict[str, Any]], fit: dict[str, Any], outdir: str) -> list[str]:
    outpath = Path(outdir)
    outpath.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    rate_path = outpath / f"{model_name}_rate_scan.png"
    plot_rate_scan(rows, fit["fit_values"]).savefig(rate_path)
    written.append(str(rate_path))

    residual_path = outpath / f"{model_name}_rate_residuals.png"
    plot_rate_residuals(rows, fit["fit_values"]).savefig(residual_path)
    written.append(str(residual_path))

    non_empty_rows = [row for row in rows if int(row["n_clicks"]) > 0]
    if non_empty_rows:
        waiting_row = max(non_empty_rows, key=lambda row: float(row["power"]))
        waiting_path = outpath / f"{model_name}_waiting_time_hist.png"
        plot_waiting_time_histogram(waiting_row["click_times"], float(waiting_row["click_times"].mean())).savefig(waiting_path)
        written.append(str(waiting_path))

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a rate scan for one detector model.")
    parser.add_argument("model", choices=sorted(MODEL_FACTORIES))
    parser.add_argument("--params", default="{}", help="JSON dictionary of model parameters.")
    parser.add_argument("--outdir", help="Directory where PNG plots should be written.")
    args = parser.parse_args()

    model = MODEL_FACTORIES[args.model]()
    params = json.loads(args.params)
    rows = [
        simulate_many_trials(
            model,
            params=params,
            P_abs=power,
            n_trials=DEFAULT_SEARCH_CONFIG.n_rate_trials,
            dt=DEFAULT_SEARCH_CONFIG.dt,
            t_max=DEFAULT_SEARCH_CONFIG.t_max,
            seed=DEFAULT_SEARCH_CONFIG.seed + index,
        )
        | {"power": power}
        for index, power in enumerate(DEFAULT_SEARCH_CONFIG.p_scan)
    ]
    fit = fit_rate_vs_power([row["power"] for row in rows], [row["rate_estimate"] for row in rows])
    payload: dict[str, Any] = {"rows": rows, "fit": fit}
    if args.outdir:
        payload["plot_paths"] = _save_rate_plots(args.model, rows, fit, args.outdir)
    print(json.dumps(payload, default=_json_default))


if __name__ == "__main__":
    main()
