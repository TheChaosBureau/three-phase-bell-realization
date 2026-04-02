from __future__ import annotations

import json
from pathlib import Path

from detector_rig import DEFAULT_DETECTOR_RIG_CONFIG, build_two_cell_detector_rig_report
from detector_rig.sim import build_matched_cell_pair, select_operating_point, simulate_race_summary


def test_operating_point_selection_finds_rare_event_window() -> None:
    operating_point = select_operating_point(DEFAULT_DETECTOR_RIG_CONFIG)
    assert operating_point["regime"] == "rare_event"
    assert abs(float(operating_point["bias_v"]) - 2.78) < 1e-12
    assert float(operating_point["dark_fraction_at_nominal_power"]) < 0.02


def test_matched_two_cell_race_tracks_power_split() -> None:
    cell_a, cell_b = build_matched_cell_pair(DEFAULT_DETECTOR_RIG_CONFIG)
    race = simulate_race_summary(
        cell_a,
        cell_b,
        splits=DEFAULT_DETECTOR_RIG_CONFIG.race_splits,
        total_power_uw=DEFAULT_DETECTOR_RIG_CONFIG.total_race_power_uw,
        n_trials=3_000,
        timeout_s=DEFAULT_DETECTOR_RIG_CONFIG.race_timeout_s,
        seed=DEFAULT_DETECTOR_RIG_CONFIG.seed,
    )
    assert race["metrics"]["race_rms_error"] < 0.05
    assert race["metrics"]["race_max_error"] < 0.08


def test_build_two_cell_detector_rig_report_writes_artifacts(tmp_path: Path) -> None:
    outputs = build_two_cell_detector_rig_report(tmp_path)

    expected_files = {
        "detector_cell_candidate.md",
        "two_cell_test_rig_block_diagram.md",
        "parts_list.csv",
        "bias_reset_scheme.md",
        "input_drive_setup.md",
        "summary_metrics.json",
        "summary_report.md",
    }
    assert expected_files.issubset({path.name for path in tmp_path.iterdir()})

    expected_subfiles = {
        tmp_path / "single_cell" / "single_cell_dark_counts.csv",
        tmp_path / "single_cell" / "single_cell_rate_scan.csv",
        tmp_path / "single_cell" / "single_cell_pulse_stats.csv",
        tmp_path / "single_cell" / "single_cell_dead_time.csv",
        tmp_path / "two_cell" / "two_cell_matching.csv",
        tmp_path / "race" / "two_branch_race.csv",
        tmp_path / "race" / "winner_frequency_vs_target.png",
    }
    assert all(path.exists() for path in expected_subfiles)

    report_text = Path(outputs["summary_md"]).read_text(encoding="utf-8")
    assert "Two-Cell Detector Rig Summary" in report_text
    assert "Race RMS error across benchmark splits" in report_text

    summary = json.loads((tmp_path / "summary_metrics.json").read_text(encoding="utf-8"))
    assert summary["acceptance"]["proceed_to_next_phase"] is True
