from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from physical_front_end_candidate.closure_path import closure_interpretations, run_four_branch_candidate_with_closure, simulate_post_click_closure
from physical_front_end_candidate.experiments.build_post_click_closure_report import build_post_click_closure_report
from physical_front_end_candidate.resonant_four_branch_candidate import benchmark_resonant_four_branch_cases, simulate_resonant_four_branch_candidate

SHOT_TRIGGER_SPEC = {
    "family": "shot_trigger",
    "model_params": {"eps_event": 0.5, "p_trig": 0.8, "lambda_dark": 1e-6, "dead_time": 0.0},
    "gain_scale": 2.0,
}


def test_closure_block_remains_inactive_before_winner_capture() -> None:
    case = benchmark_resonant_four_branch_cases()[0]
    candidate = simulate_resonant_four_branch_candidate(case["state4"], a_deg=case["a_deg"], b_deg=case["b_deg"])
    interpretation = closure_interpretations()[0]
    result = simulate_post_click_closure(
        time_s=candidate["time_s"],
        branch_power_w=candidate["branch_power_w"],
        branch_labels=candidate["branch_labels"],
        winner_index=-1,
        winner_valid=False,
        capture_time_s=0.0,
        interpretation=interpretation,
    )
    assert result["activation_count"] == 0
    assert not result["closure_active"]
    assert np.allclose(result["closure_variable"], 0.0)


def test_winner_capture_activates_closure_exactly_once_and_suppresses_losers() -> None:
    case = benchmark_resonant_four_branch_cases()[2]
    candidate = simulate_resonant_four_branch_candidate(case["state4"], a_deg=case["a_deg"], b_deg=case["b_deg"])
    interpretation = closure_interpretations()[2]
    result = simulate_post_click_closure(
        time_s=candidate["time_s"],
        branch_power_w=candidate["branch_power_w"],
        branch_labels=candidate["branch_labels"],
        winner_index=1,
        winner_valid=True,
        capture_time_s=0.5,
        interpretation=interpretation,
    )
    assert result["activation_count"] == 1
    assert result["closure_active"]
    for label, values in result["loser_suppression"].items():
        assert values[-1] > 0.9


def test_remaining_shared_energy_decreases_monotonically_and_winner_dominates() -> None:
    case = benchmark_resonant_four_branch_cases()[2]
    candidate = simulate_resonant_four_branch_candidate(case["state4"], a_deg=case["a_deg"], b_deg=case["b_deg"])
    interpretation = closure_interpretations()[2]
    result = simulate_post_click_closure(
        time_s=candidate["time_s"],
        branch_power_w=candidate["branch_power_w"],
        branch_labels=candidate["branch_labels"],
        winner_index=1,
        winner_valid=True,
        capture_time_s=0.5,
        interpretation=interpretation,
    )
    remaining = np.asarray(result["remaining_shared_energy_j"], dtype=float)
    assert np.all(np.diff(remaining) <= 1e-12)
    loser_total = float(sum(result["loser_post_click_energy_j"].values()))
    assert result["winner_drain_total_energy_j"] > loser_total


def test_chain_with_closure_preserves_preclick_behavior_with_small_shift() -> None:
    case = benchmark_resonant_four_branch_cases()[2]
    candidate = simulate_resonant_four_branch_candidate(case["state4"], a_deg=case["a_deg"], b_deg=case["b_deg"])
    result = run_four_branch_candidate_with_closure(
        candidate,
        SHOT_TRIGGER_SPEC,
        interpretation=closure_interpretations()[2],
        n_trials=120,
        seed=20260403,
    )
    assert result["closure_metrics"]["pre_click_transparency_rms_shift"] < 1e-9
    assert result["closure_metrics"]["monotonic_remaining_energy"]
    assert result["closure_metrics"]["mean_winner_drain_fraction"] > 0.75


def test_post_click_closure_report_smoke_writes_artifacts(tmp_path: Path) -> None:
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

    outputs = build_post_click_closure_report(
        tmp_path / "summary",
        detector_next_summary_csv=detector_next_summary,
        n_trials=2,
        interpretation_names=("winner_gated_common_shunt",),
        case_names=("case_a",),
    )

    assert Path(outputs["summary_md"]).exists()
    assert Path(outputs["summary_json"]).exists()
    assert Path(outputs["summary_csv"]).exists()
    assert Path(outputs["design_md"]).exists()
    report_text = Path(outputs["summary_md"]).read_text(encoding="utf-8")
    assert "Post-Click Closure / Drain Summary" in report_text
    summary = json.loads(Path(outputs["summary_json"]).read_text(encoding="utf-8"))
    assert "summary_metrics" in summary
    assert "interpretations" in summary
