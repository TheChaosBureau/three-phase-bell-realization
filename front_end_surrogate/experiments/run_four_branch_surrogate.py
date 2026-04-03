from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from front_end_surrogate.four_branch_surrogate import benchmark_four_branch_cases, simulate_four_branch_surrogate
from front_end_surrogate.metrics import chsh_metrics
from front_end_surrogate.plots import plot_chsh_comparison, plot_correlator_comparison, plot_four_branch_fraction_comparison


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
        "a_deg": result["a_deg"],
        "b_deg": result["b_deg"],
        "envelope_config": result["envelope_config"],
    }


def run_four_branch_surrogate_sweep(
    outdir: str | Path,
    *,
    envelope_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    full_results: list[dict[str, Any]] = []
    exact_correlators: dict[str, float] = {}
    surrogate_correlators: dict[str, float] = {}

    chsh_labels = {"a0b0", "a0b1", "a1b0", "a1b1"}

    for label, a_deg, b_deg in benchmark_four_branch_cases():
        result = simulate_four_branch_surrogate(a_deg=a_deg, b_deg=b_deg, envelope_config=envelope_config)
        full_results.append({"label": label, **_compact_result(result)})
        rows.append(
            {
                "label": label,
                "a_deg": a_deg,
                "b_deg": b_deg,
                "exact_weights": [result["exact_weight"][branch] for branch in result["branch_labels"]],
                "surrogate_fractions": [result["surrogate_fraction"][branch] for branch in result["branch_labels"]],
                "rms_error": result["metrics"]["rms_error"],
                "max_abs_error": result["metrics"]["max_abs_error"],
                "correlator_exact": result["metrics"]["correlator_exact"],
                "correlator_surrogate": result["metrics"]["correlator_surrogate"],
                "correlator_error": result["metrics"]["correlator_error"],
            }
        )
        if label in chsh_labels:
            exact_correlators[label] = float(result["metrics"]["correlator_exact"])
            surrogate_correlators[label] = float(result["metrics"]["correlator_surrogate"])

    four_rows = [
        {
            **row,
            "exact_weights": json.dumps(row["exact_weights"]),
            "surrogate_fractions": json.dumps(row["surrogate_fractions"]),
        }
        for row in rows
    ]
    csv_path = output_dir / "four_branch_summary.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(four_rows[0].keys()))
        writer.writeheader()
        writer.writerows(four_rows)

    chsh_result = chsh_metrics(exact_correlators, surrogate_correlators)
    json_path = output_dir / "four_branch_summary.json"
    json_path.write_text(
        json.dumps({"rows": full_results, "chsh": chsh_result}, default=_json_default, indent=2) + "\n",
        encoding="utf-8",
    )

    weights_plot = output_dir / "four_branch_fraction_comparison.png"
    plot_four_branch_fraction_comparison(rows).savefig(weights_plot)

    correlator_plot = output_dir / "correlator_comparison.png"
    plot_correlator_comparison(rows).savefig(correlator_plot)

    chsh_plot = output_dir / "chsh_comparison.png"
    plot_chsh_comparison(chsh_result).savefig(chsh_plot)

    return {
        "csv": str(csv_path),
        "json": str(json_path),
        "weights_plot": str(weights_plot),
        "correlator_plot": str(correlator_plot),
        "chsh_plot": str(chsh_plot),
        "rows": rows,
        "chsh": chsh_result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the four-branch SPICE-facing front-end surrogate sweep.")
    parser.add_argument("--outdir", default="artifacts/front_end_surrogate/four_branch")
    args = parser.parse_args()
    run_four_branch_surrogate_sweep(args.outdir)


if __name__ == "__main__":
    main()
