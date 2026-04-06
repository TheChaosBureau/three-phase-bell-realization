from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from detector_integration.experiments.run_summary_report import load_top_shot_trigger_spec

from physical_front_end_candidate.preferred_physical_chain_lc import run_preferred_physical_chain_lc_benchmark
from physical_front_end_candidate.preferred_physical_chain_lc_plots import (
    plot_lc_candidate_comparison,
    plot_lc_chsh,
    plot_lc_correlator,
    plot_lc_coupled_port_diagnostics,
    plot_lc_front_end_fraction,
    plot_lc_resonant_mode_diagnostics,
    plot_lc_shared_core_modal_diagnostics,
    plot_lc_winner_frequency,
    plot_loser_residual_fraction,
    plot_remaining_shared_energy_trace,
    plot_whole_trial_energy_flow,
    plot_winner_drain_fraction,
    plot_winner_drain_power,
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
    comparison_rows = {row["candidate"]: row for row in summary["comparison_rows"]}
    decision = (
        "Proceed toward the next hardware/netlist physicalization step."
        if bool(metrics["proceed_to_next_phase"])
        else "Iterate on the LC/coupled-port realization before deeper physicalization."
    )
    return "\n".join(
        [
            "# Preferred Physical Chain LC Summary",
            "",
            "## Architecture",
            "",
            "- Chosen direction: Option C hybrid modal preparation with explicit coupled-port readout.",
            "- Frozen boundary: `piecewise_envelope:linear:20.0ms`, gain `4.0x`, exposure `5.0s`.",
            "- Frozen detector: `shot_trigger` with the validated operating-point parameters.",
            "- Frozen latch: first-arrival arbiter.",
            "- Explicit post-click block: common inhibit RC gate plus resonant winner drain.",
            "",
            "## Full-Chain Fidelity",
            "",
            f"- Winner-law RMS error: {float(metrics['winner_law_rms_error']):.6f}",
            f"- Winner-law max error: {float(metrics['winner_law_max_error']):.6f}",
            f"- Correlator RMS error: {float(metrics['correlator_rms_error']):.6f}",
            f"- CHSH absolute error: {float(metrics['chsh_abs_error']):.6f}",
            f"- Mean decisive fraction: {float(metrics['mean_decisive_fraction']):.6f}",
            "",
            "## LC Explicitness",
            "",
            f"- Architectural explicitness pass: {bool(metrics['architecture_explicitness_pass'])}",
            f"- No trivial exact-weight fallback: {bool(metrics['no_trivial_exact_weight_assignment'])}",
            f"- Frozen boundary preserved: {bool(metrics['frozen_boundary_pass'])}",
            "",
            "## Baseline Comparison",
            "",
            f"- Current preferred-chain winner-law RMS: {float(baseline['winner_law_rms_error']):.6f}",
            f"- LC preferred-chain winner-law RMS: {float(metrics['winner_law_rms_error']):.6f}",
            f"- Current preferred-chain correlator RMS: {float(baseline['correlator_rms_error']):.6f}",
            f"- LC preferred-chain correlator RMS: {float(metrics['correlator_rms_error']):.6f}",
            f"- Current preferred-chain CHSH abs error: {float(baseline['chsh_abs_error']):.6f}",
            f"- LC preferred-chain CHSH abs error: {float(metrics['chsh_abs_error']):.6f}",
            f"- Current preferred-chain winner-drain dominance: {float(baseline['winner_drain_dominance_rate']):.6f}",
            f"- LC preferred-chain winner-drain dominance: {float(metrics['winner_drain_dominance_rate']):.6f}",
            f"- Comparison CSV: `{outputs['candidate_comparison_csv']}`",
            f"- Baseline note: {comparison_rows['current_preferred_chain']['architecture_note']}",
            f"- LC note: {comparison_rows['preferred_chain_lc']['architecture_note']}",
            "",
            "## Post-Click / Energy",
            "",
            f"- Winner-drain dominance rate: {float(metrics['winner_drain_dominance_rate']):.6f}",
            f"- Mean loser residual fraction of post-click energy: {float(metrics['mean_loser_fraction_of_post_click']):.6f}",
            f"- Completion rate: {float(metrics['completion_rate']):.6f}",
            f"- Energy-accounting pass: {bool(metrics['energy_accounting_pass'])}",
            "",
            "## Decision",
            "",
            f"- Proceed to next phase: {bool(metrics['proceed_to_next_phase'])}",
            f"- Decision: {decision}",
            "",
            "## Artifacts",
            "",
            f"- Shared core: `{outputs['shared_core_dir']}`",
            f"- Front end: `{outputs['front_end_dir']}`",
            f"- Post click: `{outputs['post_click_dir']}`",
            f"- Full chain: `{outputs['full_chain_dir']}`",
            f"- Energy accounting: `{outputs['energy_dir']}`",
            f"- Design note: `{outputs['design_md']}`",
            "",
        ]
    )


def _design_note_markdown(*, summary: dict[str, Any]) -> str:
    metrics = summary["summary_metrics"]
    return "\n".join(
        [
            "# Preferred Physical Chain LC Design Note",
            "",
            "## Chosen Architecture",
            "",
            "- Option C: hybrid modal preparation with explicit coupled-port / load readout and explicit closure/drain circuit semantics.",
            "- The shared four-tank core still prepares the singlet-like mode, but the readout side is now expressed as an admittance-coupled port network with explicit source impedances, branch loads, bridge coupling, side coupling, and return coupling.",
            "",
            "## How This Improves Physical Explicitness",
            "",
            "- The front-end now contains an explicit coupled-port nodal solve, not only a reduced modal amplitude map.",
            "- The post-click block is now written as an RC-gated, resonant winner-drain circuit with explicit shared and drain resonant frequencies, gate node, inhibit node, and clamp currents.",
            "",
            "## Preparation Representation",
            "",
            "- Preparation still targets the shared singlet-like mode of the four-tank core.",
            "- The modal preparation is injected into the explicit port solve through a hybrid state that mixes the prepared modal state with the coupled-port nodal solution.",
            "",
            "## Analyzer Dependence",
            "",
            "- Analyzer settings remain encoded through the existing Alice/Bob coupler matrices.",
            "- The analyzer output then feeds the explicit passive readout/load realization rather than a detector-facing exact-weight shortcut.",
            "",
            "## Closure / Drain Representation",
            "",
            "- Closure remains the frozen interpretation: common inhibit rail plus winner-only drain enable.",
            "- The LC candidate realizes that interpretation with explicit inhibit RC timing, winner gate timing, shared-tank energy decay, loser clamp conductances, and a resonant winner drain branch.",
            "",
            "## What Remains Abstract",
            "",
            "- The detector remains the frozen stochastic `shot_trigger` model.",
            "- The latch remains the validated first-arrival arbiter contract.",
            "- The shared core and drain are still lumped-element surrogates, not a transistor or fabrication-ready netlist.",
            "",
            "## What Was Kept Frozen",
            "",
            "- Detector export mode: `piecewise_envelope:linear:20.0ms`.",
            "- Detector gain and exposure: `4.0x`, `5.0s`.",
            "- Detector family and parameters.",
            "- Latch timing semantics.",
            "- Architectural role split between front end, detector/latch, and post-click closure/drain.",
            "",
            "## Current Outcome",
            "",
            f"- Winner-law pass: {bool(metrics['winner_law_pass'])}",
            f"- Correlator pass: {bool(metrics['correlator_pass'])}",
            f"- CHSH pass: {bool(metrics['chsh_pass'])}",
            f"- Pre-click transparency pass: {bool(metrics['pre_click_transparency_pass'])}",
            f"- Winner-drain dominance pass: {bool(metrics['winner_drain_dominance_pass'])}",
            f"- Energy-accounting pass: {bool(metrics['energy_accounting_pass'])}",
            f"- Architectural explicitness pass: {bool(metrics['architecture_explicitness_pass'])}",
            f"- No trivial exact-weight fallback: {bool(metrics['no_trivial_exact_weight_assignment'])}",
            "",
        ]
    )


def build_preferred_physical_chain_lc_report(
    outdir: str | Path = "artifacts/preferred_physical_chain_lc",
    *,
    detector_next_summary_csv: str | Path = "artifacts/detector_next/results_summary.csv",
    n_trials: int = 1_200,
    seed: int = 20260406,
    case_names: Sequence[str] | None = None,
    verbose_progress: bool = False,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    shared_core_dir = output_dir / "shared_core"
    front_end_dir = output_dir / "front_end"
    post_click_dir = output_dir / "post_click"
    full_chain_dir = output_dir / "full_chain"
    energy_dir = output_dir / "energy_accounting"
    for directory in (shared_core_dir, front_end_dir, post_click_dir, full_chain_dir, energy_dir):
        directory.mkdir(parents=True, exist_ok=True)

    detector_spec = load_top_shot_trigger_spec(detector_next_summary_csv)
    detector_model_spec = {
        "family": detector_spec["family"],
        "model_params": dict(detector_spec["model_params"]),
        "gain_scale": 2.0,
    }
    summary = run_preferred_physical_chain_lc_benchmark(
        detector_model_spec,
        n_trials=n_trials,
        seed=seed,
        case_names=case_names,
        verbose_progress=verbose_progress,
    )

    front_end_csv = front_end_dir / "front_end_summary.csv"
    shared_core_csv = shared_core_dir / "shared_core_summary.csv"
    full_chain_csv = full_chain_dir / "full_chain_summary.csv"
    pre_click_csv = full_chain_dir / "pre_click_transparency.csv"
    post_click_csv = post_click_dir / "post_click_summary.csv"
    case_comparison_csv = full_chain_dir / "baseline_case_comparison.csv"
    energy_summary_csv = energy_dir / "energy_accounting_summary.csv"
    energy_trials_csv = energy_dir / "energy_accounting_trials.csv"
    candidate_comparison_csv = output_dir / "candidate_comparison.csv"

    _write_csv(front_end_csv, list(summary["front_end_rows"]))
    _write_csv(shared_core_csv, list(summary["shared_core_rows"]))
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
    _write_csv(pre_click_csv, list(summary["pre_click_rows"]))
    _write_csv(post_click_csv, list(summary["post_click_rows"]))
    _write_csv(case_comparison_csv, list(summary["case_comparison_rows"]))
    _write_csv(energy_summary_csv, list(summary["energy_case_rows"]))
    _write_csv(
        energy_trials_csv,
        [
            {
                **{
                    key: value
                    for key, value in row.items()
                    if key
                    not in {
                        "pre_click_branch_energy_j",
                        "future_branch_energy_j",
                        "post_click_loser_energy_by_branch_j",
                    }
                },
                "pre_click_branch_energy_j_json": json.dumps(row["pre_click_branch_energy_j"], sort_keys=True),
                "future_branch_energy_j_json": json.dumps(row["future_branch_energy_j"], sort_keys=True),
                "post_click_loser_energy_by_branch_j_json": json.dumps(row["post_click_loser_energy_by_branch_j"], sort_keys=True),
            }
            for row in summary["energy_rows"]
        ],
    )
    _write_csv(candidate_comparison_csv, list(summary["comparison_rows"]))

    plot_lc_front_end_fraction(list(summary["front_end_rows"])).savefig(front_end_dir / "exact_vs_realized_four_branch_energy_fractions.png")
    plot_lc_winner_frequency(list(summary["case_rows"])).savefig(full_chain_dir / "winner_frequency_exact_vs_empirical.png")
    plot_lc_correlator(list(summary["case_rows"])).savefig(full_chain_dir / "correlator_exact_vs_empirical.png")
    if bool(summary["chsh_result"]["available"]):
        plot_lc_chsh(dict(summary["chsh_result"])).savefig(full_chain_dir / "chsh_exact_vs_empirical.png")
    plot_winner_drain_fraction(list(summary["post_click_rows"])).savefig(post_click_dir / "winner_drain_energy_fraction.png")
    plot_loser_residual_fraction(list(summary["post_click_rows"])).savefig(post_click_dir / "loser_residual_energy_fraction.png")
    plot_whole_trial_energy_flow(list(summary["energy_case_rows"])).savefig(energy_dir / "whole_trial_energy_flow_summary.png")
    plot_lc_candidate_comparison(list(summary["comparison_rows"])).savefig(output_dir / "comparison_vs_current_preferred_chain.png")

    if summary["example_front_end"] is not None:
        example_front_end = dict(summary["example_front_end"])
        plot_lc_shared_core_modal_diagnostics(example_front_end).savefig(shared_core_dir / "shared_core_modal_diagnostics.png")
        plot_lc_resonant_mode_diagnostics(example_front_end).savefig(shared_core_dir / "shared_core_resonant_mode_diagnostics.png")
        plot_lc_coupled_port_diagnostics(example_front_end).savefig(shared_core_dir / "shared_core_coupled_port_diagnostics.png")
        _write_csv(
            front_end_dir / "example_front_end_trace.csv",
            [
                {
                    "time_s": example_front_end["time_s"][index],
                    **{
                        f"{label}_branch_power_w": example_front_end["branch_power_w"][label][index]
                        for label in example_front_end["branch_labels"]
                    },
                }
                for index in range(len(example_front_end["time_s"]))
            ],
        )
        _write_csv(
            front_end_dir / "example_export_trace.csv",
            [
                {
                    "time_s": example_front_end["export_time_s"][index],
                    **{
                        f"{label}_exported_power_w": example_front_end["exported_branch_power"][label][index]
                        for label in example_front_end["branch_labels"]
                    },
                }
                for index in range(len(example_front_end["export_time_s"]))
            ],
        )
        shared = example_front_end["shared_core"]
        _write_csv(
            shared_core_dir / "example_coupled_port_snapshot.csv",
            [
                {
                    "branch_label": label,
                    "port_node_voltage_abs": abs(shared["port_node_voltage_v"][index]),
                    "source_current_abs": abs(shared["source_current_a"][index]),
                    "prepared_state_abs": abs(shared["prepared_internal_state"][index]),
                    "explicit_port_state_abs": abs(shared["explicit_port_state"][index]),
                    "hybrid_state_abs": abs(shared["hybrid_state"][index]),
                }
                for index, label in enumerate(example_front_end["branch_labels"])
            ],
        )

    if summary["example_trial"] is not None:
        example_trial = dict(summary["example_trial"])
        plot_remaining_shared_energy_trace(example_trial).savefig(post_click_dir / "remaining_shared_energy_vs_time.png")
        plot_winner_drain_power(example_trial["physical"]).savefig(post_click_dir / "winner_drain_power_vs_time.png")
        physical = example_trial["physical"]
        _write_csv(
            post_click_dir / "example_trial_trace.csv",
            [
                {
                    "time_s": physical["time_s"][index],
                    "closure_variable": physical["closure_variable"][index],
                    "common_inhibit_v": physical["common_inhibit_v"][index],
                    "winner_gate_v": physical["winner_gate_v"][index],
                    "shared_node_voltage_v": physical["shared_node_voltage_v"][index],
                    "shared_resonant_current_a": physical["shared_resonant_current_a"][index],
                    "winner_drain_tank_voltage_v": physical["winner_drain_tank_voltage_v"][index],
                    "winner_drain_power_w": physical["winner_drain_power_w"][index],
                    "winner_drain_current_a": physical["winner_drain_current_a"][index],
                    "winner_drain_energy_j": physical["winner_drain_energy_j"][index],
                    "remaining_shared_energy_j": physical["remaining_shared_energy_j"][index],
                    "trial_complete_signal": physical["trial_complete_signal"][index],
                    "winner_branch_power_w": physical["winner_branch_power_w"][index],
                    **{
                        f"{label}_loser_power_w": values[index]
                        for label, values in physical["loser_branch_power_w"].items()
                    },
                    **{
                        f"{label}_loser_clamp_current_a": values[index]
                        for label, values in physical["loser_clamp_current_a"].items()
                    },
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
                "front_end_rows": summary["front_end_rows"],
                "case_rows": summary["case_rows"],
                "pre_click_rows": summary["pre_click_rows"],
                "post_click_rows": summary["post_click_rows"],
                "energy_case_rows": summary["energy_case_rows"],
                "energy_rows": summary["energy_rows"],
                "energy_summary": summary["energy_summary"],
                "shared_core_rows": summary["shared_core_rows"],
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
        "shared_core_dir": str(shared_core_dir),
        "front_end_dir": str(front_end_dir),
        "post_click_dir": str(post_click_dir),
        "full_chain_dir": str(full_chain_dir),
        "energy_dir": str(energy_dir),
        "front_end_csv": str(front_end_csv),
        "shared_core_csv": str(shared_core_csv),
        "full_chain_csv": str(full_chain_csv),
        "pre_click_csv": str(pre_click_csv),
        "post_click_csv": str(post_click_csv),
        "case_comparison_csv": str(case_comparison_csv),
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
    parser = argparse.ArgumentParser(description="Build the preferred physical-chain LC report.")
    parser.add_argument("--outdir", default="artifacts/preferred_physical_chain_lc")
    parser.add_argument("--detector-next-summary-csv", default="artifacts/detector_next/results_summary.csv")
    parser.add_argument("--n-trials", type=int, default=1_200)
    parser.add_argument("--seed", type=int, default=20260406)
    parser.add_argument("--case", action="append", dest="case_names", default=None)
    parser.add_argument("--quiet-progress", action="store_true")
    args = parser.parse_args()
    build_preferred_physical_chain_lc_report(
        outdir=args.outdir,
        detector_next_summary_csv=args.detector_next_summary_csv,
        n_trials=args.n_trials,
        seed=args.seed,
        case_names=args.case_names,
        verbose_progress=not args.quiet_progress,
    )


if __name__ == "__main__":
    main()
