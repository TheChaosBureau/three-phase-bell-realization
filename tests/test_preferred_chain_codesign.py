from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from physical_front_end_candidate.experiments.build_preferred_chain_codesign_report import (
    build_preferred_chain_codesign_report,
)
from physical_front_end_candidate.preferred_chain_codesign import (
    preferred_chain_codesign_benchmark_cases,
    run_preferred_chain_codesign_benchmark,
    run_preferred_chain_codesign_case,
    simulate_preferred_chain_codesign_candidate,
)

SHOT_TRIGGER_SPEC = {
    "family": "shot_trigger",
    "model_params": {"eps_event": 0.5, "p_trig": 0.8, "lambda_dark": 1e-6, "dead_time": 0.0},
    "gain_scale": 2.0,
}


def test_codesign_integrated_netlist_is_finite_and_well_posed() -> None:
    case = preferred_chain_codesign_benchmark_cases()[0]
    candidate = simulate_preferred_chain_codesign_candidate(
        case["state4"],
        a_deg=case["a_deg"],
        b_deg=case["b_deg"],
    )
    matrix = np.asarray(candidate["netlist"]["admittance_matrix_s"], dtype=np.complex128)
    node_voltage = np.asarray(candidate["netlist"]["node_voltage_v"], dtype=np.complex128)
    assert matrix.shape[0] == matrix.shape[1] == len(candidate["netlist"]["node_order"])
    assert np.linalg.matrix_rank(matrix) == matrix.shape[0]
    assert np.all(np.isfinite(node_voltage.real))
    assert np.all(np.isfinite(node_voltage.imag))


def test_codesign_export_remains_compatible_with_frozen_boundary() -> None:
    case = preferred_chain_codesign_benchmark_cases()[1]
    result = run_preferred_chain_codesign_case(
        case["state4"],
        a_deg=case["a_deg"],
        b_deg=case["b_deg"],
        detector_spec=SHOT_TRIGGER_SPEC,
        n_trials=16,
        seed=20260408,
    )
    assert result["boundary_config"]["gain"] == 4.0
    assert result["boundary_config"]["exposure_s"] == 5.0
    assert result["export_config"]["mode"] == "piecewise_envelope"


def test_codesign_pre_click_transparency_stays_close_to_separated_baseline() -> None:
    summary = run_preferred_chain_codesign_benchmark(
        SHOT_TRIGGER_SPEC,
        n_trials=48,
        seed=20260408,
        case_names=("a0b0",),
    )
    row = summary["pre_click_rows"][0]
    assert row["winner_frequency_rms_shift"] < 0.05
    assert row["winner_frequency_max_shift"] < 0.05


def test_codesign_winner_drain_dominance_remains_true() -> None:
    case = preferred_chain_codesign_benchmark_cases()[2]
    result = run_preferred_chain_codesign_case(
        case["state4"],
        a_deg=case["a_deg"],
        b_deg=case["b_deg"],
        detector_spec=SHOT_TRIGGER_SPEC,
        n_trials=48,
        seed=20260408,
    )
    post_click = result["post_click_summary"]
    assert post_click["winner_drain_dominance_rate"] >= 0.99
    assert post_click["mean_activated_loser_fraction"] < 0.05


def test_codesign_energy_accounting_remains_balanced() -> None:
    case = preferred_chain_codesign_benchmark_cases()[3]
    result = run_preferred_chain_codesign_case(
        case["state4"],
        a_deg=case["a_deg"],
        b_deg=case["b_deg"],
        detector_spec=SHOT_TRIGGER_SPEC,
        n_trials=48,
        seed=20260408,
    )
    energy = result["energy_accounting_summary"]
    assert energy["finite_outputs"]
    assert energy["energy_accounting_pass"]
    assert energy["max_energy_balance_abs_fraction"] < 1e-6


def test_codesign_is_not_the_prior_separated_chain_in_disguise() -> None:
    case = preferred_chain_codesign_benchmark_cases()[0]
    candidate = simulate_preferred_chain_codesign_candidate(
        case["state4"],
        a_deg=case["a_deg"],
        b_deg=case["b_deg"],
    )
    semantics = candidate["codesign"]["integration_semantics"]
    topology = candidate["codesign"]["topology_summary"]
    explicitness = candidate["codesign"]["explicitness_metrics"]
    assert semantics["shared_front_end_and_closure_component_table"]
    assert semantics["closure_present_in_pre_click_netlist"]
    assert semantics["post_click_parameters_derived_from_attached_components"]
    assert not semantics["separated_block_fallback_used"]
    assert topology["closure_attachment_count"] >= 16
    assert topology["closure_component_count"] >= 27
    assert explicitness["uses_codesigned_netlist"]


def test_codesign_progress_output_can_be_enabled(capsys) -> None:
    run_preferred_chain_codesign_benchmark(
        SHOT_TRIGGER_SPEC,
        n_trials=2,
        seed=20260408,
        case_names=("a0b0",),
        verbose_progress=True,
    )
    captured = capsys.readouterr()
    assert "preferred-chain-codesign" in captured.err
    assert "pre-click-race" in captured.err
    assert "post-click-closure" in captured.err


def test_codesign_suite_meets_ticket_acceptance() -> None:
    summary = run_preferred_chain_codesign_benchmark(
        SHOT_TRIGGER_SPEC,
        n_trials=360,
        seed=20260403,
    )
    metrics = summary["summary_metrics"]
    assert metrics["front_end_fraction_pass"]
    assert metrics["winner_law_pass"]
    assert metrics["correlator_pass"]
    assert metrics["chsh_pass"]
    assert metrics["pre_click_transparency_pass"]
    assert metrics["winner_drain_dominance_pass"]
    assert metrics["loser_residual_pass"]
    assert metrics["completion_pass"]
    assert metrics["energy_accounting_pass"]
    assert metrics["architecture_explicitness_pass"]
    assert metrics["architectural_refinement_pass"]
    assert metrics["no_trivial_exact_weight_assignment"]
    assert metrics["proceed_to_next_phase"]


def test_codesign_report_smoke_writes_required_artifacts(tmp_path: Path) -> None:
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

    outputs = build_preferred_chain_codesign_report(
        tmp_path / "summary",
        detector_next_summary_csv=detector_next_summary,
        n_trials=12,
    )

    assert Path(outputs["summary_md"]).exists()
    assert Path(outputs["summary_json"]).exists()
    assert Path(outputs["summary_csv"]).exists()
    assert Path(outputs["design_md"]).exists()
    assert Path(outputs["candidate_comparison_csv"]).exists()
    assert Path(outputs["netlist_dir"]).exists()
    assert Path(outputs["pre_click_dir"]).exists()
    assert Path(outputs["post_click_dir"]).exists()
    assert Path(outputs["full_chain_dir"]).exists()
    assert Path(outputs["energy_dir"]).exists()

    summary_text = Path(outputs["summary_md"]).read_text(encoding="utf-8")
    assert "Preferred Chain Codesign Summary" in summary_text
    summary_json = json.loads(Path(outputs["summary_json"]).read_text(encoding="utf-8"))
    assert "summary_metrics" in summary_json
    assert "comparison_rows" in summary_json
    assert "netlist_rows" in summary_json
    assert (tmp_path / "summary" / "netlist" / "integrated_netlist_topology.png").exists()
    assert (tmp_path / "summary" / "pre_click" / "pre_click_transparency_vs_current_baseline.png").exists()
    assert (tmp_path / "summary" / "post_click" / "winner_drain_energy_fraction.png").exists()
    assert (tmp_path / "summary" / "post_click" / "remaining_shared_energy_vs_time.png").exists()
    assert (tmp_path / "summary" / "full_chain" / "winner_frequency_exact_vs_empirical.png").exists()
    assert (tmp_path / "summary" / "energy_accounting" / "whole_trial_energy_flow_summary.png").exists()
