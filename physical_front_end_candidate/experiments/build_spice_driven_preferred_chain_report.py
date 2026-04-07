from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from detector_integration.experiments.run_summary_report import load_top_shot_trigger_spec

from physical_front_end_candidate.spice_driven_preferred_chain import (
    run_spice_driven_preferred_chain_benchmark,
)
from physical_front_end_candidate.spice_driven_preferred_chain_plots import (
    plot_loser_residual_fraction,
    plot_remaining_shared_energy_trace,
    plot_spice_driven_boundary_export,
    plot_spice_driven_branch_current,
    plot_spice_driven_branch_power,
    plot_spice_driven_branch_voltage,
    plot_spice_driven_candidate_comparison,
    plot_spice_driven_chsh,
    plot_spice_driven_correlator,
    plot_spice_driven_winner_frequency,
    plot_whole_trial_energy_flow,
    plot_winner_drain_fraction,
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
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, complex):
        return {"real": value.real, "imag": value.imag}
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _summary_markdown(*, summary: dict[str, Any], outputs: dict[str, str]) -> str:
    metrics = summary["summary_metrics"]
    baseline = summary["baseline_summary_metrics"]
    spice_front = summary["actual_spice_front_end_summary_metrics"]
    comparison_rows = {row["candidate"]: row for row in summary["comparison_rows"]}
    decision = (
        "Proceed to the next Stop Level C milestone from this SPICE-driven preferred-chain baseline."
        if bool(metrics["proceed_to_next_phase"])
        else "Iterate on the SPICE-to-boundary handoff before treating this as the new preferred-chain baseline."
    )
    return "\n".join(
        [
            "# SPICE-Driven Preferred Chain Summary",
            "",
            "## Architecture",
            "",
            "- Upstream artifact: actual ngspice-generated shared front-end traces.",
            "- Downstream stack remains frozen: boundary, `shot_trigger` detector, first-arrival latch, and preferred closure/drain semantics.",
            "- Boundary contract preserved: `piecewise_envelope:linear:20.0ms`, gain `4.0x`, exposure `5.0s`.",
            "",
            "## Actual SPICE Front-End Check",
            "",
            f"- SPICE front-end RMS error vs current preferred baseline: {float(spice_front['front_end_fraction_rms_error']):.6f}",
            f"- SPICE front-end max error vs current preferred baseline: {float(spice_front['front_end_fraction_max_error']):.6f}",
            f"- SPICE front-end correlator RMS: {float(spice_front['correlator_rms_error']):.6f}",
            f"- SPICE front-end CHSH abs error: {float(spice_front['chsh_abs_error']):.6f}",
            "",
            "## Full-Chain Fidelity",
            "",
            f"- Winner-law RMS error: {float(metrics['winner_law_rms_error']):.6f}",
            f"- Winner-law max error: {float(metrics['winner_law_max_error']):.6f}",
            f"- Correlator RMS error: {float(metrics['correlator_rms_error']):.6f}",
            f"- CHSH absolute error: {float(metrics['chsh_abs_error']):.6f}",
            f"- Mean decisive fraction: {float(metrics['mean_decisive_fraction']):.6f}",
            f"- Pre-click transparency RMS shift: {float(metrics['pre_click_transparency_rms_shift']):.6f}",
            "",
            "## Post-Click / Energy",
            "",
            f"- Winner-drain dominance rate: {float(metrics['winner_drain_dominance_rate']):.6f}",
            f"- Mean loser residual fraction of post-click energy: {float(metrics['mean_loser_fraction_of_post_click']):.6f}",
            f"- Completion rate: {float(metrics['completion_rate']):.6f}",
            f"- Energy-accounting pass: {bool(metrics['energy_accounting_pass'])}",
            "",
            "## SPICE-Driven Handoff",
            "",
            f"- Actual SPICE execution pass: {bool(metrics['actual_spice_execution_pass'])}",
            f"- SPICE trace ingestion pass: {bool(metrics['spice_trace_ingestion_pass'])}",
            f"- Boundary export pass: {bool(metrics['boundary_export_pass'])}",
            f"- SPICE-driven alignment pass: {bool(metrics['spice_driven_alignment_pass'])}",
            f"- Actual SPICE-driven pass: {bool(metrics['actual_spice_driven_pass'])}",
            "",
            "## Baseline Comparison",
            "",
            f"- Current preferred-chain winner-law RMS: {float(baseline['winner_law_rms_error']):.6f}",
            f"- SPICE-driven winner-law RMS: {float(metrics['winner_law_rms_error']):.6f}",
            f"- Current preferred-chain correlator RMS: {float(baseline['correlator_rms_error']):.6f}",
            f"- SPICE-driven correlator RMS: {float(metrics['correlator_rms_error']):.6f}",
            f"- Current preferred-chain CHSH abs error: {float(baseline['chsh_abs_error']):.6f}",
            f"- SPICE-driven CHSH abs error: {float(metrics['chsh_abs_error']):.6f}",
            f"- Front-end-only actual SPICE note: {comparison_rows['actual_spice_front_end']['architecture_note']}",
            f"- Baseline note: {comparison_rows['current_preferred_chain_device_physicalization']['architecture_note']}",
            f"- SPICE-driven note: {comparison_rows['spice_driven_preferred_chain']['architecture_note']}",
            f"- Comparison CSV: `{outputs['candidate_comparison_csv']}`",
            "",
            "## Decision",
            "",
            f"- Proceed to next phase: {bool(metrics['proceed_to_next_phase'])}",
            f"- Decision: {decision}",
            "",
            "## Artifacts",
            "",
            f"- Front-end traces: `{outputs['front_end_dir']}`",
            f"- Boundary export: `{outputs['boundary_dir']}`",
            f"- Full chain: `{outputs['full_chain_dir']}`",
            f"- Post-click: `{outputs['post_click_dir']}`",
            f"- Energy accounting: `{outputs['energy_dir']}`",
            f"- Design note: `{outputs['design_md']}`",
            "",
        ]
    )


def _design_note_markdown(*, summary: dict[str, Any]) -> str:
    metrics = summary["summary_metrics"]
    return "\n".join(
        [
            "# SPICE-Driven Preferred Chain Design Note",
            "",
            "## Which Actual SPICE Traces Are Used",
            "",
            "- Raw actual-SPICE front-end branch voltages, currents, and powers from the ngspice transient benchmark.",
            "- The handoff adapter derives branch mean absorbed powers from those actual SPICE traces.",
            "",
            "## How SPICE Traces Become Frozen Detector-Boundary Inputs",
            "",
            "- The actual SPICE measurement window is carrier-averaged per branch.",
            "- The total branch power is then normalized onto the frozen preferred-chain operating point by preserving the frozen preferred-chain total pre-click envelope and reweighting the frozen per-branch envelopes with an actual-SPICE branch-fraction correction.",
            "- Those SPICE-derived branch powers are replayed over the frozen 5-second boundary exposure and then exported with the unchanged `piecewise_envelope:linear:20.0ms` boundary contract.",
            "",
            "## What Is Now SPICE-Driven",
            "",
            "- The upstream front-end artifact is no longer surrogate or merely SPICE-facing.",
            "- The detector boundary export is derived from actual SPICE-generated front-end traces.",
            "- Detector, latch, and closure/drain execution are therefore driven from an actual SPICE upstream artifact.",
            "",
            "## What Remains Outside SPICE",
            "",
            "- The detector remains the frozen `shot_trigger` model.",
            "- The latch remains the validated first-arrival arbiter contract.",
            "- The closure/drain remains the frozen preferred physicalized common-inhibit and winner-drain path model.",
            "",
            "## Remaining Assumptions / Compromises",
            "",
            "- The boundary adapter uses carrier-averaged SPICE power rather than replaying the raw carrier waveform directly through the detector model.",
            "- The SPICE handoff injects the actual-SPICE branch split as a calibrated correction over the frozen preferred-chain per-branch envelopes, because ticket 240 validated branch fractions but not detector-scale absolute power over the full 5-second boundary window.",
            "- This is the first full SPICE-driven preferred-chain milestone, not a full-SPICE downstream implementation.",
            "",
            "## Current Outcome",
            "",
            f"- Winner-law pass: {bool(metrics['winner_law_pass'])}",
            f"- Correlator pass: {bool(metrics['correlator_pass'])}",
            f"- CHSH pass: {bool(metrics['chsh_pass'])}",
            f"- Pre-click transparency pass: {bool(metrics['pre_click_transparency_pass'])}",
            f"- Winner-drain dominance pass: {bool(metrics['winner_drain_dominance_pass'])}",
            f"- Energy-accounting pass: {bool(metrics['energy_accounting_pass'])}",
            f"- Actual SPICE-driven pass: {bool(metrics['actual_spice_driven_pass'])}",
            "",
        ]
    )


def build_spice_driven_preferred_chain_report(
    outdir: str | Path = "artifacts/spice_driven_preferred_chain",
    *,
    detector_next_summary_csv: str | Path = "artifacts/detector_next/results_summary.csv",
    n_trials: int = 1_200,
    seed: int = 20260411,
    case_names: Sequence[str] | None = None,
    verbose_progress: bool = False,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    front_end_dir = output_dir / "front_end_traces"
    boundary_dir = output_dir / "boundary_export"
    full_chain_dir = output_dir / "full_chain"
    post_click_dir = output_dir / "post_click"
    energy_dir = output_dir / "energy_accounting"
    for directory in (front_end_dir, boundary_dir, full_chain_dir, post_click_dir, energy_dir):
        directory.mkdir(parents=True, exist_ok=True)

    detector_spec = load_top_shot_trigger_spec(detector_next_summary_csv)
    detector_model_spec = {
        "family": detector_spec["family"],
        "model_params": dict(detector_spec["model_params"]),
        "gain_scale": 2.0,
    }
    summary = run_spice_driven_preferred_chain_benchmark(
        detector_model_spec,
        n_trials=n_trials,
        seed=seed,
        case_names=case_names,
        verbose_progress=verbose_progress,
    )

    front_end_csv = front_end_dir / "front_end_summary.csv"
    boundary_csv = boundary_dir / "boundary_export_summary.csv"
    full_chain_csv = full_chain_dir / "full_chain_summary.csv"
    case_comparison_csv = full_chain_dir / "baseline_case_comparison.csv"
    post_click_csv = post_click_dir / "post_click_summary.csv"
    energy_summary_csv = energy_dir / "energy_accounting_summary.csv"
    energy_trials_csv = energy_dir / "energy_accounting_trials.csv"
    candidate_comparison_csv = output_dir / "candidate_comparison.csv"

    _write_csv(front_end_csv, list(summary["front_end_rows"]))
    _write_csv(boundary_csv, list(summary["boundary_export_rows"]))
    _write_csv(
        full_chain_csv,
        [
            {
                **{
                    key: value
                    for key, value in row.items()
                    if key not in {"branch_labels", "exact_weights", "realized_fractions", "empirical_frequencies"}
                },
                "branch_labels_json": json.dumps(row["branch_labels"]),
                "exact_weights_json": json.dumps(row["exact_weights"]),
                "realized_fractions_json": json.dumps(row["realized_fractions"]),
                "empirical_frequencies_json": json.dumps(row["empirical_frequencies"]),
            }
            for row in summary["case_rows"]
        ],
    )
    _write_csv(case_comparison_csv, list(summary["case_comparison_rows"]))
    _write_csv(post_click_csv, list(summary["post_click_rows"]))
    _write_csv(energy_summary_csv, list(summary["energy_case_rows"]))
    _write_csv(
        energy_trials_csv,
        [
            {
                **{
                    key: value
                    for key, value in row.items()
                    if key not in {"pre_click_branch_energy_j", "future_branch_energy_j", "post_click_loser_energy_by_branch_j"}
                },
                "pre_click_branch_energy_j_json": json.dumps(row["pre_click_branch_energy_j"], sort_keys=True),
                "future_branch_energy_j_json": json.dumps(row["future_branch_energy_j"], sort_keys=True),
                "post_click_loser_energy_by_branch_j_json": json.dumps(row["post_click_loser_energy_by_branch_j"], sort_keys=True),
            }
            for row in summary["energy_rows"]
        ],
    )
    _write_csv(candidate_comparison_csv, list(summary["comparison_rows"]))

    if summary["example_front_end"] is not None:
        example = dict(summary["example_front_end"])
        plot_spice_driven_branch_voltage(example).savefig(front_end_dir / "representative_spice_branch_voltage_traces.png")
        plot_spice_driven_branch_current(example).savefig(front_end_dir / "representative_spice_branch_current_traces.png")
        plot_spice_driven_branch_power(example).savefig(front_end_dir / "representative_spice_branch_power_traces.png")
        plot_spice_driven_boundary_export(example).savefig(
            boundary_dir / "detector_facing_exported_envelopes_derived_from_spice.png"
        )
        _write_csv(
            front_end_dir / "example_spice_trace.csv",
            [
                {
                    "time_s": example["raw_spice_time_s"][index],
                    **{f"{label}_voltage_v": example["raw_spice_branch_voltage_v"][label][index] for label in example["branch_labels"]},
                    **{f"{label}_current_a": example["raw_spice_branch_current_a"][label][index] for label in example["branch_labels"]},
                    **{f"{label}_power_w": example["raw_spice_branch_power_w"][label][index] for label in example["branch_labels"]},
                }
                for index in range(len(example["raw_spice_time_s"]))
            ],
        )
        _write_csv(
            boundary_dir / "example_boundary_export_trace.csv",
            [
                {
                    "time_s": example["export_time_s"][index],
                    **{f"{label}_exported_power_w": example["exported_branch_power"][label][index] for label in example["branch_labels"]},
                }
                for index in range(len(example["export_time_s"]))
            ],
        )

    plot_spice_driven_winner_frequency(list(summary["case_rows"])).savefig(
        full_chain_dir / "winner_frequency_exact_vs_empirical.png"
    )
    plot_spice_driven_correlator(list(summary["case_rows"])).savefig(
        full_chain_dir / "correlator_exact_vs_empirical.png"
    )
    if bool(summary["chsh_result"]["available"]):
        plot_spice_driven_chsh(dict(summary["chsh_result"])).savefig(
            full_chain_dir / "chsh_exact_vs_empirical.png"
        )
    plot_winner_drain_fraction(list(summary["post_click_rows"])).savefig(
        post_click_dir / "winner_drain_energy_fraction.png"
    )
    plot_loser_residual_fraction(list(summary["post_click_rows"])).savefig(
        post_click_dir / "loser_residual_energy_fraction.png"
    )
    plot_whole_trial_energy_flow(list(summary["energy_case_rows"])).savefig(
        energy_dir / "whole_trial_energy_flow_summary.png"
    )
    plot_spice_driven_candidate_comparison(list(summary["plot_comparison_rows"])).savefig(
        output_dir / "comparison_vs_current_preferred_chain_baseline.png"
    )

    if summary["example_trial"] is not None:
        plot_remaining_shared_energy_trace(dict(summary["example_trial"])).savefig(
            post_click_dir / "remaining_shared_energy_vs_time.png"
        )
        physical = dict(summary["example_trial"]["physical"])
        _write_csv(
            post_click_dir / "example_trial_trace.csv",
            [
                {
                    "time_s": physical["time_s"][index],
                    "common_inhibit_v": physical["common_inhibit_v"][index],
                    "winner_gate_v": physical["winner_gate_v"][index],
                    "winner_drain_current_a": physical["winner_drain_current_a"][index],
                    "winner_drain_power_w": physical["winner_drain_power_w"][index],
                    "remaining_shared_energy_j": physical["remaining_shared_energy_j"][index],
                }
                for index in range(len(physical["time_s"]))
            ],
        )

    summary_csv = output_dir / "summary_metrics.csv"
    _write_csv(summary_csv, [{"metric": key, "value": value} for key, value in summary["summary_metrics"].items()])

    summary_json = output_dir / "summary_metrics.json"
    summary_json.write_text(
        json.dumps(
            {
                "summary_metrics": summary["summary_metrics"],
                "baseline_summary_metrics": summary["baseline_summary_metrics"],
                "actual_spice_front_end_summary_metrics": summary["actual_spice_front_end_summary_metrics"],
                "front_end_rows": summary["front_end_rows"],
                "boundary_export_rows": summary["boundary_export_rows"],
                "case_rows": summary["case_rows"],
                "pre_click_rows": summary["pre_click_rows"],
                "post_click_rows": summary["post_click_rows"],
                "energy_case_rows": summary["energy_case_rows"],
                "energy_rows": summary["energy_rows"],
                "energy_summary": summary["energy_summary"],
                "case_comparison_rows": summary["case_comparison_rows"],
                "comparison_rows": summary["comparison_rows"],
                "chsh_result": summary["chsh_result"],
                "detector_spec": detector_model_spec,
            },
            indent=2,
            default=_json_default,
        )
        + "\n",
        encoding="utf-8",
    )

    outputs = {
        "front_end_dir": str(front_end_dir),
        "boundary_dir": str(boundary_dir),
        "full_chain_dir": str(full_chain_dir),
        "post_click_dir": str(post_click_dir),
        "energy_dir": str(energy_dir),
        "front_end_csv": str(front_end_csv),
        "boundary_csv": str(boundary_csv),
        "full_chain_csv": str(full_chain_csv),
        "case_comparison_csv": str(case_comparison_csv),
        "post_click_csv": str(post_click_csv),
        "energy_summary_csv": str(energy_summary_csv),
        "energy_trials_csv": str(energy_trials_csv),
        "candidate_comparison_csv": str(candidate_comparison_csv),
    }
    design_md = output_dir / "design_note.md"
    design_md.write_text(_design_note_markdown(summary=summary) + "\n", encoding="utf-8")
    outputs["design_md"] = str(design_md)

    summary_md = output_dir / "summary_report.md"
    summary_md.write_text(_summary_markdown(summary=summary, outputs=outputs) + "\n", encoding="utf-8")

    return {
        "summary_md": str(summary_md),
        "summary_json": str(summary_json),
        "summary_csv": str(summary_csv),
        "design_md": str(design_md),
        **outputs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the SPICE-driven preferred-chain report.")
    parser.add_argument("--outdir", default="artifacts/spice_driven_preferred_chain")
    parser.add_argument("--detector-next-summary-csv", default="artifacts/detector_next/results_summary.csv")
    parser.add_argument("--n-trials", type=int, default=1_200)
    parser.add_argument("--seed", type=int, default=20260411)
    parser.add_argument("--case", action="append", dest="case_names", default=None)
    parser.add_argument("--quiet-progress", action="store_true")
    args = parser.parse_args()
    build_spice_driven_preferred_chain_report(
        outdir=args.outdir,
        detector_next_summary_csv=args.detector_next_summary_csv,
        n_trials=args.n_trials,
        seed=args.seed,
        case_names=args.case_names,
        verbose_progress=not args.quiet_progress,
    )


if __name__ == "__main__":
    main()
