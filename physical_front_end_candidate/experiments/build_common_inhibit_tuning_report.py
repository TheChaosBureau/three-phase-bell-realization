from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from detector_integration.experiments.run_summary_report import load_top_shot_trigger_spec

from physical_front_end_candidate.common_inhibit_tuning import (
    run_common_inhibit_parameter_sweeps,
)
from physical_front_end_candidate.plots import (
    plot_closure_semantics_comparison,
    plot_loser_suppression,
    plot_parameter_metric_panels,
    plot_parameter_response,
    plot_post_click_energy_partition,
    plot_remaining_shared_energy,
    plot_winner_drain_power,
)


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
    if isinstance(value, complex):
        return {"real": value.real, "imag": value.imag}
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _summary_markdown(
    *,
    baseline: Mapping[str, Any],
    tuned: Mapping[str, Any],
    comparison_row: Mapping[str, Any],
    outputs: Mapping[str, str],
) -> str:
    baseline_metrics = baseline["summary_metrics"]
    tuned_metrics = tuned["summary_metrics"]
    return "\n".join(
        [
            "# Common Inhibit Tuning Summary",
            "",
            "## Objective",
            "",
            "- Topology kept fixed: `common inhibit rail + winner-gated shunt drain`.",
            "- Tuning focus: inhibit rise, loser clamp strength, winner drain strength.",
            "",
            "## Baseline vs Tuned",
            "",
            f"- Baseline winner drain fraction: {float(baseline_metrics['mean_winner_drain_fraction']):.6f}",
            f"- Tuned winner drain fraction: {float(tuned_metrics['mean_winner_drain_fraction']):.6f}",
            f"- Baseline loser residual fraction: {float(baseline_metrics['mean_loser_fraction']):.6f}",
            f"- Tuned loser residual fraction: {float(tuned_metrics['mean_loser_fraction']):.6f}",
            f"- Winner fraction improvement: {float(comparison_row['winner_drain_fraction_delta']):.6f}",
            f"- Terminal loser suppression delta: {float(comparison_row['terminal_loser_suppression_delta']):.6f}",
            "",
            "## Tuned Parameters",
            "",
            f"- `control_tau_s`: {float(tuned_metrics['control_tau_s']):.6f}",
            f"- `clamp_reference_g_on_s`: {float(tuned_metrics['clamp_reference_g_on_s']):.6f}",
            f"- `winner_drain_g_on_s`: {float(tuned_metrics['winner_drain_g_on_s']):.6f}",
            "",
            "## Acceptance",
            "",
            f"- Pre-click transparency pass: {bool(tuned_metrics['pre_click_transparency_pass'])}",
            f"- Winner drain dominance pass: {bool(tuned_metrics['winner_dominance_pass'])}",
            f"- Completion pass: {bool(tuned_metrics['completion_pass'])}",
            f"- Reduced consistency pass: {bool(tuned_metrics['reduced_consistency_pass'])}",
            "",
            "## Artifacts",
            "",
            f"- Parameter sweeps: `{outputs['parameter_sweeps_dir']}`",
            f"- Best candidate artifacts: `{outputs['best_candidate_dir']}`",
            f"- Tuned design note: `{outputs['design_md']}`",
            "",
        ]
    )


def build_common_inhibit_tuning_report(
    outdir: str | Path = "artifacts/physical_closure_drain_tuning",
    *,
    detector_next_summary_csv: str | Path = "artifacts/detector_next/results_summary.csv",
    n_trials: int = 24,
    seed: int = 20260404,
    case_names: Sequence[str] | None = None,
    verbose_progress: bool = True,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    sweeps_dir = output_dir / "parameter_sweeps"
    best_dir = output_dir / "best_candidate"
    progress_json = output_dir / "progress.json"
    for directory in (sweeps_dir, best_dir):
        directory.mkdir(parents=True, exist_ok=True)

    detector_spec = load_top_shot_trigger_spec(detector_next_summary_csv)
    detector_model_spec = {
        "family": detector_spec["family"],
        "model_params": dict(detector_spec["model_params"]),
        "gain_scale": 2.0,
    }
    tuning = run_common_inhibit_parameter_sweeps(
        detector_model_spec,
        n_trials=n_trials,
        seed=seed,
        case_names=case_names,
        verbose_progress=verbose_progress,
        progress_path=progress_json,
    )
    baseline = tuning["baseline"]
    tuned = tuning["best_tuned"]

    _write_csv(sweeps_dir / "winner_drain_strength_sweep.csv", tuning["sweep_rows"]["winner_drain_g_on_s"])
    _write_csv(sweeps_dir / "loser_clamp_strength_sweep.csv", tuning["sweep_rows"]["clamp_reference_g_on_s"])
    _write_csv(sweeps_dir / "inhibit_rise_sweep.csv", tuning["sweep_rows"]["control_tau_s"])
    _write_csv(best_dir / "integration_summary.csv", tuned["integration_rows"])
    _write_csv(best_dir / "reduced_comparison.csv", tuned["comparison_rows"])

    plot_parameter_response(
        tuning["sweep_rows"]["winner_drain_g_on_s"],
        param_key="winner_drain_g_on_s",
        metric_key="mean_winner_drain_fraction",
        title="Winner drain fraction vs winner drain strength",
        xlabel="Winner drain conductance (S)",
        ylabel="Winner drain fraction",
    ).savefig(sweeps_dir / "winner_drain_fraction_vs_winner_drain_strength.png")
    plot_parameter_response(
        tuning["sweep_rows"]["clamp_reference_g_on_s"],
        param_key="clamp_reference_g_on_s",
        metric_key="mean_winner_drain_fraction",
        title="Winner drain fraction vs loser clamp strength",
        xlabel="Loser clamp conductance (S)",
        ylabel="Winner drain fraction",
    ).savefig(sweeps_dir / "winner_drain_fraction_vs_loser_clamp_strength.png")
    plot_parameter_response(
        tuning["sweep_rows"]["control_tau_s"],
        param_key="control_tau_s",
        metric_key="mean_winner_drain_fraction",
        title="Winner drain fraction vs inhibit rise time constant",
        xlabel="Inhibit rise time constant (s)",
        ylabel="Winner drain fraction",
    ).savefig(sweeps_dir / "winner_drain_fraction_vs_inhibit_rise_rate.png")

    panel_rows = [
        {
            "label": "Winner Drain Strength",
            "rows": tuning["sweep_rows"]["winner_drain_g_on_s"],
            "param_key": "winner_drain_g_on_s",
            "xlabel": "Drain conductance (S)",
        },
        {
            "label": "Loser Clamp Strength",
            "rows": tuning["sweep_rows"]["clamp_reference_g_on_s"],
            "param_key": "clamp_reference_g_on_s",
            "xlabel": "Clamp conductance (S)",
        },
        {
            "label": "Inhibit Rise",
            "rows": tuning["sweep_rows"]["control_tau_s"],
            "param_key": "control_tau_s",
            "xlabel": "Time constant (s)",
        },
    ]
    plot_parameter_metric_panels(
        panel_rows,
        metric_key="mean_loser_fraction",
        title="Loser residual fraction vs tuned parameters",
        ylabel="Loser residual fraction",
    ).savefig(sweeps_dir / "loser_residual_fraction_vs_parameters.png")
    plot_parameter_metric_panels(
        panel_rows,
        metric_key="mean_terminal_loser_suppression",
        title="Terminal loser suppression vs tuned parameters",
        ylabel="Terminal loser suppression",
    ).savefig(sweeps_dir / "terminal_loser_suppression_vs_parameters.png")
    plot_parameter_metric_panels(
        panel_rows,
        metric_key="completion_rate",
        title="Completion rate vs tuned parameters",
        ylabel="Completion rate",
    ).savefig(sweeps_dir / "completion_rate_vs_parameters.png")
    plot_parameter_metric_panels(
        panel_rows,
        metric_key="mean_completion_time_s",
        title="Completion time vs tuned parameters",
        ylabel="Mean completion time (s)",
    ).savefig(sweeps_dir / "completion_time_vs_parameters.png")
    plot_parameter_metric_panels(
        panel_rows,
        metric_key="pre_click_transparency_rms_shift",
        title="Pre-click transparency shift vs tuned parameters",
        ylabel="Transparency RMS shift",
    ).savefig(sweeps_dir / "pre_click_transparency_shift_vs_parameters.png")

    plot_post_click_energy_partition(
        [
            {
                "label": "baseline",
                "mean_winner_drain_fraction": float(baseline["summary_metrics"]["mean_winner_drain_fraction"]),
                "mean_loser_fraction": float(baseline["summary_metrics"]["mean_loser_fraction"]),
            },
            {
                "label": "tuned",
                "mean_winner_drain_fraction": float(tuned["summary_metrics"]["mean_winner_drain_fraction"]),
                "mean_loser_fraction": float(tuned["summary_metrics"]["mean_loser_fraction"]),
            },
        ]
    ).savefig(best_dir / "best_tuned_energy_partition.png")

    if tuned["example_trial"] is not None:
        physical = tuned["example_trial"]["physical"]
        reduced = tuned["example_trial"]["reduced"]
        plot_winner_drain_power(physical).savefig(best_dir / "winner_drain_power.png")
        plot_loser_suppression(physical).savefig(best_dir / "loser_suppression.png")
        plot_remaining_shared_energy(physical).savefig(best_dir / "remaining_shared_energy.png")
        plot_closure_semantics_comparison(physical, reduced, variable_name="Z").savefig(best_dir / "reduced_vs_tuned.png")

    comparison_row = {
        "winner_drain_fraction_delta": float(tuned["summary_metrics"]["mean_winner_drain_fraction"])
        - float(baseline["summary_metrics"]["mean_winner_drain_fraction"]),
        "loser_fraction_delta": float(tuned["summary_metrics"]["mean_loser_fraction"])
        - float(baseline["summary_metrics"]["mean_loser_fraction"]),
        "terminal_loser_suppression_delta": float(tuned["summary_metrics"]["mean_terminal_loser_suppression"])
        - float(baseline["summary_metrics"]["mean_terminal_loser_suppression"]),
        "completion_rate_delta": float(tuned["summary_metrics"]["completion_rate"])
        - float(baseline["summary_metrics"]["completion_rate"]),
        "mean_completion_time_delta_s": float(tuned["summary_metrics"]["mean_completion_time_s"])
        - float(baseline["summary_metrics"]["mean_completion_time_s"]),
        "pre_click_transparency_shift_delta": float(tuned["summary_metrics"]["pre_click_transparency_rms_shift"])
        - float(baseline["summary_metrics"]["pre_click_transparency_rms_shift"]),
    }
    _write_csv(output_dir / "first_candidate_comparison.csv", [comparison_row])

    summary_metrics = {
        **tuned["summary_metrics"],
        "baseline_mean_winner_drain_fraction": float(baseline["summary_metrics"]["mean_winner_drain_fraction"]),
        "baseline_mean_loser_fraction": float(baseline["summary_metrics"]["mean_loser_fraction"]),
        "baseline_mean_terminal_loser_suppression": float(baseline["summary_metrics"]["mean_terminal_loser_suppression"]),
        "baseline_completion_rate": float(baseline["summary_metrics"]["completion_rate"]),
        "winner_drain_fraction_delta": comparison_row["winner_drain_fraction_delta"],
        "loser_fraction_delta": comparison_row["loser_fraction_delta"],
        "terminal_loser_suppression_delta": comparison_row["terminal_loser_suppression_delta"],
        "completion_rate_delta": comparison_row["completion_rate_delta"],
    }

    design_md = output_dir / "tuned_candidate_design_note.md"
    design_md.write_text(
        "\n".join(
            [
                "# Tuned Common Inhibit Candidate",
                "",
                "## What Was Tuned",
                "",
                "- Inhibit rise time constant (`control_tau_s`).",
                "- Loser clamp strength (`clamp_reference_g_on_s`).",
                "- Winner drain conductance (`winner_drain_g_on_s`).",
                "",
                "## What Changed Relative To First Candidate",
                "",
                f"- Baseline winner drain fraction: {float(baseline['summary_metrics']['mean_winner_drain_fraction']):.6f}",
                f"- Tuned winner drain fraction: {float(tuned['summary_metrics']['mean_winner_drain_fraction']):.6f}",
                f"- Baseline loser residual fraction: {float(baseline['summary_metrics']['mean_loser_fraction']):.6f}",
                f"- Tuned loser residual fraction: {float(tuned['summary_metrics']['mean_loser_fraction']):.6f}",
                "",
                "## Best Tuned Configuration",
                "",
                f"- `control_tau_s = {float(tuned['summary_metrics']['control_tau_s']):.6f}`",
                f"- `clamp_reference_g_on_s = {float(tuned['summary_metrics']['clamp_reference_g_on_s']):.6f}`",
                f"- `winner_drain_g_on_s = {float(tuned['summary_metrics']['winner_drain_g_on_s']):.6f}`",
                "",
                "## Topology Consistency",
                "",
                "- The tuned candidate remains the same preferred topology: one common inhibit rail, one winner-gated drain path, loser suppression via the same common inhibit action.",
                "- No new interpretation or alternate topology was introduced in this ticket.",
                "",
                "## Remaining Abstractions",
                "",
                "- This remains a tuned SPICE-style surrogate, not a transistor-level implementation.",
                "- Reset hardware and full nonlinear hardware co-design remain outside this ticket.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary_csv = output_dir / "summary_metrics.csv"
    _write_csv(summary_csv, [{"metric": key, "value": value} for key, value in summary_metrics.items()])
    outputs = {
        "parameter_sweeps_dir": str(sweeps_dir),
        "best_candidate_dir": str(best_dir),
        "design_md": str(design_md),
        "progress_json": str(progress_json),
    }
    summary_json = output_dir / "summary_metrics.json"
    summary_json.write_text(
        json.dumps(
            {
                "summary_metrics": summary_metrics,
                "baseline": baseline["summary_metrics"],
                "best_tuned": tuned["summary_metrics"],
                "sweep_rows": tuning["sweep_rows"],
                "comparison_row": comparison_row,
                "outputs": outputs,
            },
            indent=2,
            default=_json_default,
        )
        + "\n",
        encoding="utf-8",
    )
    summary_md = output_dir / "summary_report.md"
    summary_md.write_text(
        _summary_markdown(baseline=baseline, tuned=tuned, comparison_row=comparison_row, outputs=outputs) + "\n",
        encoding="utf-8",
    )
    return {
        "summary_md": str(summary_md),
        "summary_json": str(summary_json),
        "summary_csv": str(summary_csv),
        "design_md": str(design_md),
        "parameter_sweeps_dir": str(sweeps_dir),
        "best_candidate_dir": str(best_dir),
        "progress_json": str(progress_json),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the tuned common inhibit closure/drain report.")
    parser.add_argument("--outdir", default="artifacts/physical_closure_drain_tuning")
    parser.add_argument("--detector-next-summary", default="artifacts/detector_next/results_summary.csv")
    parser.add_argument("--trials", type=int, default=24)
    parser.add_argument("--quiet-progress", action="store_true")
    args = parser.parse_args()
    build_common_inhibit_tuning_report(
        args.outdir,
        detector_next_summary_csv=args.detector_next_summary,
        n_trials=args.trials,
        verbose_progress=not args.quiet_progress,
    )


if __name__ == "__main__":
    main()
