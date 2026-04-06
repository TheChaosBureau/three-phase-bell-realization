from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from physical_front_end_candidate.actual_spice_front_end import run_actual_spice_front_end_benchmark
from physical_front_end_candidate.actual_spice_front_end_plots import (
    plot_spice_branch_current,
    plot_spice_branch_power,
    plot_spice_branch_voltage,
    plot_spice_candidate_comparison,
    plot_spice_case_comparison,
    plot_spice_chsh,
    plot_spice_correlator,
    plot_spice_exact_vs_fraction,
    plot_spice_netlist_topology,
    plot_spice_residual_summary,
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
    comparison_rows = {row["candidate"]: row for row in summary["comparison_rows"]}
    decision = (
        "Proceed to the first downstream handoff milestone driven from actual SPICE-generated front-end traces."
        if bool(metrics["proceed_to_next_phase"])
        else "Iterate on the actual SPICE front-end translation before moving downstream."
    )
    return "\n".join(
        [
            "# Actual SPICE Front-End Summary",
            "",
            "## Architecture",
            "",
            "- Chosen direction: Option C hybrid preparation wrapper around an actual ngspice-transient shared front-end netlist.",
            f"- SPICE engine: {summary['probe_rows'][0]['engine'] if summary['probe_rows'] else 'unknown'}",
            f"- Engine library: {summary['probe_rows'][0]['engine_library'] if summary['probe_rows'] else 'unknown'}",
            "- Shared-core front-end is an actual R/L/C/coupling netlist executed through PySpice + ngspice.",
            "- Detector, latch, and closure/drain remain frozen and external for this milestone.",
            "",
            "## Front-End Fidelity",
            "",
            f"- SPICE-vs-current-baseline RMS error: {float(metrics['front_end_fraction_rms_error']):.6f}",
            f"- SPICE-vs-current-baseline max error: {float(metrics['front_end_fraction_max_error']):.6f}",
            f"- Exact-vs-SPICE RMS error: {float(metrics['exact_fraction_rms_error']):.6f}",
            f"- Exact-vs-SPICE max error: {float(metrics['exact_fraction_max_error']):.6f}",
            f"- Front-end pass: {bool(metrics['front_end_fraction_pass'])}",
            "",
            "## Front-End Correlator / CHSH",
            "",
            f"- Correlator RMS error: {float(metrics['correlator_rms_error']):.6f}",
            f"- CHSH absolute error: {float(metrics['chsh_abs_error']):.6f}",
            f"- Correlator pass: {bool(metrics['correlator_pass'])}",
            f"- CHSH pass: {bool(metrics['chsh_pass'])}",
            "",
            "## Execution / Probeability",
            "",
            f"- Actual SPICE execution pass: {bool(metrics['actual_spice_execution_pass'])}",
            f"- Finite output pass: {bool(metrics['finite_output_pass'])}",
            f"- Probeability pass: {bool(metrics['probeability_pass'])}",
            f"- Architectural explicitness pass: {bool(metrics['architecture_explicitness_pass'])}",
            f"- No trivial exact-weight fallback: {bool(metrics['no_trivial_exact_weight_assignment'])}",
            "",
            "## Baseline Comparison",
            "",
            f"- Frozen preferred-chain note: {comparison_rows['current_preferred_chain_device_physicalization_front_end']['architecture_note']}",
            f"- Actual SPICE note: {comparison_rows['actual_spice_front_end']['architecture_note']}",
            f"- Candidate comparison CSV: `{outputs['candidate_comparison_csv']}`",
            "",
            "## Decision",
            "",
            f"- Proceed to next phase: {bool(metrics['proceed_to_next_phase'])}",
            f"- Decision: {decision}",
            "",
            "## Artifacts",
            "",
            f"- Netlist artifacts: `{outputs['netlist_dir']}`",
            f"- Raw waveform artifacts: `{outputs['raw_waveforms_dir']}`",
            f"- Processed trace artifacts: `{outputs['processed_traces_dir']}`",
            f"- Front-end metrics artifacts: `{outputs['front_end_metrics_dir']}`",
            f"- Design note: `{outputs['design_md']}`",
            "",
        ]
    )


def _design_note_markdown(*, summary: dict[str, Any]) -> str:
    metrics = summary["summary_metrics"]
    example = summary["example_front_end"] or {}
    engine = example.get("spice", {}).get("engine", "PySpice+ngspice")
    library = example.get("spice", {}).get("engine_library", "unknown")
    return "\n".join(
        [
            "# Actual SPICE Front-End Design Note",
            "",
            "## Chosen SPICE Engine",
            "",
            f"- Engine: {engine}",
            f"- Dynamic library: {library}",
            "- Execution path: PySpice transient simulation backed by a real ngspice shared library.",
            "",
            "## Chosen Netlist Architecture",
            "",
            "- Option C hybrid architecture.",
            "- Shared preparation remains scripted, but the shared front-end itself is executed as an actual SPICE R/L/C/coupling netlist.",
            "- Four branch outputs are exposed as explicit probe nodes driven by behavioral analyzer/readout mixing sources and terminated with explicit load/readout elements.",
            "",
            "## How Preparation Is Represented",
            "",
            "- The validated shared-core preparation still provides the drive-frequency and source phasors.",
            "- Those phasors are translated into explicit sinusoidal current injections that drive the shared SPICE core through the same source-impedance interpretation used in the preferred explicit-netlist candidate.",
            "",
            "## How Analyzer Dependence Is Represented",
            "",
            "- The Alice/Bob analyzer dependence is represented by a netlisted behavioral readout stage attached to the SPICE core nodes.",
            "- For this first milestone, the time-domain behavioral stage uses the real projection of the validated analyzer/readout matrix so the result remains directly runnable in ngspice.",
            "",
            "## How The Four Branches Are Measured",
            "",
            "- Probe nodes: `out_pp`, `out_pm`, `out_mp`, `out_mm`.",
            "- Branch voltage is measured directly at each output node.",
            "- Branch current is computed directly through the attached load resistor as `V/R`.",
            "- Branch power is `V*I` and branch energy is the transient integral over the measurement window.",
            "",
            "## What Remains Abstract Outside The Netlist",
            "",
            "- Detector, latch, and closure/drain are not migrated into SPICE in this ticket.",
            "- The frozen downstream boundary contract is preserved conceptually, but this milestone archives raw and processed SPICE traces rather than forcing a detector-boundary replay inside the same ticket.",
            "",
            "## First-Milestone Compromises",
            "",
            "- The preparation and analyzer mapping are still wrapped around the SPICE core rather than being derived from a fully device-complete upstream and analyzer electronics netlist.",
            "- The analyzer/readout stage uses behavioral sources to make the mapping explicit and probeable without yet committing to a final passive-only implementation.",
            "- The result is intentionally a first real-SPICE execution milestone, not a fabrication-ready circuit.",
            "",
            "## Current Outcome",
            "",
            f"- Front-end pass: {bool(metrics['front_end_fraction_pass'])}",
            f"- Correlator pass: {bool(metrics['correlator_pass'])}",
            f"- CHSH pass: {bool(metrics['chsh_pass'])}",
            f"- Actual SPICE execution pass: {bool(metrics['actual_spice_execution_pass'])}",
            f"- Probeability pass: {bool(metrics['probeability_pass'])}",
            f"- Architectural explicitness pass: {bool(metrics['architecture_explicitness_pass'])}",
            "",
        ]
    )


def build_actual_spice_front_end_report(
    outdir: str | Path = "artifacts/actual_spice_front_end",
    *,
    case_names: Sequence[str] | None = None,
    verbose_progress: bool = False,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    netlist_dir = output_dir / "netlist"
    raw_waveforms_dir = output_dir / "raw_waveforms"
    processed_traces_dir = output_dir / "processed_traces"
    front_end_metrics_dir = output_dir / "front_end_metrics"
    for directory in (netlist_dir, raw_waveforms_dir, processed_traces_dir, front_end_metrics_dir):
        directory.mkdir(parents=True, exist_ok=True)

    summary = run_actual_spice_front_end_benchmark(case_names=case_names, verbose_progress=verbose_progress)

    front_end_csv = front_end_metrics_dir / "front_end_summary.csv"
    probe_csv = front_end_metrics_dir / "spice_probe_summary.csv"
    case_comparison_csv = front_end_metrics_dir / "case_comparison_summary.csv"
    energy_summary_csv = processed_traces_dir / "branch_energy_summary.csv"
    candidate_comparison_csv = output_dir / "candidate_comparison.csv"

    _write_csv(front_end_csv, list(summary["front_end_rows"]))
    _write_csv(probe_csv, list(summary["probe_rows"]))
    _write_csv(case_comparison_csv, list(summary["case_comparison_rows"]))
    _write_csv(
        energy_summary_csv,
        [
            {
                "case": row["case"],
                "a_deg": row["a_deg"],
                "b_deg": row["b_deg"],
                "exact_weights_json": json.dumps(row["exact_weights"]),
                "baseline_fractions_json": json.dumps(row["baseline_fractions"]),
                "realized_fractions_json": json.dumps(row["realized_fractions"]),
                "rms_error": row["rms_error"],
                "max_abs_error": row["max_abs_error"],
            }
            for row in summary["front_end_rows"]
        ],
    )
    _write_csv(candidate_comparison_csv, list(summary["comparison_rows"]))

    for entry in summary["case_results"]:
        case_name = str(entry["case"]["case"])
        case_slug = case_name.replace("/", "_")
        result = entry["result"]
        netlist_path = netlist_dir / f"{case_slug}.cir"
        netlist_path.write_text(str(result["spice"]["netlist_text"]) + "\n", encoding="utf-8")

        raw_time = list(result["raw_waveforms"]["time_s"])
        _write_csv(
            raw_waveforms_dir / f"{case_slug}_raw_waveforms.csv",
            [
                {
                    "time_s": raw_time[index],
                    **{f"core_{label}_v": result["raw_waveforms"]["core_node_voltage_v"][label][index] for label in result["branch_labels"]},
                    **{f"out_{label}_v": result["raw_waveforms"]["output_node_voltage_v"][label][index] for label in result["branch_labels"]},
                    **{f"src_{label}_a": result["raw_waveforms"]["source_current_a"][label][index] for label in result["branch_labels"]},
                }
                for index in range(len(raw_time))
            ],
        )

        processed_time = list(result["time_s"])
        _write_csv(
            processed_traces_dir / f"{case_slug}_processed_traces.csv",
            [
                {
                    "time_s": processed_time[index],
                    **{f"{label}_voltage_v": result["branch_voltage_v"][label][index] for label in result["branch_labels"]},
                    **{f"{label}_current_a": result["branch_current_a"][label][index] for label in result["branch_labels"]},
                    **{f"{label}_power_w": result["branch_power_w"][label][index] for label in result["branch_labels"]},
                    **{
                        f"{label}_cumulative_energy_j": result["processed_traces"]["cumulative_branch_energy_j"][label][index]
                        for label in result["branch_labels"]
                    },
                }
                for index in range(len(processed_time))
            ],
        )
        _write_csv(
            processed_traces_dir / f"{case_slug}_detector_handoff_trace.csv",
            [
                {
                    "time_s": processed_time[index],
                    **{f"{label}_power_w": result["branch_power_w"][label][index] for label in result["branch_labels"]},
                }
                for index in range(len(processed_time))
            ],
        )

    if summary["example_front_end"] is not None:
        example = dict(summary["example_front_end"])
        plot_spice_netlist_topology(example).savefig(front_end_metrics_dir / "netlist_topology_node_map.png")
        plot_spice_branch_voltage(example).savefig(front_end_metrics_dir / "representative_branch_voltage_traces.png")
        plot_spice_branch_current(example).savefig(front_end_metrics_dir / "representative_branch_current_traces.png")
        plot_spice_branch_power(example).savefig(front_end_metrics_dir / "representative_branch_power_traces.png")

    plot_spice_exact_vs_fraction(list(summary["front_end_rows"])).savefig(
        front_end_metrics_dir / "exact_vs_spice_branch_energy_fractions.png"
    )
    plot_spice_case_comparison(list(summary["case_comparison_rows"])).savefig(
        front_end_metrics_dir / "benchmark_case_comparison_summary.png"
    )
    plot_spice_residual_summary(list(summary["front_end_rows"])).savefig(
        front_end_metrics_dir / "residual_error_summary.png"
    )
    plot_spice_candidate_comparison(list(summary["comparison_rows"])).savefig(
        output_dir / "comparison_vs_current_preferred_chain.png"
    )
    plot_spice_correlator(list(summary["front_end_rows"])).savefig(
        front_end_metrics_dir / "correlator_exact_vs_spice.png"
    )
    if bool(summary["chsh_result"]["available"]):
        plot_spice_chsh(dict(summary["chsh_result"])).savefig(front_end_metrics_dir / "chsh_exact_vs_spice.png")

    summary_csv = output_dir / "summary_metrics.csv"
    _write_csv(summary_csv, [{"metric": key, "value": value} for key, value in summary["summary_metrics"].items()])

    summary_json = output_dir / "summary_metrics.json"
    summary_json.write_text(
        json.dumps(
            {
                "summary_metrics": summary["summary_metrics"],
                "front_end_rows": summary["front_end_rows"],
                "probe_rows": summary["probe_rows"],
                "case_comparison_rows": summary["case_comparison_rows"],
                "comparison_rows": summary["comparison_rows"],
                "chsh_result": summary["chsh_result"],
                "example_front_end": summary["example_front_end"],
            },
            indent=2,
            default=_json_default,
        )
        + "\n",
        encoding="utf-8",
    )

    outputs = {
        "netlist_dir": str(netlist_dir),
        "raw_waveforms_dir": str(raw_waveforms_dir),
        "processed_traces_dir": str(processed_traces_dir),
        "front_end_metrics_dir": str(front_end_metrics_dir),
        "front_end_csv": str(front_end_csv),
        "probe_csv": str(probe_csv),
        "case_comparison_csv": str(case_comparison_csv),
        "energy_summary_csv": str(energy_summary_csv),
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
    parser = argparse.ArgumentParser(description="Build the actual SPICE front-end report.")
    parser.add_argument("--outdir", default="artifacts/actual_spice_front_end")
    parser.add_argument("--case", action="append", dest="case_names", default=None)
    parser.add_argument("--quiet-progress", action="store_true")
    args = parser.parse_args()
    build_actual_spice_front_end_report(
        outdir=args.outdir,
        case_names=args.case_names,
        verbose_progress=not args.quiet_progress,
    )


if __name__ == "__main__":
    main()
