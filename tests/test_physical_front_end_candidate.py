from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from detector_integration.detectors import simulate_branch_nucleation
from physical_front_end_candidate.experiments.build_summary_report import build_physical_front_end_candidate_report
from physical_front_end_candidate.integration import run_two_branch_physical_handoff
from physical_front_end_candidate.two_branch_candidate import representative_physical_cases, simulate_two_branch_physical_candidate

SHOT_TRIGGER_SPEC = {
    "family": "shot_trigger",
    "model_params": {"eps_event": 0.5, "p_trig": 0.8, "lambda_dark": 1e-6, "dead_time": 0.0},
}
INTEGRATION_SPEC = {
    "family": "shot_trigger",
    "model_params": {"eps_event": 0.5, "p_trig": 0.8, "lambda_dark": 1e-6, "dead_time": 0.0},
    "gain_scale": 300.0,
}


def test_physical_candidate_branch_fractions_sum_to_one() -> None:
    case = representative_physical_cases()[0]
    result = simulate_two_branch_physical_candidate(case["state"], case["analyzer"])
    fractions = np.array([result["branch_energy_fraction"][label] for label in result["branch_labels"]], dtype=float)
    assert abs(float(np.sum(fractions)) - 1.0) < 1e-12


def test_physical_candidate_fractions_remain_close_to_exact_weights() -> None:
    case = representative_physical_cases()[1]
    result = simulate_two_branch_physical_candidate(case["state"], case["analyzer"])
    fractions = np.array([result["branch_energy_fraction"][label] for label in result["branch_labels"]], dtype=float)
    exact = np.array([result["exact_weight"][label] for label in result["branch_labels"]], dtype=float)
    assert result["metrics"]["rms_error"] < 0.03
    assert result["metrics"]["max_abs_error"] < 0.05
    assert np.allclose(fractions, exact, atol=0.05)


def test_detector_export_is_valid_and_consumable() -> None:
    case = representative_physical_cases()[0]
    result = run_two_branch_physical_handoff(case["state"], case["analyzer"], SHOT_TRIGGER_SPEC, n_trials=40, seed=20260403)
    for envelope in result["detector_envelopes"]:
        assert envelope["kind"] == "exp_decay"
        assert envelope["power_scale"] >= 0.0
        assert envelope["decay_tau"] > 0.0
        click_time = simulate_branch_nucleation(SHOT_TRIGGER_SPEC, 1.0, envelope, np.random.default_rng(20260403))
        assert click_time is None or click_time >= 0.0


def test_integrated_winner_frequencies_remain_close_to_exact_weights() -> None:
    case = representative_physical_cases()[0]
    result = run_two_branch_physical_handoff(case["state"], case["analyzer"], INTEGRATION_SPEC, n_trials=500, seed=20260403)
    assert result["metrics"]["rms_error"] < 0.03
    assert result["metrics"]["max_abs_error"] < 0.05
    assert result["decisive_fraction"] > 0.95


def test_physical_front_end_candidate_report_smoke_writes_artifacts(tmp_path: Path) -> None:
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

    outputs = build_physical_front_end_candidate_report(
        tmp_path / "summary",
        detector_next_summary_csv=detector_next_summary,
        n_trials=80,
    )

    assert Path(outputs["summary_md"]).exists()
    assert Path(outputs["summary_json"]).exists()
    assert Path(outputs["summary_csv"]).exists()
    assert Path(outputs["design_md"]).exists()
    assert Path(outputs["spice_facing_interface_md"]).exists()
    assert Path(tmp_path / "summary" / "two_branch" / "two_branch_summary.json").exists()
    assert Path(tmp_path / "summary" / "integration" / "integration_summary.json").exists()
    report_text = Path(outputs["summary_md"]).read_text(encoding="utf-8")
    assert "Physical Front-End Candidate Summary" in report_text
    summary = json.loads(Path(outputs["summary_json"]).read_text(encoding="utf-8"))
    assert "summary_metrics" in summary
    assert "acceptance" in summary
