from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from detector_integration.experiments.run_summary_report import load_top_shot_trigger_spec

from physical_front_end_candidate.physical_closure_drain_candidate import (
    default_physical_closure_drain_config,
    preferred_common_mode_interpretation,
    reduced_to_physical_mapping_summary,
    run_four_branch_candidate_with_physical_closure,
)
from physical_front_end_candidate.plots import (
    plot_closure_semantics_comparison,
    plot_closure_variable,
    plot_loser_suppression,
    plot_post_click_energy_partition,
    plot_remaining_shared_energy,
    plot_winner_drain_power,
)
from physical_front_end_candidate.resonant_four_branch_candidate import benchmark_resonant_four_branch_cases, simulate_resonant_four_branch_candidate


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
    summary_metrics: dict[str, float | str | bool],
    outputs: dict[str, str],
) -> str:
    decision = (
        "Proceed toward integrated resonant front-end and closure-path co-design."
        if bool(summary_metrics["proceed_to_next_phase"])
        else "Iterate on the physical closure/drain candidate before deeper hardware integration."
    )
    return "\n".join(
        [
            "# First Physical Closure / Drain Candidate Summary",
            "",
            "## Topology",
            "",
            "- Chosen option: `Option A`, common inhibit rail plus winner-gated shunt drain.",
            "- Reduced interpretation: `common-mode inhibit + winner drain`.",
            "- Pre-click behavior remains detached from the closure path until `winner_valid=True`.",
            "",
            "## Pre-Click Transparency",
            "",
            f"- Winner-law RMS transparency shift: {float(summary_metrics['pre_click_transparency_rms_shift']):.6f}",
            f"- Transparency pass: {bool(summary_metrics['pre_click_transparency_pass'])}",
            "",
            "## Post-Click Exclusivity",
            "",
            f"- Mean winner drain fraction: {float(summary_metrics['mean_winner_drain_fraction']):.6f}",
            f"- Mean loser residual fraction: {float(summary_metrics['mean_loser_fraction']):.6f}",
            f"- Mean terminal loser suppression: {float(summary_metrics['mean_terminal_loser_suppression']):.6f}",
            f"- Winner drain path count: {float(summary_metrics['mean_winner_drain_path_count']):.6f}",
            f"- Winner dominance pass: {bool(summary_metrics['winner_dominance_pass'])}",
            "",
            "## Trial Completion",
            "",
            f"- Completion rate: {float(summary_metrics['completion_rate']):.6f}",
            f"- Mean completion time (s): {float(summary_metrics['mean_completion_time_s']):.6f}",
            f"- Monotonic shared energy: {bool(summary_metrics['monotonic_remaining_energy'])}",
            f"- Completion pass: {bool(summary_metrics['completion_pass'])}",
            "",
            "## Reduced-Model Consistency",
            "",
            f"- Winner-fraction abs diff: {float(summary_metrics['reduced_winner_fraction_abs_diff']):.6f}",
            f"- Loser-fraction abs diff: {float(summary_metrics['reduced_loser_fraction_abs_diff']):.6f}",
            f"- Completion-rate abs diff: {float(summary_metrics['reduced_completion_rate_abs_diff']):.6f}",
            f"- Reduced-consistency pass: {bool(summary_metrics['reduced_consistency_pass'])}",
            "",
            "## Decision",
            "",
            f"- Proceed to next phase: {bool(summary_metrics['proceed_to_next_phase'])}",
            f"- Decision: {decision}",
            "",
            "## Artifacts",
            "",
            f"- Candidate design note: `{outputs['design_md']}`",
            f"- Reduced mapping summary: `{outputs['mapping_csv']}`",
            f"- Integration summary: `{outputs['integration_csv']}`",
            f"- SPICE-facing interface: `{outputs['spice_md']}`",
            "",
        ]
    )


def build_physical_closure_drain_candidate_report(
    outdir: str | Path = "artifacts/physical_closure_drain_candidate",
    *,
    detector_next_summary_csv: str | Path = "artifacts/detector_next/results_summary.csv",
    n_trials: int = 24,
    seed: int = 20260403,
    case_names: Sequence[str] | None = None,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    mapping_dir = output_dir / "reduced_mapping"
    integration_dir = output_dir / "integration"
    spice_dir = output_dir / "spice_facing"
    for directory in (mapping_dir, integration_dir, spice_dir):
        directory.mkdir(parents=True, exist_ok=True)

    detector_spec = load_top_shot_trigger_spec(detector_next_summary_csv)
    detector_model_spec = {
        "family": detector_spec["family"],
        "model_params": dict(detector_spec["model_params"]),
        "gain_scale": 2.0,
    }
    config = default_physical_closure_drain_config()
    reduced = preferred_common_mode_interpretation()
    mapping_summary = reduced_to_physical_mapping_summary(config, reduced_interpretation=reduced)

    selected_case_names = None if case_names is None else set(case_names)
    cases = [
        case
        for case in benchmark_resonant_four_branch_cases()
        if selected_case_names is None or case["case"] in selected_case_names
    ]
    if not cases:
        raise ValueError("No resonant benchmark cases selected.")

    integration_rows: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []
    energy_partition_rows: list[dict[str, Any]] = []
    example_trial: dict[str, Any] | None = None

    for case_index, case in enumerate(cases):
        candidate = simulate_resonant_four_branch_candidate(case["state4"], a_deg=case["a_deg"], b_deg=case["b_deg"])
        result = run_four_branch_candidate_with_physical_closure(
            candidate,
            detector_model_spec,
            n_trials=n_trials,
            seed=seed + 1_003 * case_index,
            config=config,
            reduced_interpretation=reduced,
        )
        integration_rows.append(
            {
                "case": case["case"],
                "a_deg": case["a_deg"],
                "b_deg": case["b_deg"],
                "winner_rms_error": float(result["metrics"]["rms_error"]),
                "winner_max_error": float(result["metrics"]["max_abs_error"]),
                "correlator_error": float(result["metrics"]["correlator_error"]),
                "decisive_fraction": float(result["decisive_fraction"]),
                "pre_click_transparency_rms_shift": float(result["closure_metrics"]["pre_click_transparency_rms_shift"]),
                "winner_drain_fraction": float(result["closure_metrics"]["mean_winner_drain_fraction"]),
                "loser_fraction": float(result["closure_metrics"]["mean_loser_fraction"]),
                "completion_rate": float(result["closure_metrics"]["completion_rate"]),
                "mean_completion_time_s": float(result["closure_metrics"]["mean_completion_time_s"]),
                "monotonic_remaining_energy": bool(result["closure_metrics"]["monotonic_remaining_energy"]),
                "mean_terminal_loser_suppression": float(result["closure_metrics"]["mean_terminal_loser_suppression"]),
                "winner_drain_path_count": float(result["closure_metrics"]["mean_winner_drain_path_count"]),
            }
        )
        comparison_rows.append(
            {
                "case": case["case"],
                "winner_fraction_abs_diff": float(result["comparison_metrics"]["winner_fraction_abs_diff"]),
                "loser_fraction_abs_diff": float(result["comparison_metrics"]["loser_fraction_abs_diff"]),
                "completion_rate_abs_diff": float(result["comparison_metrics"]["completion_rate_abs_diff"]),
                "completion_time_abs_diff": float(result["comparison_metrics"]["completion_time_abs_diff"]),
                "example_closure_rms_diff": float(result["comparison_metrics"].get("example_closure_rms_diff", 0.0)),
                "example_remaining_energy_rms_diff": float(result["comparison_metrics"].get("example_remaining_energy_rms_diff", 0.0)),
            }
        )
        energy_partition_rows.append(
            {
                "label": case["case"],
                "mean_winner_drain_fraction": float(result["closure_metrics"]["mean_winner_drain_fraction"]),
                "mean_loser_fraction": float(result["closure_metrics"]["mean_loser_fraction"]),
            }
        )
        if example_trial is None and result["example_trial"] is not None:
            example_trial = {
                "case": case["case"],
                **result["example_trial"],
            }

    mapping_csv = mapping_dir / "mapping_summary.csv"
    integration_csv = integration_dir / "integration_summary.csv"
    comparison_csv = mapping_dir / "reduced_comparison.csv"
    _write_csv(mapping_csv, [mapping_summary])
    _write_csv(integration_csv, integration_rows)
    _write_csv(comparison_csv, comparison_rows)

    if example_trial is not None:
        physical = example_trial["physical"]
        reduced_row = example_trial["reduced"]
        plot_closure_variable(physical, variable_name="V_inhibit / VDD").savefig(integration_dir / "common_inhibit_signal.png")
        plot_winner_drain_power(physical).savefig(integration_dir / "winner_drain_power.png")
        plot_loser_suppression(physical).savefig(integration_dir / "loser_suppression.png")
        plot_remaining_shared_energy(physical).savefig(integration_dir / "remaining_shared_energy.png")
        plot_closure_semantics_comparison(physical, reduced_row, variable_name="Z").savefig(mapping_dir / "reduced_vs_physical.png")
        _write_csv(
            integration_dir / "example_physical_trace.csv",
            [
                {
                    "time_s": physical["time_s"][index],
                    "closure_variable": physical["closure_variable"][index],
                    "common_inhibit_v": physical["common_inhibit_v"][index],
                    "shared_node_voltage_v": physical["shared_node_voltage_v"][index],
                    "winner_drain_power_w": physical["winner_drain_power_w"][index],
                    "winner_drain_current_a": physical["winner_drain_current_a"][index],
                    "remaining_shared_energy_j": physical["remaining_shared_energy_j"][index],
                    "trial_complete_signal": physical["trial_complete_signal"][index],
                    **{f"{label}_suppression": values[index] for label, values in physical["loser_suppression"].items()},
                }
                for index in range(len(physical["time_s"]))
            ],
        )

    plot_post_click_energy_partition(energy_partition_rows).savefig(integration_dir / "post_click_energy_partition.png")

    summary_metrics = {
        "topology_name": config.topology_name,
        "reduced_interpretation": reduced.label,
        "pre_click_transparency_rms_shift": float(np.sqrt(np.mean(np.square([row["pre_click_transparency_rms_shift"] for row in integration_rows])))),
        "mean_winner_drain_fraction": float(np.mean([row["winner_drain_fraction"] for row in integration_rows])),
        "mean_loser_fraction": float(np.mean([row["loser_fraction"] for row in integration_rows])),
        "completion_rate": float(np.mean([row["completion_rate"] for row in integration_rows])),
        "mean_completion_time_s": float(np.mean([row["mean_completion_time_s"] for row in integration_rows])),
        "monotonic_remaining_energy": bool(all(bool(row["monotonic_remaining_energy"]) for row in integration_rows)),
        "mean_terminal_loser_suppression": float(np.mean([row["mean_terminal_loser_suppression"] for row in integration_rows])),
        "mean_winner_drain_path_count": float(np.mean([row["winner_drain_path_count"] for row in integration_rows])),
        "reduced_winner_fraction_abs_diff": float(np.mean([row["winner_fraction_abs_diff"] for row in comparison_rows])),
        "reduced_loser_fraction_abs_diff": float(np.mean([row["loser_fraction_abs_diff"] for row in comparison_rows])),
        "reduced_completion_rate_abs_diff": float(np.mean([row["completion_rate_abs_diff"] for row in comparison_rows])),
        "reduced_completion_time_abs_diff": float(np.mean([row["completion_time_abs_diff"] for row in comparison_rows])),
    }
    summary_metrics["pre_click_transparency_pass"] = float(summary_metrics["pre_click_transparency_rms_shift"]) < 0.01
    summary_metrics["winner_dominance_pass"] = (
        float(summary_metrics["mean_winner_drain_fraction"]) > 0.75
        and float(summary_metrics["mean_loser_fraction"]) < 0.05
        and float(summary_metrics["mean_terminal_loser_suppression"]) > 0.9
        and abs(float(summary_metrics["mean_winner_drain_path_count"]) - 1.0) < 1e-9
    )
    summary_metrics["completion_pass"] = (
        float(summary_metrics["completion_rate"]) > 0.9 and bool(summary_metrics["monotonic_remaining_energy"])
    )
    summary_metrics["reduced_consistency_pass"] = (
        float(summary_metrics["reduced_winner_fraction_abs_diff"]) < 0.12
        and float(summary_metrics["reduced_loser_fraction_abs_diff"]) < 0.05
        and float(summary_metrics["reduced_completion_rate_abs_diff"]) < 0.1
    )
    summary_metrics["proceed_to_next_phase"] = all(
        bool(summary_metrics[key])
        for key in (
            "pre_click_transparency_pass",
            "winner_dominance_pass",
            "completion_pass",
            "reduced_consistency_pass",
        )
    )

    design_md = output_dir / "candidate_design.md"
    design_md.write_text(
        "\n".join(
            [
                "# First Physical Closure / Drain Candidate",
                "",
                "## Chosen Topology",
                "",
                "- Primary option: `Option A`, common inhibit rail plus winner-gated shunt drain.",
                f"- Topology identifier: `{config.topology_name}`.",
                "",
                "## Common-Mode Inhibit",
                "",
                f"- Shared control signal: `{config.control_node_name}(t)`.",
                "- Circuit meaning: a post-click inhibit rail that rises only after latch winner capture.",
                "- Reduced mapping: normalized `V_inhibit/VDD` is the physical analog of reduced `Z(t)`.",
                "",
                "## Loser Suppression",
                "",
                "- Each non-winning branch is attenuated by a winner-independent common inhibit action.",
                "- In the surrogate circuit model, loser residual branch conductance collapses exponentially with the inhibit rail.",
                "- A clamp/reference conductance provides the physical interpretation of a loser clamp or inhibit transistor.",
                "",
                "## Winner Drain Enable",
                "",
                f"- Winner-select line: `{config.winner_select_name}`.",
                "- Only the selected winner path sees the large shunt drain conductance.",
                "- This gives an explicit single winner drain path and keeps all non-winning drain enables off.",
                "",
                "## Trial Completion",
                "",
                f"- Trial complete signal: `{config.trial_complete_name}`.",
                "- Completion is asserted once remaining shared energy is below a fixed fraction and the winner drain current has decayed below threshold.",
                "",
                "## Reset",
                "",
                "- Reset is external in this ticket.",
                "- Re-arm is expected to pull the inhibit rail low, clear winner select, and reset latch outputs before the next trial.",
                "",
                "## Remaining Abstractions",
                "",
                "- The candidate is still a SPICE-style reduced circuit surrogate, not a transistor-level production design.",
                "- Device nonlinearity, dump-path saturation, and final shared-core co-design remain abstract.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    spice_md = spice_dir / "closure_spice_interface.md"
    spice_md.write_text(
        "\n".join(
            [
                "# SPICE-Facing Closure / Drain Interface",
                "",
                "## Inputs",
                "",
                "- `winner_valid`",
                "- `winner_index` or one-hot `SEL_WIN[k]`",
                "- branch residual power / energy observables from the front-end trace",
                "- optional shared energy estimate",
                "",
                "## Internal Signals",
                "",
                f"- `{config.control_node_name}(t)`: common inhibit rail",
                "- per-loser clamp conductances",
                "- winner drain conductance",
                "- shared node voltage estimate",
                "",
                "## Outputs",
                "",
                "- winner drain current / power",
                "- loser suppression observables",
                "- remaining shared energy",
                f"- `{config.trial_complete_name}`",
                "",
                "## Intended First Netlist Shape",
                "",
                "- one shared inhibit node driven from the latch domain after winner capture",
                "- one high-conductance selected drain device on the winning branch",
                "- loser clamp or attenuation devices referenced to the shared inhibit node",
                "- a simple comparator or threshold block for trial-complete",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary_csv = output_dir / "summary_metrics.csv"
    _write_csv(summary_csv, [{"metric": key, "value": value} for key, value in summary_metrics.items()])
    outputs = {
        "design_md": str(design_md),
        "mapping_csv": str(mapping_csv),
        "integration_csv": str(integration_csv),
        "comparison_csv": str(comparison_csv),
        "spice_md": str(spice_md),
    }
    summary_json = output_dir / "summary_metrics.json"
    summary_json.write_text(
        json.dumps(
            {
                "summary_metrics": summary_metrics,
                "mapping_summary": mapping_summary,
                "integration_rows": integration_rows,
                "comparison_rows": comparison_rows,
                "outputs": outputs,
            },
            indent=2,
            default=_json_default,
        )
        + "\n",
        encoding="utf-8",
    )
    summary_md = output_dir / "summary_report.md"
    summary_md.write_text(_summary_markdown(summary_metrics=summary_metrics, outputs=outputs) + "\n", encoding="utf-8")
    return {
        "summary_md": str(summary_md),
        "summary_json": str(summary_json),
        "summary_csv": str(summary_csv),
        "design_md": str(design_md),
        "mapping_csv": str(mapping_csv),
        "integration_csv": str(integration_csv),
        "comparison_csv": str(comparison_csv),
        "spice_facing_interface_md": str(spice_md),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the first physical closure/drain candidate report.")
    parser.add_argument("--outdir", default="artifacts/physical_closure_drain_candidate")
    parser.add_argument("--detector-next-summary", default="artifacts/detector_next/results_summary.csv")
    parser.add_argument("--trials", type=int, default=24)
    args = parser.parse_args()
    build_physical_closure_drain_candidate_report(
        args.outdir,
        detector_next_summary_csv=args.detector_next_summary,
        n_trials=args.trials,
    )


if __name__ == "__main__":
    main()
