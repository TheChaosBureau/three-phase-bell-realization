from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from detector_integration.experiments.sweep_four_branch_angles import run_four_branch_angle_sweep
from detector_integration.experiments.sweep_two_branch_states import run_two_branch_state_sweep


def build_detector_integration_comparison(
    outdir: str | Path,
    *,
    n_two_branch_trials: int = 2_000,
    n_four_branch_trials: int = 4_000,
) -> dict[str, object]:
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    outputs: dict[str, object] = {}

    for family in ("poisson_linear", "shot_trigger"):
        family_dir = output_dir / family
        family_dir.mkdir(parents=True, exist_ok=True)
        two_outputs = run_two_branch_state_sweep(family_dir / "two_branch", detector_family=family, n_trials=n_two_branch_trials)
        four_outputs = run_four_branch_angle_sweep(family_dir / "four_branch", detector_family=family, n_trials=n_four_branch_trials)
        outputs[family] = {"two_branch": two_outputs, "four_branch": four_outputs}
        rows.append(
            {
                "family": family,
                "two_branch_csv": two_outputs["csv"],
                "four_branch_csv": four_outputs["csv"],
                "four_branch_json": four_outputs["json"],
            }
        )

    comparison_csv = output_dir / "comparison_summary.csv"
    with comparison_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    comparison_json = output_dir / "comparison_summary.json"
    comparison_json.write_text(json.dumps(outputs, indent=2) + "\n", encoding="utf-8")
    return {
        "comparison_csv": str(comparison_csv),
        "comparison_json": str(comparison_json),
        "families": outputs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run detector-layer exact-vs-empirical comparison artifacts.")
    parser.add_argument("--outdir", default="artifacts/detector_integration/compare")
    parser.add_argument("--two-branch-trials", type=int, default=2_000)
    parser.add_argument("--four-branch-trials", type=int, default=4_000)
    args = parser.parse_args()

    print(
        json.dumps(
            build_detector_integration_comparison(
                args.outdir,
                n_two_branch_trials=args.two_branch_trials,
                n_four_branch_trials=args.four_branch_trials,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
