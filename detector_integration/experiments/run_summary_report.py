from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from detector_integration.experiments.sweep_four_branch_angles import DEFAULT_ENVELOPE as FOUR_BRANCH_ENVELOPE
from detector_integration.experiments.sweep_four_branch_angles import run_four_branch_angle_sweep
from detector_integration.experiments.sweep_two_branch_states import DEFAULT_ENVELOPE as TWO_BRANCH_ENVELOPE
from detector_integration.experiments.sweep_two_branch_states import run_two_branch_state_sweep


def load_top_shot_trigger_spec(summary_csv_path: str | Path) -> dict[str, Any]:
    path = Path(summary_csv_path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        candidates = [row for row in reader if row["model"] == "shot_trigger" and row["rank"] == "1"]
    if not candidates:
        raise ValueError(f"No top-ranked shot_trigger row found in {path}.")
    top = candidates[0]
    return {
        "family": "shot_trigger",
        "model_params": json.loads(top["params_json"]),
        "search_summary_row": top,
    }


def _two_branch_summary_metric(rows: list[dict[str, Any]]) -> float:
    values = np.asarray([float(row["winner_law_error"]) for row in rows], dtype=float)
    return float(np.sqrt(np.mean(values**2)))


def _four_branch_summary_metric(rows: list[dict[str, Any]]) -> float:
    values = np.asarray([float(row["rms_error"]) for row in rows], dtype=float)
    return float(np.sqrt(np.mean(values**2)))


def _correlator_fit_error(rows: list[dict[str, Any]]) -> dict[str, float]:
    exact = np.asarray(
        [-math.cos(math.radians(2.0 * (float(row["a_deg"]) - float(row["b_deg"])))) for row in rows],
        dtype=float,
    )
    empirical = np.asarray([float(row["correlator_empirical"]) for row in rows], dtype=float)
    errors = empirical - exact
    return {
        "rms_error": float(np.sqrt(np.mean(errors**2))),
        "max_abs_error": float(np.max(np.abs(errors))),
    }


def _mismatch_rows_at_levels(rows: list[dict[str, Any]], levels: tuple[float, ...]) -> list[dict[str, Any]]:
    return [
        {
            "kind": row["kind"],
            "level": row["level"],
            "mean_rms_error": row["mean_rms_error"],
            "max_correlator_error": row["max_correlator_error"],
            "chsh_abs_error": row["chsh_abs_error"],
        }
        for row in rows
        if float(row["level"]) in levels
    ]


def _write_summary_csv(path: Path, summary_metrics: dict[str, Any]) -> None:
    rows = [
        {"metric": "two_branch_rms_winner_law_error", "value": summary_metrics["two_branch_rms_winner_law_error"]},
        {"metric": "four_branch_rms_weight_error", "value": summary_metrics["four_branch_rms_weight_error"]},
        {"metric": "correlator_fit_rms_error", "value": summary_metrics["correlator_fit_rms_error"]},
        {"metric": "correlator_fit_max_abs_error", "value": summary_metrics["correlator_fit_max_abs_error"]},
        {"metric": "chsh_exact", "value": summary_metrics["chsh_exact"]},
        {"metric": "chsh_empirical", "value": summary_metrics["chsh_empirical"]},
        {"metric": "chsh_abs_error", "value": summary_metrics["chsh_abs_error"]},
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(rows)


def _write_mismatch_csv(path: Path, mismatch_rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["kind", "level", "mean_rms_error", "max_correlator_error", "chsh_abs_error"])
        writer.writeheader()
        writer.writerows(mismatch_rows)


def _write_markdown_report(
    path: Path,
    *,
    summary_metrics: dict[str, Any],
    detector_spec: dict[str, Any],
    summary_source: str,
    mismatch_rows: list[dict[str, Any]],
    outputs: dict[str, Any],
) -> None:
    top_row = detector_spec["search_summary_row"]
    lines = [
        "# Detector Integration Summary",
        "",
        "## Metrics",
        "",
        f"- Two-branch RMS winner-law error: {summary_metrics['two_branch_rms_winner_law_error']:.6f}",
        f"- Four-branch RMS weight error: {summary_metrics['four_branch_rms_weight_error']:.6f}",
        f"- Correlator fit RMS error vs `-cos 2(a-b)`: {summary_metrics['correlator_fit_rms_error']:.6f}",
        f"- Correlator fit max abs error vs `-cos 2(a-b)`: {summary_metrics['correlator_fit_max_abs_error']:.6f}",
        f"- CHSH exact: {summary_metrics['chsh_exact']:.6f}",
        f"- CHSH empirical: {summary_metrics['chsh_empirical']:.6f}",
        f"- CHSH absolute error: {summary_metrics['chsh_abs_error']:.6f}",
        "",
        "## Mismatch Sensitivity",
        "",
        "| kind | level | mean RMS error | max correlator error | CHSH abs error |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in mismatch_rows:
        lines.append(
            f"| {row['kind']} | {100.0 * float(row['level']):.0f}% | {float(row['mean_rms_error']):.6f} | "
            f"{float(row['max_correlator_error']):.6f} | {float(row['chsh_abs_error']):.6f} |"
        )

    lines.extend(
        [
            "",
            "## Top Shot Trigger Parameter Set",
            "",
            f"- Source summary: `{summary_source}`",
            f"- Search score: {float(top_row['score']):.6f}",
            f"- Search race RMS error: {float(top_row['race_rms_error']):.6f}",
            f"- Search linearity RMS error: {float(top_row['linearity_rms_rel']):.6f}",
            f"- Search dark-count rate: {float(top_row['dark_count_rate']):.6f}",
            f"- Model params: `{json.dumps(detector_spec['model_params'], sort_keys=True)}`",
            f"- Integration envelope: `{json.dumps(outputs['envelope_params'], sort_keys=True)}`",
            "",
            "## Artifacts",
            "",
            f"- Two-branch summary: `{outputs['two_branch_csv']}`",
            f"- Four-branch summary: `{outputs['four_branch_csv']}`",
            f"- Mismatch summary: `{outputs['mismatch_csv']}`",
            f"- Two-branch plot: `{outputs['two_branch_plot']}`",
            f"- Four-branch weights plot: `{outputs['four_branch_weights_plot']}`",
            f"- Correlator plot: `{outputs['correlator_plot']}`",
            f"- CHSH plot: `{outputs['chsh_plot']}`",
            f"- Mismatch plot: `{outputs['mismatch_plot']}`",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_detector_integration_summary_report(
    outdir: str | Path,
    *,
    detector_next_summary_csv: str | Path = "artifacts/detector_next/results_summary.csv",
    n_two_branch_trials: int = 4_000,
    n_four_branch_trials: int = 6_000,
    seed: int = 20260402,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)

    detector_spec = load_top_shot_trigger_spec(detector_next_summary_csv)
    detector_model_spec = {"family": detector_spec["family"], "model_params": dict(detector_spec["model_params"])}

    two_outputs = run_two_branch_state_sweep(
        output_dir / "two_branch",
        detector_family="shot_trigger",
        detector_spec=detector_model_spec,
        envelope_params=dict(TWO_BRANCH_ENVELOPE),
        n_trials=n_two_branch_trials,
        seed=seed,
    )
    four_outputs = run_four_branch_angle_sweep(
        output_dir / "four_branch",
        detector_family="shot_trigger",
        detector_spec=detector_model_spec,
        envelope_params=dict(FOUR_BRANCH_ENVELOPE),
        n_trials=n_four_branch_trials,
        seed=seed + 10_000,
    )

    correlator_metrics = _correlator_fit_error(four_outputs["rows"])
    mismatch_rows = _mismatch_rows_at_levels(four_outputs["mismatch_rows"], levels=(0.02, 0.05))
    summary_metrics = {
        "two_branch_rms_winner_law_error": _two_branch_summary_metric(two_outputs["rows"]),
        "four_branch_rms_weight_error": _four_branch_summary_metric(four_outputs["rows"]),
        "correlator_fit_rms_error": correlator_metrics["rms_error"],
        "correlator_fit_max_abs_error": correlator_metrics["max_abs_error"],
        "chsh_exact": float(four_outputs["chsh"]["exact_s"]),
        "chsh_empirical": float(four_outputs["chsh"]["empirical_s"]),
        "chsh_abs_error": float(four_outputs["chsh"]["abs_error"]),
    }

    summary_csv = output_dir / "summary_metrics.csv"
    _write_summary_csv(summary_csv, summary_metrics)

    mismatch_csv = output_dir / "mismatch_summary.csv"
    _write_mismatch_csv(mismatch_csv, mismatch_rows)

    summary_json = output_dir / "summary_report.json"
    summary_json.write_text(
        json.dumps(
            {
                "summary_metrics": summary_metrics,
                "mismatch_rows": mismatch_rows,
                "top_shot_trigger": detector_spec,
                "two_branch": {"csv": two_outputs["csv"], "json": two_outputs["json"], "plot": two_outputs["plot"]},
                "four_branch": {
                    "csv": four_outputs["csv"],
                    "mismatch_csv": four_outputs["mismatch_csv"],
                    "json": four_outputs["json"],
                    "weights_plot": four_outputs["weights_plot"],
                    "correlator_plot": four_outputs["correlator_plot"],
                    "chsh_plot": four_outputs["chsh_plot"],
                    "mismatch_plot": four_outputs["mismatch_plot"],
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    summary_md = output_dir / "summary_report.md"
    _write_markdown_report(
        summary_md,
        summary_metrics=summary_metrics,
        detector_spec=detector_spec,
        summary_source=str(detector_next_summary_csv),
        mismatch_rows=mismatch_rows,
        outputs={
            "two_branch_csv": two_outputs["csv"],
            "four_branch_csv": four_outputs["csv"],
            "mismatch_csv": str(mismatch_csv),
            "two_branch_plot": two_outputs["plot"],
            "four_branch_weights_plot": four_outputs["weights_plot"],
            "correlator_plot": four_outputs["correlator_plot"],
            "chsh_plot": four_outputs["chsh_plot"],
            "mismatch_plot": four_outputs["mismatch_plot"],
            "envelope_params": four_outputs["envelope_params"],
        },
    )

    return {
        "summary_md": str(summary_md),
        "summary_json": str(summary_json),
        "summary_csv": str(summary_csv),
        "mismatch_csv": str(mismatch_csv),
        "two_branch_csv": two_outputs["csv"],
        "four_branch_csv": four_outputs["csv"],
        "top_shot_trigger_params": detector_spec["model_params"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a detector integration summary report using the top shot_trigger candidate.")
    parser.add_argument("--outdir", default="artifacts/detector_integration/summary_report")
    parser.add_argument("--detector-next-summary", default="artifacts/detector_next/results_summary.csv")
    parser.add_argument("--two-branch-trials", type=int, default=4_000)
    parser.add_argument("--four-branch-trials", type=int, default=6_000)
    args = parser.parse_args()

    print(
        json.dumps(
            build_detector_integration_summary_report(
                args.outdir,
                detector_next_summary_csv=args.detector_next_summary,
                n_two_branch_trials=args.two_branch_trials,
                n_four_branch_trials=args.four_branch_trials,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
