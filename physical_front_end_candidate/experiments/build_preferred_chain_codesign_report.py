from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from detector_integration.experiments.run_summary_report import load_top_shot_trigger_spec

from physical_front_end_candidate.preferred_chain_codesign import run_preferred_chain_codesign_benchmark
from physical_front_end_candidate.preferred_chain_codesign_plots import (
    plot_codesign_candidate_comparison,
    plot_codesign_chsh,
    plot_codesign_correlator,
    plot_codesign_node_voltage_snapshot,
    plot_codesign_pre_click_transparency,
    plot_codesign_topology,
    plot_codesign_winner_frequency,
    plot_loser_residual_fraction,
    plot_remaining_shared_energy_trace,
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
    comparison_rows = {row["candidate"]: row for row in summary["comparison_rows"]}
    decision = (
        "Proceed toward a deeper integrated hardware/netlist candidate."
        if bool(metrics["proceed_to_next_phase"])
        else "Iterate on the co-designed chain before moving deeper into hardware realization."
    )
    return "\n".join(
        [
            "# Preferred Chain Codesign Summary",
            "",
            "## Architecture",
            "",
            "- Chosen direction: Option A shared front-end netlist with an attached winner-gated post-click shunt branch.",
            "- One component table now contains the explicit front-end R/L/C netlist together with the attached common-inhibit, winner-gate, drain-tank, and shared-leak subnetwork.",
            "- Frozen detector boundary remains `piecewise_envelope:linear:20.0ms`, gain `4.0x`, exposure `5.0s`.",
            "- Frozen detector and latch semantics remain unchanged downstream of the detector-facing export.",
            "",
            "## Pre-Click / Front-End",
            "",
            f"- Front-end fraction RMS error: {float(metrics['front_end_fraction_rms_error']):.6f}",
            f"- Front-end fraction max error: {float(metrics['front_end_fraction_max_error']):.6f}",
            f"- Pre-click transparency RMS shift vs separated baseline: {float(metrics['pre_click_transparency_rms_shift']):.6f}",
            f"- Pre-click transparency max shift vs separated baseline: {float(metrics['pre_click_transparency_max_shift']):.6f}",
            "",
            "## Full-Chain Fidelity",
            "",
            f"- Winner-law RMS error: {float(metrics['winner_law_rms_error']):.6f}",
            f"- Winner-law max error: {float(metrics['winner_law_max_error']):.6f}",
            f"- Correlator RMS error: {float(metrics['correlator_rms_error']):.6f}",
            f"- CHSH absolute error: {float(metrics['chsh_abs_error']):.6f}",
            f"- Mean decisive fraction: {float(metrics['mean_decisive_fraction']):.6f}",
            "",
            "## Post-Click / Energy",
            "",
            f"- Winner-drain dominance rate: {float(metrics['winner_drain_dominance_rate']):.6f}",
            f"- Mean loser residual fraction of post-click energy: {float(metrics['mean_loser_fraction_of_post_click']):.6f}",
            f"- Completion rate: {float(metrics['completion_rate']):.6f}",
            f"- Energy-accounting pass: {bool(metrics['energy_accounting_pass'])}",
            "",
            "## Architectural Refinement",
            "",
            f"- Architecture explicitness pass: {bool(metrics['architecture_explicitness_pass'])}",
            f"- Architectural refinement pass: {bool(metrics['architectural_refinement_pass'])}",
            f"- No exact-weight shortcut fallback: {bool(metrics['no_trivial_exact_weight_assignment'])}",
            f"- Frozen boundary preserved: {bool(metrics['frozen_boundary_pass'])}",
            "",
            "## Baseline Comparison",
            "",
            f"- Separated baseline winner-law RMS: {float(baseline['winner_law_rms_error']):.6f}",
            f"- Codesigned chain winner-law RMS: {float(metrics['winner_law_rms_error']):.6f}",
            f"- Separated baseline correlator RMS: {float(baseline['correlator_rms_error']):.6f}",
            f"- Codesigned chain correlator RMS: {float(metrics['correlator_rms_error']):.6f}",
            f"- Separated baseline CHSH abs error: {float(baseline['chsh_abs_error']):.6f}",
            f"- Codesigned chain CHSH abs error: {float(metrics['chsh_abs_error']):.6f}",
            f"- Comparison CSV: `{outputs['candidate_comparison_csv']}`",
            f"- Baseline note: {comparison_rows['current_preferred_chain_baseline']['architecture_note']}",
            f"- Codesign note: {comparison_rows['preferred_chain_codesign']['architecture_note']}",
            "",
            "## Decision",
            "",
            f"- Proceed to next phase: {bool(metrics['proceed_to_next_phase'])}",
            f"- Decision: {decision}",
            "",
            "## Artifacts",
            "",
            f"- Netlist: `{outputs['netlist_dir']}`",
            f"- Pre-click: `{outputs['pre_click_dir']}`",
            f"- Post-click: `{outputs['post_click_dir']}`",
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
            "# Preferred Chain Codesign Design Note",
            "",
            "## Chosen Co-Design Architecture",
            "",
            "- Option A: the explicit front-end netlist now carries an attached post-click subnetwork rather than handing off to a separately specified closure/drain block.",
            "- The attached subnetwork includes a common inhibit rail, winner gate node, drain tank, shared leak node, branch clamp paths, and branch-local drain attachments in the same component table as the front-end elements.",
            "",
            "## How The Closure / Drain Attaches To The Front-End Netlist",
            "",
            "- Each branch node is explicitly wired to the common inhibit rail through clamp R/C attachments and to the drain tank through branch-local capacitive and resistive attachments.",
            "- The gate node is tied into the attached closure subnetwork through explicit gate-to-inhibit and gate-to-drain elements so the winner gate is no longer only an external control variable.",
            "- Pre-click transparency is preserved by solving the attached closure branches in the same nodal system with a strong off-state isolation factor on the branch-facing attachments.",
            "",
            "## Physical Location Of The Common Inhibit Rail",
            "",
            "- The common inhibit rail is an explicit node in the integrated netlist and sits above the four branch outputs as a shared suppression bus.",
            "- Loser clamp paths terminate onto this rail, and shared leakage is tied back to it through the shared-leak node.",
            "",
            "## Where The Winner Drain Path Attaches",
            "",
            "- The winner drain path is modeled as an explicit drain-tank node attached to every branch by physical attachment elements that are winner-enabled only after capture.",
            "- The post-click closure model derives its drain and clamp parameters from those attached elements instead of from an unrelated hand-entered downstream block.",
            "",
            "## What Remains Frozen",
            "",
            "- Detector boundary: `piecewise_envelope:linear:20.0ms`, gain `4.0x`, exposure `5.0s`.",
            "- Detector family and parameterization: frozen `shot_trigger` operating point.",
            "- Latch: frozen first-arrival arbiter semantics.",
            "- High-level semantics: front-end -> detector -> latch -> post-click closure ordering remains unchanged.",
            "",
            "## What Remains Abstract",
            "",
            "- The detector and latch are still reduced validated models, not transistor-level circuits.",
            "- The post-click time evolution is still simulated by the LC closure surrogate, though that surrogate is now parameterized from the attached component table.",
            "- The full candidate is still a simulation netlist, not a fabrication-ready schematic or layout.",
            "",
            "## Why This Is A Deeper Physical Step Than The Separated Baseline",
            "",
            "- The separated baseline solved the explicit front-end and then invoked a downstream closure/drain interpretation as a separate block.",
            "- This codesign step keeps the closure/drain ports physically attached inside the pre-click nodal solve and uses those attached components to derive the post-click closure parameters.",
            "- That makes the co-design question explicit: the closure hardware is present in the same netlist while the pre-click behavior remains transparent.",
            "",
            "## Current Outcome",
            "",
            f"- Front-end fraction pass: {bool(metrics['front_end_fraction_pass'])}",
            f"- Pre-click transparency pass: {bool(metrics['pre_click_transparency_pass'])}",
            f"- Winner-law pass: {bool(metrics['winner_law_pass'])}",
            f"- Correlator pass: {bool(metrics['correlator_pass'])}",
            f"- CHSH pass: {bool(metrics['chsh_pass'])}",
            f"- Winner-drain dominance pass: {bool(metrics['winner_drain_dominance_pass'])}",
            f"- Energy-accounting pass: {bool(metrics['energy_accounting_pass'])}",
            f"- Architectural refinement pass: {bool(metrics['architectural_refinement_pass'])}",
            "",
        ]
    )


def build_preferred_chain_codesign_report(
    outdir: str | Path = "artifacts/preferred_chain_codesign",
    *,
    detector_next_summary_csv: str | Path = "artifacts/detector_next/results_summary.csv",
    n_trials: int = 1_200,
    seed: int = 20260408,
    case_names: Sequence[str] | None = None,
    verbose_progress: bool = False,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    netlist_dir = output_dir / "netlist"
    pre_click_dir = output_dir / "pre_click"
    post_click_dir = output_dir / "post_click"
    full_chain_dir = output_dir / "full_chain"
    energy_dir = output_dir / "energy_accounting"
    for directory in (netlist_dir, pre_click_dir, post_click_dir, full_chain_dir, energy_dir):
        directory.mkdir(parents=True, exist_ok=True)

    detector_spec = load_top_shot_trigger_spec(detector_next_summary_csv)
    detector_model_spec = {
        "family": detector_spec["family"],
        "model_params": dict(detector_spec["model_params"]),
        "gain_scale": 2.0,
    }
    summary = run_preferred_chain_codesign_benchmark(
        detector_model_spec,
        n_trials=n_trials,
        seed=seed,
        case_names=case_names,
        verbose_progress=verbose_progress,
    )

    netlist_csv = netlist_dir / "netlist_summary.csv"
    front_end_csv = pre_click_dir / "front_end_summary.csv"
    pre_click_csv = pre_click_dir / "pre_click_transparency.csv"
    post_click_csv = post_click_dir / "post_click_summary.csv"
    full_chain_csv = full_chain_dir / "full_chain_summary.csv"
    case_comparison_csv = full_chain_dir / "baseline_case_comparison.csv"
    energy_summary_csv = energy_dir / "energy_accounting_summary.csv"
    energy_trials_csv = energy_dir / "energy_accounting_trials.csv"
    candidate_comparison_csv = output_dir / "candidate_comparison.csv"

    _write_csv(netlist_csv, list(summary["netlist_rows"]))
    _write_csv(front_end_csv, list(summary["front_end_rows"]))
    _write_csv(pre_click_csv, list(summary["pre_click_rows"]))
    _write_csv(post_click_csv, list(summary["post_click_rows"]))
    _write_csv(
        full_chain_csv,
        [
            {
                **{
                    key: value
                    for key, value in row.items()
                    if key
                    not in {
                        "branch_labels",
                        "exact_weights",
                        "realized_fractions",
                        "empirical_frequencies",
                    }
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
                "post_click_loser_energy_by_branch_j_json": json.dumps(
                    row["post_click_loser_energy_by_branch_j"],
                    sort_keys=True,
                ),
            }
            for row in summary["energy_rows"]
        ],
    )
    _write_csv(candidate_comparison_csv, list(summary["comparison_rows"]))

    plot_codesign_topology(dict(summary["example_front_end"])).savefig(netlist_dir / "integrated_netlist_topology.png") if summary["example_front_end"] is not None else None
    plot_codesign_pre_click_transparency(list(summary["pre_click_rows"])).savefig(
        pre_click_dir / "pre_click_transparency_vs_current_baseline.png"
    )
    plot_winner_drain_fraction(list(summary["post_click_rows"])).savefig(
        post_click_dir / "winner_drain_energy_fraction.png"
    )
    plot_loser_residual_fraction(list(summary["post_click_rows"])).savefig(
        post_click_dir / "loser_residual_energy_fraction.png"
    )
    plot_codesign_winner_frequency(list(summary["case_rows"])).savefig(
        full_chain_dir / "winner_frequency_exact_vs_empirical.png"
    )
    plot_codesign_correlator(list(summary["case_rows"])).savefig(
        full_chain_dir / "correlator_exact_vs_empirical.png"
    )
    if bool(summary["chsh_result"]["available"]):
        plot_codesign_chsh(dict(summary["chsh_result"])).savefig(full_chain_dir / "chsh_exact_vs_empirical.png")
    plot_whole_trial_energy_flow(list(summary["energy_case_rows"])).savefig(
        energy_dir / "whole_trial_energy_flow_summary.png"
    )
    plot_codesign_candidate_comparison(list(summary["comparison_rows"])).savefig(
        output_dir / "comparison_vs_current_preferred_chain_baseline.png"
    )

    if summary["example_front_end"] is not None:
        example_front_end = dict(summary["example_front_end"])
        plot_codesign_node_voltage_snapshot(example_front_end).savefig(
            netlist_dir / "integrated_node_voltage_snapshot.png"
        )
        _write_csv(netlist_dir / "component_table.csv", list(example_front_end["netlist"]["components"]))
        _write_csv(
            netlist_dir / "closure_component_table.csv",
            list(example_front_end["codesign"]["closure_components"]),
        )
        _write_csv(
            netlist_dir / "node_voltage_snapshot.csv",
            [
                {
                    "node_name": node_name,
                    "node_voltage_abs": abs(example_front_end["netlist"]["node_voltage_v"][index]),
                }
                for index, node_name in enumerate(example_front_end["netlist"]["node_order"])
            ],
        )
        _write_csv(
            pre_click_dir / "example_front_end_trace.csv",
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
            pre_click_dir / "example_export_trace.csv",
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

    if summary["example_trial"] is not None:
        example_trial = dict(summary["example_trial"])
        plot_remaining_shared_energy_trace(example_trial).savefig(
            post_click_dir / "remaining_shared_energy_vs_time.png"
        )
        physical = dict(example_trial["physical"])
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
                    "common_inhibit_current_a": physical["common_inhibit_current_a"][index],
                    "winner_gate_current_a": physical["winner_gate_current_a"][index],
                    "drain_bus_voltage_v": physical["drain_bus_voltage_v"][index],
                    **{
                        f"{label}_branch_attachment_current_a": values[index]
                        for label, values in physical["branch_attachment_current_a"].items()
                    },
                    **{
                        f"{label}_loser_power_w": values[index]
                        for label, values in physical["loser_branch_power_w"].items()
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
                "netlist_rows": summary["netlist_rows"],
                "front_end_rows": summary["front_end_rows"],
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
        "netlist_dir": str(netlist_dir),
        "pre_click_dir": str(pre_click_dir),
        "post_click_dir": str(post_click_dir),
        "full_chain_dir": str(full_chain_dir),
        "energy_dir": str(energy_dir),
        "netlist_csv": str(netlist_csv),
        "front_end_csv": str(front_end_csv),
        "pre_click_csv": str(pre_click_csv),
        "post_click_csv": str(post_click_csv),
        "full_chain_csv": str(full_chain_csv),
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
    parser = argparse.ArgumentParser(description="Build the preferred chain codesign report.")
    parser.add_argument("--outdir", default="artifacts/preferred_chain_codesign")
    parser.add_argument("--detector-next-summary-csv", default="artifacts/detector_next/results_summary.csv")
    parser.add_argument("--n-trials", type=int, default=1_200)
    parser.add_argument("--seed", type=int, default=20260408)
    parser.add_argument("--case", action="append", dest="case_names", default=None)
    parser.add_argument("--quiet-progress", action="store_true")
    args = parser.parse_args()
    build_preferred_chain_codesign_report(
        outdir=args.outdir,
        detector_next_summary_csv=args.detector_next_summary_csv,
        n_trials=args.n_trials,
        seed=args.seed,
        case_names=args.case_names,
        verbose_progress=not args.quiet_progress,
    )


if __name__ == "__main__":
    main()
