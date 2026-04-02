from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from detector_integration.plots import plot_two_branch_frequency_comparison
from detector_integration.sim.run_two_branch_integration import run_two_branch_trials

DEFAULT_ENVELOPE = {"kind": "constant", "power_scale": 4.0, "dt": 1e-4, "t_max": 5.0}


def default_detector_spec(family: str) -> dict[str, Any]:
    if family == "poisson_linear":
        return {"family": "poisson_linear", "model_params": {"lambda_dark": 1e-6, "alpha": 1.6, "dead_time": 0.0}}
    if family == "shot_trigger":
        return {"family": "shot_trigger", "model_params": {"eps_event": 0.5, "p_trig": 0.8, "lambda_dark": 1e-6, "dead_time": 0.0}}
    raise ValueError(f"Unsupported detector family: {family}")


def representative_two_branch_cases() -> list[dict[str, Any]]:
    return [
        {"case": "pole_plus_30", "state": np.array([1.0, 0.0], dtype=np.complex128), "analyzer": 30.0},
        {"case": "pole_minus_30", "state": np.array([0.0, 1.0], dtype=np.complex128), "analyzer": 30.0},
        {"case": "equator_x_0", "state": np.array([1.0, 1.0], dtype=np.complex128) / np.sqrt(2.0), "analyzer": 0.0},
        {"case": "equator_x_45", "state": np.array([1.0, 1.0], dtype=np.complex128) / np.sqrt(2.0), "analyzer": 45.0},
        {"case": "phase_y_22_5", "state": np.array([1.0, 1.0j], dtype=np.complex128) / np.sqrt(2.0), "analyzer": 22.5},
    ]


def _json_default(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def run_two_branch_state_sweep(
    outdir: str | Path,
    *,
    detector_family: str = "shot_trigger",
    detector_spec: dict[str, Any] | None = None,
    envelope_params: dict[str, Any] | None = None,
    n_trials: int = 2_000,
    seed: int = 20260402,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)
    resolved_detector_spec = default_detector_spec(detector_family) if detector_spec is None else detector_spec
    resolved_envelope = DEFAULT_ENVELOPE if envelope_params is None else envelope_params
    rows: list[dict[str, Any]] = []
    full_results: list[dict[str, Any]] = []

    for index, case in enumerate(representative_two_branch_cases()):
        result = run_two_branch_trials(
            case["state"],
            case["analyzer"],
            resolved_detector_spec,
            n_trials=n_trials,
            seed=seed + 97 * index,
            envelope_params=resolved_envelope,
        )
        full_results.append({"case": case["case"], **result})
        rows.append(
            {
                "case": case["case"],
                "exact_p1": float(result["exact_weights"][0]),
                "empirical_p1": float(result["empirical_frequencies"][0]),
                "exact_p2": float(result["exact_weights"][1]),
                "empirical_p2": float(result["empirical_frequencies"][1]),
                "rms_error": result["metrics"]["rms_error"],
                "max_abs_error": result["metrics"]["max_abs_error"],
                "winner_law_error": result["metrics"]["winner_law_error"],
                "decisive_fraction": result["decisive_fraction"],
            }
        )

    csv_path = output_dir / "two_branch_summary.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    json_path = output_dir / "two_branch_summary.json"
    json_path.write_text(json.dumps({"rows": full_results}, default=_json_default, indent=2) + "\n", encoding="utf-8")

    plot_path = output_dir / "two_branch_winner_frequencies.png"
    plot_two_branch_frequency_comparison(rows).savefig(plot_path)
    return {
        "csv": str(csv_path),
        "json": str(json_path),
        "plot": str(plot_path),
        "rows": rows,
        "detector_spec": resolved_detector_spec,
        "envelope_params": resolved_envelope,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep representative two-branch states through the detector layer.")
    parser.add_argument("--outdir", default="artifacts/detector_integration/two_branch")
    parser.add_argument("--family", default="shot_trigger", choices=["shot_trigger", "poisson_linear"])
    parser.add_argument("--trials", type=int, default=2_000)
    args = parser.parse_args()

    print(json.dumps(run_two_branch_state_sweep(args.outdir, detector_family=args.family, n_trials=args.trials), indent=2))


if __name__ == "__main__":
    main()
