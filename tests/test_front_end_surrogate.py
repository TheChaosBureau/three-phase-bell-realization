from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from front_end_surrogate.experiments.build_summary_report import build_front_end_surrogate_report
from front_end_surrogate.four_branch_surrogate import simulate_four_branch_surrogate
from front_end_surrogate.integration_adapter import run_four_branch_surrogate_handoff, run_two_branch_surrogate_handoff
from front_end_surrogate.two_branch_surrogate import representative_two_branch_cases, simulate_two_branch_surrogate

SHOT_TRIGGER_SPEC = {
    "family": "shot_trigger",
    "model_params": {"eps_event": 0.5, "p_trig": 0.8, "lambda_dark": 1e-6, "dead_time": 0.0},
}


def test_two_branch_surrogate_fractions_match_exact_weights() -> None:
    case = representative_two_branch_cases()[0]
    result = simulate_two_branch_surrogate(case["state"], case["analyzer"])
    fractions = np.array([result["branch_energy_fraction"][label] for label in result["branch_labels"]], dtype=float)
    exact = np.array([result["exact_weight"][label] for label in result["branch_labels"]], dtype=float)
    assert abs(float(np.sum(fractions)) - 1.0) < 1e-12
    assert np.allclose(fractions, exact, atol=1e-12)


def test_four_branch_surrogate_fractions_match_exact_weights() -> None:
    result = simulate_four_branch_surrogate(a_deg=45.0, b_deg=22.5)
    fractions = np.array([result["branch_energy_fraction"][label] for label in result["branch_labels"]], dtype=float)
    exact = np.array([result["exact_weight"][label] for label in result["branch_labels"]], dtype=float)
    assert abs(float(np.sum(fractions)) - 1.0) < 1e-12
    assert np.allclose(fractions, exact, atol=1e-12)


def test_surrogate_handoff_into_detector_latch_stays_reasonable() -> None:
    case = representative_two_branch_cases()[0]
    two = run_two_branch_surrogate_handoff(case["state"], case["analyzer"], SHOT_TRIGGER_SPEC, n_trials=200, seed=20260402)
    four = run_four_branch_surrogate_handoff(a_deg=45.0, b_deg=22.5, detector_spec=SHOT_TRIGGER_SPEC, n_trials=300, seed=20260402)
    assert two["metrics"]["rms_error"] < 0.05
    assert two["metrics"]["max_abs_error"] < 0.05
    assert four["metrics"]["rms_error"] < 0.03
    assert four["metrics"]["correlator_error"] < 0.05


def test_front_end_surrogate_summary_report_smoke_writes_artifacts(tmp_path: Path) -> None:
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

    outputs = build_front_end_surrogate_report(
        tmp_path / "summary",
        detector_next_summary_csv=detector_next_summary,
        n_two_branch_trials=50,
        n_four_branch_trials=80,
    )

    assert Path(outputs["summary_md"]).exists()
    assert Path(outputs["summary_json"]).exists()
    assert Path(outputs["summary_csv"]).exists()
    assert Path(outputs["spice_facing_interface_md"]).exists()
    report_text = Path(outputs["summary_md"]).read_text(encoding="utf-8")
    assert "Front-End Surrogate Summary" in report_text
    summary = json.loads(Path(outputs["summary_json"]).read_text(encoding="utf-8"))
    assert "summary_metrics" in summary
