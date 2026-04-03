from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from detector_integration.detectors.closure_latch import LatchArbiterConfig, latch_first_event, validated_latch_arbiter_config
from detector_integration.experiments.run_latch_enabled_summary_report import build_latch_enabled_integration_report
from detector_integration.sim.run_four_branch_latch_integration import run_four_branch_latch_trials, run_latch_enabled_chsh_trials
from detector_integration.sim.run_two_branch_latch_integration import run_two_branch_latch_trials
from src.shared_4tank_core import singlet_state

SHOT_TRIGGER_SPEC = {
    "family": "shot_trigger",
    "model_params": {"eps_event": 0.5, "p_trig": 0.8, "lambda_dark": 1e-6, "dead_time": 0.0},
}
DEFAULT_ENVELOPE = {"kind": "constant", "power_scale": 4.0, "dt": 1e-4, "t_max": 5.0}


def test_latch_arbiter_resolves_tie_with_deterministic_priority() -> None:
    config = LatchArbiterConfig(input_delay_s=0.0, settle_time_s=1e-9, tie_window_s=5e-10, priority_order=(2, 0, 1, 3))
    result = latch_first_event(np.array([1.0, 2.0, 1.0 + 2e-10, np.inf]), config=config, rng=np.random.default_rng(20260403))
    assert result["winner_index"] == 2
    assert result["winner_valid"] is True
    assert result["tie_region"] is True


def test_latch_enabled_two_branch_integration_tracks_exact_weights() -> None:
    result = run_two_branch_latch_trials(
        np.array([1.0, 0.0], dtype=np.complex128),
        30.0,
        SHOT_TRIGGER_SPEC,
        n_trials=2_500,
        seed=20260402,
        envelope_params=DEFAULT_ENVELOPE,
        latch_config=validated_latch_arbiter_config(2),
    )
    assert result["metrics"]["rms_error"] < 0.02
    assert result["metrics"]["max_abs_error"] < 0.05


def test_latch_enabled_four_branch_and_chsh_preserve_targets() -> None:
    result = run_four_branch_latch_trials(
        singlet_state(),
        a_deg=45.0,
        b_deg=22.5,
        detector_params=SHOT_TRIGGER_SPEC,
        n_trials=4_000,
        seed=20260402,
        envelope_params=DEFAULT_ENVELOPE,
        latch_config=validated_latch_arbiter_config(4),
    )
    chsh = run_latch_enabled_chsh_trials(
        singlet_state(),
        detector_params=SHOT_TRIGGER_SPEC,
        n_trials=4_000,
        seed=20260402,
        envelope_params=DEFAULT_ENVELOPE,
        latch_config=validated_latch_arbiter_config(4),
    )
    assert result["metrics"]["rms_error"] < 0.03
    assert result["metrics"]["correlator_error"] < 0.05
    assert abs(abs(chsh["empirical_s"]) - 2.0 * math.sqrt(2.0)) < 0.1


def test_latch_enabled_summary_report_smoke_writes_artifacts(tmp_path: Path) -> None:
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

    outputs = build_latch_enabled_integration_report(
        tmp_path / "summary",
        detector_next_summary_csv=detector_next_summary,
        n_two_branch_trials=2_500,
        n_four_branch_trials=4_000,
        n_mismatch_trials=1_000,
    )

    assert Path(outputs["summary_md"]).exists()
    assert Path(outputs["summary_json"]).exists()
    assert Path(outputs["summary_csv"]).exists()
    assert Path(outputs["spice_abstraction_md"]).exists()
    report_text = Path(outputs["summary_md"]).read_text(encoding="utf-8")
    assert "Latch-Enabled Front-End Integration Summary" in report_text
    summary = json.loads(Path(outputs["summary_json"]).read_text(encoding="utf-8"))
    assert summary["acceptance"]["proceed_to_next_phase"] is True
