from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from front_end_surrogate.plots import plot_two_branch_fraction_comparison
from front_end_surrogate.two_branch_surrogate import representative_two_branch_cases, simulate_two_branch_surrogate


def _json_default(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _compact_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "branch_labels": result["branch_labels"],
        "branch_energy_j": result["branch_energy_j"],
        "branch_energy_fraction": result["branch_energy_fraction"],
        "exact_weight": result["exact_weight"],
        "surrogate_fraction": result["surrogate_fraction"],
        "metrics": result["metrics"],
        "envelope_config": result["envelope_config"],
    }


def run_two_branch_surrogate_sweep(
    outdir: str | Path,
    *,
    envelope_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    full_results: list[dict[str, Any]] = []

    for case in representative_two_branch_cases():
        result = simulate_two_branch_surrogate(case["state"], case["analyzer"], envelope_config=envelope_config)
        full_results.append({"case": case["case"], **_compact_result(result)})
        rows.append(
            {
                "case": case["case"],
                "exact_p1": result["exact_weight"]["branch_1"],
                "surrogate_p1": result["surrogate_fraction"]["branch_1"],
                "exact_p2": result["exact_weight"]["branch_2"],
                "surrogate_p2": result["surrogate_fraction"]["branch_2"],
                "rms_error": result["metrics"]["rms_error"],
                "max_abs_error": result["metrics"]["max_abs_error"],
            }
        )

    csv_path = output_dir / "two_branch_summary.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    json_path = output_dir / "two_branch_summary.json"
    json_path.write_text(json.dumps({"rows": full_results}, default=_json_default, indent=2) + "\n", encoding="utf-8")

    plot_path = output_dir / "two_branch_fraction_comparison.png"
    plot_two_branch_fraction_comparison(rows).savefig(plot_path)
    return {
        "csv": str(csv_path),
        "json": str(json_path),
        "plot": str(plot_path),
        "rows": rows,
        "envelope_config": envelope_config,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the two-branch SPICE-facing front-end surrogate sweep.")
    parser.add_argument("--outdir", default="artifacts/front_end_surrogate/two_branch")
    args = parser.parse_args()
    run_two_branch_surrogate_sweep(args.outdir)


if __name__ == "__main__":
    main()
