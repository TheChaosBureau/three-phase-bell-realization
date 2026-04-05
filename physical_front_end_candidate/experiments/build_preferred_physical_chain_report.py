from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from detector_integration.experiments.run_summary_report import load_top_shot_trigger_spec

from physical_front_end_candidate.preferred_physical_chain import run_preferred_physical_chain_benchmark
from physical_front_end_candidate.preferred_physical_chain_plots import (
    plot_loser_residual_fraction,
    plot_pre_click_transparency,
    plot_preferred_chain_chsh,
    plot_preferred_chain_correlator,
    plot_preferred_chain_winner_frequency,
    plot_remaining_shared_energy_trace,
    plot_whole_trial_energy_flow,
    plot_winner_drain_fraction,
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


def _summary_markdown(*, summary_metrics: dict[str, Any], outputs: dict[str, str]) -> str:
    decision = (
        "Proceed toward a deeper LC/coupled-port realization of the preferred chain."
        if bool(summary_metrics["proceed_to_next_phase"])
        else "Iterate on the integrated preferred chain before deeper physicalization."
    )
    return "\n".join(
        [
            "# Preferred Physical Chain Summary",
            "",
            "## Chain",
            "",
            "- Front-end: resonant shared four-branch candidate.",
            "- Frozen detector boundary: `piecewise_envelope:linear:20.0ms`, gain `4.0x`, exposure `5.0s`.",
            "- Frozen detector family: `shot_trigger` with the frozen operating-point parameters.",
            "- Frozen winner latch: first-arrival arbiter contract.",
            "- Post-click block: tuned common inhibit rail + winner-gated shunt drain.",
            "",
            "## Full-Chain Fidelity",
            "",
            f"- Winner-law RMS error: {float(summary_metrics['winner_law_rms_error']):.6f}",
            f"- Winner-law max error: {float(summary_metrics['winner_law_max_error']):.6f}",
            f"- Correlator RMS error: {float(summary_metrics['correlator_rms_error']):.6f}",
            f"- CHSH absolute error: {float(summary_metrics['chsh_abs_error']):.6f}",
            f"- Mean decisive fraction: {float(summary_metrics['mean_decisive_fraction']):.6f}",
            "",
            "## Pre-Click Transparency",
            "",
            f"- Winner-frequency RMS shift vs baseline: {float(summary_metrics['pre_click_transparency_rms_shift']):.6f}",
            f"- Winner-frequency max shift vs baseline: {float(summary_metrics['pre_click_transparency_max_shift']):.6f}",
            f"- Transparency pass: {bool(summary_metrics['pre_click_transparency_pass'])}",
            "",
            "## Post-Click Exclusivity",
            "",
            f"- Mean winner drain fraction of post-click energy: {float(summary_metrics['mean_winner_drain_fraction_of_post_click']):.6f}",
            f"- Mean loser residual fraction of post-click energy: {float(summary_metrics['mean_loser_fraction_of_post_click']):.6f}",
            f"- Winner-drain dominance rate: {float(summary_metrics['winner_drain_dominance_rate']):.6f}",
            f"- Mean terminal loser suppression: {float(summary_metrics['mean_terminal_loser_suppression']):.6f}",
            f"- Monotonic shared-energy decay: {bool(summary_metrics['monotonic_remaining_energy'])}",
            "",
            "## Whole-Trial Energy Accounting",
            "",
            f"- Mean pre-click fraction of total energy: {float(summary_metrics['mean_pre_click_fraction_of_total']):.6f}",
            f"- Mean winner drain fraction of total energy: {float(summary_metrics['mean_winner_drain_fraction_of_total']):.6f}",
            f"- Mean loser fraction of total energy: {float(summary_metrics['mean_loser_fraction_of_total']):.6f}",
            f"- Mean shared-leak fraction of total energy: {float(summary_metrics['mean_shared_leak_fraction_of_total']):.6f}",
            f"- Max energy-balance abs fraction: {float(summary_metrics['max_energy_balance_abs_fraction']):.6e}",
            f"- Energy-accounting pass: {bool(summary_metrics['energy_accounting_pass'])}",
            "",
            "## Decision Gate",
            "",
            f"- Winner-law pass: {bool(summary_metrics['winner_law_pass'])}",
            f"- Correlator pass: {bool(summary_metrics['correlator_pass'])}",
            f"- CHSH pass: {bool(summary_metrics['chsh_pass'])}",
            f"- Winner-drain dominance pass: {bool(summary_metrics['winner_drain_dominance_pass'])}",
            f"- Loser-residual pass: {bool(summary_metrics['loser_residual_pass'])}",
            f"- Completion pass: {bool(summary_metrics['completion_pass'])}",
            f"- Proceed to next phase: {bool(summary_metrics['proceed_to_next_phase'])}",
            f"- Decision: {decision}",
            "",
            "## Artifacts",
            "",
            f"- Full-chain artifacts: `{outputs['full_chain_dir']}`",
            f"- Pre-click artifacts: `{outputs['pre_click_dir']}`",
            f"- Post-click artifacts: `{outputs['post_click_dir']}`",
            f"- Energy-accounting artifacts: `{outputs['energy_dir']}`",
            f"- Chain design note: `{outputs['design_md']}`",
            "",
        ]
    )


def _design_note_markdown(*, summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Preferred Physical Chain Design Note",
            "",
            "## Exact Blocks Integrated",
            "",
            "- Resonant shared four-branch front-end candidate.",
            "- Frozen detector-boundary export contract: piecewise linear envelope with 20 ms bins.",
            "- Frozen detector family: `shot_trigger` using the frozen operating-point parameters and `gain_scale=2.0`.",
            "- Frozen winner latch timing contract from the validated first-arrival arbiter.",
            "- Tuned physical closure/drain candidate: common inhibit rail plus winner-gated shunt drain.",
            "",
            "## What Remains Frozen",
            "",
            "- Front-end architecture and resonant parameterization.",
            "- Detector-boundary gain `4.0x` and exposure `5.0s`.",
            "- Detector family and model parameters.",
            "- Latch timing assumptions and winner semantics.",
            "- Tuned closure/drain parameter set used by the preferred candidate.",
            "",
            "## Integration Block Diagram",
            "",
            "```text",
            "[resonant shared front-end]",
            "  -> [frozen detector export: piecewise linear 20 ms]",
            "  -> [frozen shot-trigger detector]",
            "  -> [frozen first-arrival latch]",
            "  -> [tuned common-inhibit / winner-drain closure]",
            "```",
            "",
            "## What Is Measured Pre-Click",
            "",
            "- Exact vs empirical four-branch winner frequencies.",
            "- Winner-law transparency shift against the front-end -> detector -> latch baseline.",
            "- Decisive and timeout fractions.",
            "- Correlator fidelity.",
            "",
            "## What Is Measured Post-Click",
            "",
            "- Winner drain energy fraction.",
            "- Loser residual fraction.",
            "- Remaining shared energy monotonicity.",
            "- Completion rate and completion time.",
            "- Whole-trial energy bookkeeping from pre-click branch energy through post-click drain/leak/residual terms.",
            "",
            "## Intended Meaning Of Full Preferred Physical Chain",
            "",
            "- A single Monte Carlo trial now runs the frozen resonant front-end, the frozen export contract, the frozen detector family, the frozen latch, and the tuned closure/drain in one continuous flow.",
            "- The latch capture time from the detector-facing chain gates the post-click closure/drain dynamics and the energy accounting for the remaining shared energy.",
            "",
            "## What Is Integrated vs Still Abstract",
            "",
            "- Integrated: front-end branch-power traces, frozen detector-facing export, detector race, latch capture, tuned post-click drain, and whole-trial bookkeeping.",
            "- Still abstract: detector internals remain a stochastic shot-trigger model, the latch remains a validated timing contract rather than a transistor netlist, and the closure/drain remains a lumped physical candidate rather than a full LC/coupled-port implementation.",
            "- Reset/re-arm remains a trial-boundary abstraction outside this ticket's integrated chain.",
            "",
            "## Current Outcome",
            "",
            f"- Proceed to next phase: {bool(summary['summary_metrics']['proceed_to_next_phase'])}",
            f"- Winner-law pass: {bool(summary['summary_metrics']['winner_law_pass'])}",
            f"- Correlator pass: {bool(summary['summary_metrics']['correlator_pass'])}",
            f"- CHSH pass: {bool(summary['summary_metrics']['chsh_pass'])}",
            f"- Winner-drain dominance pass: {bool(summary['summary_metrics']['winner_drain_dominance_pass'])}",
            f"- Energy-accounting pass: {bool(summary['summary_metrics']['energy_accounting_pass'])}",
            "",
        ]
    )


def build_preferred_physical_chain_report(
    outdir: str | Path = "artifacts/preferred_physical_chain",
    *,
    detector_next_summary_csv: str | Path = "artifacts/detector_next/results_summary.csv",
    n_trials: int = 1_200,
    seed: int = 20260405,
    case_names: Sequence[str] | None = None,
    verbose_progress: bool = False,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    full_chain_dir = output_dir / "full_chain"
    pre_click_dir = output_dir / "pre_click"
    post_click_dir = output_dir / "post_click"
    energy_dir = output_dir / "energy_accounting"
    for directory in (full_chain_dir, pre_click_dir, post_click_dir, energy_dir):
        directory.mkdir(parents=True, exist_ok=True)

    detector_spec = load_top_shot_trigger_spec(detector_next_summary_csv)
    detector_model_spec = {
        "family": detector_spec["family"],
        "model_params": dict(detector_spec["model_params"]),
        "gain_scale": 2.0,
    }
    summary = run_preferred_physical_chain_benchmark(
        detector_model_spec,
        n_trials=n_trials,
        seed=seed,
        case_names=case_names,
        verbose_progress=verbose_progress,
    )

    full_chain_rows = [
        {
            **{key: value for key, value in row.items() if key not in {"branch_labels", "exact_weights", "empirical_frequencies"}},
            "branch_labels_json": json.dumps(row["branch_labels"]),
            "exact_weights_json": json.dumps(row["exact_weights"]),
            "empirical_frequencies_json": json.dumps(row["empirical_frequencies"]),
        }
        for row in summary["case_rows"]
    ]
    full_chain_csv = full_chain_dir / "full_chain_summary.csv"
    pre_click_csv = pre_click_dir / "pre_click_comparison.csv"
    post_click_csv = post_click_dir / "post_click_summary.csv"
    energy_summary_csv = energy_dir / "energy_accounting_summary.csv"
    energy_trials_csv = energy_dir / "energy_accounting_trials.csv"
    _write_csv(full_chain_csv, full_chain_rows)
    _write_csv(pre_click_csv, list(summary["pre_click_rows"]))
    _write_csv(post_click_csv, list(summary["post_click_rows"]))
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

    plot_preferred_chain_winner_frequency(list(summary["case_rows"])).savefig(full_chain_dir / "winner_frequency_exact_vs_empirical.png")
    plot_preferred_chain_correlator(list(summary["case_rows"])).savefig(full_chain_dir / "correlator_exact_vs_empirical.png")
    if bool(summary["chsh_result"]["available"]):
        plot_preferred_chain_chsh(dict(summary["chsh_result"])).savefig(full_chain_dir / "chsh_exact_vs_empirical.png")
    plot_pre_click_transparency(list(summary["pre_click_rows"])).savefig(pre_click_dir / "pre_click_transparency_comparison.png")
    plot_winner_drain_fraction(list(summary["post_click_rows"])).savefig(post_click_dir / "winner_drain_energy_fraction.png")
    plot_loser_residual_fraction(list(summary["post_click_rows"])).savefig(post_click_dir / "loser_residual_energy_fraction.png")
    plot_whole_trial_energy_flow(list(summary["energy_case_rows"])).savefig(energy_dir / "whole_trial_energy_flow_summary.png")

    if summary["example_trial"] is not None:
        example_trial = dict(summary["example_trial"])
        plot_remaining_shared_energy_trace(example_trial).savefig(post_click_dir / "remaining_shared_energy_vs_time.png")
        physical = example_trial["physical"]
        _write_csv(
            post_click_dir / "example_trial_trace.csv",
            [
                {
                    "time_s": physical["time_s"][index],
                    "closure_variable": physical["closure_variable"][index],
                    "common_inhibit_v": physical["common_inhibit_v"][index],
                    "shared_node_voltage_v": physical["shared_node_voltage_v"][index],
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
                "case_rows": summary["case_rows"],
                "pre_click_rows": summary["pre_click_rows"],
                "post_click_rows": summary["post_click_rows"],
                "energy_case_rows": summary["energy_case_rows"],
                "energy_rows": summary["energy_rows"],
                "energy_summary": summary["energy_summary"],
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
        "full_chain_dir": str(full_chain_dir),
        "pre_click_dir": str(pre_click_dir),
        "post_click_dir": str(post_click_dir),
        "energy_dir": str(energy_dir),
        "full_chain_csv": str(full_chain_csv),
        "pre_click_csv": str(pre_click_csv),
        "post_click_csv": str(post_click_csv),
        "energy_summary_csv": str(energy_summary_csv),
        "energy_trials_csv": str(energy_trials_csv),
    }
    design_md = output_dir / "chain_design_note.md"
    design_md.write_text(_design_note_markdown(summary=summary) + "\n", encoding="utf-8")
    outputs["design_md"] = str(design_md)

    summary_md = output_dir / "summary_report.md"
    summary_md.write_text(
        _summary_markdown(summary_metrics=summary["summary_metrics"], outputs=outputs)
        + "\n",
        encoding="utf-8",
    )

    return {
        "summary_md": str(summary_md),
        "summary_json": str(summary_json),
        "summary_csv": str(summary_csv),
        "design_md": str(design_md),
        **outputs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the preferred physical-chain integration report.")
    parser.add_argument("--outdir", default="artifacts/preferred_physical_chain")
    parser.add_argument("--detector-next-summary-csv", default="artifacts/detector_next/results_summary.csv")
    parser.add_argument("--n-trials", type=int, default=1_200)
    parser.add_argument("--seed", type=int, default=20260405)
    parser.add_argument("--case", action="append", dest="case_names", default=None)
    parser.add_argument("--quiet-progress", action="store_true")
    args = parser.parse_args()
    build_preferred_physical_chain_report(
        outdir=args.outdir,
        detector_next_summary_csv=args.detector_next_summary_csv,
        n_trials=args.n_trials,
        seed=args.seed,
        case_names=args.case_names,
        verbose_progress=not args.quiet_progress,
    )


if __name__ == "__main__":
    main()
