from __future__ import annotations

import json
from pathlib import Path

from detector_integration.experiments.run_summary_report import load_top_shot_trigger_spec
from physical_front_end_candidate.boundary_repro_check import classify_reproducibility, rerun_frozen_boundary_case
from physical_front_end_candidate.experiments.build_boundary_repro_check_report import build_physical_front_end_boundary_repro_check_report
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


def test_frozen_contract_is_enforced_exactly(tmp_path: Path) -> None:
    detector_csv = tmp_path / "detector_next_summary.csv"
    _write_detector_summary(detector_csv)
    detector_spec = load_top_shot_trigger_spec(detector_csv)
    detector_model_spec = {"family": detector_spec["family"], "model_params": dict(detector_spec["model_params"])}
    case = representative_physical_cases()[0]
    result = rerun_frozen_boundary_case(
        case["state"],
        case["analyzer"],
        detector_model_spec,
        seed=20260403,
        config={"min_trials_per_case": 20, "target_decisive_count": 3, "max_trials_per_case": 20, "batch_trials": 10},
    )
    assert result["config"].gain == 4.0
    assert result["config"].exposure_s == 5.0


def test_trial_count_increase_is_applied_and_reported(tmp_path: Path) -> None:
    detector_csv = tmp_path / "detector_next_summary.csv"
    _write_detector_summary(detector_csv)
    detector_spec = load_top_shot_trigger_spec(detector_csv)
    detector_model_spec = {"family": detector_spec["family"], "model_params": dict(detector_spec["model_params"])}
    case = representative_physical_cases()[0]
    result = rerun_frozen_boundary_case(
        case["state"],
        case["analyzer"],
        detector_model_spec,
        seed=20260403,
        config={"min_trials_per_case": 20, "target_decisive_count": 3, "max_trials_per_case": 40, "batch_trials": 10},
    )
    assert result["total_trials"] >= 20
    assert result["decisive_count"] >= 0


def test_decisive_counts_are_included_in_outputs(tmp_path: Path) -> None:
    detector_csv = tmp_path / "detector_next_summary.csv"
    _write_detector_summary(detector_csv)
    outputs = build_physical_front_end_boundary_repro_check_report(
        tmp_path / "repro",
        detector_next_summary_csv=detector_csv,
        min_trials_per_case=20,
        target_decisive_count=3,
        max_trials_per_case=40,
        batch_trials=10,
    )
    summary = json.loads(Path(outputs["summary_json"]).read_text(encoding="utf-8"))
    assert all("decisive_count" in row for row in summary["results"])
    assert all("total_trials" in row for row in summary["results"])


def test_summary_report_classifies_reproducibility_deterministically() -> None:
    reproducible = classify_reproducibility(
        [
            {"sufficient_evidence": True, "rms_error": 0.01, "max_abs_error": 0.02},
            {"sufficient_evidence": True, "rms_error": 0.02, "max_abs_error": 0.03},
        ]
    )
    not_repro = classify_reproducibility(
        [
            {"sufficient_evidence": True, "rms_error": 0.08, "max_abs_error": 0.11},
            {"sufficient_evidence": True, "rms_error": 0.06, "max_abs_error": 0.07},
        ]
    )
    inconclusive = classify_reproducibility(
        [
            {"sufficient_evidence": False, "rms_error": 0.01, "max_abs_error": 0.02},
        ]
    )
    assert reproducible["outcome"] == "reproducible"
    assert not_repro["outcome"] == "not reproducible"
    assert inconclusive["outcome"] == "inconclusive"
