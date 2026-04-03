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
    plot_resonant_mode_diagnostics,
)
from physical_front_end_candidate.refined_four_branch_candidate import benchmark_refined_four_branch_cases, simulate_refined_four_branch_candidate
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


def _summary_markdown(
    *,
    summary_metrics: dict[str, float],
    acceptance: dict[str, bool | str],
    comparison_rows: list[dict[str, Any]],
    outputs: dict[str, str],
) -> str:
    decision = "Proceed toward post-click closure/drain specification or a deeper explicit LC/coupled-port realization." if acceptance["proceed_to_next_phase"] else "Iterate on the resonant/shared-mode realization before moving on."
    return "\n".join(
        [
            "# Resonant Four-Branch Front-End Summary",
            "",
            "## Architecture",
            "",
            "- Chosen option: `Option A`, explicit modal resonator realization.",
            "- Internal structure: coupled shared-mode eigenbasis, drive-to-mode response, modal ringdown, analyzer/readout coupling, finite branch loads.",
            "",
            "## Frozen Boundary",
            "",
            "- Export mode: `piecewise_envelope:linear:20.0ms`",
            "- Gain: `4.0x`",
            "- Exposure: `5.0s`",
            "",
            "## Resonant Candidate Fidelity",
            "",
            f"- RMS four-branch energy-fraction error: {summary_metrics['front_end_rms_error']:.6f}",
            f"- Max four-branch energy-fraction error: {summary_metrics['front_end_max_error']:.6f}",
            f"- RMS four-branch winner-law error: {summary_metrics['winner_rms_error']:.6f}",
            f"- Max four-branch winner-law error: {summary_metrics['winner_max_error']:.6f}",
            f"- Correlator RMS error: {summary_metrics['correlator_rms_error']:.6f}",
            f"- CHSH absolute error: {summary_metrics['chsh_abs_error']:.6f}",
            f"- Mean decisive fraction: {summary_metrics['mean_decisive_fraction']:.6f}",
            "",
            "## Comparison To Prior Refined Candidate",
            "",
            f"- Refined 4-state winner-law RMS {comparison_rows[0]['winner_rms_error']:.6f} vs resonant {comparison_rows[1]['winner_rms_error']:.6f}.",
            f"- Refined 4-state correlator RMS {comparison_rows[0]['correlator_rms_error']:.6f} vs resonant {comparison_rows[1]['correlator_rms_error']:.6f}.",
            f"- Physical realism gain: {comparison_rows[1]['architecture_note']}",
            "",
            "## Decision Gate",
            "",
            f"- Front-end pass: {acceptance['front_end_pass']}",
            f"- Winner-law pass: {acceptance['winner_pass']}",
            f"- Correlator pass: {acceptance['correlator_pass']}",
            f"- CHSH pass: {acceptance['chsh_pass']}",
            f"- Export stability pass: {acceptance['export_stability_pass']}",
            f"- Resonant-structure pass: {acceptance['resonant_structure_pass']}",
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


def build_physical_front_end_four_branch_resonant_report(
    outdir: str | Path = "artifacts/physical_front_end_four_branch_resonant",
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

    resonant_front_rows: list[dict[str, Any]] = []
    resonant_integration_rows: list[dict[str, Any]] = []
    refined_front_rows: list[dict[str, Any]] = []
    refined_integration_rows: list[dict[str, Any]] = []
    shared_core_rows: list[dict[str, Any]] = []
    resonant_runs: list[dict[str, Any]] = []
    example_power_row: dict[str, Any] | None = None
    example_mode_row: dict[str, Any] | None = None

    for index, case in enumerate(benchmark_resonant_four_branch_cases()):
        candidate = simulate_resonant_four_branch_candidate(case["state4"], a_deg=case["a_deg"], b_deg=case["b_deg"])
        run = run_four_branch_candidate_handoff(candidate, detector_model_spec, n_trials=n_trials, seed=seed + 1_003 * index)
        exact_weights = [candidate["exact_weight"][label] for label in candidate["branch_labels"]]
        realized = [candidate["branch_energy_fraction"][label] for label in candidate["branch_labels"]]
        empirical = [float(value) for value in run["empirical_frequencies"]]
        resonant_runs.append({"case": case["case"], **candidate})
        resonant_front_rows.append(
            {
                "case": case["case"],
                "a_deg": case["a_deg"],
                "b_deg": case["b_deg"],
                "branch_labels": list(candidate["branch_labels"]),
                "exact_weights": exact_weights,
                "realized_fractions": realized,
                "rms_error": float(candidate["metrics"]["rms_error"]),
                "max_abs_error": float(candidate["metrics"]["max_abs_error"]),
                "correlator_exact": float(candidate["metrics"]["correlator_exact"]),
                "correlator_realized": float(candidate["metrics"]["correlator_realized"]),
                "correlator_error": float(candidate["metrics"]["correlator_error"]),
            }
        )
        resonant_integration_rows.append(
            {
                "case": case["case"],
                "a_deg": case["a_deg"],
                "b_deg": case["b_deg"],
                "branch_labels": list(candidate["branch_labels"]),
                "exact_weights": exact_weights,
                "empirical_frequencies": empirical,
                "rms_error": float(run["metrics"]["rms_error"]),
                "max_abs_error": float(run["metrics"]["max_abs_error"]),
                "correlator_exact": float(run["metrics"]["correlator_exact"]),
                "correlator_empirical": float(run["metrics"]["correlator_empirical"]),
                "correlator_error": float(run["metrics"]["correlator_error"]),
                "decisive_fraction": float(run["decisive_fraction"]),
                "decisive_count": int(run["decisive_count"]),
                "timeout_count": int(run["timeout_count"]),
            }
        )
        shared_core_rows.append(
            {
                "case": case["case"],
                "a_deg": case["a_deg"],
                "b_deg": case["b_deg"],
                "singlet_mode_index": int(candidate["shared_core"]["singlet_mode_index"]),
                "singlet_mode_overlap": float(candidate["shared_core"]["singlet_mode_overlap"]),
                "modal_response_magnitude": json.dumps(np.abs(np.asarray(candidate["shared_core"]["modal_response"], dtype=np.complex128)).tolist()),
                "modal_decay_rates": json.dumps(np.asarray(candidate["shared_core"]["modal_decay_rates"], dtype=float).tolist()),
                "mode_overlap_profile": json.dumps(np.asarray(candidate["shared_core"]["mode_overlap_profile"], dtype=float).tolist()),
            }
        )

        if example_power_row is None:
            example_power_row = {
                "case": case["case"],
                "branch_labels": list(candidate["branch_labels"]),
                "time_s": list(candidate["time_s"]),
                "branch_power_w": {label: list(candidate["branch_power_w"][label]) for label in candidate["branch_labels"]},
            }
            example_mode_row = {
                "modal_response_magnitude": np.abs(np.asarray(candidate["shared_core"]["modal_response"], dtype=np.complex128)).tolist(),
                "modal_decay_rates": np.asarray(candidate["shared_core"]["modal_decay_rates"], dtype=float).tolist(),
                "mode_overlap_profile": np.asarray(candidate["shared_core"]["mode_overlap_profile"], dtype=float).tolist(),
            }

        _write_csv(
            spice_dir / f"{case['case']}_exported_envelopes.csv",
            [
                {
                    "time_s": run["trace"]["time_s"][sample_index],
                    **{f"{label}_power_w": run["exported_branch_power"][label][sample_index] for label in candidate["branch_labels"]},
                }
                for sample_index in range(len(run["trace"]["time_s"]))
            ],
        )

    for index, case in enumerate(benchmark_refined_four_branch_cases()):
        candidate = simulate_refined_four_branch_candidate(case["state4"], a_deg=case["a_deg"], b_deg=case["b_deg"])
        run = run_four_branch_candidate_handoff(candidate, detector_model_spec, n_trials=n_trials, seed=seed + 50_000 + 1_003 * index)
        refined_front_rows.append(
            {
                "case": case["case"],
                "rms_error": float(candidate["metrics"]["rms_error"]),
                "max_abs_error": float(candidate["metrics"]["max_abs_error"]),
                "correlator_error": float(candidate["metrics"]["correlator_error"]),
            }
        )
        refined_integration_rows.append(
            {
                "case": case["case"],
                "rms_error": float(run["metrics"]["rms_error"]),
                "max_abs_error": float(run["metrics"]["max_abs_error"]),
                "correlator_error": float(run["metrics"]["correlator_error"]),
                "decisive_fraction": float(run["decisive_fraction"]),
            }
        )

    resonant_chsh_rows: list[dict[str, Any]] = []
    refined_chsh_rows: list[dict[str, Any]] = []
    exact_resonant: dict[str, float] = {}
    empirical_resonant: dict[str, float] = {}
    exact_refined: dict[str, float] = {}
    empirical_refined: dict[str, float] = {}

    for index, (label, (a_deg, b_deg)) in enumerate(DEFAULT_CHSH_SETTINGS.items()):
        resonant_candidate = simulate_resonant_four_branch_candidate(singlet_state(), a_deg=a_deg, b_deg=b_deg)
        resonant_run = run_four_branch_candidate_handoff(resonant_candidate, detector_model_spec, n_trials=n_trials, seed=seed + 100_000 + 1_003 * index)
        resonant_chsh_rows.append(
            {
                "label": label,
                "a_deg": a_deg,
                "b_deg": b_deg,
                "correlator_exact": float(resonant_run["metrics"]["correlator_exact"]),
                "correlator_empirical": float(resonant_run["metrics"]["correlator_empirical"]),
                "correlator_error": float(resonant_run["metrics"]["correlator_error"]),
                "winner_rms_error": float(resonant_run["metrics"]["rms_error"]),
                "decisive_fraction": float(resonant_run["decisive_fraction"]),
            }
        )
        exact_resonant[label] = float(resonant_run["metrics"]["correlator_exact"])
        empirical_resonant[label] = float(resonant_run["metrics"]["correlator_empirical"])

        refined_candidate = simulate_refined_four_branch_candidate(singlet_state(), a_deg=a_deg, b_deg=b_deg)
        refined_run = run_four_branch_candidate_handoff(refined_candidate, detector_model_spec, n_trials=n_trials, seed=seed + 150_000 + 1_003 * index)
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
        exact_refined[label] = float(refined_run["metrics"]["correlator_exact"])
        empirical_refined[label] = float(refined_run["metrics"]["correlator_empirical"])

    resonant_chsh = {
        "rows": resonant_chsh_rows,
        "exact_s": float(exact_resonant["a0b0"] + exact_resonant["a0b1"] + exact_resonant["a1b0"] - exact_resonant["a1b1"]),
        "empirical_s": float(empirical_resonant["a0b0"] + empirical_resonant["a0b1"] + empirical_resonant["a1b0"] - empirical_resonant["a1b1"]),
    }
    resonant_chsh["abs_error"] = abs(resonant_chsh["empirical_s"] - resonant_chsh["exact_s"])
    refined_chsh = {
        "rows": refined_chsh_rows,
        "exact_s": float(exact_refined["a0b0"] + exact_refined["a0b1"] + exact_refined["a1b0"] - exact_refined["a1b1"]),
        "empirical_s": float(empirical_refined["a0b0"] + empirical_refined["a0b1"] + empirical_refined["a1b0"] - empirical_refined["a1b1"]),
    }
    refined_chsh["abs_error"] = abs(refined_chsh["empirical_s"] - refined_chsh["exact_s"])

    resonant_summary = _candidate_summary(resonant_front_rows, resonant_integration_rows, resonant_chsh)
    refined_summary = _candidate_summary(refined_front_rows, refined_integration_rows, refined_chsh)
    comparison_rows = [
        {"candidate": "refined_shared_core", **refined_summary, "architecture_note": "Explicit 4-state shared core plus analyzer/readout map."},
        {"candidate": "resonant_shared_mode", **resonant_summary, "architecture_note": "Explicit modal resonator response and ringdown in the shared core."},
    ]

    if example_power_row is not None:
        plot_four_branch_power_traces(example_power_row).savefig(four_dir / "four_branch_power_traces.png")
    if example_mode_row is not None:
        plot_resonant_mode_diagnostics(example_mode_row).savefig(shared_core_dir / "resonant_mode_diagnostics.png")

    plot_four_branch_fraction_comparison(resonant_front_rows).savefig(four_dir / "exact_vs_realized_four_branch_fractions.png")
    plot_four_branch_winner_frequency(resonant_integration_rows).savefig(integration_dir / "exact_vs_empirical_four_branch_winner_frequencies.png")
    plot_correlator_exact_vs_empirical(resonant_integration_rows).savefig(integration_dir / "correlator_exact_vs_empirical.png")
    plot_chsh_exact_vs_empirical(resonant_chsh).savefig(integration_dir / "chsh_exact_vs_empirical.png")
    plot_four_branch_residual_summary(resonant_front_rows, resonant_integration_rows, resonant_chsh).savefig(integration_dir / "residual_error_summary.png")
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
        [{**row, "branch_labels": json.dumps(row["branch_labels"]), "exact_weights": json.dumps(row["exact_weights"]), "realized_fractions": json.dumps(row["realized_fractions"])} for row in resonant_front_rows],
    )
    _write_csv(
        integration_csv,
        [{**row, "branch_labels": json.dumps(row["branch_labels"]), "exact_weights": json.dumps(row["exact_weights"]), "empirical_frequencies": json.dumps(row["empirical_frequencies"])} for row in resonant_integration_rows],
    )
    _write_csv(shared_core_csv, shared_core_rows)
    _write_csv(comparison_csv, comparison_rows)

    four_json.write_text(json.dumps({"rows": resonant_runs}, indent=2, default=_json_default) + "\n", encoding="utf-8")
    integration_json.write_text(json.dumps({"rows": resonant_integration_rows, "chsh": resonant_chsh}, indent=2, default=_json_default) + "\n", encoding="utf-8")
    shared_core_json.write_text(json.dumps({"rows": shared_core_rows}, indent=2, default=_json_default) + "\n", encoding="utf-8")

    export_metrics = (
        finite_export_metrics([np.asarray(resonant_runs[0]["branch_power_w"][label], dtype=float) for label in resonant_runs[0]["branch_labels"]])
        if resonant_runs
        else {"finite": True, "nonnegative_with_tolerance": True, "min_power_w": 0.0}
    )
    summary_metrics = {
        **resonant_summary,
        "export_finite": float(bool(export_metrics["finite"])),
        "export_nonnegative": float(bool(export_metrics["nonnegative_with_tolerance"])),
        "min_export_power_w": float(export_metrics["min_power_w"]),
        "singlet_mode_overlap_mean": float(np.mean([float(row["singlet_mode_overlap"]) for row in shared_core_rows])),
    }
    acceptance = {
        "front_end_pass": summary_metrics["front_end_rms_error"] < 0.03 and summary_metrics["front_end_max_error"] < 0.05,
        "winner_pass": summary_metrics["winner_rms_error"] < 0.03 and summary_metrics["winner_max_error"] < 0.05,
        "correlator_pass": summary_metrics["correlator_rms_error"] < 0.05,
        "chsh_pass": summary_metrics["chsh_abs_error"] < 0.1,
        "export_stability_pass": bool(export_metrics["finite"] and export_metrics["nonnegative_with_tolerance"]),
        "resonant_structure_pass": summary_metrics["singlet_mode_overlap_mean"] > 0.9,
    }
    acceptance["proceed_to_next_phase"] = all(acceptance.values())
    acceptance["recommended_next_ticket"] = (
        "Begin specifying the post-click closure/drain path or move one step deeper toward an explicit LC/coupled-port implementation."
        if acceptance["proceed_to_next_phase"]
        else "Iterate on the resonant/shared-mode front-end realization before moving deeper into hardware detail."
    )

    summary_csv = output_dir / "summary_metrics.csv"
    _write_csv(summary_csv, [{"metric": key, "value": value} for key, value in summary_metrics.items()])

    design_md = output_dir / "front_end_candidate_design.md"
    design_md.write_text(
        "\n".join(
            [
                "# Resonant Four-Branch Front-End Candidate Design",
                "",
                "Chosen option: Option A, explicit modal resonator realization.",
                "",
                "## Physical Interpretability Gain",
                "",
                "- The prior refined candidate exposed an internal state but not an explicit resonant modal response.",
                "- This candidate makes the shared-core eigenmodes explicit, computes drive-to-mode response, and reconstructs branch outputs from modal ringdown.",
                "",
                "## Preparation Representation",
                "",
                "- Preparation is represented as a drive vector injected into the shared resonant core and projected into the coupled eigenmode basis.",
                "- The singlet-like mode is selected by overlap and used as the resonant preparation target.",
                "",
                "## Analyzer Dependence",
                "",
                "- Analyzer dependence remains in the joint analyzer/readout matrix acting on the resonant internal state, not through direct branch-weight assignment.",
                "",
                "## What Remains Abstract",
                "",
                "- The realization is still linear and reduced-order rather than a final explicit R/L/C netlist.",
                "- Detector, latch, frozen export contract, and post-click closure/drain path remain unchanged abstractions.",
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
                "# Resonant Four-Branch SPICE-Facing Interface",
                "",
                "## Internal Resonant Structure",
                "",
                "- Coupled shared-core eigenmodes derived from the effective generator.",
                "- Drive-to-mode response and modal decay rates are explicit and reported.",
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
                "resonant_front_rows": resonant_front_rows,
                "resonant_integration_rows": resonant_integration_rows,
                "resonant_chsh": resonant_chsh,
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
    parser = argparse.ArgumentParser(description="Build the resonant/shared-mode four-branch front-end report.")
    parser.add_argument("--outdir", default="artifacts/physical_front_end_four_branch_resonant")
    parser.add_argument("--detector-next-summary", default="artifacts/detector_next/results_summary.csv")
    parser.add_argument("--trials", type=int, default=4_000)
    args = parser.parse_args()
    build_physical_front_end_four_branch_resonant_report(
        args.outdir,
        detector_next_summary_csv=args.detector_next_summary,
        n_trials=args.trials,
    )


if __name__ == "__main__":
    main()
