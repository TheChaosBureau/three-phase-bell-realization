from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from detector_integration.experiments.run_summary_report import load_top_shot_trigger_spec
from front_end_surrogate.experiments.run_four_branch_surrogate import run_four_branch_surrogate_sweep
from front_end_surrogate.experiments.run_surrogate_integration import run_front_end_surrogate_integration
from front_end_surrogate.experiments.run_two_branch_surrogate import run_two_branch_surrogate_sweep
from front_end_surrogate.export_interface import SurrogateEnvelopeConfig


def _summary_markdown(
    *,
    summary_metrics: dict[str, float],
    detector_spec: dict[str, Any],
    outputs: dict[str, str],
    acceptance: dict[str, bool | str],
) -> str:
    decision = "Proceed to the first physical/SPICE front-end candidate." if acceptance["proceed_to_next_phase"] else "Hold physical SPICE work and debug the surrogate boundary."
    top_row = detector_spec["search_summary_row"]
    return "\n".join(
        [
            "# Front-End Surrogate Summary",
            "",
            "## Surrogate Accuracy",
            "",
            f"- Two-branch RMS energy-fraction error: {summary_metrics['two_branch_rms_error']:.6f}",
            f"- Two-branch max energy-fraction error: {summary_metrics['two_branch_max_error']:.6f}",
            f"- Four-branch RMS energy-fraction error: {summary_metrics['four_branch_rms_error']:.6f}",
            f"- Four-branch max branch error: {summary_metrics['four_branch_max_error']:.6f}",
            f"- Correlator RMS error: {summary_metrics['correlator_rms_error']:.6f}",
            f"- CHSH absolute error: {summary_metrics['chsh_abs_error']:.6f}",
            "",
            "## Detector + Latch Handoff",
            "",
            f"- Integrated two-branch RMS winner-law error: {summary_metrics['integration_two_branch_rms_error']:.6f}",
            f"- Integrated four-branch RMS winner-law error: {summary_metrics['integration_four_branch_rms_error']:.6f}",
            f"- Integrated CHSH absolute error: {summary_metrics['integration_chsh_abs_error']:.6f}",
            "",
            "## Decision Gate",
            "",
            f"- Two-branch surrogate pass: {acceptance['two_branch_surrogate_pass']}",
            f"- Four-branch surrogate pass: {acceptance['four_branch_surrogate_pass']}",
            f"- Correlator pass: {acceptance['correlator_pass']}",
            f"- CHSH pass: {acceptance['chsh_pass']}",
            f"- Handoff pass: {acceptance['handoff_pass']}",
            f"- Decision: {decision}",
            f"- Next ticket: {acceptance['recommended_next_ticket']}",
            "",
            "## Detector Reference",
            "",
            f"- Source summary: `{outputs['detector_next_summary_csv']}`",
            f"- Search score: {float(top_row['score']):.6f}",
            f"- Model params: `{json.dumps(detector_spec['model_params'], sort_keys=True)}`",
            "",
            "## Artifacts",
            "",
            f"- Two-branch summary: `{outputs['two_branch_csv']}`",
            f"- Four-branch summary: `{outputs['four_branch_csv']}`",
            f"- Integration summary: `{outputs['integration_csv']}`",
            f"- SPICE-facing interface: `{outputs['spice_interface_md']}`",
            "",
        ]
    )


def build_front_end_surrogate_report(
    outdir: str | Path = "artifacts/front_end_surrogate",
    *,
    detector_next_summary_csv: str | Path = "artifacts/detector_next/results_summary.csv",
    n_two_branch_trials: int = 2_500,
    n_four_branch_trials: int = 4_000,
    seed: int = 20260402,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)
    detector_spec = load_top_shot_trigger_spec(detector_next_summary_csv)
    envelope_config = SurrogateEnvelopeConfig()

    two_outputs = run_two_branch_surrogate_sweep(output_dir / "two_branch", envelope_config=asdict(envelope_config))
    four_outputs = run_four_branch_surrogate_sweep(output_dir / "four_branch", envelope_config=asdict(envelope_config))
    integration_outputs = run_front_end_surrogate_integration(
        output_dir / "integration",
        detector_next_summary_csv=detector_next_summary_csv,
        n_two_branch_trials=n_two_branch_trials,
        n_four_branch_trials=n_four_branch_trials,
        envelope_config=asdict(envelope_config),
        seed=seed,
    )

    two_rms = float(np.sqrt(np.mean([float(row["rms_error"]) ** 2 for row in two_outputs["rows"]])))
    two_max = float(np.max([float(row["max_abs_error"]) for row in two_outputs["rows"]]))
    four_rms = float(np.sqrt(np.mean([float(row["rms_error"]) ** 2 for row in four_outputs["rows"]])))
    four_max = float(np.max([float(row["max_abs_error"]) for row in four_outputs["rows"]]))
    correlator_rms = float(np.sqrt(np.mean([float(row["correlator_error"]) ** 2 for row in four_outputs["rows"]])))

    integration_two_rows = [row for row in integration_outputs["rows"] if row["mode"] == "two_branch"]
    integration_four_rows = [row for row in integration_outputs["rows"] if row["mode"] == "four_branch"]

    summary_metrics = {
        "two_branch_rms_error": two_rms,
        "two_branch_max_error": two_max,
        "four_branch_rms_error": four_rms,
        "four_branch_max_error": four_max,
        "correlator_rms_error": correlator_rms,
        "chsh_abs_error": float(four_outputs["chsh"]["abs_error"]),
        "integration_two_branch_rms_error": float(np.sqrt(np.mean([float(row["rms_error"]) ** 2 for row in integration_two_rows]))),
        "integration_four_branch_rms_error": float(np.sqrt(np.mean([float(row["rms_error"]) ** 2 for row in integration_four_rows]))),
        "integration_chsh_abs_error": float(integration_outputs["chsh"]["abs_error"]),
    }

    acceptance = {
        "two_branch_surrogate_pass": summary_metrics["two_branch_rms_error"] < 0.02 and summary_metrics["two_branch_max_error"] < 0.05,
        "four_branch_surrogate_pass": summary_metrics["four_branch_rms_error"] < 0.03 and summary_metrics["four_branch_max_error"] < 0.05,
        "correlator_pass": summary_metrics["correlator_rms_error"] < 0.05,
        "chsh_pass": abs(abs(four_outputs["chsh"]["surrogate_s"]) - 2.0 * math.sqrt(2.0)) < 0.1,
        "handoff_pass": summary_metrics["integration_two_branch_rms_error"] < 0.02
        and summary_metrics["integration_four_branch_rms_error"] < 0.03
        and summary_metrics["integration_chsh_abs_error"] < 0.1,
    }
    acceptance["proceed_to_next_phase"] = all(
        [
            acceptance["two_branch_surrogate_pass"],
            acceptance["four_branch_surrogate_pass"],
            acceptance["correlator_pass"],
            acceptance["chsh_pass"],
            acceptance["handoff_pass"],
        ]
    )
    acceptance["recommended_next_ticket"] = (
        "Design the first physical/SPICE front-end implementation candidate and connect it to the frozen detector+latch abstraction."
        if acceptance["proceed_to_next_phase"]
        else "Debug the SPICE-facing front-end surrogate before attempting a physical implementation candidate."
    )

    summary_csv = output_dir / "summary_metrics.csv"
    with summary_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows([{"metric": key, "value": value} for key, value in summary_metrics.items()])

    spice_dir = output_dir / "spice_facing"
    spice_dir.mkdir(parents=True, exist_ok=True)
    spice_interface_md = spice_dir / "spice_facing_interface.md"
    spice_interface_md.write_text(
        "\n".join(
            [
                "# SPICE-Facing Front-End Interface",
                "",
                "Implementation path: Option A behavioral surrogate.",
                "",
                "## Export Contract",
                "",
                "For each run the surrogate exports:",
                "",
                "```python",
                "{",
                '    "branch_labels": [...],',
                '    "time_s": [...],',
                '    "branch_voltage_v": {label: [...]},',
                '    "branch_current_a": {label: [...]},',
                '    "branch_power_w": {label: [...]},',
                '    "branch_energy_j": {label: float},',
                '    "branch_energy_fraction": {label: float},',
                '    "exact_weight": {label: float},',
                "}",
                "```",
                "",
                "## Detector Handoff",
                "",
                "The detector layer consumes each branch as a sampled absorbed-power envelope with `kind=\"sampled\"`, `time_s`, and `power_w` arrays. The abstract detector model then emits first-pulse times into the validated winner latch.",
                "",
                f"- Common envelope: `{json.dumps(asdict(envelope_config), sort_keys=True)}`",
                f"- Detector params: `{json.dumps(detector_spec['model_params'], sort_keys=True)}`",
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
                "two_branch": two_outputs,
                "four_branch": four_outputs,
                "integration": {
                    "csv": integration_outputs["csv"],
                    "plot": integration_outputs["plot"],
                    "chsh": integration_outputs["chsh"],
                },
                "spice_facing_interface": str(spice_interface_md),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    outputs = {
        "detector_next_summary_csv": str(detector_next_summary_csv),
        "two_branch_csv": two_outputs["csv"],
        "four_branch_csv": four_outputs["csv"],
        "integration_csv": integration_outputs["csv"],
        "spice_interface_md": str(spice_interface_md),
    }
    summary_md = output_dir / "summary_report.md"
    summary_md.write_text(_summary_markdown(summary_metrics=summary_metrics, detector_spec=detector_spec, outputs=outputs, acceptance=acceptance) + "\n", encoding="utf-8")

    return {
        "summary_md": str(summary_md),
        "summary_json": str(summary_json),
        "summary_csv": str(summary_csv),
        "two_branch_csv": two_outputs["csv"],
        "four_branch_csv": four_outputs["csv"],
        "integration_csv": integration_outputs["csv"],
        "spice_facing_interface_md": str(spice_interface_md),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the SPICE-facing linear front-end surrogate report.")
    parser.add_argument("--outdir", default="artifacts/front_end_surrogate")
    parser.add_argument("--detector-next-summary", default="artifacts/detector_next/results_summary.csv")
    parser.add_argument("--two-branch-trials", type=int, default=2_500)
    parser.add_argument("--four-branch-trials", type=int, default=4_000)
    args = parser.parse_args()
    build_front_end_surrogate_report(
        args.outdir,
        detector_next_summary_csv=args.detector_next_summary,
        n_two_branch_trials=args.two_branch_trials,
        n_four_branch_trials=args.four_branch_trials,
    )


if __name__ == "__main__":
    main()
