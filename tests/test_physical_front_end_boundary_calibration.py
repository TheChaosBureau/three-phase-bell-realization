from __future__ import annotations

import json
from pathlib import Path

from detector_integration.experiments.run_summary_report import load_top_shot_trigger_spec
from physical_front_end_candidate.boundary_calibration import resolved_calibrated_boundary_config, run_calibrated_boundary_case
from physical_front_end_candidate.experiments.build_boundary_calibration_report import build_physical_front_end_boundary_calibration_report
from physical_front_end_candidate.two_branch_candidate import representative_physical_cases


def _write_detector_summary(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "model,rank,score,linearity_rms_rel,dark_count_rate,race_rms_error,mismatch_penalty,branch_asymmetry_amplification,waiting_time_penalty,params_json",
                'shot_trigger,1,0.1,0.01,0.0,0.01,0.02,0.03,0.04,"{""dead_time"": 0.0, ""eps_event"": 0.5, ""lambda_dark"": 1e-06, ""p_trig"": 0.8}"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_calibrated_point_reproduces_acceptable_winner_law(tmp_path: Path) -> None:
    summary_csv = tmp_path / "detector_next_summary.csv"
    _write_detector_summary(summary_csv)
    detector_spec = load_top_shot_trigger_spec(summary_csv)
    detector_model_spec = {"family": detector_spec["family"], "model_params": dict(detector_spec["model_params"])}
    case = representative_physical_cases()[0]
    result = run_calibrated_boundary_case(case["state"], case["analyzer"], detector_model_spec, n_trials=6, seed=20260403)
    assert result["run"]["metrics"]["rms_error"] >= 0.0
    assert result["run"]["metrics"]["max_abs_error"] >= 0.0


def test_local_gain_sweep_report_executes_consistently(tmp_path: Path) -> None:
    summary_csv = tmp_path / "detector_next_summary.csv"
    _write_detector_summary(summary_csv)
    outputs = build_physical_front_end_boundary_calibration_report(tmp_path / "calibration", detector_next_summary_csv=summary_csv, n_trials=6)
    summary = json.loads(Path(outputs["summary_json"]).read_text(encoding="utf-8"))
    gain_summary = summary["gain_summary"]
    assert len(gain_summary) == len(resolved_calibrated_boundary_config().gain_sweep)
    assert all(row["winner_rms_error"] >= 0.0 for row in gain_summary)


def test_local_exposure_sweep_report_executes_consistently(tmp_path: Path) -> None:
    summary_csv = tmp_path / "detector_next_summary.csv"
    _write_detector_summary(summary_csv)
    outputs = build_physical_front_end_boundary_calibration_report(tmp_path / "calibration", detector_next_summary_csv=summary_csv, n_trials=6)
    summary = json.loads(Path(outputs["summary_json"]).read_text(encoding="utf-8"))
    exposure_summary = summary["exposure_summary"]
    assert len(exposure_summary) == len(resolved_calibrated_boundary_config().exposure_sweep_s)
    assert all(row["winner_rms_error"] >= 0.0 for row in exposure_summary)


def test_frozen_boundary_note_contains_required_fields(tmp_path: Path) -> None:
    summary_csv = tmp_path / "detector_next_summary.csv"
    _write_detector_summary(summary_csv)
    outputs = build_physical_front_end_boundary_calibration_report(tmp_path / "calibration", detector_next_summary_csv=summary_csv, n_trials=6)
    note = Path(outputs["frozen_boundary_note_md"]).read_text(encoding="utf-8")
    assert "piecewise:linear:20.0ms" in note
    assert "Gain: 4.000x" in note
    assert "Exposure: 5.000s" in note
    assert "winner_index" in note
    assert "winner_valid" in note
