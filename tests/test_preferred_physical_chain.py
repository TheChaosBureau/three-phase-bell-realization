from __future__ import annotations

import json
from pathlib import Path

from physical_front_end_candidate.experiments.build_preferred_physical_chain_report import (
    build_preferred_physical_chain_report,
)
from physical_front_end_candidate.preferred_physical_chain import (
    run_preferred_physical_chain_benchmark,
    run_preferred_physical_chain_case,
)
from physical_front_end_candidate.resonant_four_branch_candidate import benchmark_resonant_four_branch_cases

SHOT_TRIGGER_SPEC = {
    "family": "shot_trigger",
    "model_params": {"eps_event": 0.5, "p_trig": 0.8, "lambda_dark": 1e-6, "dead_time": 0.0},
    "gain_scale": 2.0,
}


def test_preferred_chain_runs_end_to_end_on_benchmark_case() -> None:
    case = benchmark_resonant_four_branch_cases()[0]
    result = run_preferred_physical_chain_case(
        case["state4"],
        a_deg=case["a_deg"],
        b_deg=case["b_deg"],
        detector_spec=SHOT_TRIGGER_SPEC,
        n_trials=16,
        seed=20260405,
    )
    assert result["boundary_config"]["gain"] == 4.0
    assert result["boundary_config"]["exposure_s"] == 5.0
    assert result["export_config"]["mode"] == "piecewise_envelope"
    assert result["post_click_summary"]["activation_rate"] > 0.0
    assert result["energy_accounting_summary"]["trial_count"] == 16


def test_preferred_chain_pre_click_transparency_matches_baseline() -> None:
    case = benchmark_resonant_four_branch_cases()[4]
    result = run_preferred_physical_chain_case(
        case["state4"],
        a_deg=case["a_deg"],
        b_deg=case["b_deg"],
        detector_spec=SHOT_TRIGGER_SPEC,
        n_trials=40,
        seed=20260405,
    )
    assert result["pre_click_comparison"]["winner_frequency_rms_shift"] < 1e-9
    assert result["pre_click_comparison"]["winner_frequency_max_shift"] < 1e-9
    assert abs(result["pre_click_comparison"]["decisive_fraction_shift"]) < 1e-12


def test_preferred_chain_post_click_exclusivity_and_monotonic_decay_hold() -> None:
    case = benchmark_resonant_four_branch_cases()[2]
    result = run_preferred_physical_chain_case(
        case["state4"],
        a_deg=case["a_deg"],
        b_deg=case["b_deg"],
        detector_spec=SHOT_TRIGGER_SPEC,
        n_trials=48,
        seed=20260405,
    )
    assert result["post_click_summary"]["winner_drain_dominant"]
    assert result["post_click_summary"]["winner_drain_dominance_rate"] > 0.95
    assert result["post_click_summary"]["mean_activated_loser_fraction"] < 0.05
    assert result["post_click_summary"]["monotonic_remaining_energy"]


def test_preferred_chain_suite_meets_ticket_acceptance() -> None:
    summary = run_preferred_physical_chain_benchmark(
        SHOT_TRIGGER_SPEC,
        n_trials=480,
        seed=20260403,
    )
    metrics = summary["summary_metrics"]
    assert metrics["winner_law_pass"]
    assert metrics["correlator_pass"]
    assert metrics["chsh_pass"]
    assert metrics["pre_click_transparency_pass"]
    assert metrics["winner_drain_dominance_pass"]
    assert metrics["completion_pass"]
    assert metrics["energy_accounting_pass"]


def test_preferred_chain_energy_accounting_is_finite_and_consistent() -> None:
    case = benchmark_resonant_four_branch_cases()[5]
    result = run_preferred_physical_chain_case(
        case["state4"],
        a_deg=case["a_deg"],
        b_deg=case["b_deg"],
        detector_spec=SHOT_TRIGGER_SPEC,
        n_trials=32,
        seed=20260405,
    )
    energy = result["energy_accounting_summary"]
    assert energy["finite_outputs"]
    assert energy["energy_accounting_pass"]
    assert energy["max_energy_balance_abs_fraction"] < 1e-6


def test_preferred_chain_report_smoke_writes_artifacts(tmp_path: Path) -> None:
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

    outputs = build_preferred_physical_chain_report(
        tmp_path / "summary",
        detector_next_summary_csv=detector_next_summary,
        n_trials=12,
    )

    assert Path(outputs["summary_md"]).exists()
    assert Path(outputs["summary_json"]).exists()
    assert Path(outputs["summary_csv"]).exists()
    assert Path(outputs["design_md"]).exists()
    assert Path(outputs["full_chain_dir"]).exists()
    assert Path(outputs["pre_click_dir"]).exists()
    assert Path(outputs["post_click_dir"]).exists()
    assert Path(outputs["energy_dir"]).exists()
    report_text = Path(outputs["summary_md"]).read_text(encoding="utf-8")
    assert "Preferred Physical Chain Summary" in report_text
    summary = json.loads(Path(outputs["summary_json"]).read_text(encoding="utf-8"))
    assert "summary_metrics" in summary
    assert "case_rows" in summary
    assert "post_click_rows" in summary
    assert (tmp_path / "summary" / "full_chain" / "winner_frequency_exact_vs_empirical.png").exists()
    assert (tmp_path / "summary" / "pre_click" / "pre_click_transparency_comparison.png").exists()
    assert (tmp_path / "summary" / "post_click" / "winner_drain_energy_fraction.png").exists()
    assert (tmp_path / "summary" / "energy_accounting" / "whole_trial_energy_flow_summary.png").exists()
