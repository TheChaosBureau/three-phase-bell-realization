from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from detector_integration.experiments.run_summary_report import load_top_shot_trigger_spec

from physical_front_end_candidate.spice_driven_baseline_reconciliation import (
    ROBUSTNESS_NOMINAL_BASELINE,
    VALIDATED_SPICE_DRIVEN_BASELINE,
    BaselineRunSpec,
    build_signature_from_spec,
    run_spice_driven_baseline_reconciliation,
)
from physical_front_end_candidate.spice_driven_baseline_reconciliation_plots import (
    plot_configuration_difference_summary,
    plot_metric_difference_breakdown,
    plot_reproduction_vs_reference,
    plot_side_by_side_metric_comparison,
)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({key for row in rows for key in row.keys()}) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        if rows:
            writer.writerows(rows)


def _json_default(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, complex):
        return {"real": value.real, "imag": value.imag}
    return value


def _compact_report_payload(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary_metrics": dict(summary["summary_metrics"]),
        "root_cause": dict(summary["root_cause"]),
        "reference_run": dict(summary["reference_run"]),
        "nominal_run": dict(summary["nominal_run"]),
        "reproduction_run": dict(summary["reproduction_run"]),
        "reference_signature": dict(summary["reference_signature"]),
        "nominal_signature": dict(summary["nominal_signature"]),
        "reproduction_signature": dict(summary["reproduction_signature"]),
        "comparison_rows": list(summary["comparison_rows"]),
        "metric_rows": list(summary["metric_rows"]),
    }


def _read_metric_csv(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    metrics: dict[str, Any] = {}
    for row in rows:
        metric = str(row["metric"])
        value_text = str(row["value"])
        if value_text in {"True", "False"}:
            metrics[metric] = value_text == "True"
            continue
        try:
            metrics[metric] = float(value_text)
        except ValueError:
            metrics[metric] = value_text
    return metrics


def _artifact_reference_run(
    *,
    artifact_dir: Path,
    detector_spec: dict[str, Any],
    spec: BaselineRunSpec,
) -> dict[str, Any]:
    summary_metrics = _read_metric_csv(artifact_dir / "summary_metrics.csv")
    return {
        "spec": spec,
        "driver": f"artifact:{artifact_dir / 'summary_metrics.csv'}",
        "summary_metrics": summary_metrics,
        "signature": build_signature_from_spec(spec, detector_spec, driver=f"artifact:{artifact_dir / 'summary_metrics.csv'}"),
    }


def _artifact_nominal_run(
    *,
    artifact_dir: Path,
    detector_spec: dict[str, Any],
    spec: BaselineRunSpec,
) -> dict[str, Any]:
    source_metrics = _read_metric_csv(artifact_dir / "summary_metrics.csv")
    summary_metrics = {
        "winner_law_rms_error": source_metrics.get("baseline_winner_law_rms_error", float("nan")),
        "correlator_rms_error": source_metrics.get("baseline_correlator_rms_error", float("nan")),
        "chsh_abs_error": source_metrics.get("baseline_chsh_abs_error", float("nan")),
        "pre_click_transparency_rms_shift": source_metrics.get("baseline_pre_click_transparency_rms_shift", float("nan")),
    }
    return {
        "spec": spec,
        "driver": f"artifact:{artifact_dir / 'summary_metrics.csv'}",
        "summary_metrics": summary_metrics,
        "signature": build_signature_from_spec(spec, detector_spec, driver=f"artifact:{artifact_dir / 'summary_metrics.csv'}"),
    }


def _different_setting_lines(rows: list[dict[str, Any]]) -> list[str]:
    mismatches = [row for row in rows if not bool(row["matches"])]
    if not mismatches:
        return ["- None."]
    return [
        f"- `{row['setting_key']}` ({row['category']}): reference {row['reference_value_json']}, nominal {row['nominal_value_json']}"
        for row in mismatches
    ]


def _identical_setting_lines(rows: list[dict[str, Any]]) -> list[str]:
    matches = [row for row in rows if bool(row["matches"])]
    if not matches:
        return ["- None."]
    return [f"- `{row['setting_key']}` ({row['category']})" for row in matches]


def _summary_markdown(*, summary: dict[str, Any], outputs: dict[str, str]) -> str:
    metrics = summary["summary_metrics"]
    root_cause = summary["root_cause"]
    mismatch_counts = Counter(str(row["category"]) for row in summary["comparison_rows"] if not bool(row["matches"]))
    mismatch_line = ", ".join(f"{category}={count}" for category, count in sorted(mismatch_counts.items())) or "none"
    return "\n".join(
        [
            "# SPICE-Driven Baseline Reconciliation Summary",
            "",
            "## Compared Baselines",
            "",
            f"- Reference baseline A: `{summary['reference_signature']['label']}` ({summary['reference_signature']['driver']})",
            f"- Nominal robustness baseline B: `{summary['nominal_signature']['label']}` ({summary['nominal_signature']['driver']})",
            f"- Matched-settings reproduction: `{summary['reproduction_signature']['label']}`",
            "",
            "## Findings",
            "",
            f"- Root-cause classification: `{root_cause['classification']}`",
            f"- Recommendation: `{root_cause['recommendation']}`",
            f"- Reproduction matches reference: {bool(metrics['reproduction_matches_reference'])}",
            f"- Different setting count: {int(metrics['different_setting_count'])}",
            f"- Mismatch categories: {mismatch_line}",
            "",
            "## Key Metrics",
            "",
            f"- Winner-law RMS: reference {float(metrics['reference_winner_law_rms_error']):.6f}, nominal {float(metrics['nominal_winner_law_rms_error']):.6f}, reproduction {float(metrics['reproduction_winner_law_rms_error']):.6f}",
            f"- Correlator RMS: reference {float(metrics['reference_correlator_rms_error']):.6f}, nominal {float(metrics['nominal_correlator_rms_error']):.6f}, reproduction {float(metrics['reproduction_correlator_rms_error']):.6f}",
            f"- CHSH abs error: reference {float(metrics['reference_chsh_abs_error']):.6f}, nominal {float(metrics['nominal_chsh_abs_error']):.6f}, reproduction {float(metrics['reproduction_chsh_abs_error']):.6f}",
            "",
            "## Artifacts",
            "",
            f"- Comparison directory: `{outputs['comparison_dir']}`",
            f"- Reproduction directory: `{outputs['reproduction_dir']}`",
            f"- Comparison CSV: `{outputs['comparison_csv']}`",
            f"- Metric comparison CSV: `{outputs['metric_csv']}`",
            f"- Reconciliation note: `{outputs['reconciliation_note']}`",
            "",
        ]
    )


def _reconciliation_note_markdown(*, summary: dict[str, Any]) -> str:
    root_cause = summary["root_cause"]
    return "\n".join(
        [
            "# SPICE-Driven Baseline Reconciliation Note",
            "",
            "## What Was Compared",
            "",
            f"- Reference baseline A: `{summary['reference_signature']['label']}` with `n_trials={summary['reference_signature']['n_trials']}` and `seed={summary['reference_signature']['seed']}`.",
            f"- Nominal robustness baseline B: `{summary['nominal_signature']['label']}` with `n_trials={summary['nominal_signature']['n_trials']}` and `seed={summary['nominal_signature']['seed']}`.",
            f"- Reproduction run: robustness harness with reference baseline settings `n_trials={summary['reproduction_signature']['n_trials']}` and `seed={summary['reproduction_signature']['seed']}`.",
            "",
            "## Settings That Stayed Identical",
            "",
            *(_identical_setting_lines(list(summary["comparison_rows"]))),
            "",
            "## Settings That Differed",
            "",
            *(_different_setting_lines(list(summary["comparison_rows"]))),
            "",
            "## Reproduction Result",
            "",
            f"- Reproduction matches the earlier SPICE-driven baseline: {bool(summary['summary_metrics']['reproduction_matches_reference'])}.",
            f"- Winner-law RMS delta after matching settings: {float(summary['reproduction_run']['summary_metrics']['winner_law_rms_error']) - float(summary['reference_run']['summary_metrics']['winner_law_rms_error']):.6e}.",
            f"- Correlator RMS delta after matching settings: {float(summary['reproduction_run']['summary_metrics']['correlator_rms_error']) - float(summary['reference_run']['summary_metrics']['correlator_rms_error']):.6e}.",
            f"- CHSH abs delta after matching settings: {float(summary['reproduction_run']['summary_metrics']['chsh_abs_error']) - float(summary['reference_run']['summary_metrics']['chsh_abs_error']):.6e}.",
            "",
            "## Root Cause",
            "",
            f"- Classification: `{root_cause['classification']}`",
            f"- Reason: {root_cause['reason']}",
            "",
            "## Next Step",
            "",
            f"- {root_cause['recommendation']}.",
            "",
        ]
    )


def build_spice_driven_baseline_reconciliation_report(
    outdir: str | Path = "artifacts/spice_driven_baseline_reconciliation",
    *,
    detector_next_summary_csv: str | Path = "artifacts/detector_next/results_summary.csv",
    reference_artifact_dir: str | Path | None = None,
    nominal_artifact_dir: str | Path | None = None,
    reference_spec: BaselineRunSpec = VALIDATED_SPICE_DRIVEN_BASELINE,
    nominal_spec: BaselineRunSpec = ROBUSTNESS_NOMINAL_BASELINE,
    verbose_progress: bool = True,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    comparison_dir = output_dir / "comparison"
    reproduction_dir = output_dir / "reproduction"
    comparison_dir.mkdir(parents=True, exist_ok=True)
    reproduction_dir.mkdir(parents=True, exist_ok=True)

    detector_spec = load_top_shot_trigger_spec(detector_next_summary_csv)
    detector_model_spec = {
        "family": detector_spec["family"],
        "model_params": dict(detector_spec["model_params"]),
        "gain_scale": 2.0,
    }
    reference_run_override = None
    nominal_run_override = None
    if reference_artifact_dir is not None:
        resolved_reference_artifact_dir = Path(reference_artifact_dir)
        if (resolved_reference_artifact_dir / "summary_metrics.csv").exists():
            reference_run_override = _artifact_reference_run(
                artifact_dir=resolved_reference_artifact_dir,
                detector_spec=detector_model_spec,
                spec=reference_spec,
            )
    if nominal_artifact_dir is not None:
        resolved_nominal_artifact_dir = Path(nominal_artifact_dir)
        if (resolved_nominal_artifact_dir / "summary_metrics.csv").exists():
            nominal_run_override = _artifact_nominal_run(
                artifact_dir=resolved_nominal_artifact_dir,
                detector_spec=detector_model_spec,
                spec=nominal_spec,
            )
    summary = run_spice_driven_baseline_reconciliation(
        detector_model_spec,
        reference_spec=reference_spec,
        nominal_spec=nominal_spec,
        reference_run_override=reference_run_override,
        nominal_run_override=nominal_run_override,
        verbose_progress=verbose_progress,
    )

    comparison_csv = comparison_dir / "baseline_comparison.csv"
    metric_csv = comparison_dir / "metric_comparison.csv"
    _write_csv(comparison_csv, list(summary["comparison_rows"]))
    _write_csv(metric_csv, list(summary["metric_rows"]))
    _write_csv(
        output_dir / "summary_metrics.csv",
        [{"metric": key, "value": value} for key, value in summary["summary_metrics"].items()],
    )

    (comparison_dir / "reference_signature.json").write_text(
        json.dumps(summary["reference_signature"], indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    (comparison_dir / "nominal_signature.json").write_text(
        json.dumps(summary["nominal_signature"], indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    (reproduction_dir / "reproduction_signature.json").write_text(
        json.dumps(summary["reproduction_signature"], indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    (reproduction_dir / "reproduction_metrics.json").write_text(
        json.dumps(summary["reproduction_run"]["summary_metrics"], indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )

    summary_metrics_json = output_dir / "summary_metrics.json"
    report_payload = _compact_report_payload(summary)
    with summary_metrics_json.open("w", encoding="utf-8") as handle:
        json.dump(report_payload, handle, indent=2, default=_json_default)
        handle.write("\n")

    plot_side_by_side_metric_comparison(list(summary["metric_rows"])).savefig(output_dir / "baseline_metric_comparison.png")
    plot_reproduction_vs_reference(list(summary["metric_rows"])).savefig(output_dir / "reproduction_vs_reference.png")
    plot_metric_difference_breakdown(list(summary["metric_rows"])).savefig(output_dir / "metric_difference_breakdown.png")
    plot_configuration_difference_summary(list(summary["comparison_rows"])).savefig(
        output_dir / "configuration_difference_summary.png"
    )

    outputs = {
        "comparison_dir": str(comparison_dir),
        "reproduction_dir": str(reproduction_dir),
        "comparison_csv": str(comparison_csv),
        "metric_csv": str(metric_csv),
        "summary_metrics_json": str(summary_metrics_json),
        "summary_metrics_csv": str(output_dir / "summary_metrics.csv"),
    }
    reconciliation_note = output_dir / "reconciliation_note.md"
    reconciliation_note.write_text(_reconciliation_note_markdown(summary=summary) + "\n", encoding="utf-8")
    outputs["reconciliation_note"] = str(reconciliation_note)

    summary_md = output_dir / "summary_report.md"
    summary_md.write_text(_summary_markdown(summary=summary, outputs=outputs) + "\n", encoding="utf-8")
    return {
        "summary_md": str(summary_md),
        "reconciliation_note": str(reconciliation_note),
        **outputs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the SPICE-driven baseline reconciliation report.")
    parser.add_argument("--outdir", default="artifacts/spice_driven_baseline_reconciliation")
    parser.add_argument("--detector-next-summary-csv", default="artifacts/detector_next/results_summary.csv")
    parser.add_argument("--reference-artifact-dir", default="artifacts/spice_driven_preferred_chain")
    parser.add_argument("--nominal-artifact-dir", default="artifacts/spice_driven_robustness")
    parser.add_argument("--quiet-progress", action="store_true")
    args = parser.parse_args()

    build_spice_driven_baseline_reconciliation_report(
        outdir=args.outdir,
        detector_next_summary_csv=args.detector_next_summary_csv,
        reference_artifact_dir=args.reference_artifact_dir,
        nominal_artifact_dir=args.nominal_artifact_dir,
        verbose_progress=not args.quiet_progress,
    )


if __name__ == "__main__":
    main()
