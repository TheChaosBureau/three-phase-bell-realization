from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from detector_integration.experiments.run_summary_report import load_top_shot_trigger_spec

from physical_front_end_candidate.boundary_calibration import resolved_calibrated_boundary_config
from physical_front_end_candidate.boundary_repro_check import (
    PRIOR_DIAGNOSIS_REFERENCE,
    classify_reproducibility,
    resolved_repro_check_config,
    rerun_frozen_boundary_case,
)
from physical_front_end_candidate.plots import plot_calibrated_frequency_with_ci, plot_decisive_counts, plot_prior_vs_rerun
from physical_front_end_candidate.two_branch_candidate import representative_physical_cases


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _json_default(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _summary_markdown(
    *,
    classification: dict[str, str],
    rerun_summary: dict[str, Any],
    outputs: dict[str, str],
) -> str:
    return "\n".join(
        [
            "# Front-End Detector Boundary Reproducibility Check",
            "",
            "## Frozen Contract",
            "",
            "- Export mode: `piecewise:linear:20.0ms`",
            "- Gain: `4.0x`",
            "- Exposure: `5.0s`",
            "",
            "## High-Statistics Rerun",
            "",
            f"- RMS winner-law error: {float(rerun_summary['winner_rms_error']):.6f}",
            f"- Max winner-law error: {float(rerun_summary['winner_max_error']):.6f}",
            f"- Mean decisive fraction: {float(rerun_summary['mean_decisive_fraction']):.6f}",
            f"- Min decisive count: {int(rerun_summary['min_decisive_count'])}",
            "",
            "## Decision",
            "",
            f"- Outcome: `{classification['outcome']}`",
            f"- Next ticket: {classification['next_ticket']}",
            "",
            "## Artifacts",
            "",
            f"- High-stat run: `{outputs['high_stat_csv']}`",
            f"- Comparison CSV: `{outputs['comparison_csv']}`",
            "",
        ]
    )


def build_physical_front_end_boundary_repro_check_report(
    outdir: str | Path = "artifacts/physical_front_end_boundary_repro_check",
    *,
    detector_next_summary_csv: str | Path = "artifacts/detector_next/results_summary.csv",
    min_trials_per_case: int = 500,
    target_decisive_count: int = 100,
    max_trials_per_case: int = 20_000,
    batch_trials: int = 500,
    seed: int = 20260403,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    high_stat_dir = output_dir / "high_stat_run"
    comparison_dir = output_dir / "comparison"
    for directory in (high_stat_dir, comparison_dir):
        directory.mkdir(parents=True, exist_ok=True)

    detector_spec = load_top_shot_trigger_spec(detector_next_summary_csv)
    detector_model_spec = {"family": detector_spec["family"], "model_params": dict(detector_spec["model_params"])}
    calibration_config = resolved_calibrated_boundary_config()
    repro_config = resolved_repro_check_config(
        {
            "min_trials_per_case": min_trials_per_case,
            "target_decisive_count": target_decisive_count,
            "max_trials_per_case": max_trials_per_case,
            "batch_trials": batch_trials,
            "gain": calibration_config.gain,
            "exposure_s": calibration_config.exposure_s,
        }
    )

    result_rows: list[dict[str, Any]] = []
    full_results: list[dict[str, Any]] = []
    for case_index, case in enumerate(representative_physical_cases()):
        rerun = rerun_frozen_boundary_case(
            case["state"],
            case["analyzer"],
            detector_model_spec,
            seed=seed + 101 * case_index,
            config=asdict(repro_config),
        )
        result_rows.append(
            {
                "case": case["case"],
                "total_trials": int(rerun["total_trials"]),
                "decisive_count": int(rerun["decisive_count"]),
                "timeout_count": int(rerun["timeout_count"]),
                "decisive_fraction": float(rerun["decisive_fraction"]),
                "decisive_fraction_ci95": float(rerun["decisive_fraction_ci95"]),
                "exact_p1": float(rerun["exact_weights"][0]),
                "empirical_p1": float(rerun["empirical_frequencies"][0]),
                "empirical_p1_ci95": float(rerun["p1_ci95"]),
                "exact_p2": float(rerun["exact_weights"][1]),
                "empirical_p2": float(rerun["empirical_frequencies"][1]),
                "rms_error": float(rerun["metrics"]["rms_error"]),
                "max_abs_error": float(rerun["metrics"]["max_abs_error"]),
                "winner_rms_error_ci95": float(rerun["winner_rms_error_ci95"]),
                "sufficient_evidence": bool(rerun["sufficient_evidence"]),
            }
        )
        full_results.append(rerun)

    high_stat_csv = high_stat_dir / "high_stat_run.csv"
    _write_csv(high_stat_csv, result_rows)
    decisive_csv = high_stat_dir / "decisive_count_summary.csv"
    _write_csv(
        decisive_csv,
        [
            {
                "case": row["case"],
                "total_trials": row["total_trials"],
                "decisive_count": row["decisive_count"],
                "timeout_count": row["timeout_count"],
                "decisive_fraction": row["decisive_fraction"],
                "decisive_fraction_ci95": row["decisive_fraction_ci95"],
            }
            for row in result_rows
        ],
    )

    rerun_summary = {
        "winner_rms_error": float(np.sqrt(np.mean([float(row["rms_error"]) ** 2 for row in result_rows]))),
        "winner_max_error": float(np.max([float(row["max_abs_error"]) for row in result_rows])),
        "mean_decisive_fraction": float(np.mean([float(row["decisive_fraction"]) for row in result_rows])),
        "min_decisive_count": int(np.min([int(row["decisive_count"]) for row in result_rows])),
        "mean_total_trials": float(np.mean([float(row["total_trials"]) for row in result_rows])),
    }
    comparison_rows = [
        {
            "label": "prior diagnosis",
            "winner_rms_error": float(PRIOR_DIAGNOSIS_REFERENCE["winner_rms_error"]),
            "winner_max_error": float(PRIOR_DIAGNOSIS_REFERENCE["winner_max_error"]),
            "decisive_fraction": float(PRIOR_DIAGNOSIS_REFERENCE["decisive_fraction"]),
            "gain": float(PRIOR_DIAGNOSIS_REFERENCE["gain"]),
            "exposure_s": float(PRIOR_DIAGNOSIS_REFERENCE["exposure_s"]),
        },
        {
            "label": "high-stat rerun",
            "winner_rms_error": rerun_summary["winner_rms_error"],
            "winner_max_error": rerun_summary["winner_max_error"],
            "decisive_fraction": rerun_summary["mean_decisive_fraction"],
            "gain": float(repro_config.gain),
            "exposure_s": float(repro_config.exposure_s),
        },
    ]
    comparison_csv = comparison_dir / "comparison.csv"
    _write_csv(comparison_csv, comparison_rows)

    classification = classify_reproducibility(result_rows)

    winner_plot = high_stat_dir / "winner_frequency_high_stat.png"
    plot_calibrated_frequency_with_ci(result_rows).savefig(winner_plot)
    decisive_plot = high_stat_dir / "decisive_counts.png"
    plot_decisive_counts(result_rows).savefig(decisive_plot)
    comparison_plot = comparison_dir / "prior_vs_rerun.png"
    plot_prior_vs_rerun(comparison_rows).savefig(comparison_plot)

    summary_metrics = {
        "winner_rms_error": rerun_summary["winner_rms_error"],
        "winner_max_error": rerun_summary["winner_max_error"],
        "mean_decisive_fraction": rerun_summary["mean_decisive_fraction"],
        "min_decisive_count": rerun_summary["min_decisive_count"],
        "mean_total_trials": rerun_summary["mean_total_trials"],
    }

    summary_csv = output_dir / "summary_metrics.csv"
    _write_csv(summary_csv, [{"metric": key, "value": value} for key, value in summary_metrics.items()])
    summary_json = output_dir / "summary_metrics.json"
    summary_json.write_text(
        json.dumps(
            {
                "config": asdict(repro_config),
                "prior_reference": PRIOR_DIAGNOSIS_REFERENCE,
                "summary_metrics": summary_metrics,
                "classification": classification,
                "results": result_rows,
                "comparison_rows": comparison_rows,
            },
            indent=2,
            default=_json_default,
        )
        + "\n",
        encoding="utf-8",
    )

    outputs = {
        "high_stat_csv": str(high_stat_csv),
        "comparison_csv": str(comparison_csv),
    }
    summary_md = output_dir / "summary_report.md"
    summary_md.write_text(_summary_markdown(classification=classification, rerun_summary=rerun_summary, outputs=outputs) + "\n", encoding="utf-8")

    return {
        "summary_md": str(summary_md),
        "summary_json": str(summary_json),
        "summary_csv": str(summary_csv),
        "high_stat_csv": str(high_stat_csv),
        "comparison_csv": str(comparison_csv),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the physical front-end detector boundary reproducibility report.")
    parser.add_argument("--outdir", default="artifacts/physical_front_end_boundary_repro_check")
    parser.add_argument("--detector-next-summary", default="artifacts/detector_next/results_summary.csv")
    parser.add_argument("--min-trials-per-case", type=int, default=500)
    parser.add_argument("--target-decisive-count", type=int, default=100)
    parser.add_argument("--max-trials-per-case", type=int, default=20_000)
    parser.add_argument("--batch-trials", type=int, default=500)
    args = parser.parse_args()
    build_physical_front_end_boundary_repro_check_report(
        args.outdir,
        detector_next_summary_csv=args.detector_next_summary,
        min_trials_per_case=args.min_trials_per_case,
        target_decisive_count=args.target_decisive_count,
        max_trials_per_case=args.max_trials_per_case,
        batch_trials=args.batch_trials,
    )


if __name__ == "__main__":
    main()
