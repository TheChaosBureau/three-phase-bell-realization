from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from physical_front_end_candidate.experiments.build_preferred_front_end_netlist_candidate_report import (
    build_preferred_front_end_netlist_candidate_report,
)
from physical_front_end_candidate.preferred_front_end_netlist_candidate import (
    preferred_front_end_netlist_benchmark_cases,
    run_preferred_front_end_netlist_benchmark,
    run_preferred_front_end_netlist_case,
    simulate_preferred_front_end_netlist_candidate,
)

SHOT_TRIGGER_SPEC = {
    "family": "shot_trigger",
    "model_params": {"eps_event": 0.5, "p_trig": 0.8, "lambda_dark": 1e-6, "dead_time": 0.0},
    "gain_scale": 2.0,
}


def test_netlist_candidate_energy_fractions_are_finite_and_normalized() -> None:
    case = preferred_front_end_netlist_benchmark_cases()[0]
    candidate = simulate_preferred_front_end_netlist_candidate(
        case["state4"],
        a_deg=case["a_deg"],
        b_deg=case["b_deg"],
    )
    fractions = np.asarray([candidate["branch_energy_fraction"][label] for label in candidate["branch_labels"]], dtype=float)
    assert np.all(np.isfinite(fractions))
    assert np.all(fractions >= 0.0)
    assert abs(float(np.sum(fractions)) - 1.0) < 1e-9


def test_netlist_candidate_export_remains_compatible_with_frozen_boundary() -> None:
    case = preferred_front_end_netlist_benchmark_cases()[1]
    result = run_preferred_front_end_netlist_case(
        case["state4"],
        a_deg=case["a_deg"],
        b_deg=case["b_deg"],
        detector_spec=SHOT_TRIGGER_SPEC,
        n_trials=16,
        seed=20260407,
    )
    assert result["boundary_config"]["gain"] == 4.0
    assert result["boundary_config"]["exposure_s"] == 5.0
    assert result["export_config"]["mode"] == "piecewise_envelope"


def test_netlist_candidate_is_not_a_trivial_exact_weight_assignment() -> None:
    case = preferred_front_end_netlist_benchmark_cases()[2]
    candidate = simulate_preferred_front_end_netlist_candidate(
        case["state4"],
        a_deg=case["a_deg"],
        b_deg=case["b_deg"],
    )
    explicitness = candidate["shared_core"]["explicitness_metrics"]
    topology = candidate["netlist"]["topology_summary"]
    assert not explicitness["forward_path_uses_exact_weights"]
    assert explicitness["uses_component_netlist"]
    assert explicitness["component_count"] >= 28
    assert topology["coupling_component_count"] >= 7


def test_netlist_candidate_energy_accounting_remains_finite_and_balanced() -> None:
    case = preferred_front_end_netlist_benchmark_cases()[3]
    result = run_preferred_front_end_netlist_case(
        case["state4"],
        a_deg=case["a_deg"],
        b_deg=case["b_deg"],
        detector_spec=SHOT_TRIGGER_SPEC,
        n_trials=48,
        seed=20260407,
    )
    energy = result["energy_accounting_summary"]
    assert energy["finite_outputs"]
    assert energy["energy_accounting_pass"]
    assert energy["max_energy_balance_abs_fraction"] < 1e-6


def test_netlist_candidate_progress_output_can_be_enabled(capsys) -> None:
    run_preferred_front_end_netlist_benchmark(
        SHOT_TRIGGER_SPEC,
        n_trials=2,
        seed=20260407,
        case_names=("case_a",),
        verbose_progress=True,
    )
    captured = capsys.readouterr()
    assert "preferred-front-end-netlist" in captured.err
    assert "pre-click-race" in captured.err
    assert "post-click-closure" in captured.err


def test_netlist_candidate_suite_meets_ticket_acceptance() -> None:
    summary = run_preferred_front_end_netlist_benchmark(
        SHOT_TRIGGER_SPEC,
        n_trials=360,
        seed=20260403,
    )
    metrics = summary["summary_metrics"]
    assert metrics["front_end_fraction_pass"]
    assert metrics["winner_law_pass"]
    assert metrics["correlator_pass"]
    assert metrics["chsh_pass"]
    assert metrics["energy_accounting_pass"]
    assert metrics["architecture_explicitness_pass"]
    assert metrics["no_trivial_exact_weight_assignment"]
    assert metrics["proceed_to_next_phase"]


def test_netlist_candidate_report_smoke_writes_required_artifacts(tmp_path: Path) -> None:
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

    outputs = build_preferred_front_end_netlist_candidate_report(
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
    assert Path(outputs["front_end_dir"]).exists()
    assert Path(outputs["integration_dir"]).exists()
    assert Path(outputs["energy_dir"]).exists()

    summary_text = Path(outputs["summary_md"]).read_text(encoding="utf-8")
    assert "Preferred Front-End Netlist Candidate Summary" in summary_text
    summary_json = json.loads(Path(outputs["summary_json"]).read_text(encoding="utf-8"))
    assert "summary_metrics" in summary_json
    assert "comparison_rows" in summary_json
    assert "netlist_rows" in summary_json
    assert (tmp_path / "summary" / "netlist" / "netlist_topology.png").exists()
    assert (tmp_path / "summary" / "front_end" / "exact_vs_realized_four_branch_energy_fractions.png").exists()
    assert (tmp_path / "summary" / "integration" / "winner_frequency_exact_vs_empirical.png").exists()
    assert (tmp_path / "summary" / "energy_accounting" / "whole_trial_energy_flow_summary.png").exists()
