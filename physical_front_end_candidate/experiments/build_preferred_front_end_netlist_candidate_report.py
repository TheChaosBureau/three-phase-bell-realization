from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from detector_integration.experiments.run_summary_report import load_top_shot_trigger_spec

from physical_front_end_candidate.preferred_front_end_netlist_candidate import run_preferred_front_end_netlist_benchmark
from physical_front_end_candidate.preferred_front_end_netlist_candidate_plots import (
    plot_netlist_candidate_comparison,
    plot_netlist_chsh,
    plot_netlist_correlator,
    plot_netlist_front_end_fraction,
    plot_netlist_modal_diagnostics,
    plot_netlist_node_magnitudes,
    plot_netlist_resonant_mode_diagnostics,
    plot_netlist_topology,
    plot_netlist_winner_frequency,
    plot_whole_trial_energy_flow,
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
        "Proceed toward front-end plus closure/drain co-design or a deeper hardware candidate."
        if bool(metrics["proceed_to_next_phase"])
        else "Iterate on the front-end netlist candidate before deeper hardware physicalization."
    )
    return "\n".join(
        [
            "# Preferred Front-End Netlist Candidate Summary",
            "",
            "## Architecture",
            "",
            "- Chosen direction: Option C hybrid preparation with an explicit component-level R/L/C netlist for the preferred front-end.",
            "- Frozen detector boundary remains `piecewise_envelope:linear:20.0ms`, gain `4.0x`, exposure `5.0s`.",
            "- Frozen detector, latch, and closure/drain semantics are unchanged downstream of the front-end.",
            "",
            "## Front-End Fidelity",
            "",
            f"- Front-end fraction RMS error: {float(metrics['front_end_fraction_rms_error']):.6f}",
            f"- Front-end fraction max error: {float(metrics['front_end_fraction_max_error']):.6f}",
            f"- Front-end fraction pass: {bool(metrics['front_end_fraction_pass'])}",
            "",
            "## Full-Chain Fidelity",
            "",
            f"- Winner-law RMS error: {float(metrics['winner_law_rms_error']):.6f}",
            f"- Winner-law max error: {float(metrics['winner_law_max_error']):.6f}",
            f"- Correlator RMS error: {float(metrics['correlator_rms_error']):.6f}",
            f"- CHSH absolute error: {float(metrics['chsh_abs_error']):.6f}",
            f"- Mean decisive fraction: {float(metrics['mean_decisive_fraction']):.6f}",
            "",
            "## Architectural Explicitness",
            "",
            f"- Architecture explicitness pass: {bool(metrics['architecture_explicitness_pass'])}",
            f"- No trivial exact-weight fallback: {bool(metrics['no_trivial_exact_weight_assignment'])}",
            f"- Frozen boundary preserved: {bool(metrics['frozen_boundary_pass'])}",
            "",
            "## LC Baseline Comparison",
            "",
            f"- Current LC preferred-chain winner-law RMS: {float(baseline['winner_law_rms_error']):.6f}",
            f"- Netlist candidate winner-law RMS: {float(metrics['winner_law_rms_error']):.6f}",
            f"- Current LC preferred-chain correlator RMS: {float(baseline['correlator_rms_error']):.6f}",
            f"- Netlist candidate correlator RMS: {float(metrics['correlator_rms_error']):.6f}",
            f"- Current LC preferred-chain CHSH abs error: {float(baseline['chsh_abs_error']):.6f}",
            f"- Netlist candidate CHSH abs error: {float(metrics['chsh_abs_error']):.6f}",
            f"- Comparison CSV: `{outputs['candidate_comparison_csv']}`",
            f"- Baseline note: {comparison_rows['current_preferred_chain_lc']['architecture_note']}",
            f"- Netlist note: {comparison_rows['preferred_front_end_netlist']['architecture_note']}",
            "",
            "## Energy Accounting",
            "",
            f"- Energy-accounting pass: {bool(metrics['energy_accounting_pass'])}",
            f"- Max energy-balance abs fraction: {float(metrics['max_energy_balance_abs_fraction']):.6e}",
            "",
            "## Decision",
            "",
            f"- Proceed to next phase: {bool(metrics['proceed_to_next_phase'])}",
            f"- Decision: {decision}",
            "",
            "## Artifacts",
            "",
            f"- Netlist artifacts: `{outputs['netlist_dir']}`",
            f"- Front-end artifacts: `{outputs['front_end_dir']}`",
            f"- Integration artifacts: `{outputs['integration_dir']}`",
            f"- Energy-accounting artifacts: `{outputs['energy_dir']}`",
            f"- Design note: `{outputs['design_md']}`",
            "",
        ]
    )


def _design_note_markdown(*, summary: dict[str, Any]) -> str:
    metrics = summary["summary_metrics"]
    return "\n".join(
        [
            "# Preferred Front-End Netlist Candidate Design Note",
            "",
            "## Chosen Netlist Architecture",
            "",
            "- Option C: hybrid preparation retained, but the preferred front-end is now represented and solved as an explicit component-level netlist.",
            "- The netlist is organized as four branch-mode nodes with explicit source branches, tank storage elements, load/readout elements, and inter-branch coupling elements.",
            "",
            "## Element Classes Used",
            "",
            "- Resistors: source resistors, tank-loss resistors, bridge resistor, load resistors.",
            "- Inductors: source inductors and branch tank inductors.",
            "- Capacitors: tank capacitors, readout shunt capacitors, bridge capacitor, side/return coupling capacitors.",
            "- Norton-equivalent drive sources: one per branch drive port at the solved drive frequency.",
            "",
            "## Shared Resonant Structure",
            "",
            "- Each branch-mode node has an explicit tank inductance, tank capacitance, and damping resistance.",
            "- The shared resonant structure is created by explicit inter-node coupling components rather than by directly assigning branch weights.",
            "",
            "## Preparation Representation",
            "",
            "- Preparation still targets the singlet-like shared mode of the four-tank core.",
            "- That preparation drives the explicit netlist through branch drive sources, and the solved netlist state is combined with the prepared modal state using the existing hybrid bridge needed for fidelity.",
            "",
            "## Analyzer / Readout Coupling",
            "",
            "- Analyzer dependence remains encoded through explicit analyzer-port transformations using the validated Alice/Bob coupler matrices.",
            "- The transformed state then passes through the explicit load/readout branches rather than a direct exact-weight assignment.",
            "",
            "## What Remains Abstract",
            "",
            "- The preparation block is still reduced-order rather than a final drive electronics netlist.",
            "- The detector, latch, and closure/drain remain frozen downstream abstractions from the validated chain.",
            "- The candidate is still a simulation netlist, not a fabrication-ready layout.",
            "",
            "## Why This Is More Explicit Than The Current LC Preferred Chain",
            "",
            "- The previous LC preferred chain exposed an admittance solve but not a component-level netlist decomposition.",
            "- This ticket introduces an explicit component table with identifiable R/L/C branches and couplers, plus a topology report and component-level diagnostics.",
            "",
            "## Current Outcome",
            "",
            f"- Front-end fraction pass: {bool(metrics['front_end_fraction_pass'])}",
            f"- Winner-law pass: {bool(metrics['winner_law_pass'])}",
            f"- Correlator pass: {bool(metrics['correlator_pass'])}",
            f"- CHSH pass: {bool(metrics['chsh_pass'])}",
            f"- Energy-accounting pass: {bool(metrics['energy_accounting_pass'])}",
            f"- Architectural explicitness pass: {bool(metrics['architecture_explicitness_pass'])}",
            f"- No trivial exact-weight fallback: {bool(metrics['no_trivial_exact_weight_assignment'])}",
            "",
        ]
    )


def build_preferred_front_end_netlist_candidate_report(
    outdir: str | Path = "artifacts/preferred_front_end_netlist_candidate",
    *,
    detector_next_summary_csv: str | Path = "artifacts/detector_next/results_summary.csv",
    n_trials: int = 1_200,
    seed: int = 20260407,
    case_names: Sequence[str] | None = None,
    verbose_progress: bool = False,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    netlist_dir = output_dir / "netlist"
    front_end_dir = output_dir / "front_end"
    integration_dir = output_dir / "integration"
    energy_dir = output_dir / "energy_accounting"
    for directory in (netlist_dir, front_end_dir, integration_dir, energy_dir):
        directory.mkdir(parents=True, exist_ok=True)

    detector_spec = load_top_shot_trigger_spec(detector_next_summary_csv)
    detector_model_spec = {
        "family": detector_spec["family"],
        "model_params": dict(detector_spec["model_params"]),
        "gain_scale": 2.0,
    }
    summary = run_preferred_front_end_netlist_benchmark(
        detector_model_spec,
        n_trials=n_trials,
        seed=seed,
        case_names=case_names,
        verbose_progress=verbose_progress,
    )

    netlist_csv = netlist_dir / "netlist_summary.csv"
    front_end_csv = front_end_dir / "front_end_summary.csv"
    integration_csv = integration_dir / "integration_summary.csv"
    pre_click_csv = integration_dir / "pre_click_comparison.csv"
    case_comparison_csv = integration_dir / "baseline_case_comparison.csv"
    energy_summary_csv = energy_dir / "energy_accounting_summary.csv"
    energy_trials_csv = energy_dir / "energy_accounting_trials.csv"
    candidate_comparison_csv = output_dir / "candidate_comparison.csv"

    _write_csv(netlist_csv, list(summary["netlist_rows"]))
    _write_csv(front_end_csv, list(summary["front_end_rows"]))
    _write_csv(
        integration_csv,
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

    plot_netlist_front_end_fraction(list(summary["front_end_rows"])).savefig(front_end_dir / "exact_vs_realized_four_branch_energy_fractions.png")
    plot_netlist_winner_frequency(list(summary["case_rows"])).savefig(integration_dir / "winner_frequency_exact_vs_empirical.png")
    plot_netlist_correlator(list(summary["case_rows"])).savefig(integration_dir / "correlator_exact_vs_empirical.png")
    if bool(summary["chsh_result"]["available"]):
        plot_netlist_chsh(dict(summary["chsh_result"])).savefig(integration_dir / "chsh_exact_vs_empirical.png")
    plot_whole_trial_energy_flow(list(summary["energy_case_rows"])).savefig(energy_dir / "whole_trial_energy_flow_summary.png")
    plot_netlist_candidate_comparison(list(summary["comparison_rows"])).savefig(output_dir / "comparison_vs_current_lc_preferred_chain.png")

    if summary["example_front_end"] is not None:
        example_front_end = dict(summary["example_front_end"])
        plot_netlist_topology(example_front_end).savefig(netlist_dir / "netlist_topology.png")
        plot_netlist_modal_diagnostics(example_front_end).savefig(netlist_dir / "internal_modal_diagnostics.png")
        plot_netlist_resonant_mode_diagnostics(example_front_end).savefig(netlist_dir / "internal_resonant_mode_diagnostics.png")
        plot_netlist_node_magnitudes(example_front_end).savefig(netlist_dir / "node_voltage_and_drive_current.png")
        _write_csv(netlist_dir / "component_table.csv", list(example_front_end["netlist"]["components"]))
        _write_csv(netlist_dir / "source_branches.csv", list(example_front_end["netlist"]["source_branches"]))
        _write_csv(
            netlist_dir / "node_voltage_snapshot.csv",
            [
                {
                    "branch_label": label,
                    "node_voltage_abs": abs(example_front_end["netlist"]["node_voltage_v"][index]),
                }
                for index, label in enumerate(example_front_end["branch_labels"])
            ],
        )
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

    summary_csv = output_dir / "summary_metrics.csv"
    _write_csv(summary_csv, [{"metric": key, "value": value} for key, value in summary["summary_metrics"].items()])

    summary_json = output_dir / "summary_metrics.json"
    summary_json.write_text(
        json.dumps(
            {
                "summary_metrics": summary["summary_metrics"],
                "baseline_summary_metrics": summary["baseline_summary_metrics"],
                "netlist_rows": summary["netlist_rows"],
                "front_end_rows": summary["front_end_rows"],
                "case_rows": summary["case_rows"],
                "pre_click_rows": summary["pre_click_rows"],
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
        "netlist_dir": str(netlist_dir),
        "front_end_dir": str(front_end_dir),
        "integration_dir": str(integration_dir),
        "energy_dir": str(energy_dir),
        "netlist_csv": str(netlist_csv),
        "front_end_csv": str(front_end_csv),
        "integration_csv": str(integration_csv),
        "pre_click_csv": str(pre_click_csv),
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
    parser = argparse.ArgumentParser(description="Build the preferred front-end netlist candidate report.")
    parser.add_argument("--outdir", default="artifacts/preferred_front_end_netlist_candidate")
    parser.add_argument("--detector-next-summary-csv", default="artifacts/detector_next/results_summary.csv")
    parser.add_argument("--n-trials", type=int, default=1_200)
    parser.add_argument("--seed", type=int, default=20260407)
    parser.add_argument("--case", action="append", dest="case_names", default=None)
    parser.add_argument("--quiet-progress", action="store_true")
    args = parser.parse_args()
    build_preferred_front_end_netlist_candidate_report(
        outdir=args.outdir,
        detector_next_summary_csv=args.detector_next_summary_csv,
        n_trials=args.n_trials,
        seed=args.seed,
        case_names=args.case_names,
        verbose_progress=not args.quiet_progress,
    )


if __name__ == "__main__":
    main()
