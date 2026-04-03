from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from detector_integration.experiments.run_summary_report import load_top_shot_trigger_spec

from physical_front_end_candidate.boundary_diagnosis import (
    BOUNDARY_EXPOSURE_SWEEP_S,
    BOUNDARY_GAIN_SWEEP,
    classify_boundary_outcome,
    expected_click_count,
    materialize_exported_trace,
    run_trace_handoff,
    scale_trace_power,
    selected_handoff_export_config,
    synthetic_common_envelope_trace,
    truncate_trace,
)
from physical_front_end_candidate.plots import (
    plot_diagnosis_summary,
    plot_expected_click_summary,
    plot_exposure_sweep,
    plot_gain_sweep,
    plot_synthetic_vs_physical,
)
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


def _summary_by_gain(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[float, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(float(row["gain"]), []).append(row)
    summary = []
    for gain, values in sorted(grouped.items()):
        summary.append(
            {
                "gain": gain,
                "mean_decisive_fraction": float(np.mean([float(row["decisive_fraction"]) for row in values])),
                "winner_rms_error": float(np.sqrt(np.mean([float(row["rms_error"]) ** 2 for row in values]))),
                "winner_max_error": float(np.max([float(row["max_abs_error"]) for row in values])),
                "mean_mu": float(np.mean([float(row["mean_mu"]) for row in values])),
            }
        )
    return summary


def _summary_by_exposure(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[float, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(float(row["exposure_s"]), []).append(row)
    summary = []
    for exposure_s, values in sorted(grouped.items()):
        summary.append(
            {
                "exposure_s": exposure_s,
                "mean_decisive_fraction": float(np.mean([float(row["decisive_fraction"]) for row in values])),
                "winner_rms_error": float(np.sqrt(np.mean([float(row["rms_error"]) ** 2 for row in values]))),
                "winner_max_error": float(np.max([float(row["max_abs_error"]) for row in values])),
                "mean_mu": float(np.mean([float(row["mean_mu"]) for row in values])),
            }
        )
    return summary


def _best_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return min(rows, key=lambda row: (float(row["rms_error"]), float(row["max_abs_error"]), -float(row["decisive_fraction"])))


def _summary_markdown(
    *,
    classification: dict[str, str],
    best_physical: dict[str, Any],
    best_synthetic: dict[str, Any],
    summary_metrics: dict[str, Any],
    outputs: dict[str, str],
) -> str:
    return "\n".join(
        [
            "# Front-End Detector Boundary Diagnosis Summary",
            "",
            "## Classification",
            "",
            f"- Outcome: `{classification['classification']}`",
            f"- Recommended next ticket: {classification['next_ticket']}",
            "",
            "## Best Physical Configuration",
            "",
            f"- Gain: {float(best_physical['gain']):.2f}x",
            f"- Exposure: {float(best_physical['exposure_s']):.3f}s",
            f"- Winner-law RMS error: {float(best_physical['rms_error']):.6f}",
            f"- Winner-law max error: {float(best_physical['max_abs_error']):.6f}",
            f"- Decisive fraction: {float(best_physical['decisive_fraction']):.6f}",
            f"- Mean expected click count: {float(best_physical['mean_mu']):.6f}",
            "",
            "## Best Synthetic Configuration",
            "",
            f"- Gain: {float(best_synthetic['gain']):.2f}x",
            f"- Winner-law RMS error: {float(best_synthetic['rms_error']):.6f}",
            f"- Winner-law max error: {float(best_synthetic['max_abs_error']):.6f}",
            f"- Decisive fraction: {float(best_synthetic['decisive_fraction']):.6f}",
            f"- Mean expected click count: {float(best_synthetic['mean_mu']):.6f}",
            "",
            "## Artifacts",
            "",
            f"- Scale sweep: `{outputs['scale_csv']}`",
            f"- Time-window sweep: `{outputs['time_csv']}`",
            f"- Expected click count: `{outputs['expected_csv']}`",
            f"- Synthetic comparison: `{outputs['synthetic_csv']}`",
            f"- Analysis note: `{outputs['note_md']}`",
            "",
        ]
    )


def build_physical_front_end_boundary_diagnosis_report(
    outdir: str | Path = "artifacts/physical_front_end_boundary_diagnosis",
    *,
    detector_next_summary_csv: str | Path = "artifacts/detector_next/results_summary.csv",
    n_trials: int = 120,
    seed: int = 20260403,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    scale_dir = output_dir / "scale_sweep"
    time_dir = output_dir / "time_window_sweep"
    expected_dir = output_dir / "expected_click_count"
    synthetic_dir = output_dir / "synthetic_envelope"
    for directory in (scale_dir, time_dir, expected_dir, synthetic_dir):
        directory.mkdir(parents=True, exist_ok=True)

    detector_spec = load_top_shot_trigger_spec(detector_next_summary_csv)
    detector_model_spec = {"family": detector_spec["family"], "model_params": dict(detector_spec["model_params"])}
    export_config = selected_handoff_export_config()

    scale_rows: list[dict[str, Any]] = []
    time_rows: list[dict[str, Any]] = []
    expected_rows: list[dict[str, Any]] = []
    synthetic_rows: list[dict[str, Any]] = []

    for case_index, case in enumerate(representative_physical_cases()):
        base_trace = materialize_exported_trace(case["state"], case["analyzer"], export_config=export_config)
        physical_trace = {**base_trace, "trace_kind": "physical_export"}
        synthetic_trace = synthetic_common_envelope_trace(base_trace)

        for gain_index, gain in enumerate(BOUNDARY_GAIN_SWEEP):
            scaled_physical = scale_trace_power(physical_trace, gain)
            physical_click = expected_click_count(scaled_physical, detector_model_spec)
            physical_run = run_trace_handoff(scaled_physical, detector_model_spec, n_trials=n_trials, seed=seed + 101 * case_index + 17 * gain_index)
            physical_row = {
                "case": case["case"],
                "trace_kind": "physical_export",
                "gain": float(gain),
                "exposure_s": float(np.asarray(scaled_physical["time_s"], dtype=float)[-1]),
                "decisive_fraction": float(physical_run["decisive_fraction"]),
                "rms_error": float(physical_run["metrics"]["rms_error"]),
                "max_abs_error": float(physical_run["metrics"]["max_abs_error"]),
                "mean_mu": float(physical_click["mean_mu"]),
                "min_mu": float(physical_click["min_mu"]),
                "max_mu": float(physical_click["max_mu"]),
            }
            scale_rows.append(physical_row)
            expected_rows.append(dict(physical_row))

            scaled_synthetic = scale_trace_power(synthetic_trace, gain)
            synthetic_click = expected_click_count(scaled_synthetic, detector_model_spec)
            synthetic_run = run_trace_handoff(scaled_synthetic, detector_model_spec, n_trials=n_trials, seed=seed + 10_000 + 101 * case_index + 17 * gain_index)
            synthetic_rows.append(
                {
                    "case": case["case"],
                    "trace_kind": "synthetic_common_envelope",
                    "gain": float(gain),
                    "decisive_fraction": float(synthetic_run["decisive_fraction"]),
                    "rms_error": float(synthetic_run["metrics"]["rms_error"]),
                    "max_abs_error": float(synthetic_run["metrics"]["max_abs_error"]),
                    "mean_mu": float(synthetic_click["mean_mu"]),
                }
            )

        for exposure_index, exposure_s in enumerate(BOUNDARY_EXPOSURE_SWEEP_S):
            truncated = truncate_trace(physical_trace, exposure_s)
            click_summary = expected_click_count(truncated, detector_model_spec)
            run = run_trace_handoff(truncated, detector_model_spec, n_trials=n_trials, seed=seed + 20_000 + 97 * case_index + 13 * exposure_index)
            row = {
                "case": case["case"],
                "exposure_s": float(exposure_s),
                "gain": 1.0,
                "decisive_fraction": float(run["decisive_fraction"]),
                "rms_error": float(run["metrics"]["rms_error"]),
                "max_abs_error": float(run["metrics"]["max_abs_error"]),
                "mean_mu": float(click_summary["mean_mu"]),
                "min_mu": float(click_summary["min_mu"]),
                "max_mu": float(click_summary["max_mu"]),
            }
            time_rows.append(row)
            expected_rows.append({**row, "trace_kind": "physical_export_exposure"})

    scale_csv = scale_dir / "scale_sweep.csv"
    _write_csv(scale_csv, scale_rows)
    time_csv = time_dir / "time_window_sweep.csv"
    _write_csv(time_csv, time_rows)
    expected_csv = expected_dir / "expected_click_count.csv"
    _write_csv(expected_csv, expected_rows)
    synthetic_csv = synthetic_dir / "synthetic_comparison.csv"
    _write_csv(synthetic_csv, synthetic_rows)

    scale_summary = _summary_by_gain(scale_rows)
    exposure_summary = _summary_by_exposure(time_rows)
    synthetic_summary = _summary_by_gain(synthetic_rows)
    best_physical = _best_row(scale_rows + time_rows)
    best_synthetic = _best_row(synthetic_rows)
    classification = classify_boundary_outcome(
        best_physical={
            "winner_rms_error": best_physical["rms_error"],
            "winner_max_error": best_physical["max_abs_error"],
        },
        best_synthetic={
            "winner_rms_error": best_synthetic["rms_error"],
            "winner_max_error": best_synthetic["max_abs_error"],
        },
    )

    baseline_gain_row = next(row for row in scale_summary if float(row["gain"]) == 1.0)
    summary_metrics = {
        "baseline_winner_rms_error": float(baseline_gain_row["winner_rms_error"]),
        "baseline_decisive_fraction": float(baseline_gain_row["mean_decisive_fraction"]),
        "best_physical_winner_rms_error": float(best_physical["rms_error"]),
        "best_physical_decisive_fraction": float(best_physical["decisive_fraction"]),
        "best_synthetic_winner_rms_error": float(best_synthetic["rms_error"]),
        "best_synthetic_decisive_fraction": float(best_synthetic["decisive_fraction"]),
    }

    note_md = output_dir / "boundary_diagnosis_note.md"
    note_md.write_text(
        "\n".join(
            [
                "# Boundary Diagnosis Note",
                "",
                "## Held Fixed",
                "",
                "- Physical front-end topology from ticket 150.",
                "- Selected detector-facing export mode from ticket 151: `piecewise:linear:20.0ms`.",
                "- Frozen detector family and validated latch abstraction.",
                "",
                "## Varied",
                "",
                "- Explicit branch-power gain sweep on exported traces.",
                "- Detector observation window sweep on exported traces.",
                "- Synthetic common-envelope traces built from measured gamma and exact branch weights.",
                "",
                "## Implication",
                "",
                f"- Classification: `{classification['classification']}`.",
                f"- Recommended next action: {classification['next_ticket']}",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    decisive_gain_plot = scale_dir / "decisive_fraction_vs_gain.png"
    plot_gain_sweep(scale_rows, metric_key="decisive_fraction", title="Decisive fraction vs power-scale gain", ylabel="Decisive fraction").savefig(decisive_gain_plot)
    error_gain_plot = scale_dir / "winner_rms_error_vs_gain.png"
    plot_gain_sweep(scale_rows, metric_key="rms_error", title="Winner-law RMS error vs power-scale gain", ylabel="RMS error").savefig(error_gain_plot)
    decisive_time_plot = time_dir / "decisive_fraction_vs_exposure.png"
    plot_exposure_sweep(time_rows, metric_key="decisive_fraction", title="Decisive fraction vs exposure window", ylabel="Decisive fraction").savefig(decisive_time_plot)
    error_time_plot = time_dir / "winner_rms_error_vs_exposure.png"
    plot_exposure_sweep(time_rows, metric_key="rms_error", title="Winner-law RMS error vs exposure window", ylabel="RMS error").savefig(error_time_plot)
    expected_plot = expected_dir / "expected_click_count_summary.png"
    plot_expected_click_summary(scale_summary).savefig(expected_plot)
    synthetic_plot = synthetic_dir / "synthetic_vs_physical_rms_error.png"
    plot_synthetic_vs_physical(scale_rows + synthetic_rows, metric_key="rms_error", title="Synthetic vs physical winner-law RMS error", ylabel="RMS error").savefig(synthetic_plot)
    diagnosis_plot = output_dir / "diagnosis_summary.png"
    plot_diagnosis_summary(
        [
            {
                "label": "baseline",
                "winner_rms_error": float(baseline_gain_row["winner_rms_error"]),
                "decisive_fraction": float(baseline_gain_row["mean_decisive_fraction"]),
            },
            {
                "label": "best physical",
                "winner_rms_error": float(best_physical["rms_error"]),
                "decisive_fraction": float(best_physical["decisive_fraction"]),
            },
            {
                "label": "best synthetic",
                "winner_rms_error": float(best_synthetic["rms_error"]),
                "decisive_fraction": float(best_synthetic["decisive_fraction"]),
            },
        ]
    ).savefig(diagnosis_plot)

    summary_csv = output_dir / "summary_metrics.csv"
    _write_csv(summary_csv, [{"metric": key, "value": value} for key, value in summary_metrics.items()])
    summary_json = output_dir / "summary_metrics.json"
    summary_json.write_text(
        json.dumps(
            {
                "summary_metrics": summary_metrics,
                "classification": classification,
                "best_physical": best_physical,
                "best_synthetic": best_synthetic,
                "scale_summary": scale_summary,
                "exposure_summary": exposure_summary,
                "synthetic_summary": synthetic_summary,
                "note_md": str(note_md),
            },
            indent=2,
            default=_json_default,
        )
        + "\n",
        encoding="utf-8",
    )

    outputs = {
        "scale_csv": str(scale_csv),
        "time_csv": str(time_csv),
        "expected_csv": str(expected_csv),
        "synthetic_csv": str(synthetic_csv),
        "note_md": str(note_md),
    }
    summary_md = output_dir / "summary_report.md"
    summary_md.write_text(
        _summary_markdown(
            classification=classification,
            best_physical=best_physical,
            best_synthetic=best_synthetic,
            summary_metrics=summary_metrics,
            outputs=outputs,
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "summary_md": str(summary_md),
        "summary_json": str(summary_json),
        "summary_csv": str(summary_csv),
        "boundary_diagnosis_note_md": str(note_md),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the physical front-end detector boundary diagnosis report.")
    parser.add_argument("--outdir", default="artifacts/physical_front_end_boundary_diagnosis")
    parser.add_argument("--detector-next-summary", default="artifacts/detector_next/results_summary.csv")
    parser.add_argument("--trials", type=int, default=120)
    args = parser.parse_args()
    build_physical_front_end_boundary_diagnosis_report(
        args.outdir,
        detector_next_summary_csv=args.detector_next_summary,
        n_trials=args.trials,
    )


if __name__ == "__main__":
    main()
