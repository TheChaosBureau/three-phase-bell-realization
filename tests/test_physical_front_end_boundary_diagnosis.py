from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from physical_front_end_candidate.boundary_diagnosis import (
    BOUNDARY_GAIN_SWEEP,
    classify_boundary_outcome,
    expected_click_count,
    materialize_exported_trace,
    scale_trace_power,
    synthetic_common_envelope_trace,
)
from physical_front_end_candidate.experiments.build_boundary_diagnosis_report import build_physical_front_end_boundary_diagnosis_report
from physical_front_end_candidate.two_branch_candidate import representative_physical_cases

SHOT_TRIGGER_SPEC = {
    "family": "shot_trigger",
    "model_params": {"eps_event": 0.5, "p_trig": 0.8, "lambda_dark": 1e-6, "dead_time": 0.0},
}


def test_scale_sweep_report_covers_all_benchmark_cases(tmp_path: Path) -> None:
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
    outputs = build_physical_front_end_boundary_diagnosis_report(
        tmp_path / "diagnosis",
        detector_next_summary_csv=detector_next_summary,
        n_trials=6,
    )
    scale_csv = tmp_path / "diagnosis" / "scale_sweep" / "scale_sweep.csv"
    rows = list(csv.DictReader(scale_csv.open("r", encoding="utf-8", newline="")))
    assert len(rows) == len(representative_physical_cases()) * len(BOUNDARY_GAIN_SWEEP)
    assert Path(outputs["summary_json"]).exists()


def test_expected_click_count_is_finite_and_monotone_under_scaling() -> None:
    case = representative_physical_cases()[0]
    trace = materialize_exported_trace(case["state"], case["analyzer"])
    mu_1 = expected_click_count(scale_trace_power(trace, 1.0), SHOT_TRIGGER_SPEC)
    mu_4 = expected_click_count(scale_trace_power(trace, 4.0), SHOT_TRIGGER_SPEC)
    assert np.isfinite(mu_1["mean_mu"])
    assert np.isfinite(mu_4["mean_mu"])
    assert mu_4["mean_mu"] > mu_1["mean_mu"]


def test_synthetic_common_envelope_preserves_exact_branch_weight_ratios() -> None:
    case = representative_physical_cases()[1]
    trace = materialize_exported_trace(case["state"], case["analyzer"])
    synthetic = synthetic_common_envelope_trace(trace)
    branch_1 = np.asarray(synthetic["exported_branch_power"]["branch_1"], dtype=float)
    branch_2 = np.asarray(synthetic["exported_branch_power"]["branch_2"], dtype=float)
    exact_1 = float(trace["candidate"]["exact_weight"]["branch_1"])
    exact_2 = float(trace["candidate"]["exact_weight"]["branch_2"])
    mask = branch_2 > 1e-12
    ratios = branch_1[mask] / branch_2[mask]
    assert np.allclose(ratios, exact_1 / exact_2, atol=1e-6)


def test_classification_is_deterministic_from_metrics() -> None:
    regime = classify_boundary_outcome(
        best_physical={"winner_rms_error": 0.02, "winner_max_error": 0.04},
        best_synthetic={"winner_rms_error": 0.02, "winner_max_error": 0.04},
    )
    adapter = classify_boundary_outcome(
        best_physical={"winner_rms_error": 0.08, "winner_max_error": 0.11},
        best_synthetic={"winner_rms_error": 0.02, "winner_max_error": 0.04},
    )
    deeper = classify_boundary_outcome(
        best_physical={"winner_rms_error": 0.08, "winner_max_error": 0.11},
        best_synthetic={"winner_rms_error": 0.06, "winner_max_error": 0.07},
    )
    assert regime["classification"] == "regime mismatch"
    assert adapter["classification"] == "adapter/export mismatch"
    assert deeper["classification"] == "deeper detector abstraction mismatch"


def test_boundary_diagnosis_report_smoke_writes_artifacts(tmp_path: Path) -> None:
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
    outputs = build_physical_front_end_boundary_diagnosis_report(
        tmp_path / "diagnosis",
        detector_next_summary_csv=detector_next_summary,
        n_trials=6,
    )
    assert Path(outputs["summary_md"]).exists()
    assert Path(outputs["summary_json"]).exists()
    assert Path(outputs["summary_csv"]).exists()
    assert Path(outputs["boundary_diagnosis_note_md"]).exists()
    summary = json.loads(Path(outputs["summary_json"]).read_text(encoding="utf-8"))
    assert "classification" in summary
    assert summary["classification"]["classification"] in {
        "regime mismatch",
        "adapter/export mismatch",
        "deeper detector abstraction mismatch",
    }
