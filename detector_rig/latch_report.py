from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from detector_rig.config import (
    DEFAULT_DETECTOR_RIG_CONFIG,
    DEFAULT_LATCH_RIG_CONFIG,
    DetectorRigConfig,
    LatchRigConfig,
)
from detector_rig.latch import (
    build_timing_case_rows,
    simulate_exclusivity_suite,
    simulate_first_arrival_suite,
    simulate_race_with_latch,
    simulate_reset_suite,
    summarize_latch_interface,
)
from detector_rig.latch_hardware import write_latch_hardware_deliverables
from detector_rig.plots import plot_latch_race_comparison, plot_race_summary, plot_reset_cycle_stability
from detector_rig.sim import build_matched_cell_pair


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Cannot write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _save_figure(path: Path, figure) -> str:
    figure.savefig(path)
    return str(path)


def _summary_markdown(
    *,
    latch_config: LatchRigConfig,
    interface_metrics: dict[str, float],
    first_arrival_metrics: dict[str, float | str],
    exclusivity_metrics: dict[str, float],
    reset_metrics: dict[str, float],
    race_metrics: dict[str, float],
    acceptance: dict[str, bool | str],
    hardware_paths: dict[str, str],
    artifact_paths: dict[str, str],
) -> str:
    decision = (
        "Proceed to latch-enabled front-end integration and SPICE-facing abstraction."
        if acceptance["proceed_to_next_phase"]
        else "Hold front-end integration and revise the latch design."
    )
    return "\n".join(
        [
            "# Winner Latch Rig Summary",
            "",
            "## Logic Contract",
            "",
            "- First valid detector pulse captures the winner and masks the rival until reset.",
            f"- Deterministic tie rule inside +/-{latch_config.tie_window_ns:.2f} ns: `{latch_config.tie_break_priority}` wins.",
            f"- Reset holdoff: {latch_config.rearm_holdoff_us:.2f} us after a {latch_config.reset_pulse_ns:.2f} ns reset pulse.",
            "",
            "## Detector / Latch Interface",
            "",
            f"- Minimum threshold margin: {interface_metrics['min_threshold_margin_v']:.3f} V.",
            f"- Minimum pulse-width margin: {interface_metrics['min_width_margin_ns']:.3f} ns.",
            f"- Added timing jitter from latch input loading: {interface_metrics['input_load_added_jitter_ns']:.3f} ns.",
            "",
            "## First Arrival And Exclusivity",
            "",
            f"- Ordered-case winner accuracy: {100.0 * float(first_arrival_metrics['ordered_capture_accuracy']):.4f}%.",
            f"- Tie-region width: {float(first_arrival_metrics['tie_region_width_ns']):.3f} ns.",
            f"- Double-winner count: {int(first_arrival_metrics['double_winner_count'])}.",
            f"- Masked-rival fraction: {100.0 * exclusivity_metrics['masked_rival_fraction']:.3f}%.",
            f"- Hold success fraction: {100.0 * exclusivity_metrics['hold_success_fraction']:.3f}%.",
            "",
            "## Reset / Re-Arm",
            "",
            f"- Reset success fraction: {100.0 * reset_metrics['reset_success_fraction']:.3f}%.",
            f"- Re-arm latency: {reset_metrics['rearm_latency_us']:.4f} us.",
            f"- Retained-memory count: {int(reset_metrics['retained_memory_count'])}.",
            f"- Post-reset bias drift: {reset_metrics['post_reset_bias_drift']:.5f}.",
            "",
            "## Race Transparency",
            "",
            f"- Baseline race RMS error: {race_metrics['baseline_race_rms_error']:.5f}.",
            f"- Latch-attached race RMS error: {race_metrics['latch_race_rms_error']:.5f}.",
            f"- Added RMS error: {race_metrics['added_race_rms_error']:.5f}.",
            f"- Max branch bias shift: {race_metrics['max_branch_bias_shift']:.5f}.",
            f"- Max decisive-fraction shift: {race_metrics['max_decisive_fraction_shift']:.5f}.",
            f"- Max missed-winner rate: {race_metrics['max_missed_winner_rate']:.5f}.",
            "",
            "## Decision Gate",
            "",
            f"- First-arrival capture pass: {acceptance['first_arrival_pass']}.",
            f"- Exclusivity pass: {acceptance['exclusivity_pass']}.",
            f"- Reset pass: {acceptance['reset_pass']}.",
            f"- Pulse-interface transparency pass: {acceptance['interface_pass']}.",
            f"- Race transparency pass: {acceptance['race_transparency_pass']}.",
            f"- Decision: {decision}",
            f"- Next ticket: {acceptance['recommended_next_ticket']}",
            "",
            "## Hardware Deliverables",
            "",
            f"- Latch block diagram: `{hardware_paths['block_diagram_md']}`",
            f"- Latch logic design: `{hardware_paths['schematic_md']}`",
            "",
            "## Artifacts",
            "",
            f"- Timing cases CSV: `{artifact_paths['timing_cases_csv']}`",
            f"- First-arrival CSV: `{artifact_paths['first_arrival_csv']}`",
            f"- Exclusivity CSV: `{artifact_paths['exclusivity_csv']}`",
            f"- Reset CSV: `{artifact_paths['reset_csv']}`",
            f"- Race-with-latch CSV: `{artifact_paths['race_with_latch_csv']}`",
            f"- Summary JSON: `{artifact_paths['summary_metrics_json']}`",
            "",
        ]
    )


def build_latch_rig_report(
    outdir: str | Path = "artifacts/latch_rig",
    *,
    detector_config: DetectorRigConfig = DEFAULT_DETECTOR_RIG_CONFIG,
    latch_config: LatchRigConfig = DEFAULT_LATCH_RIG_CONFIG,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)

    hardware_paths = write_latch_hardware_deliverables(output_dir, latch_config)
    cell_a, cell_b = build_matched_cell_pair(detector_config)

    timing_rows = build_timing_case_rows(latch_config)
    first_arrival = simulate_first_arrival_suite(cell_a, cell_b, latch_config)
    exclusivity = simulate_exclusivity_suite(latch_config)
    reset = simulate_reset_suite(latch_config)
    race = simulate_race_with_latch(
        cell_a,
        cell_b,
        splits=detector_config.race_splits,
        total_power_uw=detector_config.total_race_power_uw,
        n_trials=detector_config.race_trials,
        timeout_s=detector_config.race_timeout_s,
        latch_config=latch_config,
        seed=detector_config.seed + 200,
    )
    interface = summarize_latch_interface(cell_a, cell_b, latch_config)

    timing_cases_csv = output_dir / "timing_cases.csv"
    first_arrival_csv = output_dir / "first_arrival_tests.csv"
    exclusivity_csv = output_dir / "exclusivity_tests.csv"
    reset_csv = output_dir / "reset_tests.csv"
    race_with_latch_csv = output_dir / "race_with_latch.csv"

    _write_csv(timing_cases_csv, timing_rows)
    _write_csv(first_arrival_csv, first_arrival["rows"])
    _write_csv(exclusivity_csv, exclusivity["rows"])
    _write_csv(reset_csv, reset["rows"])
    _write_csv(race_with_latch_csv, race["comparison_rows"])

    artifact_paths = {
        "timing_cases_csv": str(timing_cases_csv),
        "first_arrival_csv": str(first_arrival_csv),
        "exclusivity_csv": str(exclusivity_csv),
        "reset_csv": str(reset_csv),
        "race_with_latch_csv": str(race_with_latch_csv),
    }

    latch_summary_rows = [
        {
            "split_label": row["split_label"],
            "target_p1": row["target_p1"],
            "empirical_p1": row["latch_p1"],
        }
        for row in race["comparison_rows"]
    ]
    artifact_paths["winner_frequency_vs_target_png"] = _save_figure(
        output_dir / "winner_frequency_vs_target.png",
        plot_race_summary(latch_summary_rows),
    )
    artifact_paths["baseline_vs_latch_png"] = _save_figure(
        output_dir / "baseline_vs_latch.png",
        plot_latch_race_comparison(race["comparison_rows"]),
    )
    artifact_paths["reset_stability_png"] = _save_figure(
        output_dir / "reset_stability.png",
        plot_reset_cycle_stability(reset["rows"]),
    )

    interface_metrics = {key: float(value) for key, value in interface["summary"].items()}
    first_arrival_metrics = {
        key: (float(value) if isinstance(value, (int, float)) else value)
        for key, value in first_arrival["summary"].items()
    }
    exclusivity_metrics = {key: float(value) for key, value in exclusivity["summary"].items()}
    reset_metrics = {key: float(value) for key, value in reset["summary"].items()}
    race_metrics = {key: float(value) for key, value in race["metrics"].items()}

    acceptance = {
        "first_arrival_pass": (
            float(first_arrival_metrics["ordered_capture_accuracy"]) >= 0.999
            and int(first_arrival_metrics["double_winner_count"]) == 0
        ),
        "exclusivity_pass": (
            exclusivity_metrics["masked_rival_fraction"] >= 0.999
            and exclusivity_metrics["hold_success_fraction"] >= 0.999
            and exclusivity_metrics["double_winner_count"] == 0.0
        ),
        "reset_pass": (
            reset_metrics["reset_success_fraction"] >= 0.999
            and reset_metrics["retained_memory_count"] == 0.0
            and reset_metrics["post_reset_bias_drift"] <= 0.01
        ),
        "interface_pass": interface_metrics["min_threshold_margin_v"] > 0.2 and interface_metrics["min_width_margin_ns"] > 1.0,
        "race_transparency_pass": (
            race_metrics["added_race_rms_error"] < 0.01
            and race_metrics["max_branch_bias_shift"] < 0.01
            and race_metrics["max_decisive_fraction_shift"] < 0.01
            and race_metrics["max_missed_winner_rate"] <= 0.001
            and race_metrics["double_winner_count"] == 0.0
        ),
    }
    acceptance["proceed_to_next_phase"] = all(
        [
            acceptance["first_arrival_pass"],
            acceptance["exclusivity_pass"],
            acceptance["reset_pass"],
            acceptance["interface_pass"],
            acceptance["race_transparency_pass"],
        ]
    )
    acceptance["recommended_next_ticket"] = (
        "Integrate the latch-enabled detector chain with the linear front-end, validate branch-weight to winner-law behavior end-to-end, then prepare a SPICE-facing abstraction."
        if acceptance["proceed_to_next_phase"]
        else "Revise the latch timing or masking design and repeat the latch bench before front-end integration."
    )

    summary_metrics = {
        "latch_config": {
            "input_threshold_v": latch_config.input_threshold_v,
            "min_input_pulse_width_ns": latch_config.min_input_pulse_width_ns,
            "pickoff_delay_ns": latch_config.pickoff_delay_ns,
            "propagation_delay_ns": latch_config.propagation_delay_ns,
            "inhibit_delay_ns": latch_config.inhibit_delay_ns,
            "settle_time_ns": latch_config.settle_time_ns,
            "tie_window_ns": latch_config.tie_window_ns,
            "reset_pulse_ns": latch_config.reset_pulse_ns,
            "rearm_holdoff_us": latch_config.rearm_holdoff_us,
            "tie_break_priority": latch_config.tie_break_priority,
        },
        "interface": {"rows": interface["rows"], **interface_metrics},
        "first_arrival": {"rows": first_arrival["rows"], **first_arrival_metrics},
        "exclusivity": {"rows": exclusivity["rows"], **exclusivity_metrics},
        "reset": {"rows": reset["rows"], **reset_metrics},
        "race_with_latch": {"rows": race["comparison_rows"], **race_metrics},
        "acceptance": acceptance,
        "artifacts": {**hardware_paths, **artifact_paths},
    }

    summary_metrics_json = output_dir / "summary_metrics.json"
    summary_metrics_json.write_text(json.dumps(summary_metrics, indent=2) + "\n", encoding="utf-8")
    artifact_paths["summary_metrics_json"] = str(summary_metrics_json)

    summary_md = output_dir / "summary_report.md"
    summary_md.write_text(
        _summary_markdown(
            latch_config=latch_config,
            interface_metrics=interface_metrics,
            first_arrival_metrics=first_arrival_metrics,
            exclusivity_metrics=exclusivity_metrics,
            reset_metrics=reset_metrics,
            race_metrics=race_metrics,
            acceptance=acceptance,
            hardware_paths=hardware_paths,
            artifact_paths=artifact_paths,
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "summary_md": str(summary_md),
        "summary_json": str(summary_metrics_json),
        **hardware_paths,
        **artifact_paths,
    }
