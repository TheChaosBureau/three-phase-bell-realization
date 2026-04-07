from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from detector_integration.experiments.run_summary_report import load_top_shot_trigger_spec

from physical_front_end_candidate.spice_driven_robustness import (
    BOUNDARY_VARIATION_KEY,
    CLASS_DISPLAY_NAMES,
    CLOSURE_VARIATION_KEY,
    COUPLING_MISMATCH_KEY,
    FRONT_END_TOLERANCES_KEY,
    LEAKAGE_VARIATION_KEY,
    LOAD_MISMATCH_KEY,
    SpiceDrivenRobustnessConfig,
    run_spice_driven_robustness_sweep,
)
from physical_front_end_candidate.spice_driven_robustness_plots import (
    plot_baseline_vs_class_worst_case,
    plot_boundary_metric_heatmap,
    plot_robustness_metric_sweep,
    plot_safe_window_pass_counts,
    plot_sensitivity_ranking,
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
    if isinstance(value, complex):
        return {"real": value.real, "imag": value.imag}
    return value


def _summary_markdown(*, summary: dict[str, Any], outputs: dict[str, str]) -> str:
    metrics = summary["summary_metrics"]
    baseline = summary["baseline_summary_metrics"]
    ranking = summary["sensitivity_ranking_rows"]
    top_row = ranking[0] if ranking else None
    return "\n".join(
        [
            "# SPICE-Driven Robustness Summary",
            "",
            "## Baseline",
            "",
            "- Upstream artifact remains actual ngspice-generated shared front-end traces.",
            "- Detector boundary nominal point remains `piecewise_envelope:linear:20.0ms`, gain `4.0x`, exposure `5.0s`.",
            f"- Baseline winner-law RMS error: {float(baseline['winner_law_rms_error']):.6f}",
            f"- Baseline correlator RMS error: {float(baseline['correlator_rms_error']):.6f}",
            f"- Baseline CHSH abs error: {float(baseline['chsh_abs_error']):.6f}",
            "",
            "## Robustness Sweep",
            "",
            f"- Configurations evaluated: {int(metrics['configuration_count'])}",
            f"- Passing configurations: {int(metrics['passing_configuration_count'])}",
            f"- Pass rate: {float(metrics['pass_rate']):.6f}",
            f"- Classes with a passing operating window: {int(metrics['classes_with_passing_window'])} / {int(metrics['class_count'])}",
            f"- Worst damage score: {float(metrics['worst_damage_score']):.6f}",
            f"- Mean damage score: {float(metrics['mean_damage_score']):.6f}",
            f"- Most dangerous class: {metrics['most_dangerous_class']}",
            f"- Most dangerous configuration: {metrics['most_dangerous_configuration']}",
            "",
            "## Sensitivity Ranking",
            "",
            f"- Top sensitivity class: {top_row['class_key']} ({top_row['class_display']})" if top_row else "- No ranking rows available.",
            f"- Top sensitivity worst-case damage score: {float(top_row['worst_damage_score']):.6f}" if top_row else "",
            f"- Sensitivity ranking CSV: `{outputs['sensitivity_ranking_csv']}`",
            "",
            "## Safe Operating Window",
            "",
            f"- Safe window available: {bool(metrics['safe_window_available'])}",
            f"- Safe-window summary CSV: `{outputs['safe_window_csv']}`",
            "",
            "## Artifacts",
            "",
            f"- Front-end tolerances: `{outputs['front_end_tolerances_dir']}`",
            f"- Coupling mismatch: `{outputs['coupling_mismatch_dir']}`",
            f"- Load mismatch: `{outputs['load_mismatch_dir']}`",
            f"- Leakage variation: `{outputs['leakage_variation_dir']}`",
            f"- Boundary variation: `{outputs['boundary_variation_dir']}`",
            f"- Closure variation: `{outputs['closure_variation_dir']}`",
            f"- Design note: `{outputs['design_md']}`",
            "",
        ]
    )


def _design_note_markdown(*, summary: dict[str, Any]) -> str:
    metrics = summary["summary_metrics"]
    ranking = summary["sensitivity_ranking_rows"]
    ranking_lines = [
        f"- {row['rank']}. {row['class_key']} ({row['class_display']}): worst damage score {float(row['worst_damage_score']):.6f}, pass rate {float(row['pass_rate']):.6f}"
        for row in ranking
    ]
    return "\n".join(
        [
            "# SPICE-Driven Robustness Design Note",
            "",
            "## Sweep Structure",
            "",
            "- Each perturbation class is swept in isolation against the frozen SPICE-driven preferred-chain baseline.",
            "- Front-end classes rerun the actual ngspice front-end with perturbed explicit component values.",
            "- Boundary variation perturbs only gain and exposure while keeping the export mode frozen to `piecewise_envelope:linear:20.0ms`.",
            "- Closure/drain variation perturbs local control-rise, winner-drain, and loser-clamp strengths without re-optimization.",
            "",
            "## Pass Contract",
            "",
            "- Winner law, correlator, CHSH, pre-click transparency, winner-drain dominance, loser residual, completion, and energy-accounting all reuse the existing SPICE-driven thresholds.",
            "- Robustness additionally requires decisive fraction above the configured threshold and a valid detector-boundary export.",
            "",
            "## Sensitivity Ranking",
            "",
            *(ranking_lines or ["- No ranking rows available."]),
            "",
            "## Outcome",
            "",
            f"- Passing configurations: {int(metrics['passing_configuration_count'])} / {int(metrics['configuration_count'])}",
            f"- Safe window available: {bool(metrics['safe_window_available'])}",
            f"- Most dangerous class: {metrics['most_dangerous_class']}",
            f"- Most dangerous configuration: {metrics['most_dangerous_configuration']}",
            "",
        ]
    )


def build_spice_driven_robustness_report(
    outdir: str | Path = "artifacts/spice_driven_robustness",
    *,
    detector_next_summary_csv: str | Path = "artifacts/detector_next/results_summary.csv",
    n_trials: int = 180,
    seed: int = 20260412,
    case_names: Sequence[str] | None = None,
    robustness_config: SpiceDrivenRobustnessConfig | dict[str, Any] | None = None,
    verbose_progress: bool = False,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    class_dirs = {
        FRONT_END_TOLERANCES_KEY: output_dir / FRONT_END_TOLERANCES_KEY,
        COUPLING_MISMATCH_KEY: output_dir / COUPLING_MISMATCH_KEY,
        LOAD_MISMATCH_KEY: output_dir / LOAD_MISMATCH_KEY,
        LEAKAGE_VARIATION_KEY: output_dir / LEAKAGE_VARIATION_KEY,
        BOUNDARY_VARIATION_KEY: output_dir / BOUNDARY_VARIATION_KEY,
        CLOSURE_VARIATION_KEY: output_dir / CLOSURE_VARIATION_KEY,
    }
    for directory in class_dirs.values():
        directory.mkdir(parents=True, exist_ok=True)

    detector_spec = load_top_shot_trigger_spec(detector_next_summary_csv)
    detector_model_spec = {
        "family": detector_spec["family"],
        "model_params": dict(detector_spec["model_params"]),
        "gain_scale": 2.0,
    }
    summary = run_spice_driven_robustness_sweep(
        detector_model_spec,
        n_trials=n_trials,
        seed=seed,
        case_names=case_names,
        robustness_config=robustness_config,
        verbose_progress=verbose_progress,
    )

    for class_key, directory in class_dirs.items():
        class_rows = [row for row in summary["perturbation_rows"] if row["class_key"] == class_key]
        _write_csv(directory / "sweep_results.csv", class_rows)
        if class_key == BOUNDARY_VARIATION_KEY:
            plot_boundary_metric_heatmap(
                class_rows,
                metric_key="damage_score",
                title=f"{CLASS_DISPLAY_NAMES[class_key]} Damage Score",
            ).savefig(directory / "damage_score_heatmap.png")
            plot_boundary_metric_heatmap(
                class_rows,
                metric_key="winner_law_rms_error",
                title=f"{CLASS_DISPLAY_NAMES[class_key]} Winner-Law RMS",
            ).savefig(directory / "winner_law_rms_heatmap.png")
        else:
            plot_robustness_metric_sweep(
                class_rows,
                metric_key="winner_law_rms_error",
                title=f"{CLASS_DISPLAY_NAMES[class_key]} Winner-Law RMS",
                ylabel="Winner-law RMS error",
            ).savefig(directory / "winner_law_rms_vs_level.png")
            plot_robustness_metric_sweep(
                class_rows,
                metric_key="mean_decisive_fraction",
                title=f"{CLASS_DISPLAY_NAMES[class_key]} Decisive Fraction",
                ylabel="Mean decisive fraction",
            ).savefig(directory / "decisive_fraction_vs_level.png")
            plot_robustness_metric_sweep(
                class_rows,
                metric_key="damage_score",
                title=f"{CLASS_DISPLAY_NAMES[class_key]} Damage Score",
                ylabel="Damage score",
            ).savefig(directory / "damage_score_vs_level.png")

    summary_metrics_csv = output_dir / "summary_metrics.csv"
    summary_metrics_json = output_dir / "summary_metrics.json"
    sensitivity_ranking_csv = output_dir / "sensitivity_ranking.csv"
    safe_window_csv = output_dir / "safe_window_summary.csv"
    _write_csv(summary_metrics_csv, [{"metric": key, "value": value} for key, value in summary["summary_metrics"].items()])
    _write_csv(sensitivity_ranking_csv, list(summary["sensitivity_ranking_rows"]))
    _write_csv(safe_window_csv, list(summary["safe_window_rows"]))
    summary_metrics_json.write_text(
        json.dumps(summary, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )

    plot_sensitivity_ranking(list(summary["sensitivity_ranking_rows"])).savefig(output_dir / "sensitivity_ranking.png")
    plot_safe_window_pass_counts(list(summary["safe_window_rows"])).savefig(output_dir / "safe_window_pass_counts.png")
    plot_baseline_vs_class_worst_case(
        dict(summary["baseline_summary_metrics"]),
        list(summary["class_rows"]),
    ).savefig(output_dir / "baseline_vs_class_worst_case.png")

    outputs = {
        "front_end_tolerances_dir": str(class_dirs[FRONT_END_TOLERANCES_KEY]),
        "coupling_mismatch_dir": str(class_dirs[COUPLING_MISMATCH_KEY]),
        "load_mismatch_dir": str(class_dirs[LOAD_MISMATCH_KEY]),
        "leakage_variation_dir": str(class_dirs[LEAKAGE_VARIATION_KEY]),
        "boundary_variation_dir": str(class_dirs[BOUNDARY_VARIATION_KEY]),
        "closure_variation_dir": str(class_dirs[CLOSURE_VARIATION_KEY]),
        "summary_metrics_csv": str(summary_metrics_csv),
        "summary_metrics_json": str(summary_metrics_json),
        "sensitivity_ranking_csv": str(sensitivity_ranking_csv),
        "safe_window_csv": str(safe_window_csv),
    }
    design_md = output_dir / "design_note.md"
    design_md.write_text(_design_note_markdown(summary=summary) + "\n", encoding="utf-8")
    outputs["design_md"] = str(design_md)

    summary_md = output_dir / "summary_report.md"
    summary_md.write_text(_summary_markdown(summary=summary, outputs=outputs) + "\n", encoding="utf-8")
    return {
        "summary_md": str(summary_md),
        "design_md": str(design_md),
        **outputs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the SPICE-driven robustness report.")
    parser.add_argument("--outdir", default="artifacts/spice_driven_robustness")
    parser.add_argument("--detector-next-summary-csv", default="artifacts/detector_next/results_summary.csv")
    parser.add_argument("--n-trials", type=int, default=180)
    parser.add_argument("--seed", type=int, default=20260412)
    parser.add_argument("--case", action="append", dest="case_names", default=None)
    parser.add_argument("--quiet-progress", action="store_true")
    args = parser.parse_args()
    build_spice_driven_robustness_report(
        outdir=args.outdir,
        detector_next_summary_csv=args.detector_next_summary_csv,
        n_trials=args.n_trials,
        seed=args.seed,
        case_names=args.case_names,
        verbose_progress=not args.quiet_progress,
    )


if __name__ == "__main__":
    main()
