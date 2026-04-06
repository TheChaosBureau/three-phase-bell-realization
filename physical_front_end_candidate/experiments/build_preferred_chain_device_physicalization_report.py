from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from detector_integration.experiments.run_summary_report import load_top_shot_trigger_spec

from physical_front_end_candidate.preferred_chain_device_physicalization import (
    run_preferred_chain_device_physicalization_benchmark,
)
from physical_front_end_candidate.preferred_chain_device_physicalization_plots import (
    plot_device_candidate_comparison,
    plot_device_chsh,
    plot_device_correlator,
    plot_device_pre_click_transparency,
    plot_device_subblock_component_summary,
    plot_device_subblock_internal_signals,
    plot_device_subblock_node_snapshot,
    plot_device_winner_frequency,
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
        "Proceed toward either another subblock physicalization step or a deeper integrated hardware candidate."
        if bool(metrics["proceed_to_next_phase"])
        else "Iterate on the physicalized subblocks before pushing the integrated chain further."
    )
    return "\n".join(
        [
            "# Preferred Chain Device Physicalization Summary",
            "",
            "## Architecture",
            "",
            "- Selected subblocks: common inhibit rail realization and winner drain path realization.",
            "- The current integrated preferred-chain baseline is preserved at the top level while the selected subblocks are made more device-explicit internally.",
            "- Frozen detector boundary remains `piecewise_envelope:linear:20.0ms`, gain `4.0x`, exposure `5.0s`.",
            "- Frozen detector and latch semantics remain unchanged.",
            "",
            "## Preserved Chain Performance",
            "",
            f"- Front-end fraction RMS error: {float(metrics['front_end_fraction_rms_error']):.6f}",
            f"- Winner-law RMS error: {float(metrics['winner_law_rms_error']):.6f}",
            f"- Winner-law max error: {float(metrics['winner_law_max_error']):.6f}",
            f"- Correlator RMS error: {float(metrics['correlator_rms_error']):.6f}",
            f"- CHSH absolute error: {float(metrics['chsh_abs_error']):.6f}",
            f"- Pre-click transparency RMS shift vs current integrated baseline: {float(metrics['pre_click_transparency_rms_shift']):.6f}",
            "",
            "## Post-Click / Energy",
            "",
            f"- Winner-drain dominance rate: {float(metrics['winner_drain_dominance_rate']):.6f}",
            f"- Mean loser residual fraction of post-click energy: {float(metrics['mean_loser_fraction_of_post_click']):.6f}",
            f"- Completion rate: {float(metrics['completion_rate']):.6f}",
            f"- Energy-accounting pass: {bool(metrics['energy_accounting_pass'])}",
            "",
            "## Realism Gain",
            "",
            f"- Architectural realism gain pass: {bool(metrics['architectural_realism_gain_pass'])}",
            f"- No legacy subblock fallback: {bool(metrics['no_legacy_subblock_fallback'])}",
            f"- Frozen boundary preserved: {bool(metrics['frozen_boundary_pass'])}",
            "",
            "## Baseline Comparison",
            "",
            f"- Current integrated preferred-chain winner-law RMS: {float(baseline['winner_law_rms_error']):.6f}",
            f"- Physicalized chain winner-law RMS: {float(metrics['winner_law_rms_error']):.6f}",
            f"- Current integrated preferred-chain correlator RMS: {float(baseline['correlator_rms_error']):.6f}",
            f"- Physicalized chain correlator RMS: {float(metrics['correlator_rms_error']):.6f}",
            f"- Current integrated preferred-chain CHSH abs error: {float(baseline['chsh_abs_error']):.6f}",
            f"- Physicalized chain CHSH abs error: {float(metrics['chsh_abs_error']):.6f}",
            f"- Comparison CSV: `{outputs['candidate_comparison_csv']}`",
            f"- Baseline note: {comparison_rows['current_integrated_preferred_chain']['architecture_note']}",
            f"- Physicalized note: {comparison_rows['preferred_chain_device_physicalization']['architecture_note']}",
            "",
            "## Decision",
            "",
            f"- Proceed to next phase: {bool(metrics['proceed_to_next_phase'])}",
            f"- Decision: {decision}",
            "",
            "## Artifacts",
            "",
            f"- Subblocks: `{outputs['subblocks_dir']}`",
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
            "# Preferred Chain Device Physicalization Design Note",
            "",
            "## Which Subblocks Were Deepened",
            "",
            "- Common inhibit rail realization.",
            "- Winner drain path realization.",
            "",
            "## Old Abstraction",
            "",
            "- The integrated codesign baseline still represented the common inhibit subblock as a reduced RC-style control rise attached to the inhibit rail.",
            "- The winner drain path was still represented as a reduced gated drain branch with limited internal device meaning.",
            "",
            "## New Device / Component-Level Realization",
            "",
            "- The common inhibit subblock now includes an explicit trigger-sense RC, inhibit-storage capacitor, bleed path, and hysteretic tie into the inhibit rail.",
            "- The winner drain subblock now includes an explicit gate-driver RC, off-state switch surrogate, snubber capacitor, series inductance, and drain-dump RC branch.",
            "- The post-click dynamics are driven from these component values rather than from the prior reduced subblock parameters alone.",
            "",
            "## Why This Is A Physical Realism Gain",
            "",
            "- The selected subblocks now expose internal state variables that correspond to more believable circuit roles: sensing, stored bias, gate drive, switch conduction, and dump-path filling.",
            "- That makes the realism gain legible without changing the frozen detector/latch/export semantics.",
            "",
            "## What Remains Abstract",
            "",
            "- The detector remains the frozen `shot_trigger` model.",
            "- The latch remains the validated first-arrival arbiter contract.",
            "- The device-level subblocks are still lumped circuit surrogates, not transistor-level production netlists or fabrication-ready layouts.",
            "",
            "## What Was Intentionally Left Frozen",
            "",
            "- Detector boundary: `piecewise_envelope:linear:20.0ms`, gain `4.0x`, exposure `5.0s`.",
            "- Detector family and parameters.",
            "- Latch semantics and timing assumptions.",
            "- Top-level role split between front-end, detector/latch, and post-click closure/drain.",
            "",
            "## Current Outcome",
            "",
            f"- Front-end fraction pass: {bool(metrics['front_end_fraction_pass'])}",
            f"- Winner-law pass: {bool(metrics['winner_law_pass'])}",
            f"- Correlator pass: {bool(metrics['correlator_pass'])}",
            f"- CHSH pass: {bool(metrics['chsh_pass'])}",
            f"- Pre-click transparency pass: {bool(metrics['pre_click_transparency_pass'])}",
            f"- Winner-drain dominance pass: {bool(metrics['winner_drain_dominance_pass'])}",
            f"- Energy-accounting pass: {bool(metrics['energy_accounting_pass'])}",
            f"- Architectural realism gain pass: {bool(metrics['architectural_realism_gain_pass'])}",
            "",
        ]
    )


def build_preferred_chain_device_physicalization_report(
    outdir: str | Path = "artifacts/preferred_chain_device_physicalization",
    *,
    detector_next_summary_csv: str | Path = "artifacts/detector_next/results_summary.csv",
    n_trials: int = 1_200,
    seed: int = 20260409,
    case_names: Sequence[str] | None = None,
    verbose_progress: bool = False,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    subblocks_dir = output_dir / "subblocks"
    pre_click_dir = output_dir / "pre_click"
    post_click_dir = output_dir / "post_click"
    full_chain_dir = output_dir / "full_chain"
    energy_dir = output_dir / "energy_accounting"
    for directory in (subblocks_dir, pre_click_dir, post_click_dir, full_chain_dir, energy_dir):
        directory.mkdir(parents=True, exist_ok=True)

    detector_spec = load_top_shot_trigger_spec(detector_next_summary_csv)
    detector_model_spec = {
        "family": detector_spec["family"],
        "model_params": dict(detector_spec["model_params"]),
        "gain_scale": 2.0,
    }
    summary = run_preferred_chain_device_physicalization_benchmark(
        detector_model_spec,
        n_trials=n_trials,
        seed=seed,
        case_names=case_names,
        verbose_progress=verbose_progress,
    )

    subblock_csv = subblocks_dir / "subblock_summary.csv"
    front_end_csv = pre_click_dir / "front_end_summary.csv"
    pre_click_csv = pre_click_dir / "pre_click_transparency.csv"
    post_click_csv = post_click_dir / "post_click_summary.csv"
    full_chain_csv = full_chain_dir / "full_chain_summary.csv"
    case_comparison_csv = full_chain_dir / "baseline_case_comparison.csv"
    energy_summary_csv = energy_dir / "energy_accounting_summary.csv"
    energy_trials_csv = energy_dir / "energy_accounting_trials.csv"
    candidate_comparison_csv = output_dir / "candidate_comparison.csv"

    _write_csv(subblock_csv, list(summary["subblock_rows"]))
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

    plot_device_pre_click_transparency(list(summary["pre_click_rows"])).savefig(
        pre_click_dir / "pre_click_transparency_vs_current_integrated_baseline.png"
    )
    plot_winner_drain_fraction(list(summary["post_click_rows"])).savefig(
        post_click_dir / "winner_drain_energy_fraction.png"
    )
    plot_loser_residual_fraction(list(summary["post_click_rows"])).savefig(
        post_click_dir / "loser_residual_energy_fraction.png"
    )
    plot_device_winner_frequency(list(summary["case_rows"])).savefig(
        full_chain_dir / "winner_frequency_exact_vs_empirical.png"
    )
    plot_device_correlator(list(summary["case_rows"])).savefig(
        full_chain_dir / "correlator_exact_vs_empirical.png"
    )
    if bool(summary["chsh_result"]["available"]):
        plot_device_chsh(dict(summary["chsh_result"])).savefig(full_chain_dir / "chsh_exact_vs_empirical.png")
    plot_whole_trial_energy_flow(list(summary["energy_case_rows"])).savefig(
        energy_dir / "whole_trial_energy_flow_summary.png"
    )
    plot_device_candidate_comparison(list(summary["comparison_rows"])).savefig(
        output_dir / "comparison_vs_current_integrated_preferred_chain.png"
    )

    if summary["example_front_end"] is not None:
        example_front_end = dict(summary["example_front_end"])
        plot_device_subblock_component_summary(example_front_end).savefig(
            subblocks_dir / "selected_subblock_component_summary.png"
        )
        plot_device_subblock_node_snapshot(example_front_end).savefig(
            subblocks_dir / "selected_subblock_node_snapshot.png"
        )
        _write_csv(
            subblocks_dir / "device_component_table.csv",
            list(example_front_end["device_physicalization"]["device_components"]),
        )
        _write_csv(
            subblocks_dir / "device_node_voltage_snapshot.csv",
            [
                {
                    "node_name": node_name,
                    "node_voltage_abs": abs(complex(value)),
                }
                for node_name, value in example_front_end["shared_core"]["device_node_voltage_v"].items()
            ],
        )

    if summary["example_trial"] is not None:
        example_trial = dict(summary["example_trial"])
        plot_device_subblock_internal_signals(example_trial).savefig(
            subblocks_dir / "selected_subblock_internal_signals.png"
        )
        plot_remaining_shared_energy_trace(example_trial).savefig(
            post_click_dir / "remaining_shared_energy_vs_time.png"
        )
        physical = dict(example_trial["physical"])
        _write_csv(
            post_click_dir / "example_trial_trace.csv",
            [
                {
                    "time_s": physical["time_s"][index],
                    "trigger_sense_v": physical["trigger_sense_v"][index],
                    "trigger_comparator_output": physical["trigger_comparator_output"][index],
                    "inhibit_store_v": physical["inhibit_store_v"][index],
                    "common_inhibit_v": physical["common_inhibit_v"][index],
                    "winner_gate_driver_v": physical["winner_gate_driver_v"][index],
                    "winner_gate_v": physical["winner_gate_v"][index],
                    "winner_switch_conductance_s": physical["winner_switch_conductance_s"][index],
                    "winner_switch_channel_current_a": physical["winner_switch_channel_current_a"][index],
                    "winner_drain_current_a": physical["winner_drain_current_a"][index],
                    "drain_dump_voltage_v": physical["drain_dump_voltage_v"][index],
                    "winner_drain_tank_voltage_v": physical["winner_drain_tank_voltage_v"][index],
                    "remaining_shared_energy_j": physical["remaining_shared_energy_j"][index],
                    **{
                        f"{label}_branch_attachment_current_a": values[index]
                        for label, values in physical["branch_attachment_current_a"].items()
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
                "subblock_rows": summary["subblock_rows"],
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
        "subblocks_dir": str(subblocks_dir),
        "pre_click_dir": str(pre_click_dir),
        "post_click_dir": str(post_click_dir),
        "full_chain_dir": str(full_chain_dir),
        "energy_dir": str(energy_dir),
        "subblock_csv": str(subblock_csv),
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
    parser = argparse.ArgumentParser(description="Build the preferred chain device physicalization report.")
    parser.add_argument("--outdir", default="artifacts/preferred_chain_device_physicalization")
    parser.add_argument("--detector-next-summary-csv", default="artifacts/detector_next/results_summary.csv")
    parser.add_argument("--n-trials", type=int, default=1_200)
    parser.add_argument("--seed", type=int, default=20260409)
    parser.add_argument("--case", action="append", dest="case_names", default=None)
    parser.add_argument("--quiet-progress", action="store_true")
    args = parser.parse_args()
    build_preferred_chain_device_physicalization_report(
        outdir=args.outdir,
        detector_next_summary_csv=args.detector_next_summary_csv,
        n_trials=args.n_trials,
        seed=args.seed,
        case_names=args.case_names,
        verbose_progress=not args.quiet_progress,
    )


if __name__ == "__main__":
    main()
