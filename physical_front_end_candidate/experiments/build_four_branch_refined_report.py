from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from detector_integration.experiments.run_summary_report import load_top_shot_trigger_spec
from detector_integration.sim.run_four_branch_latch_integration import DEFAULT_CHSH_SETTINGS
from src.shared_4tank_core import BASIS_LABELS, singlet_state

from physical_front_end_candidate.boundary_calibration import resolved_calibrated_boundary_config
from physical_front_end_candidate.boundary_diagnosis import selected_handoff_export_config
from physical_front_end_candidate.four_branch_candidate import benchmark_four_branch_physical_cases, simulate_four_branch_physical_candidate
from physical_front_end_candidate.integration import run_four_branch_candidate_handoff
from physical_front_end_candidate.metrics import aggregate_case_error, correlator_rms_error, finite_export_metrics
from physical_front_end_candidate.plots import (
    plot_candidate_metric_comparison,
    plot_chsh_exact_vs_empirical,
    plot_correlator_exact_vs_empirical,
    plot_four_branch_fraction_comparison,
    plot_four_branch_power_traces,
    plot_four_branch_residual_summary,
    plot_four_branch_winner_frequency,
    plot_shared_core_diagnostics,
)
from physical_front_end_candidate.refined_four_branch_candidate import benchmark_refined_four_branch_cases, simulate_refined_four_branch_candidate


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
    summary_metrics: dict[str, float],
    acceptance: dict[str, bool | str],
    comparison_rows: list[dict[str, Any]],
    outputs: dict[str, str],
) -> str:
    decision = "Proceed toward a more explicit resonant/shared-mode realization or closure-path specification." if acceptance["proceed_to_next_phase"] else "Iterate on the refined shared-core realization before deeper physicalization."
    comparison_note = (
        f"Prior candidate winner-law RMS {comparison_rows[0]['winner_rms_error']:.6f} vs refined {comparison_rows[1]['winner_rms_error']:.6f}; "
        f"prior correlator RMS {comparison_rows[0]['correlator_rms_error']:.6f} vs refined {comparison_rows[1]['correlator_rms_error']:.6f}."
    )
    return "\n".join(
        [
            "# Refined Four-Branch Front-End Summary",
            "",
            "## Architecture",
            "",
            "- Chosen option: `Option A`, explicit 4-state linear shared core.",
            "- Removed from prior candidate: direct exact-weight-to-branch-driver mapping.",
            "- Replaced with: internal shared-core solve, analyzer-dependent joint output map, then finite-output branch loads.",
            "",
            "## Frozen Boundary",
            "",
            "- Export mode: `piecewise:linear:20.0ms`",
            "- Gain: `4.0x`",
            "- Exposure: `5.0s`",
            "",
            "## Refined Candidate Fidelity",
            "",
            f"- RMS four-branch energy-fraction error: {summary_metrics['front_end_rms_error']:.6f}",
            f"- Max four-branch energy-fraction error: {summary_metrics['front_end_max_error']:.6f}",
            f"- RMS four-branch winner-law error: {summary_metrics['winner_rms_error']:.6f}",
            f"- Max four-branch winner-law error: {summary_metrics['winner_max_error']:.6f}",
            f"- Correlator RMS error: {summary_metrics['correlator_rms_error']:.6f}",
            f"- CHSH absolute error: {summary_metrics['chsh_abs_error']:.6f}",
            f"- Mean decisive fraction: {summary_metrics['mean_decisive_fraction']:.6f}",
            "",
            "## Comparison To Prior Candidate",
            "",
            f"- {comparison_note}",
            f"- Architectural realism gain: {comparison_rows[1]['architecture_note']}",
            "",
            "## Decision Gate",
            "",
            f"- Front-end pass: {acceptance['front_end_pass']}",
            f"- Winner-law pass: {acceptance['winner_pass']}",
            f"- Correlator pass: {acceptance['correlator_pass']}",
            f"- CHSH pass: {acceptance['chsh_pass']}",
            f"- Export stability pass: {acceptance['export_stability_pass']}",
            f"- Architectural refinement pass: {acceptance['architectural_refinement_pass']}",
            f"- Decision: {decision}",
            f"- Next ticket: {acceptance['recommended_next_ticket']}",
            "",
            "## Artifacts",
            "",
            f"- Shared-core summary: `{outputs['shared_core_csv']}`",
            f"- Four-branch summary: `{outputs['four_branch_csv']}`",
            f"- Integration summary: `{outputs['integration_csv']}`",
            f"- Comparison summary: `{outputs['comparison_csv']}`",
            f"- Design note: `{outputs['design_md']}`",
            f"- SPICE-facing interface: `{outputs['spice_md']}`",
            "",
        ]
    )


def _candidate_summary(front_rows: list[dict[str, Any]], integration_rows: list[dict[str, Any]], chsh_result: dict[str, Any]) -> dict[str, float]:
    front_aggregate = aggregate_case_error(front_rows)
    integration_aggregate = aggregate_case_error(integration_rows)
    return {
        "front_end_rms_error": float(front_aggregate["rms_error"]),
        "front_end_max_error": float(front_aggregate["max_abs_error"]),
        "winner_rms_error": float(integration_aggregate["rms_error"]),
        "winner_max_error": float(integration_aggregate["max_abs_error"]),
        "correlator_rms_error": float(correlator_rms_error(integration_rows)),
        "chsh_abs_error": float(chsh_result["abs_error"]),
        "mean_decisive_fraction": float(np.mean([row["decisive_fraction"] for row in integration_rows])),
    }


def build_physical_front_end_four_branch_refined_report(
    outdir: str | Path = "artifacts/physical_front_end_four_branch_refined",
    *,
    detector_next_summary_csv: str | Path = "artifacts/detector_next/results_summary.csv",
    n_trials: int = 4_000,
    seed: int = 20260403,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    shared_core_dir = output_dir / "shared_core"
    four_dir = output_dir / "four_branch"
    integration_dir = output_dir / "integration"
    spice_dir = output_dir / "spice_facing"
    for directory in (shared_core_dir, four_dir, integration_dir, spice_dir):
        directory.mkdir(parents=True, exist_ok=True)

    detector_spec = load_top_shot_trigger_spec(detector_next_summary_csv)
    detector_model_spec = {"family": detector_spec["family"], "model_params": dict(detector_spec["model_params"])}
    frozen_boundary = resolved_calibrated_boundary_config()
    frozen_export = selected_handoff_export_config()

    refined_front_rows: list[dict[str, Any]] = []
    refined_integration_rows: list[dict[str, Any]] = []
    prior_front_rows: list[dict[str, Any]] = []
    prior_integration_rows: list[dict[str, Any]] = []
    shared_core_rows: list[dict[str, Any]] = []
    refined_runs: list[dict[str, Any]] = []
    prior_runs: list[dict[str, Any]] = []
    example_power_row: dict[str, Any] | None = None

    refined_cases = benchmark_refined_four_branch_cases()
    prior_cases = benchmark_four_branch_physical_cases()

    for index, case in enumerate(refined_cases):
        refined_candidate = simulate_refined_four_branch_candidate(case["state4"], a_deg=case["a_deg"], b_deg=case["b_deg"])
        refined_run = run_four_branch_candidate_handoff(refined_candidate, detector_model_spec, n_trials=n_trials, seed=seed + 1_003 * index)
        exact_weights = [refined_candidate["exact_weight"][label] for label in refined_candidate["branch_labels"]]
        realized = [refined_candidate["branch_energy_fraction"][label] for label in refined_candidate["branch_labels"]]
        empirical = [float(value) for value in refined_run["empirical_frequencies"]]
        refined_runs.append({"case": case["case"], **refined_candidate})

        refined_front_rows.append(
            {
                "case": case["case"],
                "a_deg": case["a_deg"],
                "b_deg": case["b_deg"],
                "branch_labels": list(refined_candidate["branch_labels"]),
                "exact_weights": exact_weights,
                "realized_fractions": realized,
                "rms_error": float(refined_candidate["metrics"]["rms_error"]),
                "max_abs_error": float(refined_candidate["metrics"]["max_abs_error"]),
                "correlator_exact": float(refined_candidate["metrics"]["correlator_exact"]),
                "correlator_realized": float(refined_candidate["metrics"]["correlator_realized"]),
                "correlator_error": float(refined_candidate["metrics"]["correlator_error"]),
            }
        )
        refined_integration_rows.append(
            {
                "case": case["case"],
                "a_deg": case["a_deg"],
                "b_deg": case["b_deg"],
                "branch_labels": list(refined_candidate["branch_labels"]),
                "exact_weights": exact_weights,
                "empirical_frequencies": empirical,
                "rms_error": float(refined_run["metrics"]["rms_error"]),
                "max_abs_error": float(refined_run["metrics"]["max_abs_error"]),
                "correlator_exact": float(refined_run["metrics"]["correlator_exact"]),
                "correlator_empirical": float(refined_run["metrics"]["correlator_empirical"]),
                "correlator_error": float(refined_run["metrics"]["correlator_error"]),
                "decisive_fraction": float(refined_run["decisive_fraction"]),
                "decisive_count": int(refined_run["decisive_count"]),
                "timeout_count": int(refined_run["timeout_count"]),
            }
        )
        shared_core_rows.append(
            {
                "case": case["case"],
                "a_deg": case["a_deg"],
                "b_deg": case["b_deg"],
                "drive_frequency_rad_s": float(refined_candidate["shared_core"]["drive_frequency_rad_s"]),
                "singlet_state_overlap": float(refined_candidate["shared_core"]["singlet_state_overlap"]),
                "singlet_mode_energy": float(refined_candidate["shared_core"]["singlet_mode_energy"]),
                "dominant_mode_index": int(refined_candidate["shared_core"]["dominant_mode_index"]),
                "singlet_mode_index": int(refined_candidate["shared_core"]["singlet_mode_index"]),
                "prepared_state_magnitude": json.dumps(np.abs(np.asarray(refined_candidate["shared_core"]["prepared_internal_state"], dtype=np.complex128)).tolist()),
                "modal_energies": json.dumps(np.asarray(refined_candidate["shared_core"]["modal_energies"], dtype=float).tolist()),
            }
        )

        if example_power_row is None:
            example_power_row = {
                "case": case["case"],
                "branch_labels": list(refined_candidate["branch_labels"]),
                "time_s": list(refined_candidate["time_s"]),
                "branch_power_w": {label: list(refined_candidate["branch_power_w"][label]) for label in refined_candidate["branch_labels"]},
                "state_labels": list(BASIS_LABELS),
                "prepared_state_magnitude": np.abs(np.asarray(refined_candidate["shared_core"]["prepared_internal_state"], dtype=np.complex128)).tolist(),
                "modal_energies": np.asarray(refined_candidate["shared_core"]["modal_energies"], dtype=float).tolist(),
            }

        _write_csv(
            spice_dir / f"{case['case']}_exported_envelopes.csv",
            [
                {
                    "time_s": refined_run["trace"]["time_s"][sample_index],
                    **{f"{label}_power_w": refined_run["exported_branch_power"][label][sample_index] for label in refined_candidate["branch_labels"]},
                }
                for sample_index in range(len(refined_run["trace"]["time_s"]))
            ],
        )

    for index, case in enumerate(prior_cases):
        prior_candidate = simulate_four_branch_physical_candidate(case["state4"], a_deg=case["a_deg"], b_deg=case["b_deg"])
        prior_run = run_four_branch_candidate_handoff(prior_candidate, detector_model_spec, n_trials=n_trials, seed=seed + 50_000 + 1_003 * index)
        prior_runs.append({"case": case["case"], **prior_candidate})
        prior_front_rows.append(
            {
                "case": case["case"],
                "rms_error": float(prior_candidate["metrics"]["rms_error"]),
                "max_abs_error": float(prior_candidate["metrics"]["max_abs_error"]),
                "correlator_error": float(prior_candidate["metrics"]["correlator_error"]),
            }
        )
        prior_integration_rows.append(
            {
                "case": case["case"],
                "rms_error": float(prior_run["metrics"]["rms_error"]),
                "max_abs_error": float(prior_run["metrics"]["max_abs_error"]),
                "correlator_error": float(prior_run["metrics"]["correlator_error"]),
                "decisive_fraction": float(prior_run["decisive_fraction"]),
            }
        )

    refined_chsh_rows: list[dict[str, Any]] = []
    prior_chsh_rows: list[dict[str, Any]] = []
    exact_refined_correlators: dict[str, float] = {}
    empirical_refined_correlators: dict[str, float] = {}
    exact_prior_correlators: dict[str, float] = {}
    empirical_prior_correlators: dict[str, float] = {}

    for index, (label, (a_deg, b_deg)) in enumerate(DEFAULT_CHSH_SETTINGS.items()):
        refined_candidate = simulate_refined_four_branch_candidate(singlet_state(), a_deg=a_deg, b_deg=b_deg)
        refined_run = run_four_branch_candidate_handoff(refined_candidate, detector_model_spec, n_trials=n_trials, seed=seed + 100_000 + 1_003 * index)
        refined_chsh_rows.append(
            {
                "label": label,
                "a_deg": a_deg,
                "b_deg": b_deg,
                "correlator_exact": float(refined_run["metrics"]["correlator_exact"]),
                "correlator_empirical": float(refined_run["metrics"]["correlator_empirical"]),
                "correlator_error": float(refined_run["metrics"]["correlator_error"]),
                "winner_rms_error": float(refined_run["metrics"]["rms_error"]),
                "decisive_fraction": float(refined_run["decisive_fraction"]),
            }
        )
        exact_refined_correlators[label] = float(refined_run["metrics"]["correlator_exact"])
        empirical_refined_correlators[label] = float(refined_run["metrics"]["correlator_empirical"])

        prior_candidate = simulate_four_branch_physical_candidate(singlet_state(), a_deg=a_deg, b_deg=b_deg)
        prior_run = run_four_branch_candidate_handoff(prior_candidate, detector_model_spec, n_trials=n_trials, seed=seed + 150_000 + 1_003 * index)
        prior_chsh_rows.append(
            {
                "label": label,
                "a_deg": a_deg,
                "b_deg": b_deg,
                "correlator_exact": float(prior_run["metrics"]["correlator_exact"]),
                "correlator_empirical": float(prior_run["metrics"]["correlator_empirical"]),
                "correlator_error": float(prior_run["metrics"]["correlator_error"]),
                "winner_rms_error": float(prior_run["metrics"]["rms_error"]),
                "decisive_fraction": float(prior_run["decisive_fraction"]),
            }
        )
        exact_prior_correlators[label] = float(prior_run["metrics"]["correlator_exact"])
        empirical_prior_correlators[label] = float(prior_run["metrics"]["correlator_empirical"])

    refined_chsh = {
        "rows": refined_chsh_rows,
        "exact_s": float(sum([exact_refined_correlators["a0b0"], exact_refined_correlators["a0b1"], exact_refined_correlators["a1b0"], -exact_refined_correlators["a1b1"]])),
        "empirical_s": float(sum([empirical_refined_correlators["a0b0"], empirical_refined_correlators["a0b1"], empirical_refined_correlators["a1b0"], -empirical_refined_correlators["a1b1"]])),
    }
    refined_chsh["abs_error"] = abs(refined_chsh["empirical_s"] - refined_chsh["exact_s"])
    prior_chsh = {
        "rows": prior_chsh_rows,
        "exact_s": float(sum([exact_prior_correlators["a0b0"], exact_prior_correlators["a0b1"], exact_prior_correlators["a1b0"], -exact_prior_correlators["a1b1"]])),
        "empirical_s": float(sum([empirical_prior_correlators["a0b0"], empirical_prior_correlators["a0b1"], empirical_prior_correlators["a1b0"], -empirical_prior_correlators["a1b1"]])),
    }
    prior_chsh["abs_error"] = abs(prior_chsh["empirical_s"] - prior_chsh["exact_s"])

    refined_summary = _candidate_summary(refined_front_rows, refined_integration_rows, refined_chsh)
    prior_summary = _candidate_summary(prior_front_rows, prior_integration_rows, prior_chsh)

    comparison_rows = [
        {"candidate": "prior_exact_weight_mapper", **prior_summary, "architecture_note": "Direct exact-weight-driven branch drivers."},
        {"candidate": "refined_shared_core", **refined_summary, "architecture_note": "Explicit four-state shared core plus analyzer/readout map."},
    ]

    if example_power_row is not None:
        plot_shared_core_diagnostics(example_power_row).savefig(shared_core_dir / "shared_core_diagnostics.png")
        plot_four_branch_power_traces(example_power_row).savefig(four_dir / "four_branch_power_traces.png")

    plot_four_branch_fraction_comparison(refined_front_rows).savefig(four_dir / "exact_vs_realized_four_branch_fractions.png")
    plot_four_branch_winner_frequency(refined_integration_rows).savefig(integration_dir / "exact_vs_empirical_four_branch_winner_frequencies.png")
    plot_correlator_exact_vs_empirical(refined_integration_rows).savefig(integration_dir / "correlator_exact_vs_empirical.png")
    plot_chsh_exact_vs_empirical(refined_chsh).savefig(integration_dir / "chsh_exact_vs_empirical.png")
    plot_four_branch_residual_summary(refined_front_rows, refined_integration_rows, refined_chsh).savefig(integration_dir / "residual_error_summary.png")
    plot_candidate_metric_comparison(comparison_rows).savefig(shared_core_dir / "candidate_metric_comparison.png")

    four_csv = four_dir / "four_branch_summary.csv"
    four_json = four_dir / "four_branch_summary.json"
    integration_csv = integration_dir / "integration_summary.csv"
    integration_json = integration_dir / "integration_summary.json"
    shared_core_csv = shared_core_dir / "shared_core_summary.csv"
    shared_core_json = shared_core_dir / "shared_core_summary.json"
    comparison_csv = output_dir / "candidate_comparison.csv"

    _write_csv(
        four_csv,
        [
            {
                **row,
                "branch_labels": json.dumps(row["branch_labels"]),
                "exact_weights": json.dumps(row["exact_weights"]),
                "realized_fractions": json.dumps(row["realized_fractions"]),
            }
            for row in refined_front_rows
        ],
    )
    _write_csv(
        integration_csv,
        [
            {
                **row,
                "branch_labels": json.dumps(row["branch_labels"]),
                "exact_weights": json.dumps(row["exact_weights"]),
                "empirical_frequencies": json.dumps(row["empirical_frequencies"]),
            }
            for row in refined_integration_rows
        ],
    )
    _write_csv(shared_core_csv, shared_core_rows)
    _write_csv(comparison_csv, comparison_rows)

    four_json.write_text(json.dumps({"rows": refined_runs}, indent=2, default=_json_default) + "\n", encoding="utf-8")
    integration_json.write_text(json.dumps({"rows": refined_integration_rows, "chsh": refined_chsh}, indent=2, default=_json_default) + "\n", encoding="utf-8")
    shared_core_json.write_text(json.dumps({"rows": shared_core_rows}, indent=2, default=_json_default) + "\n", encoding="utf-8")

    export_metrics = (
        finite_export_metrics(
            [np.asarray(refined_runs[0]["branch_power_w"][label], dtype=float) for label in refined_runs[0]["branch_labels"]]
        )
        if refined_runs
        else {"finite": True, "nonnegative_with_tolerance": True, "min_power_w": 0.0}
    )
    summary_metrics = {
        **refined_summary,
        "export_finite": float(bool(export_metrics["finite"])),
        "export_nonnegative": float(bool(export_metrics["nonnegative_with_tolerance"])),
        "min_export_power_w": float(export_metrics["min_power_w"]),
        "shared_core_overlap_mean": float(np.mean([float(row["singlet_state_overlap"]) for row in shared_core_rows])),
    }
    acceptance = {
        "front_end_pass": summary_metrics["front_end_rms_error"] < 0.03 and summary_metrics["front_end_max_error"] < 0.05,
        "winner_pass": summary_metrics["winner_rms_error"] < 0.03 and summary_metrics["winner_max_error"] < 0.05,
        "correlator_pass": summary_metrics["correlator_rms_error"] < 0.05,
        "chsh_pass": summary_metrics["chsh_abs_error"] < 0.1,
        "export_stability_pass": bool(export_metrics["finite"] and export_metrics["nonnegative_with_tolerance"]),
        "architectural_refinement_pass": summary_metrics["shared_core_overlap_mean"] > 0.9,
    }
    acceptance["proceed_to_next_phase"] = all(acceptance.values())
    acceptance["recommended_next_ticket"] = (
        "Move toward an explicit resonant/shared-mode front-end realization or start specifying the post-click closure/drain path."
        if acceptance["proceed_to_next_phase"]
        else "Iterate on the shared-core refinement before pushing further toward hardware physicalization."
    )

    summary_csv = output_dir / "summary_metrics.csv"
    _write_csv(summary_csv, [{"metric": key, "value": value} for key, value in summary_metrics.items()])

    design_md = output_dir / "front_end_candidate_design.md"
    design_md.write_text(
        "\n".join(
            [
                "# Refined Four-Branch Front-End Candidate Design",
                "",
                "Chosen option: Option A, explicit 4-state linear shared core.",
                "",
                "## What Was Removed",
                "",
                "- The prior candidate assigned branch-driver amplitudes directly from the exact reduced-model weights.",
                "",
                "## What Replaced It",
                "",
                "- A `Shared4TankCore` solve prepares an internal shared state near the singlet-like mode.",
                "- Analyzer dependence is represented by the joint analyzer matrix acting on that internal state.",
                "- Four measurable output branches are then produced by finite source/load ports driven from the analyzer outputs.",
                "",
                "## What Is More Physical Now",
                "",
                "- The branch outputs arise from an explicit internal shared-core state and output map rather than from direct exact-weight assignment.",
                "- The model exposes drive vector, steady-state internal amplitudes, modal energies, and branch output amplitudes as diagnostics.",
                "",
                "## What Remains Abstract",
                "",
                "- The shared core is still linear and reduced-order rather than a full nonlinear or final resonant LC/tank hardware netlist.",
                "- Detector, latch, export contract, and post-click drain path remain unchanged abstractions.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    spice_md = spice_dir / "spice_facing_interface.md"
    spice_md.write_text(
        "\n".join(
            [
                "# Refined Four-Branch SPICE-Facing Interface",
                "",
                "## Internal Shared-Core Block",
                "",
                "- Four-state linear shared core prepared near the singlet-like eigenmode.",
                "- Analyzer dependence enters through the joint analyzer matrix applied to the prepared internal state.",
                "",
                "## Frozen Detector Boundary",
                "",
                f"- Export mode: `{frozen_export.mode}:{frozen_export.piecewise_mode}:{frozen_export.piecewise_bin_width_s * 1e3:.1f}ms`.",
                f"- Gain: `{frozen_boundary.gain:.1f}x`.",
                f"- Exposure: `{frozen_boundary.exposure_s:.1f}s`.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    outputs = {
        "shared_core_csv": str(shared_core_csv),
        "four_branch_csv": str(four_csv),
        "integration_csv": str(integration_csv),
        "comparison_csv": str(comparison_csv),
        "design_md": str(design_md),
        "spice_md": str(spice_md),
    }
    summary_json = output_dir / "summary_metrics.json"
    summary_json.write_text(
        json.dumps(
            {
                "summary_metrics": summary_metrics,
                "acceptance": acceptance,
                "comparison_rows": comparison_rows,
                "refined_front_rows": refined_front_rows,
                "refined_integration_rows": refined_integration_rows,
                "refined_chsh": refined_chsh,
                "shared_core_rows": shared_core_rows,
                "outputs": outputs,
            },
            indent=2,
            default=_json_default,
        )
        + "\n",
        encoding="utf-8",
    )
    summary_md = output_dir / "summary_report.md"
    summary_md.write_text(_summary_markdown(summary_metrics=summary_metrics, acceptance=acceptance, comparison_rows=comparison_rows, outputs=outputs) + "\n", encoding="utf-8")
    return {
        "summary_md": str(summary_md),
        "summary_json": str(summary_json),
        "summary_csv": str(summary_csv),
        "shared_core_csv": str(shared_core_csv),
        "four_branch_csv": str(four_csv),
        "integration_csv": str(integration_csv),
        "comparison_csv": str(comparison_csv),
        "design_md": str(design_md),
        "spice_facing_interface_md": str(spice_md),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the refined four-branch physical/SPICE front-end report.")
    parser.add_argument("--outdir", default="artifacts/physical_front_end_four_branch_refined")
    parser.add_argument("--detector-next-summary", default="artifacts/detector_next/results_summary.csv")
    parser.add_argument("--trials", type=int, default=4_000)
    args = parser.parse_args()
    build_physical_front_end_four_branch_refined_report(
        args.outdir,
        detector_next_summary_csv=args.detector_next_summary,
        n_trials=args.trials,
    )


if __name__ == "__main__":
    main()
