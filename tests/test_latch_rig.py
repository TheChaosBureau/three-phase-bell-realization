from __future__ import annotations

import json
from pathlib import Path

from detector_rig import DEFAULT_DETECTOR_RIG_CONFIG, DEFAULT_LATCH_RIG_CONFIG, build_latch_rig_report
from detector_rig.latch import LatchPulse, simulate_latch_sequence, simulate_race_with_latch
from detector_rig.sim import build_matched_cell_pair


def test_latch_sequence_captures_first_edge_masks_rivals_and_rearms() -> None:
    config = DEFAULT_LATCH_RIG_CONFIG
    holdoff_ns = 1000.0 * config.rearm_holdoff_us
    pulses = [
        LatchPulse("A", 40.0, 1.0, 12.0),
        LatchPulse("B", 40.10, 1.0, 12.0),
        LatchPulse("B", 54.0, 1.0, 12.0),
        LatchPulse("reset", 200.0, 1.0, config.reset_pulse_ns),
        LatchPulse("A", 200.0 + config.reset_pulse_ns + 0.5 * holdoff_ns, 1.0, 12.0),
        LatchPulse("B", 200.0 + config.reset_pulse_ns + holdoff_ns + 20.0, 1.0, 12.0),
    ]

    result = simulate_latch_sequence(pulses, config)

    assert [event["channel"] for event in result["winner_events"]] == ["A", "B"]
    assert result["double_winner_count"] == 0
    assert result["winner"] == "B"
    assert any(row["action"] == "masked_rival" for row in result["event_rows"])
    assert any(row["action"] == "ignored_holdoff" for row in result["event_rows"])


def test_race_with_latch_preserves_the_detector_only_race_law() -> None:
    cell_a, cell_b = build_matched_cell_pair(DEFAULT_DETECTOR_RIG_CONFIG)
    race = simulate_race_with_latch(
        cell_a,
        cell_b,
        splits=DEFAULT_DETECTOR_RIG_CONFIG.race_splits,
        total_power_uw=DEFAULT_DETECTOR_RIG_CONFIG.total_race_power_uw,
        n_trials=DEFAULT_DETECTOR_RIG_CONFIG.race_trials,
        timeout_s=DEFAULT_DETECTOR_RIG_CONFIG.race_timeout_s,
        latch_config=DEFAULT_LATCH_RIG_CONFIG,
        seed=DEFAULT_DETECTOR_RIG_CONFIG.seed + 200,
    )

    assert race["metrics"]["baseline_race_rms_error"] < 0.05
    assert race["metrics"]["latch_race_rms_error"] < 0.05
    assert race["metrics"]["added_race_rms_error"] < 0.01
    assert race["metrics"]["max_branch_bias_shift"] < 0.01
    assert race["metrics"]["max_decisive_fraction_shift"] < 0.01
    assert race["metrics"]["max_missed_winner_rate"] == 0.0
    assert race["metrics"]["double_winner_count"] == 0.0


def test_build_latch_rig_report_writes_artifacts(tmp_path: Path) -> None:
    outputs = build_latch_rig_report(tmp_path)

    expected_files = {
        "latch_block_diagram.md",
        "latch_schematic.md",
        "timing_cases.csv",
        "first_arrival_tests.csv",
        "exclusivity_tests.csv",
        "reset_tests.csv",
        "race_with_latch.csv",
        "winner_frequency_vs_target.png",
        "baseline_vs_latch.png",
        "reset_stability.png",
        "summary_metrics.json",
        "summary_report.md",
    }
    assert expected_files.issubset({path.name for path in tmp_path.iterdir()})

    report_text = Path(outputs["summary_md"]).read_text(encoding="utf-8")
    assert "Winner Latch Rig Summary" in report_text
    assert "Added RMS error" in report_text

    summary = json.loads((tmp_path / "summary_metrics.json").read_text(encoding="utf-8"))
    assert summary["acceptance"]["proceed_to_next_phase"] is True
    assert summary["first_arrival"]["ordered_capture_accuracy"] >= 0.999
    assert summary["race_with_latch"]["added_race_rms_error"] < 0.01
