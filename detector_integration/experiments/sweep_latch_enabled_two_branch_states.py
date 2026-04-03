from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import numpy as np

from detector_integration.detectors.closure_latch import validated_latch_arbiter_config
from detector_integration.experiments.sweep_two_branch_states import (
    DEFAULT_ENVELOPE,
    _json_default,
    default_detector_spec,
    representative_two_branch_cases,
)
from detector_integration.plots import plot_two_branch_frequency_comparison
from detector_integration.sim.run_two_branch_latch_integration import run_two_branch_latch_trials


def _latch_json_default(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    return _json_default(value)


def run_latch_enabled_two_branch_state_sweep(
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
    resolved_latch = validated_latch_arbiter_config(2)
    rows: list[dict[str, Any]] = []
    full_results: list[dict[str, Any]] = []

    for index, case in enumerate(representative_two_branch_cases()):
        result = run_two_branch_latch_trials(
            case["state"],
            case["analyzer"],
            resolved_detector_spec,
            n_trials=n_trials,
            seed=seed + 97 * index,
            envelope_params=resolved_envelope,
            latch_config=resolved_latch,
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
                "tie_region_fraction": result["tie_region_fraction"],
            }
        )

    csv_path = output_dir / "two_branch_summary.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    json_path = output_dir / "two_branch_summary.json"
    json_path.write_text(json.dumps({"rows": full_results}, default=_latch_json_default, indent=2) + "\n", encoding="utf-8")

    plot_path = output_dir / "two_branch_winner_frequencies.png"
    plot_two_branch_frequency_comparison(rows).savefig(plot_path)
    return {
        "csv": str(csv_path),
        "json": str(json_path),
        "plot": str(plot_path),
        "rows": rows,
        "detector_spec": resolved_detector_spec,
        "latch_config": resolved_latch,
        "envelope_params": resolved_envelope,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep representative two-branch states through the latch-enabled detector layer.")
    parser.add_argument("--outdir", default="artifacts/front_end_integration/two_branch")
    parser.add_argument("--family", default="shot_trigger", choices=["shot_trigger", "poisson_linear"])
    parser.add_argument("--trials", type=int, default=2_000)
    args = parser.parse_args()

    print(json.dumps(run_latch_enabled_two_branch_state_sweep(args.outdir, detector_family=args.family, n_trials=args.trials), indent=2))


if __name__ == "__main__":
    main()
