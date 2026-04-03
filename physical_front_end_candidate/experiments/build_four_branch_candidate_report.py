from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from detector_integration.experiments.run_summary_report import load_top_shot_trigger_spec
from src.shared_4tank_core import singlet_state

from physical_front_end_candidate.boundary_calibration import resolved_calibrated_boundary_config
from physical_front_end_candidate.boundary_diagnosis import selected_handoff_export_config
from physical_front_end_candidate.four_branch_candidate import benchmark_four_branch_physical_cases, simulate_four_branch_physical_candidate
from physical_front_end_candidate.integration import run_four_branch_physical_chsh, run_four_branch_physical_handoff
from physical_front_end_candidate.metrics import aggregate_case_error, correlator_rms_error, finite_export_metrics
from physical_front_end_candidate.plots import (
    plot_chsh_exact_vs_empirical,
    plot_correlator_exact_vs_empirical,
    plot_four_branch_export_envelopes,
    plot_four_branch_fraction_comparison,
    plot_four_branch_power_traces,
    plot_four_branch_residual_summary,
    plot_four_branch_winner_frequency,
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
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _summary_markdown(
    *,
    summary_metrics: dict[str, float],
    acceptance: dict[str, bool | str],
    outputs: dict[str, str],
) -> str:
    decision = "Proceed to deeper shared-state physical refinement." if acceptance["proceed_to_next_phase"] else "Hold shared-state scaling and debug the four-branch front-end boundary."
    return "\n".join(
        [
            "# Four-Branch Physical Front-End Candidate Summary",
            "",
            "## Frozen Boundary",
            "",
            "- Export mode: `piecewise:linear:20.0ms`",
            "- Gain: `4.0x`",
            "- Exposure: `5.0s`",
            "",
            "## Front-End Fidelity",
            "",
            f"- RMS four-branch energy-fraction error: {summary_metrics['front_end_rms_error']:.6f}",
            f"- Max four-branch energy-fraction error: {summary_metrics['front_end_max_error']:.6f}",
            "",
            "## Integrated Detector + Latch Fidelity",
            "",
            f"- RMS four-branch winner-law error: {summary_metrics['winner_rms_error']:.6f}",
            f"- Max four-branch winner-law error: {summary_metrics['winner_max_error']:.6f}",
            f"- Correlator RMS error: {summary_metrics['correlator_rms_error']:.6f}",
            f"- CHSH absolute error: {summary_metrics['chsh_abs_error']:.6f}",
            f"- Mean decisive fraction: {summary_metrics['mean_decisive_fraction']:.6f}",
            "",
            "## Decision Gate",
            "",
            f"- Front-end pass: {acceptance['front_end_pass']}",
            f"- Winner-law pass: {acceptance['winner_pass']}",
            f"- Correlator pass: {acceptance['correlator_pass']}",
            f"- CHSH pass: {acceptance['chsh_pass']}",
            f"- Export stability pass: {acceptance['export_stability_pass']}",
            f"- Decision: {decision}",
            f"- Next ticket: {acceptance['recommended_next_ticket']}",
            "",
            "## Artifacts",
            "",
            f"- Four-branch summary: `{outputs['four_branch_csv']}`",
            f"- Integration summary: `{outputs['integration_csv']}`",
            f"- Design note: `{outputs['design_md']}`",
            f"- SPICE-facing interface: `{outputs['spice_md']}`",
            "",
        ]
    )


def build_physical_front_end_four_branch_candidate_report(
    outdir: str | Path = "artifacts/physical_front_end_four_branch_candidate",
    *,
    detector_next_summary_csv: str | Path = "artifacts/detector_next/results_summary.csv",
    n_trials: int = 4_000,
    seed: int = 20260403,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    four_dir = output_dir / "four_branch"
    integration_dir = output_dir / "integration"
    spice_dir = output_dir / "spice_facing"
    four_dir.mkdir(parents=True, exist_ok=True)
    integration_dir.mkdir(parents=True, exist_ok=True)
    spice_dir.mkdir(parents=True, exist_ok=True)

    detector_spec = load_top_shot_trigger_spec(detector_next_summary_csv)
    detector_model_spec = {"family": detector_spec["family"], "model_params": dict(detector_spec["model_params"])}
    frozen_boundary = resolved_calibrated_boundary_config()
    frozen_export = selected_handoff_export_config()

    front_rows: list[dict[str, Any]] = []
    integration_rows: list[dict[str, Any]] = []
    full_front_runs: list[dict[str, Any]] = []
    power_trace_row: dict[str, Any] | None = None
    export_trace_row: dict[str, Any] | None = None

    for index, case in enumerate(benchmark_four_branch_physical_cases()):
        front_result = simulate_four_branch_physical_candidate(case["state4"], a_deg=case["a_deg"], b_deg=case["b_deg"])
        handoff_result = run_four_branch_physical_handoff(
            case["state4"],
            a_deg=case["a_deg"],
            b_deg=case["b_deg"],
            detector_spec=detector_model_spec,
            n_trials=n_trials,
            seed=seed + 1_003 * index,
        )
        exact_weights = [front_result["exact_weight"][label] for label in front_result["branch_labels"]]
        realized = [front_result["branch_energy_fraction"][label] for label in front_result["branch_labels"]]
        empirical = [float(value) for value in handoff_result["empirical_frequencies"]]

        front_row = {
            "case": case["case"],
            "a_deg": case["a_deg"],
            "b_deg": case["b_deg"],
            "branch_labels": list(front_result["branch_labels"]),
            "exact_weights": exact_weights,
            "realized_fractions": realized,
            "rms_error": float(front_result["metrics"]["rms_error"]),
            "max_abs_error": float(front_result["metrics"]["max_abs_error"]),
            "correlator_exact": float(front_result["metrics"]["correlator_exact"]),
            "correlator_realized": float(front_result["metrics"]["correlator_realized"]),
            "correlator_error": float(front_result["metrics"]["correlator_error"]),
        }
        integration_row = {
            "case": case["case"],
            "a_deg": case["a_deg"],
            "b_deg": case["b_deg"],
            "branch_labels": list(front_result["branch_labels"]),
            "exact_weights": exact_weights,
            "empirical_frequencies": empirical,
            "rms_error": float(handoff_result["metrics"]["rms_error"]),
            "max_abs_error": float(handoff_result["metrics"]["max_abs_error"]),
            "correlator_exact": float(handoff_result["metrics"]["correlator_exact"]),
            "correlator_empirical": float(handoff_result["metrics"]["correlator_empirical"]),
            "correlator_error": float(handoff_result["metrics"]["correlator_error"]),
            "decisive_fraction": float(handoff_result["decisive_fraction"]),
            "decisive_count": int(handoff_result["decisive_count"]),
            "timeout_count": int(handoff_result["timeout_count"]),
        }
        front_rows.append(front_row)
        integration_rows.append(integration_row)
        full_front_runs.append({"case": case["case"], **front_result})

        if power_trace_row is None:
            power_trace_row = {
                "case": case["case"],
                "branch_labels": list(front_result["branch_labels"]),
                "time_s": list(front_result["time_s"]),
                "branch_power_w": {label: list(front_result["branch_power_w"][label]) for label in front_result["branch_labels"]},
            }
        if export_trace_row is None:
            export_trace_row = {
                "case": case["case"],
                "branch_labels": list(front_result["branch_labels"]),
                "time_s": list(front_result["time_s"]),
                "branch_power_w": {label: list(front_result["branch_power_w"][label]) for label in front_result["branch_labels"]},
                "export_time_s": list(handoff_result["trace"]["time_s"]),
                "exported_branch_power": {label: list(handoff_result["exported_branch_power"][label]) for label in front_result["branch_labels"]},
            }

        trace_csv = four_dir / f"{case['case']}_traces.csv"
        _write_csv(
            trace_csv,
            [
                {
                    "time_s": front_result["time_s"][sample_index],
                    **{f"{label}_voltage_v": front_result["branch_voltage_v"][label][sample_index] for label in front_result["branch_labels"]},
                    **{f"{label}_current_a": front_result["branch_current_a"][label][sample_index] for label in front_result["branch_labels"]},
                    **{f"{label}_power_w": front_result["branch_power_w"][label][sample_index] for label in front_result["branch_labels"]},
                }
                for sample_index in range(len(front_result["time_s"]))
            ],
        )

    chsh_result = run_four_branch_physical_chsh(singlet_state(), detector_model_spec, n_trials=n_trials, seed=seed + 20_000)

    four_csv_rows = [
        {
            **row,
            "branch_labels": json.dumps(row["branch_labels"]),
            "exact_weights": json.dumps(row["exact_weights"]),
            "realized_fractions": json.dumps(row["realized_fractions"]),
        }
        for row in front_rows
    ]
    integration_csv_rows = [
        {
            **row,
            "branch_labels": json.dumps(row["branch_labels"]),
            "exact_weights": json.dumps(row["exact_weights"]),
            "empirical_frequencies": json.dumps(row["empirical_frequencies"]),
        }
        for row in integration_rows
    ]
    four_csv = four_dir / "four_branch_summary.csv"
    integration_csv = integration_dir / "integration_summary.csv"
    _write_csv(four_csv, four_csv_rows)
    _write_csv(integration_csv, integration_csv_rows)

    four_json = four_dir / "four_branch_summary.json"
    four_json.write_text(json.dumps({"rows": full_front_runs}, indent=2, default=_json_default) + "\n", encoding="utf-8")
    integration_json = integration_dir / "integration_summary.json"
    integration_json.write_text(json.dumps({"rows": integration_rows, "chsh": chsh_result}, indent=2, default=_json_default) + "\n", encoding="utf-8")

    plot_four_branch_fraction_comparison(front_rows).savefig(four_dir / "exact_vs_realized_four_branch_fractions.png")
    if power_trace_row is not None:
        plot_four_branch_power_traces(power_trace_row).savefig(four_dir / "four_branch_power_traces.png")
    if export_trace_row is not None:
        plot_four_branch_export_envelopes(export_trace_row).savefig(spice_dir / "detector_facing_exported_envelopes.png")
    plot_four_branch_winner_frequency(integration_rows).savefig(integration_dir / "exact_vs_empirical_four_branch_winner_frequencies.png")
    plot_correlator_exact_vs_empirical(integration_rows).savefig(integration_dir / "correlator_exact_vs_empirical.png")
    plot_chsh_exact_vs_empirical(chsh_result).savefig(integration_dir / "chsh_exact_vs_empirical.png")
    plot_four_branch_residual_summary(front_rows, integration_rows, chsh_result).savefig(integration_dir / "residual_error_summary.png")

    export_metrics = (
        finite_export_metrics([np.asarray(export_trace_row["exported_branch_power"][label], dtype=float) for label in export_trace_row["branch_labels"]])
        if export_trace_row is not None
        else {"finite": True, "nonnegative_with_tolerance": True, "min_power_w": 0.0}
    )
    front_aggregate = aggregate_case_error(front_rows)
    integration_aggregate = aggregate_case_error(integration_rows)
    summary_metrics = {
        "front_end_rms_error": float(front_aggregate["rms_error"]),
        "front_end_max_error": float(front_aggregate["max_abs_error"]),
        "winner_rms_error": float(integration_aggregate["rms_error"]),
        "winner_max_error": float(integration_aggregate["max_abs_error"]),
        "correlator_rms_error": float(correlator_rms_error(integration_rows)),
        "chsh_abs_error": float(chsh_result["abs_error"]),
        "mean_decisive_fraction": float(np.mean([row["decisive_fraction"] for row in integration_rows])),
        "export_finite": float(bool(export_metrics["finite"])),
        "export_nonnegative": float(bool(export_metrics["nonnegative_with_tolerance"])),
        "min_export_power_w": float(export_metrics["min_power_w"]),
    }
    acceptance = {
        "front_end_pass": summary_metrics["front_end_rms_error"] < 0.03 and summary_metrics["front_end_max_error"] < 0.05,
        "winner_pass": summary_metrics["winner_rms_error"] < 0.03 and summary_metrics["winner_max_error"] < 0.05,
        "correlator_pass": summary_metrics["correlator_rms_error"] < 0.05,
        "chsh_pass": summary_metrics["chsh_abs_error"] < 0.1,
        "export_stability_pass": bool(export_metrics["finite"] and export_metrics["nonnegative_with_tolerance"]),
    }
    acceptance["proceed_to_next_phase"] = all(acceptance.values())
    acceptance["recommended_next_ticket"] = (
        "Refine the four-branch physical/SPICE candidate toward a less abstract shared-core realization while preserving the frozen boundary."
        if acceptance["proceed_to_next_phase"]
        else "Debug the four-branch physical front-end realization or the frozen boundary coupling before deeper hardware work."
    )

    summary_csv = output_dir / "summary_metrics.csv"
    _write_csv(summary_csv, [{"metric": key, "value": value} for key, value in summary_metrics.items()])

    design_md = output_dir / "front_end_candidate_design.md"
    design_md.write_text(
        "\n".join(
            [
                "# Four-Branch Front-End Candidate Design",
                "",
                "Chosen topology: four explicit Thevenin-loaded output branches driven by a shared-state branch-weight mapper.",
                "",
                "## Why This First Candidate",
                "",
                "- It is the mildest physical/SPICE-style scale-up from the validated two-branch candidate.",
                "- It preserves explicit physical ports, finite source impedance, matched loads, and measurable branch power.",
                "- It keeps the detector+latch boundary frozen and only changes the front-end dimensionality.",
                "",
                "## Mapping To Branch-Power Export",
                "",
                "- Exact reduced-model branch weights are converted into branch source amplitudes proportional to `sqrt(w_k)`.",
                "- Each branch drives a resistive load through finite source impedance, so voltage, current, power, and integrated energy are directly measurable.",
                "- Detector-facing envelopes are exported from those absorbed-power traces using the frozen `piecewise:linear:20.0ms` contract, then scaled by the frozen `4.0x` gain and clipped to the frozen `5.0s` exposure window.",
                "",
                "## Known Limitations",
                "",
                "- The candidate is still a linear controlled-source realization rather than a final shared-core resonant hardware netlist.",
                "- The shared-state preparation is represented through the exact reduced-model branch-weight map rather than a full physical core solve at this stage.",
                "- Detector, latch, drain, and post-click closure hardware remain abstract and unchanged.",
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
                "# Four-Branch SPICE-Facing Interface",
                "",
                "## Circuit Boundary",
                "",
                "- Inputs: reduced shared four-mode state, analyzer settings `(a, b)`.",
                "- Internal block: four controlled branch drivers into finite source impedance and matched branch loads.",
                "- Outputs: branch voltage, current, instantaneous power, absorbed energy, normalized energy fraction, and detector-facing exported envelopes.",
                "",
                "## Frozen Detector Contract",
                "",
                f"- Export mode: `{frozen_export.mode}` with `{frozen_export.piecewise_mode}` bins of `{frozen_export.piecewise_bin_width_s:.3f}s`.",
                f"- Gain: `{frozen_boundary.gain:.1f}x`.",
                f"- Exposure: `{frozen_boundary.exposure_s:.1f}s`.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary_json = output_dir / "summary_metrics.json"
    summary_json.write_text(
        json.dumps(
            {
                "summary_metrics": summary_metrics,
                "acceptance": acceptance,
                "frozen_boundary": {
                    "export_mode": f"{frozen_export.mode}:{frozen_export.piecewise_mode}:{frozen_export.piecewise_bin_width_s * 1e3:.1f}ms",
                    "gain": frozen_boundary.gain,
                    "exposure_s": frozen_boundary.exposure_s,
                },
                "four_branch": {"csv": str(four_csv), "json": str(four_json), "rows": front_rows},
                "integration": {"csv": str(integration_csv), "json": str(integration_json), "rows": integration_rows, "chsh": chsh_result},
                "design_md": str(design_md),
                "spice_facing_interface_md": str(spice_md),
            },
            indent=2,
            default=_json_default,
        )
        + "\n",
        encoding="utf-8",
    )

    outputs = {
        "four_branch_csv": str(four_csv),
        "integration_csv": str(integration_csv),
        "design_md": str(design_md),
        "spice_md": str(spice_md),
    }
    summary_md = output_dir / "summary_report.md"
    summary_md.write_text(_summary_markdown(summary_metrics=summary_metrics, acceptance=acceptance, outputs=outputs) + "\n", encoding="utf-8")
    return {
        "summary_md": str(summary_md),
        "summary_json": str(summary_json),
        "summary_csv": str(summary_csv),
        "four_branch_csv": str(four_csv),
        "integration_csv": str(integration_csv),
        "design_md": str(design_md),
        "spice_facing_interface_md": str(spice_md),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the first four-branch physical/SPICE front-end candidate report.")
    parser.add_argument("--outdir", default="artifacts/physical_front_end_four_branch_candidate")
    parser.add_argument("--detector-next-summary", default="artifacts/detector_next/results_summary.csv")
    parser.add_argument("--trials", type=int, default=4_000)
    args = parser.parse_args()
    build_physical_front_end_four_branch_candidate_report(
        args.outdir,
        detector_next_summary_csv=args.detector_next_summary,
        n_trials=args.trials,
    )


if __name__ == "__main__":
    main()
