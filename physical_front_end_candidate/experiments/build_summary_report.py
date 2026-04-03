from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from detector_integration.experiments.run_summary_report import load_top_shot_trigger_spec

from physical_front_end_candidate.export_interface import detector_export_from_power, resolve_envelope_config
from physical_front_end_candidate.integration import run_two_branch_physical_handoff
from physical_front_end_candidate.metrics import finite_export_metrics
from physical_front_end_candidate.plots import (
    plot_error_summary,
    plot_export_comparison,
    plot_fraction_comparison,
    plot_power_envelopes,
    plot_winner_frequency,
)
from physical_front_end_candidate.two_branch_candidate import representative_physical_cases, simulate_two_branch_physical_candidate


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


def build_physical_front_end_candidate_report(
    outdir: str | Path = "artifacts/physical_front_end_candidate",
    *,
    detector_next_summary_csv: str | Path = "artifacts/detector_next/results_summary.csv",
    n_trials: int = 500,
    seed: int = 20260402,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    two_dir = output_dir / "two_branch"
    integration_dir = output_dir / "integration"
    spice_dir = output_dir / "spice_facing"
    two_dir.mkdir(parents=True, exist_ok=True)
    integration_dir.mkdir(parents=True, exist_ok=True)
    spice_dir.mkdir(parents=True, exist_ok=True)

    detector_spec = load_top_shot_trigger_spec(detector_next_summary_csv)
    detector_model_spec = {"family": detector_spec["family"], "model_params": dict(detector_spec["model_params"])}

    two_rows: list[dict[str, Any]] = []
    power_rows: list[dict[str, Any]] = []
    full_runs: list[dict[str, Any]] = []
    export_examples: list[dict[str, Any]] = []

    for case in representative_physical_cases():
        result = simulate_two_branch_physical_candidate(case["state"], case["analyzer"])
        full_runs.append({"case": case["case"], **result})
        time_s = result["time_s"]
        export = detector_export_from_power(result["branch_power_w"], branch_labels=result["branch_labels"], envelope_config=resolve_envelope_config(result["envelope_config"]))

        peak_1 = export[0]["power_scale"] * np.exp(-np.asarray(time_s) / export[0]["decay_tau"])
        peak_2 = export[1]["power_scale"] * np.exp(-np.asarray(time_s) / export[1]["decay_tau"])
        export_examples.append(
            {
                "case": case["case"],
                "time_s": time_s,
                "branch_power_1": result["branch_power_w"]["branch_1"],
                "branch_power_2": result["branch_power_w"]["branch_2"],
                "export_power_1": peak_1.tolist(),
                "export_power_2": peak_2.tolist(),
            }
        )

        two_rows.append(
            {
                "case": case["case"],
                "exact_p1": result["exact_weight"]["branch_1"],
                "realized_p1": result["branch_energy_fraction"]["branch_1"],
                "exact_p2": result["exact_weight"]["branch_2"],
                "realized_p2": result["branch_energy_fraction"]["branch_2"],
                "rms_error": result["metrics"]["rms_error"],
                "max_abs_error": result["metrics"]["max_abs_error"],
                "energy_sum": result["branch_energy_fraction"]["branch_1"] + result["branch_energy_fraction"]["branch_2"],
            }
        )

        for index, time_value in enumerate(time_s):
            power_rows.append(
                {
                    "case": case["case"],
                    "time_s": time_value,
                    "branch_power_1_w": result["branch_power_w"]["branch_1"][index],
                    "branch_power_2_w": result["branch_power_w"]["branch_2"][index],
                }
            )

        envelope_path = spice_dir / f"{case['case']}_exported_envelopes.csv"
        envelope_rows = [
            {
                "time_s": time_s[index],
                "branch_power_1_w": result["branch_power_w"]["branch_1"][index],
                "branch_power_2_w": result["branch_power_w"]["branch_2"][index],
                "detector_export_1_w": peak_1[index],
                "detector_export_2_w": peak_2[index],
            }
            for index in range(len(time_s))
        ]
        _write_csv(envelope_path, envelope_rows)

    two_summary_csv = two_dir / "two_branch_summary.csv"
    _write_csv(two_summary_csv, two_rows)
    branch_energy_csv = two_dir / "branch_energy_summary.csv"
    _write_csv(branch_energy_csv, power_rows)
    (two_dir / "two_branch_summary.json").write_text(
        json.dumps({"rows": full_runs}, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )

    fraction_plot = two_dir / "exact_vs_physical_fractions.png"
    plot_fraction_comparison(two_rows).savefig(fraction_plot)
    power_plot = two_dir / "branch_power_envelopes.png"
    plot_power_envelopes(export_examples).savefig(power_plot)
    export_plot = spice_dir / "detector_export_comparison.png"
    plot_export_comparison(export_examples[0]).savefig(export_plot)
    error_plot = two_dir / "residual_error_summary.png"
    plot_error_summary(two_rows).savefig(error_plot)

    integration_rows: list[dict[str, Any]] = []
    full_integration: list[dict[str, Any]] = []
    for index, case in enumerate(representative_physical_cases()):
        result = run_two_branch_physical_handoff(
            case["state"],
            case["analyzer"],
            detector_model_spec,
            n_trials=n_trials,
            seed=seed + 97 * index,
        )
        full_integration.append({"case": case["case"], **result})
        integration_rows.append(
            {
                "case": case["case"],
                "exact_p1": float(result["exact_weights"][0]),
                "empirical_p1": float(result["empirical_frequencies"][0]),
                "exact_p2": float(result["exact_weights"][1]),
                "empirical_p2": float(result["empirical_frequencies"][1]),
                "rms_error": float(result["metrics"]["rms_error"]),
                "max_abs_error": float(result["metrics"]["max_abs_error"]),
                "decisive_fraction": float(result["decisive_fraction"]),
            }
        )

    integration_csv = integration_dir / "integration_summary.csv"
    _write_csv(integration_csv, integration_rows)
    (integration_dir / "integration_summary.json").write_text(
        json.dumps({"rows": full_integration}, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    winner_plot = integration_dir / "winner_frequency_vs_target.png"
    plot_winner_frequency(integration_rows).savefig(winner_plot)

    rms_error = float(np.sqrt(np.mean([row["rms_error"] ** 2 for row in two_rows])))
    max_error = float(np.max([row["max_abs_error"] for row in two_rows]))
    integration_rms = float(np.sqrt(np.mean([row["rms_error"] ** 2 for row in integration_rows])))
    integration_max = float(np.max([row["max_abs_error"] for row in integration_rows]))
    export_metrics = finite_export_metrics([run["branch_power_w"][label] for run in full_runs for label in run["branch_labels"]])
    summary_metrics = {
        "two_branch_rms_error": rms_error,
        "two_branch_max_error": max_error,
        "integrated_rms_error": integration_rms,
        "integrated_max_error": integration_max,
        "finite_export_pass": bool(export_metrics["finite"] and export_metrics["nonnegative_with_tolerance"]),
        "min_export_power_w": float(export_metrics["min_power_w"]),
    }
    acceptance = {
        "two_branch_pass": rms_error < 0.03 and max_error < 0.05,
        "integration_pass": integration_rms < 0.03 and integration_max < 0.05,
        "stability_pass": bool(export_metrics["finite"] and export_metrics["nonnegative_with_tolerance"]),
    }
    acceptance["proceed_to_next_phase"] = all(acceptance.values())
    acceptance["recommended_next_ticket"] = (
        "Extend the physical/SPICE front-end candidate toward the four-branch shared-state case, or design the first explicit resonant front-end implementation candidate."
        if acceptance["proceed_to_next_phase"]
        else "Iterate on the two-branch physical front-end candidate before scaling up."
    )

    summary_csv = output_dir / "summary_metrics.csv"
    _write_csv(summary_csv, [{"metric": key, "value": value} for key, value in summary_metrics.items()])

    design_md = output_dir / "front_end_candidate_design.md"
    design_md.write_text(
        "\n".join(
            [
                "# Front-End Candidate Design",
                "",
                "Chosen option: Option A, SPICE linear subcircuit with physical ports.",
                "",
                "## Topology",
                "",
                "- Two preparation/source ports encode the normalized state amplitudes.",
                "- An analyzer rotation matrix maps those source amplitudes into two branch drive phasors.",
                "- Each branch is realized as a Thevenin source driving a matched resistive load through a finite source resistance.",
                "- Branch voltage, current, instantaneous power, and absorbed energy are measured at the load.",
                "",
                "## Why This Candidate",
                "",
                "- It is the simplest physically interpretable linear circuit candidate that still has explicit measurable ports.",
                "- It preserves the frozen detector/latch abstraction boundary by exporting only branch power envelopes.",
                "- It is SPICE-compatible because the same behavior can be represented with controlled sources, source impedances, and resistive loads.",
                "",
                "## Mapping To Envelope Export",
                "",
                "- The common drive envelope multiplies the branch Thevenin source amplitudes.",
                "- The load power traces are exported directly, then compressed into detector-facing exponential envelopes for the frozen abstract detector layer.",
                "",
                "## Known Limitations",
                "",
                "- This first candidate is still quasi-static and envelope-level rather than a full resonant LC realization.",
                "- Only the two-branch case is implemented in this ticket.",
                "- No physical detector, latch, or drain hardware is modeled here.",
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
                "# Physical Front-End SPICE-Facing Interface",
                "",
                "## Circuit Boundary",
                "",
                "- Inputs: normalized two-mode state preparation amplitudes and analyzer setting.",
                "- Internal block: analyzer-controlled Thevenin branch drivers with finite source impedance into matched resistive loads.",
                "- Outputs: branch voltage, current, instantaneous power, absorbed energy, and detector-facing power envelopes.",
                "",
                "## Detector Export Contract",
                "",
                "Each branch is exported to the frozen detector layer as an `exp_decay` envelope with:",
                "",
                "- `power_scale`: branch peak absorbed power",
                "- `decay_tau`: shared envelope decay constant",
                "- `dt`: detector-side integration step",
                "- `t_max`: envelope duration",
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
                "two_branch_csv": str(two_summary_csv),
                "integration_csv": str(integration_csv),
                "design_md": str(design_md),
                "spice_facing_interface_md": str(spice_md),
            },
            indent=2,
            default=_json_default,
        )
        + "\n",
        encoding="utf-8",
    )

    summary_md = output_dir / "summary_report.md"
    summary_md.write_text(
        "\n".join(
            [
                "# Physical Front-End Candidate Summary",
                "",
                f"- Two-branch RMS energy-fraction error: {rms_error:.6f}",
                f"- Two-branch max energy-fraction error: {max_error:.6f}",
                f"- Integrated RMS winner-law error: {integration_rms:.6f}",
                f"- Integrated max winner-law error: {integration_max:.6f}",
                f"- Proceed to next phase: {acceptance['proceed_to_next_phase']}",
                f"- Next ticket: {acceptance['recommended_next_ticket']}",
                "",
                "## Artifacts",
                "",
                f"- Two-branch summary: `{two_summary_csv}`",
                f"- Integration summary: `{integration_csv}`",
                f"- Design note: `{design_md}`",
                f"- SPICE-facing interface: `{spice_md}`",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "summary_md": str(summary_md),
        "summary_json": str(summary_json),
        "summary_csv": str(summary_csv),
        "two_branch_csv": str(two_summary_csv),
        "integration_csv": str(integration_csv),
        "design_md": str(design_md),
        "spice_facing_interface_md": str(spice_md),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the first physical/SPICE front-end candidate report.")
    parser.add_argument("--outdir", default="artifacts/physical_front_end_candidate")
    parser.add_argument("--detector-next-summary", default="artifacts/detector_next/results_summary.csv")
    parser.add_argument("--trials", type=int, default=500)
    args = parser.parse_args()
    build_physical_front_end_candidate_report(
        args.outdir,
        detector_next_summary_csv=args.detector_next_summary,
        n_trials=args.trials,
    )


if __name__ == "__main__":
    main()
