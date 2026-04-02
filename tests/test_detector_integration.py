from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from detector_integration.detectors.closure_latch import first_event_latch
from detector_integration.experiments.compare_with_exact import build_detector_integration_comparison
from detector_integration.experiments.run_summary_report import build_detector_integration_summary_report
from detector_integration.frontends.four_branch import four_branch_weights
from detector_integration.frontends.two_branch import two_branch_weights
from detector_integration.sim.run_four_branch_integration import run_chsh_trials, run_four_branch_trials
from detector_integration.sim.run_two_branch_integration import run_two_branch_trials
from src.benchmarks import singlet_closed_form_weights
from src.shared_4tank_core import singlet_state

SHOT_TRIGGER_SPEC = {
    "family": "shot_trigger",
    "model_params": {"eps_event": 0.5, "p_trig": 0.8, "lambda_dark": 1e-6, "dead_time": 0.0},
}
POISSON_SPEC = {
    "family": "poisson_linear",
    "model_params": {"lambda_dark": 1e-6, "alpha": 1.6, "dead_time": 0.0},
}
DEFAULT_ENVELOPE = {"kind": "constant", "power_scale": 4.0, "dt": 1e-4, "t_max": 5.0}


def test_two_branch_weights_follow_rotation_contract() -> None:
    weights = two_branch_weights(np.array([1.0, 0.0], dtype=np.complex128), 30.0)
    assert np.allclose(weights, np.array([0.75, 0.25]), atol=1e-12)


def test_four_branch_weights_match_existing_singlet_reference() -> None:
    weights = four_branch_weights(singlet_state(), a_deg=45.0, b_deg=22.5)
    assert np.allclose(weights, singlet_closed_form_weights(45.0, 22.5), atol=1e-12)


def test_first_event_latch_returns_earliest_finite_event() -> None:
    assert first_event_latch(np.array([np.inf, 0.2, 0.5])) == 1
    assert first_event_latch(np.array([np.inf, np.inf])) == -1


def test_two_branch_integration_tracks_exact_weights() -> None:
    result = run_two_branch_trials(
        np.array([1.0, 0.0], dtype=np.complex128),
        30.0,
        SHOT_TRIGGER_SPEC,
        n_trials=2_500,
        seed=20260402,
        envelope_params=DEFAULT_ENVELOPE,
    )
    assert result["metrics"]["rms_error"] < 0.02
    assert result["metrics"]["max_abs_error"] < 0.05


def test_four_branch_integration_tracks_exact_weights_and_correlator() -> None:
    result = run_four_branch_trials(
        singlet_state(),
        a_deg=45.0,
        b_deg=22.5,
        detector_params=SHOT_TRIGGER_SPEC,
        n_trials=4_000,
        seed=20260402,
        envelope_params=DEFAULT_ENVELOPE,
    )
    assert result["metrics"]["rms_error"] < 0.03
    assert result["metrics"]["correlator_error"] < 0.05


def test_chsh_integration_stays_close_to_exact_target() -> None:
    result = run_chsh_trials(
        singlet_state(),
        detector_params=SHOT_TRIGGER_SPEC,
        n_trials=4_000,
        seed=20260402,
        envelope_params=DEFAULT_ENVELOPE,
    )
    assert abs(abs(result["empirical_s"]) - 2.0 * math.sqrt(2.0)) < 0.1


def test_compare_with_exact_smoke_writes_artifacts(tmp_path: Path) -> None:
    outputs = build_detector_integration_comparison(
        tmp_path,
        n_two_branch_trials=250,
        n_four_branch_trials=400,
    )
    assert Path(outputs["comparison_csv"]).exists()
    assert Path(outputs["comparison_json"]).exists()


def test_summary_report_smoke_uses_top_shot_trigger_and_writes_report(tmp_path: Path) -> None:
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

    outputs = build_detector_integration_summary_report(
        tmp_path / "summary",
        detector_next_summary_csv=detector_next_summary,
        n_two_branch_trials=250,
        n_four_branch_trials=400,
    )

    assert Path(outputs["summary_md"]).exists()
    assert Path(outputs["summary_json"]).exists()
    assert Path(outputs["summary_csv"]).exists()
    report_text = Path(outputs["summary_md"]).read_text(encoding="utf-8")
    assert "Two-branch RMS winner-law error" in report_text
    assert "Top Shot Trigger Parameter Set" in report_text
