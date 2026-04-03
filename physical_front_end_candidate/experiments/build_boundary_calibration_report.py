from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from detector_integration.experiments.run_summary_report import load_top_shot_trigger_spec

from physical_front_end_candidate.boundary_calibration import (
    CalibratedBoundaryConfig,
    freeze_boundary_note_data,
    resolved_calibrated_boundary_config,
    run_calibrated_boundary_case,
)
from physical_front_end_candidate.boundary_diagnosis import run_trace_handoff, scale_trace_power, truncate_trace
from physical_front_end_candidate.metrics import fraction_error_metrics
from physical_front_end_candidate.plots import plot_calibrated_frequency, plot_exposure_sweep, plot_gain_sweep
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


def _sweep_summary(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    grouped: dict[float, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(float(row[key]), []).append(row)
    summary_rows = []
    for value, case_rows in sorted(grouped.items()):
        summary_rows.append(
            {
                key: value,
                "winner_rms_error": float(np.sqrt(np.mean([float(row["rms_error"]) ** 2 for row in case_rows]))),
                "winner_max_error": float(np.max([float(row["max_abs_error"]) for row in case_rows])),
                "mean_decisive_fraction": float(np.mean([float(row["decisive_fraction"]) for row in case_rows])),
                "max_branch_bias": float(np.max([abs(float(row["branch_bias_p1"])) for row in case_rows])),
            }
        )
    return summary_rows


def _classify_calibration(calibrated: dict[str, Any], gain_summary: list[dict[str, Any]], exposure_summary: list[dict[str, Any]]) -> dict[str, str]:
    calibrated_pass = float(calibrated["winner_rms_error"]) < 0.03 and float(calibrated["winner_max_error"]) < 0.05
    local_max_rms = max([float(row["winner_rms_error"]) for row in gain_summary + exposure_summary], default=np.inf)
    local_min_decisive = min([float(row["mean_decisive_fraction"]) for row in gain_summary + exposure_summary], default=0.0)
    local_max_bias = max([float(row["max_branch_bias"]) for row in gain_summary + exposure_summary], default=np.inf)
    if calibrated_pass and local_max_rms < 0.05 and local_min_decisive > 0.02 and local_max_bias < 0.08:
        return {
            "outcome": "proceed",
            "next_ticket": "Extend the calibrated physical/SPICE front-end candidate toward either a four-branch physical candidate or a more explicit resonant front-end realization, while keeping the frozen detector+latch boundary fixed.",
        }
    if calibrated_pass:
        return {
            "outcome": "proceed cautiously",
            "next_ticket": "Proceed with the next physical/SPICE front-end phase, but preserve and monitor the documented gain/exposure tolerances.",
        }
    return {
        "outcome": "do not proceed",
        "next_ticket": "Revisit detector-boundary abstraction assumptions before further front-end scaling.",
    }


def _summary_markdown(
    *,
    config: CalibratedBoundaryConfig,
    calibrated_summary: dict[str, Any],
    classification: dict[str, str],
    outputs: dict[str, str],
) -> str:
    return "\n".join(
        [
            "# Front-End Detector Boundary Calibration Summary",
            "",
            "## Frozen Contract",
            "",
            f"- Export mode: `{config.export_mode}`",
            f"- Gain: {config.gain:.3f}x",
            f"- Exposure: {config.exposure_s:.3f}s",
            f"- RMS winner-law error: {float(calibrated_summary['winner_rms_error']):.6f}",
            f"- Max winner-law error: {float(calibrated_summary['winner_max_error']):.6f}",
            f"- Mean decisive fraction: {float(calibrated_summary['mean_decisive_fraction']):.6f}",
            "",
            "## Decision",
            "",
            f"- Outcome: `{classification['outcome']}`",
            f"- Next ticket: {classification['next_ticket']}",
            "",
            "## Artifacts",
            "",
            f"- Calibrated run: `{outputs['calibrated_csv']}`",
            f"- Local gain sweep: `{outputs['gain_csv']}`",
            f"- Local exposure sweep: `{outputs['exposure_csv']}`",
            f"- Frozen boundary note: `{outputs['note_md']}`",
            "",
        ]
    )


def build_physical_front_end_boundary_calibration_report(
    outdir: str | Path = "artifacts/physical_front_end_boundary_calibration",
    *,
    detector_next_summary_csv: str | Path = "artifacts/detector_next/results_summary.csv",
    n_trials: int = 120,
    seed: int = 20260403,
    calibration_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    calibrated_dir = output_dir / "calibrated_run"
    gain_dir = output_dir / "local_gain_sweep"
    exposure_dir = output_dir / "local_exposure_sweep"
    for directory in (calibrated_dir, gain_dir, exposure_dir):
        directory.mkdir(parents=True, exist_ok=True)

    config = resolved_calibrated_boundary_config(calibration_config)
    detector_spec = load_top_shot_trigger_spec(detector_next_summary_csv)
    detector_model_spec = {"family": detector_spec["family"], "model_params": dict(detector_spec["model_params"])}

    calibrated_case_rows: list[dict[str, Any]] = []
    gain_rows: list[dict[str, Any]] = []
    exposure_rows: list[dict[str, Any]] = []

    for case_index, case in enumerate(representative_physical_cases()):
        calibrated = run_calibrated_boundary_case(
            case["state"],
            case["analyzer"],
            detector_model_spec,
            n_trials=n_trials,
            seed=seed + 101 * case_index,
            config=asdict(config),
        )
        run = calibrated["run"]
        errors = np.asarray(run["empirical_frequencies"], dtype=float) - np.asarray(run["exact_weights"], dtype=float)
        calibrated_case_rows.append(
            {
                "case": case["case"],
                "exact_p1": float(run["exact_weights"][0]),
                "empirical_p1": float(run["empirical_frequencies"][0]),
                "exact_p2": float(run["exact_weights"][1]),
                "empirical_p2": float(run["empirical_frequencies"][1]),
                "rms_error": float(run["metrics"]["rms_error"]),
                "max_abs_error": float(run["metrics"]["max_abs_error"]),
                "decisive_fraction": float(run["decisive_fraction"]),
                "branch_bias_p1": float(errors[0]),
            }
        )

        base_trace = calibrated["trace"]
        for gain_index, gain in enumerate(config.gain_sweep):
            sweep_trace = truncate_trace(scale_trace_power(base_trace, gain / config.gain), config.exposure_s)
            sweep_run = run_trace_handoff(sweep_trace, detector_model_spec, n_trials=n_trials, seed=seed + 10_000 + 101 * case_index + gain_index)
            errors = np.asarray(sweep_run["empirical_frequencies"], dtype=float) - np.asarray(sweep_run["exact_weights"], dtype=float)
            gain_rows.append(
                {
                    "case": case["case"],
                    "gain": float(gain),
                    "exposure_s": float(config.exposure_s),
                    "rms_error": float(sweep_run["metrics"]["rms_error"]),
                    "max_abs_error": float(sweep_run["metrics"]["max_abs_error"]),
                    "decisive_fraction": float(sweep_run["decisive_fraction"]),
                    "branch_bias_p1": float(errors[0]),
                }
            )

        for exposure_index, exposure_s in enumerate(config.exposure_sweep_s):
            sweep_trace = truncate_trace(base_trace, exposure_s)
            sweep_run = run_trace_handoff(sweep_trace, detector_model_spec, n_trials=n_trials, seed=seed + 20_000 + 101 * case_index + exposure_index)
            errors = np.asarray(sweep_run["empirical_frequencies"], dtype=float) - np.asarray(sweep_run["exact_weights"], dtype=float)
            exposure_rows.append(
                {
                    "case": case["case"],
                    "gain": float(config.gain),
                    "exposure_s": float(exposure_s),
                    "rms_error": float(sweep_run["metrics"]["rms_error"]),
                    "max_abs_error": float(sweep_run["metrics"]["max_abs_error"]),
                    "decisive_fraction": float(sweep_run["decisive_fraction"]),
                    "branch_bias_p1": float(errors[0]),
                }
            )

    calibrated_csv = calibrated_dir / "calibrated_run.csv"
    _write_csv(calibrated_csv, calibrated_case_rows)
    gain_csv = gain_dir / "local_gain_sweep.csv"
    _write_csv(gain_csv, gain_rows)
    exposure_csv = exposure_dir / "local_exposure_sweep.csv"
    _write_csv(exposure_csv, exposure_rows)

    calibrated_summary = {
        "winner_rms_error": float(np.sqrt(np.mean([float(row["rms_error"]) ** 2 for row in calibrated_case_rows]))),
        "winner_max_error": float(np.max([float(row["max_abs_error"]) for row in calibrated_case_rows])),
        "mean_decisive_fraction": float(np.mean([float(row["decisive_fraction"]) for row in calibrated_case_rows])),
        "max_branch_bias": float(np.max([abs(float(row["branch_bias_p1"])) for row in calibrated_case_rows])),
    }
    gain_summary = _sweep_summary(gain_rows, "gain")
    exposure_summary = _sweep_summary(exposure_rows, "exposure_s")
    classification = _classify_calibration(calibrated_summary, gain_summary, exposure_summary)

    note_data = freeze_boundary_note_data(detector_spec)
    note_md = output_dir / "frozen_boundary_note.md"
    note_md.write_text(
        "\n".join(
            [
                "# Frozen Boundary Note",
                "",
                "## Selected Export Mode",
                "",
                f"- `{config.export_mode}`",
                "",
                "## Selected Gain And Exposure",
                "",
                f"- Gain: {config.gain:.3f}x",
                f"- Exposure: {config.exposure_s:.3f}s",
                "",
                "## Detector Reference",
                "",
                f"- Detector family: `{note_data['detector_family']}`",
                f"- Detector params: `{json.dumps(note_data['detector_model_params'], sort_keys=True)}`",
                "",
                "## Latch Reference",
                "",
                f"- Input delay: {note_data['latch_config']['input_delay_s']:.3e}s",
                f"- Tie window: {note_data['latch_config']['tie_window_s']:.3e}s",
                f"- Settle time: {note_data['latch_config']['settle_time_s']:.3e}s",
                f"- Priority order: `{note_data['latch_config']['priority_order']}`",
                "",
                "## Output Semantics",
                "",
                f"- `winner_index`: {note_data['winner_semantics']['winner_index']}",
                f"- `winner_valid`: {note_data['winner_semantics']['winner_valid']}",
                "",
                "## Reset Semantics",
                "",
                f"- {note_data['reset_semantics']}",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    gain_error_plot = gain_dir / "winner_law_error_vs_gain.png"
    plot_gain_sweep(gain_rows, metric_key="rms_error", title="Winner-law error vs gain near calibrated point", ylabel="RMS error").savefig(gain_error_plot)
    gain_decisive_plot = gain_dir / "decisive_fraction_vs_gain.png"
    plot_gain_sweep(gain_rows, metric_key="decisive_fraction", title="Decisive fraction vs gain near calibrated point", ylabel="Decisive fraction").savefig(gain_decisive_plot)
    exposure_error_plot = exposure_dir / "winner_law_error_vs_exposure.png"
    plot_exposure_sweep(exposure_rows, metric_key="rms_error", title="Winner-law error vs exposure near calibrated point", ylabel="RMS error").savefig(exposure_error_plot)
    exposure_decisive_plot = exposure_dir / "decisive_fraction_vs_exposure.png"
    plot_exposure_sweep(exposure_rows, metric_key="decisive_fraction", title="Decisive fraction vs exposure near calibrated point", ylabel="Decisive fraction").savefig(exposure_decisive_plot)
    calibrated_plot = calibrated_dir / "calibrated_exact_vs_empirical.png"
    plot_calibrated_frequency(calibrated_case_rows).savefig(calibrated_plot)

    summary_metrics = {
        "calibrated_winner_rms_error": calibrated_summary["winner_rms_error"],
        "calibrated_winner_max_error": calibrated_summary["winner_max_error"],
        "calibrated_mean_decisive_fraction": calibrated_summary["mean_decisive_fraction"],
        "local_gain_max_rms_error": float(np.max([row["winner_rms_error"] for row in gain_summary])),
        "local_exposure_max_rms_error": float(np.max([row["winner_rms_error"] for row in exposure_summary])),
    }

    summary_csv = output_dir / "summary_metrics.csv"
    _write_csv(summary_csv, [{"metric": key, "value": value} for key, value in summary_metrics.items()])
    summary_json = output_dir / "summary_metrics.json"
    summary_json.write_text(
        json.dumps(
            {
                "config": asdict(config),
                "summary_metrics": summary_metrics,
                "calibrated_summary": calibrated_summary,
                "gain_summary": gain_summary,
                "exposure_summary": exposure_summary,
                "classification": classification,
                "frozen_boundary_note": str(note_md),
            },
            indent=2,
            default=_json_default,
        )
        + "\n",
        encoding="utf-8",
    )

    outputs = {
        "calibrated_csv": str(calibrated_csv),
        "gain_csv": str(gain_csv),
        "exposure_csv": str(exposure_csv),
        "note_md": str(note_md),
    }
    summary_md = output_dir / "summary_report.md"
    summary_md.write_text(_summary_markdown(config=config, calibrated_summary=calibrated_summary, classification=classification, outputs=outputs) + "\n", encoding="utf-8")

    return {
        "summary_md": str(summary_md),
        "summary_json": str(summary_json),
        "summary_csv": str(summary_csv),
        "frozen_boundary_note_md": str(note_md),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the physical front-end detector boundary calibration report.")
    parser.add_argument("--outdir", default="artifacts/physical_front_end_boundary_calibration")
    parser.add_argument("--detector-next-summary", default="artifacts/detector_next/results_summary.csv")
    parser.add_argument("--trials", type=int, default=120)
    args = parser.parse_args()
    build_physical_front_end_boundary_calibration_report(
        args.outdir,
        detector_next_summary_csv=args.detector_next_summary,
        n_trials=args.trials,
    )


if __name__ == "__main__":
    main()
