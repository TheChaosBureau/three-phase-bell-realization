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
from detector_search.plots import plot_race_law
from detector_search.sim.race import simulate_many_races


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


def _save_race_plot(model_name: str, rows: list[dict[str, Any]], outdir: str) -> str:
    outpath = Path(outdir)
    outpath.mkdir(parents=True, exist_ok=True)
    race_path = outpath / f"{model_name}_race_law.png"
    plot_race_law(rows).savefig(race_path)
    return str(race_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a race-law scan for one detector model.")
    parser.add_argument("model", choices=sorted(MODEL_FACTORIES))
    parser.add_argument("--params", default="{}", help="JSON dictionary of model parameters.")
    parser.add_argument("--outdir", help="Directory where PNG plots should be written.")
    args = parser.parse_args()

    model = MODEL_FACTORIES[args.model]()
    params = json.loads(args.params)
    rows = [
        simulate_many_races(
            model,
            params1=params,
            params2=params,
            P1=P1,
            P2=P2,
            n_trials=DEFAULT_SEARCH_CONFIG.n_race_trials,
            dt=DEFAULT_SEARCH_CONFIG.dt,
            t_max=DEFAULT_SEARCH_CONFIG.t_max,
            seed=DEFAULT_SEARCH_CONFIG.seed + index,
        )
        | {"P1": P1, "P2": P2, "target_p1": P1 / (P1 + P2)}
        for index, (P1, P2) in enumerate(DEFAULT_SEARCH_CONFIG.race_pairs)
    ]
    payload: dict[str, Any] = {"rows": rows}
    if args.outdir:
        payload["plot_path"] = _save_race_plot(args.model, rows, args.outdir)
    print(json.dumps(payload, default=_json_default))


if __name__ == "__main__":
    main()
