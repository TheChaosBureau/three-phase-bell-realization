from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

from detector_rig.config import DEFAULT_DETECTOR_RIG_CONFIG, DetectorRigConfig
from detector_rig.hardware import write_hardware_deliverables
from detector_rig.plots import (
    plot_dark_count_vs_bias,
    plot_dark_stability,
    plot_dead_time_distribution,
    plot_dead_time_recovery,
    plot_pulse_overlays,
    plot_race_summary,
    plot_rate_residuals,
    plot_rate_scan,
    plot_two_cell_matching,
)
from detector_rig.sim import (
    build_matched_cell_pair,
    click_rate,
    select_operating_point,
    simulate_dark_counts,
    simulate_dead_time_scan,
    simulate_pulses,
    simulate_race_summary,
    simulate_rate_scan,
    summarize_bias_sweep,
    summarize_matching,
)


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
    operating_point: dict[str, Any],
    single_cell_metrics: dict[str, Any],
    matching_metrics: dict[str, Any],
    race_metrics: dict[str, Any],
    acceptance: dict[str, bool | str],
    hardware_paths: dict[str, str],
    artifact_paths: dict[str, str],
) -> str:
    decision = "Proceed to common-mode / zero-sequence latch design." if acceptance["proceed_to_next_phase"] else "Hold the next phase and revise the detector class or operating point."
    next_ticket = acceptance["recommended_next_ticket"]
    return "\n".join(
        [
            "# Two-Cell Detector Rig Summary",
            "",
            "## Candidate",
            "",
            "- Detector class: matched absorber plus near-threshold avalanche/latch cell with one-shot output and explicit reset.",
            f"- Selected operating bias: {float(operating_point['bias_v']):.3f} V.",
            f"- Operating regime: {operating_point['regime']}.",
            f"- Nominal signal rate at {single_cell_metrics['nominal_power_uw']:.1f} uW: {single_cell_metrics['nominal_signal_rate_hz']:.3f} Hz.",
            "",
            "## Single-Cell Characterization",
            "",
            f"- Dark-count mean rate: {single_cell_metrics['dark_mean_rate_hz']:.4f} Hz.",
            f"- Dark-count Fano factor: {single_cell_metrics['dark_fano_factor']:.4f}.",
            f"- Linear fit lambda_dark: {single_cell_metrics['lambda_dark_fit_hz']:.4f} Hz.",
            f"- Linear fit alpha: {single_cell_metrics['alpha_fit_hz_per_uw']:.4f} Hz/uW.",
            f"- Linearity RMS residual: {single_cell_metrics['linearity_rms_rel']:.4f}.",
            f"- Double-pulse rate: {single_cell_metrics['double_pulse_rate']:.4f}.",
            f"- Dead-time mean: {single_cell_metrics['dead_time_mean_us']:.4f} us.",
            f"- Recovery-90 interval: {single_cell_metrics['recovery_90_us']:.4f} us.",
            "",
            "## Two-Cell Match And Race",
            "",
            f"- Gain mismatch after trim: {100.0 * matching_metrics['alpha_mismatch_rel']:.2f}%.",
            f"- Dark-rate mismatch: {matching_metrics['dark_rate_mismatch_hz']:.4f} Hz.",
            f"- Pulse-width mismatch: {100.0 * matching_metrics['pulse_width_mismatch_rel']:.2f}%.",
            f"- Timing-jitter mismatch: {100.0 * matching_metrics['timing_jitter_mismatch_rel']:.2f}%.",
            f"- Race RMS error across benchmark splits: {race_metrics['race_rms_error']:.4f}.",
            f"- Race max error across benchmark splits: {race_metrics['race_max_error']:.4f}.",
            "",
            "## Decision Gate",
            "",
            f"- Rare-event operating point exists: {acceptance['rare_event_operating_point_exists']}.",
            f"- Linear-hazard residual < 5%: {acceptance['linearity_window_pass']}.",
            f"- Dark count small vs nominal signal rate: {acceptance['dark_count_pass']}.",
            f"- One clean pulse per event: {acceptance['pulse_integrity_pass']}.",
            f"- Reset behavior stable: {acceptance['dead_time_pass']}.",
            f"- Gain mismatch <= 2%: {acceptance['gain_match_pass']}.",
            f"- Race RMS error < 0.05: {acceptance['race_pass']}.",
            f"- Decision: {decision}",
            f"- Next ticket: {next_ticket}",
            "",
            "## Hardware Deliverables",
            "",
            f"- Detector-cell candidate: `{hardware_paths['schematic_md']}`",
            f"- Two-cell block diagram: `{hardware_paths['block_diagram_md']}`",
            f"- Parts list: `{hardware_paths['parts_csv']}`",
            f"- Bias and reset scheme: `{hardware_paths['bias_reset_md']}`",
            f"- Calibrated input-drive setup: `{hardware_paths['input_drive_md']}`",
            "",
            "## Artifacts",
            "",
            f"- Dark counts CSV: `{artifact_paths['single_cell_dark_counts_csv']}`",
            f"- Rate scan CSV: `{artifact_paths['single_cell_rate_scan_csv']}`",
            f"- Pulse stats CSV: `{artifact_paths['single_cell_pulse_stats_csv']}`",
            f"- Dead-time CSV: `{artifact_paths['single_cell_dead_time_csv']}`",
            f"- Two-cell matching CSV: `{artifact_paths['two_cell_matching_csv']}`",
            f"- Two-branch race CSV: `{artifact_paths['two_branch_race_csv']}`",
            f"- Summary JSON: `{artifact_paths['summary_metrics_json']}`",
            "",
        ]
    )


def build_two_cell_detector_rig_report(
    outdir: str | Path = "artifacts/detector_rig",
    *,
    config: DetectorRigConfig = DEFAULT_DETECTOR_RIG_CONFIG,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    single_cell_dir = output_dir / "single_cell"
    two_cell_dir = output_dir / "two_cell"
    race_dir = output_dir / "race"
    single_cell_dir.mkdir(parents=True, exist_ok=True)
    two_cell_dir.mkdir(parents=True, exist_ok=True)
    race_dir.mkdir(parents=True, exist_ok=True)

    hardware_paths = write_hardware_deliverables(output_dir)

    bias_rows = summarize_bias_sweep(config)
    operating_point = select_operating_point(config)
    cell_a, cell_b = build_matched_cell_pair(config)

    dark_a = simulate_dark_counts(
        cell_a,
        window_s=config.dark_window_s,
        n_windows=config.n_dark_windows,
        seed=config.seed + 10,
    )
    rate_a = simulate_rate_scan(
        cell_a,
        powers_uw=config.rate_scan_powers_uw,
        window_s=config.rate_window_s,
        repeats=config.rate_repeats,
        seed=config.seed + 20,
    )
    pulses_a = simulate_pulses(
        cell_a,
        n_events=config.pulse_events,
        window_ns=config.pulse_window_ns,
        dt_ns=config.pulse_dt_ns,
        seed=config.seed + 30,
    )
    dead_a = simulate_dead_time_scan(
        cell_a,
        intervals_us=config.dead_time_intervals_us,
        repeats=config.dead_time_repeats,
        seed=config.seed + 40,
    )

    rate_b = simulate_rate_scan(
        cell_b,
        powers_uw=config.rate_scan_powers_uw,
        window_s=config.rate_window_s,
        repeats=config.rate_repeats,
        seed=config.seed + 120,
    )
    pulses_b = simulate_pulses(
        cell_b,
        n_events=config.pulse_events,
        window_ns=config.pulse_window_ns,
        dt_ns=config.pulse_dt_ns,
        seed=config.seed + 130,
    )
    dead_b = simulate_dead_time_scan(
        cell_b,
        intervals_us=config.dead_time_intervals_us,
        repeats=config.dead_time_repeats,
        seed=config.seed + 140,
    )
    matching = summarize_matching(
        cell_a,
        cell_b,
        rate_a["fit"],
        rate_b["fit"],
        pulses_a["summary"],
        pulses_b["summary"],
        dead_a["summary"],
        dead_b["summary"],
    )
    race = simulate_race_summary(
        cell_a,
        cell_b,
        splits=config.race_splits,
        total_power_uw=config.total_race_power_uw,
        n_trials=config.race_trials,
        timeout_s=config.race_timeout_s,
        seed=config.seed + 200,
    )

    single_cell_dark_counts_csv = single_cell_dir / "single_cell_dark_counts.csv"
    single_cell_rate_scan_csv = single_cell_dir / "single_cell_rate_scan.csv"
    single_cell_pulse_stats_csv = single_cell_dir / "single_cell_pulse_stats.csv"
    single_cell_dead_time_csv = single_cell_dir / "single_cell_dead_time.csv"
    two_cell_matching_csv = two_cell_dir / "two_cell_matching.csv"
    two_branch_race_csv = race_dir / "two_branch_race.csv"

    _write_csv(single_cell_dark_counts_csv, dark_a["rows"])
    _write_csv(single_cell_rate_scan_csv, rate_a["rows"])
    _write_csv(single_cell_pulse_stats_csv, pulses_a["rows"])
    _write_csv(single_cell_dead_time_csv, dead_a["rows"])
    _write_csv(two_cell_matching_csv, matching["rows"])
    _write_csv(two_branch_race_csv, race["raw_rows"])

    artifact_paths = {
        "single_cell_dark_counts_csv": str(single_cell_dark_counts_csv),
        "single_cell_rate_scan_csv": str(single_cell_rate_scan_csv),
        "single_cell_pulse_stats_csv": str(single_cell_pulse_stats_csv),
        "single_cell_dead_time_csv": str(single_cell_dead_time_csv),
        "two_cell_matching_csv": str(two_cell_matching_csv),
        "two_branch_race_csv": str(two_branch_race_csv),
    }

    artifact_paths["dark_count_vs_bias_png"] = _save_figure(single_cell_dir / "dark_count_vs_bias.png", plot_dark_count_vs_bias(bias_rows))
    artifact_paths["dark_stability_png"] = _save_figure(single_cell_dir / "dark_count_stability.png", plot_dark_stability(dark_a["rows"]))
    artifact_paths["rate_scan_png"] = _save_figure(single_cell_dir / "rate_vs_power.png", plot_rate_scan(rate_a["rows"]))
    artifact_paths["rate_residuals_png"] = _save_figure(single_cell_dir / "rate_fit_residuals.png", plot_rate_residuals(rate_a["rows"]))
    artifact_paths["pulse_overlay_png"] = _save_figure(
        single_cell_dir / "pulse_overlays.png",
        plot_pulse_overlays(pulses_a["time_axis_ns"], pulses_a["waveforms"], config.pulse_overlay_count),
    )
    artifact_paths["dead_time_distribution_png"] = _save_figure(
        single_cell_dir / "dead_time_distribution.png",
        plot_dead_time_distribution(dead_a["observed_dead_times_us"]),
    )
    artifact_paths["dead_time_recovery_png"] = _save_figure(
        single_cell_dir / "reset_recovery.png",
        plot_dead_time_recovery(dead_a["rows"]),
    )
    artifact_paths["two_cell_matching_png"] = _save_figure(two_cell_dir / "two_cell_matching.png", plot_two_cell_matching(matching["rows"]))
    artifact_paths["race_summary_png"] = _save_figure(race_dir / "winner_frequency_vs_target.png", plot_race_summary(race["summary_rows"]))

    nominal_signal_rate_hz = click_rate(cell_a, config.nominal_power_uw)
    single_cell_metrics = {
        "nominal_power_uw": config.nominal_power_uw,
        "nominal_signal_rate_hz": nominal_signal_rate_hz,
        "dark_mean_rate_hz": float(dark_a["mean_rate_hz"]),
        "dark_std_rate_hz": float(dark_a["std_rate_hz"]),
        "dark_fano_factor": float(dark_a["fano_factor"]),
        "lambda_dark_fit_hz": float(rate_a["fit"]["lambda_dark_fit"]),
        "alpha_fit_hz_per_uw": float(rate_a["fit"]["alpha_fit"]),
        "linearity_rms_rel": float(rate_a["fit"]["linearity_rms_rel"]),
        "linearity_max_rel": float(rate_a["fit"]["linearity_max_rel"]),
        "double_pulse_rate": float(pulses_a["summary"]["double_pulse_rate"]),
        "pulse_amplitude_mean_v": float(pulses_a["summary"]["amplitude_mean_v"]),
        "pulse_width_mean_ns": float(pulses_a["summary"]["width_mean_ns"]),
        "timing_jitter_ns": float(pulses_a["summary"]["timing_jitter_ns"]),
        "dead_time_mean_us": float(dead_a["summary"]["dead_time_mean_us"]),
        "dead_time_std_us": float(dead_a["summary"]["dead_time_std_us"]),
        "recovery_90_us": float(dead_a["summary"]["recovery_90_us"]),
    }
    matching_metrics = {key: float(value) for key, value in matching["summary"].items()}
    race_metrics = {key: float(value) for key, value in race["metrics"].items()}

    acceptance = {
        "rare_event_operating_point_exists": operating_point["regime"] == "rare_event",
        "linearity_window_pass": single_cell_metrics["linearity_rms_rel"] < 0.05,
        "dark_count_pass": single_cell_metrics["dark_mean_rate_hz"] < 0.05 * nominal_signal_rate_hz,
        "pulse_integrity_pass": single_cell_metrics["double_pulse_rate"] <= 0.01,
        "dead_time_pass": single_cell_metrics["recovery_90_us"] < math.inf
        and single_cell_metrics["dead_time_std_us"] / max(single_cell_metrics["dead_time_mean_us"], 1e-12) < 0.1,
        "gain_match_pass": matching_metrics["alpha_mismatch_rel"] <= 0.02,
        "race_pass": race_metrics["race_rms_error"] < 0.05,
    }
    acceptance["proceed_to_next_phase"] = all(
        [
            acceptance["rare_event_operating_point_exists"],
            acceptance["linearity_window_pass"],
            acceptance["dark_count_pass"],
            acceptance["pulse_integrity_pass"],
            acceptance["dead_time_pass"],
            acceptance["gain_match_pass"],
            acceptance["race_pass"],
        ]
    )
    acceptance["recommended_next_ticket"] = (
        "Design and characterize the common-mode / zero-sequence latch, then integrate with the linear front-end."
        if acceptance["proceed_to_next_phase"]
        else "Revise the detector class or operating bias and repeat two-cell characterization."
    )

    summary_metrics = {
        "operating_point": operating_point,
        "single_cell": single_cell_metrics,
        "two_cell_matching": matching_metrics,
        "race": {
            "summary_rows": race["summary_rows"],
            **race_metrics,
        },
        "acceptance": acceptance,
        "artifacts": {**hardware_paths, **artifact_paths},
    }

    summary_metrics_json = output_dir / "summary_metrics.json"
    summary_metrics_json.write_text(json.dumps(summary_metrics, indent=2) + "\n", encoding="utf-8")
    artifact_paths["summary_metrics_json"] = str(summary_metrics_json)

    summary_md = output_dir / "summary_report.md"
    summary_md.write_text(
        _summary_markdown(
            operating_point=operating_point,
            single_cell_metrics=single_cell_metrics,
            matching_metrics=matching_metrics,
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
        "summary_metrics_json": str(summary_metrics_json),
        **hardware_paths,
        **artifact_paths,
        "operating_point": operating_point,
        "single_cell_metrics": single_cell_metrics,
        "matching_metrics": matching_metrics,
        "race_metrics": race_metrics,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the two-cell detector characterization rig report.")
    parser.add_argument("--outdir", default="artifacts/detector_rig", help="Output directory for detector rig artifacts.")
    args = parser.parse_args()
    build_two_cell_detector_rig_report(args.outdir)


if __name__ == "__main__":
    main()
