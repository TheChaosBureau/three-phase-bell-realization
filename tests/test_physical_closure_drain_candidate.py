from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from physical_front_end_candidate.experiments.build_physical_closure_drain_candidate_report import (
    build_physical_closure_drain_candidate_report,
)
from physical_front_end_candidate.physical_closure_drain_candidate import (
    default_physical_closure_drain_config,
    run_four_branch_candidate_with_physical_closure,
    simulate_physical_closure_drain,
)
from physical_front_end_candidate.resonant_four_branch_candidate import benchmark_resonant_four_branch_cases, simulate_resonant_four_branch_candidate

SHOT_TRIGGER_SPEC = {
    "family": "shot_trigger",
    "model_params": {"eps_event": 0.5, "p_trig": 0.8, "lambda_dark": 1e-6, "dead_time": 0.0},
    "gain_scale": 2.0,
}


def test_physical_closure_remains_inactive_before_winner_capture() -> None:
    case = benchmark_resonant_four_branch_cases()[0]
    candidate = simulate_resonant_four_branch_candidate(case["state4"], a_deg=case["a_deg"], b_deg=case["b_deg"])
    result = simulate_physical_closure_drain(
        time_s=candidate["time_s"],
        branch_power_w=candidate["branch_power_w"],
        branch_labels=candidate["branch_labels"],
        winner_index=-1,
        winner_valid=False,
        capture_time_s=0.0,
    )
    assert result["activation_count"] == 0
    assert not result["closure_active"]
    assert np.allclose(result["closure_variable"], 0.0)


def test_winner_capture_activates_exactly_one_drain_path() -> None:
    case = benchmark_resonant_four_branch_cases()[2]
    candidate = simulate_resonant_four_branch_candidate(case["state4"], a_deg=case["a_deg"], b_deg=case["b_deg"])
    result = simulate_physical_closure_drain(
        time_s=candidate["time_s"],
        branch_power_w=candidate["branch_power_w"],
        branch_labels=candidate["branch_labels"],
        winner_index=1,
        winner_valid=True,
        capture_time_s=0.5,
    )
    assert result["activation_count"] == 1
    assert result["winner_drain_path_count"] == 1
    active_labels = [label for label, values in result["winner_drain_enable_by_branch"].items() if values[-1] > 0.9]
    assert active_labels == [candidate["branch_labels"][1]]


def test_loser_suppression_occurs_after_activation() -> None:
    case = benchmark_resonant_four_branch_cases()[2]
    candidate = simulate_resonant_four_branch_candidate(case["state4"], a_deg=case["a_deg"], b_deg=case["b_deg"])
    result = simulate_physical_closure_drain(
        time_s=candidate["time_s"],
        branch_power_w=candidate["branch_power_w"],
        branch_labels=candidate["branch_labels"],
        winner_index=1,
        winner_valid=True,
        capture_time_s=0.5,
    )
    for values in result["loser_suppression"].values():
        assert values[-1] > 0.9


def test_remaining_shared_energy_decreases_monotonically_after_activation() -> None:
    case = benchmark_resonant_four_branch_cases()[2]
    candidate = simulate_resonant_four_branch_candidate(case["state4"], a_deg=case["a_deg"], b_deg=case["b_deg"])
    result = simulate_physical_closure_drain(
        time_s=candidate["time_s"],
        branch_power_w=candidate["branch_power_w"],
        branch_labels=candidate["branch_labels"],
        winner_index=1,
        winner_valid=True,
        capture_time_s=0.5,
    )
    remaining = np.asarray(result["remaining_shared_energy_j"], dtype=float)
    assert np.all(np.diff(remaining) <= 1e-12)
    assert result["monotonic_remaining_energy"]


def test_winner_drain_dominates_post_click_energy_share() -> None:
    case = benchmark_resonant_four_branch_cases()[2]
    candidate = simulate_resonant_four_branch_candidate(case["state4"], a_deg=case["a_deg"], b_deg=case["b_deg"])
    result = simulate_physical_closure_drain(
        time_s=candidate["time_s"],
        branch_power_w=candidate["branch_power_w"],
        branch_labels=candidate["branch_labels"],
        winner_index=1,
        winner_valid=True,
        capture_time_s=0.5,
        config=default_physical_closure_drain_config(),
    )
    loser_total = float(sum(result["loser_post_click_energy_j"].values()))
    assert result["winner_drain_total_energy_j"] > loser_total


def test_trial_complete_signal_is_generated_consistently() -> None:
    case = benchmark_resonant_four_branch_cases()[2]
    candidate = simulate_resonant_four_branch_candidate(case["state4"], a_deg=case["a_deg"], b_deg=case["b_deg"])
    result = simulate_physical_closure_drain(
        time_s=candidate["time_s"],
        branch_power_w=candidate["branch_power_w"],
        branch_labels=candidate["branch_labels"],
        winner_index=1,
        winner_valid=True,
        capture_time_s=0.5,
    )
    assert result["trial_complete"]
    signal = np.asarray(result["trial_complete_signal"], dtype=float)
    assert signal[-1] == 1.0
    assert np.all(np.diff(signal) >= -1e-12)


def test_integrated_physical_closure_preserves_preclick_behavior_and_reduced_semantics() -> None:
    case = benchmark_resonant_four_branch_cases()[2]
    candidate = simulate_resonant_four_branch_candidate(case["state4"], a_deg=case["a_deg"], b_deg=case["b_deg"])
    result = run_four_branch_candidate_with_physical_closure(
        candidate,
        SHOT_TRIGGER_SPEC,
        n_trials=80,
        seed=20260403,
    )
    assert result["closure_metrics"]["pre_click_transparency_rms_shift"] < 1e-9
    assert result["closure_metrics"]["mean_winner_drain_fraction"] > 0.75
    assert result["closure_metrics"]["mean_loser_fraction"] < 0.05
    assert result["comparison_metrics"]["winner_fraction_abs_diff"] < 0.12


def test_physical_closure_candidate_report_smoke_writes_artifacts(tmp_path: Path) -> None:
    detector_next_summary = tmp_path / "detector_next_summary.csv"
    detector_next_summary.write_text(
        "\n".join(
            [
                "model,rank,score,linearity_rms_rel,dark_count_rate,race_rms_error,mismatch_penalty,branch_asymmetry_amplification,waiting_time_penalty,params_json",
                'shot_trigger,1,0.1,0.01,0.0,0.01,0.02,0.03,0.04,"{""dead_time"": 0.0, ""eps_event"": 0.5, ""lambda_dark"": 1e-06, ""p_trig"": 0.8}"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    outputs = build_physical_closure_drain_candidate_report(
        tmp_path / "summary",
        detector_next_summary_csv=detector_next_summary,
        n_trials=4,
        case_names=("case_a",),
    )

    assert Path(outputs["summary_md"]).exists()
    assert Path(outputs["summary_json"]).exists()
    assert Path(outputs["summary_csv"]).exists()
    assert Path(outputs["design_md"]).exists()
    assert Path(outputs["spice_facing_interface_md"]).exists()
    assert Path(tmp_path / "summary" / "reduced_mapping" / "mapping_summary.csv").exists()
    assert Path(tmp_path / "summary" / "integration" / "integration_summary.csv").exists()
    report_text = Path(outputs["summary_md"]).read_text(encoding="utf-8")
    assert "First Physical Closure / Drain Candidate Summary" in report_text
    summary = json.loads(Path(outputs["summary_json"]).read_text(encoding="utf-8"))
    assert "summary_metrics" in summary
    assert "comparison_rows" in summary
