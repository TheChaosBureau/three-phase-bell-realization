from __future__ import annotations

import json
from pathlib import Path

from physical_front_end_candidate.closure_path import simulate_four_branch_candidate_pre_click_race
from physical_front_end_candidate.common_inhibit_tuning import run_common_inhibit_parameter_sweeps
from physical_front_end_candidate.experiments.build_common_inhibit_tuning_report import build_common_inhibit_tuning_report
from physical_front_end_candidate.physical_closure_drain_candidate import (
    default_physical_closure_drain_config,
    run_four_branch_candidate_with_physical_closure,
    simulate_physical_closure_drain,
    tuned_physical_closure_drain_config,
)
from physical_front_end_candidate.resonant_four_branch_candidate import benchmark_resonant_four_branch_cases, simulate_resonant_four_branch_candidate

SHOT_TRIGGER_SPEC = {
    "family": "shot_trigger",
    "model_params": {"eps_event": 0.5, "p_trig": 0.8, "lambda_dark": 1e-6, "dead_time": 0.0},
    "gain_scale": 2.0,
}


def test_tuned_closure_remains_inactive_before_winner_valid() -> None:
    case = benchmark_resonant_four_branch_cases()[0]
    candidate = simulate_resonant_four_branch_candidate(case["state4"], a_deg=case["a_deg"], b_deg=case["b_deg"])
    tuned = tuned_physical_closure_drain_config(control_tau_s=0.06, clamp_reference_g_on_s=1.4, winner_drain_g_on_s=3.2)
    result = simulate_physical_closure_drain(
        time_s=candidate["time_s"],
        branch_power_w=candidate["branch_power_w"],
        branch_labels=candidate["branch_labels"],
        winner_index=-1,
        winner_valid=False,
        capture_time_s=0.0,
        config=tuned,
    )
    assert result["activation_count"] == 0
    assert not result["closure_active"]


def test_winner_drain_fraction_improves_under_stronger_drain_and_clamp() -> None:
    case = benchmark_resonant_four_branch_cases()[2]
    candidate = simulate_resonant_four_branch_candidate(case["state4"], a_deg=case["a_deg"], b_deg=case["b_deg"])
    race = simulate_four_branch_candidate_pre_click_race(candidate, SHOT_TRIGGER_SPEC, n_trials=12, seed=20260404)
    baseline = run_four_branch_candidate_with_physical_closure(
        candidate,
        SHOT_TRIGGER_SPEC,
        n_trials=12,
        seed=20260404,
        config=default_physical_closure_drain_config(),
        race_result=race,
    )
    tuned = run_four_branch_candidate_with_physical_closure(
        candidate,
        SHOT_TRIGGER_SPEC,
        n_trials=12,
        seed=20260404,
        config=tuned_physical_closure_drain_config(control_tau_s=0.06, clamp_reference_g_on_s=1.4, winner_drain_g_on_s=3.2),
        race_result=race,
    )
    assert tuned["closure_metrics"]["mean_winner_drain_fraction"] > baseline["closure_metrics"]["mean_winner_drain_fraction"]


def test_loser_suppression_remains_strong_after_tuning() -> None:
    case = benchmark_resonant_four_branch_cases()[2]
    candidate = simulate_resonant_four_branch_candidate(case["state4"], a_deg=case["a_deg"], b_deg=case["b_deg"])
    tuned = run_four_branch_candidate_with_physical_closure(
        candidate,
        SHOT_TRIGGER_SPEC,
        n_trials=16,
        seed=20260404,
        config=tuned_physical_closure_drain_config(control_tau_s=0.06, clamp_reference_g_on_s=1.4, winner_drain_g_on_s=3.2),
    )
    assert tuned["closure_metrics"]["mean_terminal_loser_suppression"] > 0.9


def test_shared_energy_remains_monotonic_after_tuning() -> None:
    case = benchmark_resonant_four_branch_cases()[2]
    candidate = simulate_resonant_four_branch_candidate(case["state4"], a_deg=case["a_deg"], b_deg=case["b_deg"])
    tuned = run_four_branch_candidate_with_physical_closure(
        candidate,
        SHOT_TRIGGER_SPEC,
        n_trials=16,
        seed=20260404,
        config=tuned_physical_closure_drain_config(control_tau_s=0.06, clamp_reference_g_on_s=1.4, winner_drain_g_on_s=3.2),
    )
    assert tuned["closure_metrics"]["monotonic_remaining_energy"]


def test_best_tuned_candidate_improves_on_first_candidate() -> None:
    tuning = run_common_inhibit_parameter_sweeps(SHOT_TRIGGER_SPEC, n_trials=6, seed=20260404, case_names=("case_a",))
    assert tuning["best_tuned"]["summary_metrics"]["mean_winner_drain_fraction"] > tuning["baseline"]["summary_metrics"]["mean_winner_drain_fraction"]
    assert "winner_path_activation_rate" in tuning["best_tuned"]["summary_metrics"]
    assert "winner_path_activation_pass" in tuning["best_tuned"]["summary_metrics"]


def test_common_inhibit_tuning_report_smoke_writes_artifacts(tmp_path: Path) -> None:
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

    outputs = build_common_inhibit_tuning_report(
        tmp_path / "summary",
        detector_next_summary_csv=detector_next_summary,
        n_trials=4,
        case_names=("case_a",),
    )

    assert Path(outputs["summary_md"]).exists()
    assert Path(outputs["summary_json"]).exists()
    assert Path(outputs["summary_csv"]).exists()
    assert Path(outputs["design_md"]).exists()
    assert Path(outputs["parameter_sweeps_dir"]).exists()
    assert Path(outputs["best_candidate_dir"]).exists()
    assert Path(outputs["progress_json"]).exists()
    assert Path(outputs["top_candidates_csv"]).exists()
    summary = json.loads(Path(outputs["summary_json"]).read_text(encoding="utf-8"))
    assert "summary_metrics" in summary
    assert "sweep_rows" in summary
    assert "top_candidates" in summary
    assert "winner_path_activation_rate" in summary["summary_metrics"]
    assert "winner_path_activation_pass" in summary["summary_metrics"]
