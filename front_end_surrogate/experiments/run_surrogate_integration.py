from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from detector_integration.experiments.run_summary_report import load_top_shot_trigger_spec

from front_end_surrogate.integration_adapter import (
    benchmark_four_branch_handoff_rows,
    representative_two_branch_handoff_rows,
    run_surrogate_chsh_handoff,
)
from front_end_surrogate.plots import plot_integration_winner_frequency


def run_front_end_surrogate_integration(
    outdir: str | Path,
    *,
    detector_next_summary_csv: str | Path = "artifacts/detector_next/results_summary.csv",
    n_two_branch_trials: int = 2_500,
    n_four_branch_trials: int = 4_000,
    envelope_config: dict[str, Any] | None = None,
    seed: int = 20260402,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)

    detector_spec = load_top_shot_trigger_spec(detector_next_summary_csv)
    detector_model_spec = {"family": detector_spec["family"], "model_params": dict(detector_spec["model_params"])}

    two_rows = representative_two_branch_handoff_rows(detector_model_spec, n_trials=n_two_branch_trials, seed=seed, envelope_config=envelope_config)
    four_rows = benchmark_four_branch_handoff_rows(detector_model_spec, n_trials=n_four_branch_trials, seed=seed + 10_000, envelope_config=envelope_config)
    all_rows = two_rows + four_rows

    csv_rows = [
        {
            **row,
            "exact_weights": json.dumps(row["exact_weights"]),
            "empirical_frequencies": json.dumps(row["empirical_frequencies"]),
        }
        for row in all_rows
    ]
    fieldnames = sorted({key for row in csv_rows for key in row.keys()})
    csv_path = output_dir / "integration_summary.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    chsh_result = run_surrogate_chsh_handoff(detector_model_spec, n_trials=n_four_branch_trials, seed=seed + 20_000, envelope_config=envelope_config)
    json_path = output_dir / "integration_summary.json"
    json_path.write_text(json.dumps({"rows": all_rows, "chsh": chsh_result}, indent=2) + "\n", encoding="utf-8")

    plot_rows = [
        {"exact_weights": row["exact_weights"], "empirical_frequencies": row["empirical_frequencies"]}
        for row in all_rows
    ]
    plot_path = output_dir / "integration_winner_frequency_comparison.png"
    plot_integration_winner_frequency(plot_rows).savefig(plot_path)
    return {
        "csv": str(csv_path),
        "json": str(json_path),
        "plot": str(plot_path),
        "rows": all_rows,
        "chsh": chsh_result,
        "detector_spec": detector_model_spec,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the front-end surrogate handoff into the abstract detector+latch layer.")
    parser.add_argument("--outdir", default="artifacts/front_end_surrogate/integration")
    parser.add_argument("--detector-next-summary", default="artifacts/detector_next/results_summary.csv")
    parser.add_argument("--two-branch-trials", type=int, default=2_500)
    parser.add_argument("--four-branch-trials", type=int, default=4_000)
    args = parser.parse_args()
    run_front_end_surrogate_integration(
        args.outdir,
        detector_next_summary_csv=args.detector_next_summary,
        n_two_branch_trials=args.two_branch_trials,
        n_four_branch_trials=args.four_branch_trials,
    )


if __name__ == "__main__":
    main()
