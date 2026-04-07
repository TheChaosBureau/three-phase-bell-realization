from __future__ import annotations

import ctypes.util
import json
from pathlib import Path

import pytest

pytest.importorskip("PySpice")

from physical_front_end_candidate.experiments.build_spice_driven_robustness_report import (
    build_spice_driven_robustness_report,
)
from physical_front_end_candidate.spice_driven_robustness import (
    BOUNDARY_VARIATION_KEY,
    CLOSURE_VARIATION_KEY,
    COUPLING_MISMATCH_KEY,
    FRONT_END_TOLERANCES_KEY,
    LEAKAGE_VARIATION_KEY,
    LOAD_MISMATCH_KEY,
    SpiceDrivenRobustnessConfig,
    run_spice_driven_robustness_sweep,
)

SHOT_TRIGGER_SPEC = {
    "family": "shot_trigger",
    "model_params": {"eps_event": 0.5, "p_trig": 0.8, "lambda_dark": 1e-6, "dead_time": 0.0},
    "gain_scale": 2.0,
}


def _require_ngspice() -> None:
    libngspice = ctypes.util.find_library("ngspice") or ctypes.util.find_library("libngspice")
    if not libngspice:
        pytest.skip("ngspice shared library is not available in this environment")


def _compact_robustness_config() -> SpiceDrivenRobustnessConfig:
    return SpiceDrivenRobustnessConfig(
        front_end_tolerance_levels=(0.01,),
        coupling_mismatch_levels=(0.02,),
        load_mismatch_levels=(0.02,),
        leakage_severity_levels=(0.10,),
        boundary_gains=(4.0, 4.5),
        boundary_exposures_s=(5.0,),
        closure_variation_levels=(0.10,),
    )


def test_spice_driven_robustness_sweep_covers_all_classes_and_ranking() -> None:
    _require_ngspice()
    summary = run_spice_driven_robustness_sweep(
        SHOT_TRIGGER_SPEC,
        n_trials=8,
        seed=20260412,
        case_names=("case_a",),
        robustness_config=_compact_robustness_config(),
    )
    class_keys = {row["class_key"] for row in summary["class_rows"]}
    assert class_keys == {
        FRONT_END_TOLERANCES_KEY,
        COUPLING_MISMATCH_KEY,
        LOAD_MISMATCH_KEY,
        LEAKAGE_VARIATION_KEY,
        BOUNDARY_VARIATION_KEY,
        CLOSURE_VARIATION_KEY,
    }
    assert len(summary["sensitivity_ranking_rows"]) == 6
    assert summary["summary_metrics"]["configuration_count"] == len(summary["perturbation_rows"])
    assert any(row["pass_count"] >= 0 for row in summary["safe_window_rows"])


def test_spice_driven_robustness_boundary_grid_is_explicit() -> None:
    _require_ngspice()
    config = SpiceDrivenRobustnessConfig(
        front_end_tolerance_levels=(),
        coupling_mismatch_levels=(),
        load_mismatch_levels=(),
        leakage_severity_levels=(),
        boundary_gains=(3.5, 4.0),
        boundary_exposures_s=(4.0, 5.0),
        closure_variation_levels=(),
    )
    summary = run_spice_driven_robustness_sweep(
        SHOT_TRIGGER_SPEC,
        n_trials=6,
        seed=20260412,
        case_names=("case_a",),
        robustness_config=config,
    )
    rows = summary["perturbation_rows"]
    assert len(rows) == 4
    assert all(row["class_key"] == BOUNDARY_VARIATION_KEY for row in rows)
    assert {(row["gain"], row["exposure_s"]) for row in rows} == {(3.5, 4.0), (3.5, 5.0), (4.0, 4.0), (4.0, 5.0)}


def test_spice_driven_robustness_progress_output_can_be_enabled(capsys) -> None:
    _require_ngspice()
    run_spice_driven_robustness_sweep(
        SHOT_TRIGGER_SPEC,
        n_trials=2,
        seed=20260412,
        case_names=("case_a",),
        robustness_config=SpiceDrivenRobustnessConfig(
            front_end_tolerance_levels=(0.01,),
            coupling_mismatch_levels=(),
            load_mismatch_levels=(),
            leakage_severity_levels=(),
            boundary_gains=(),
            boundary_exposures_s=(),
            closure_variation_levels=(),
        ),
        verbose_progress=True,
    )
    captured = capsys.readouterr()
    assert "spice-driven-robustness" in captured.err
    assert "baseline-complete" in captured.err
    assert "perturbation-complete" in captured.err


def test_spice_driven_robustness_report_smoke_writes_required_artifacts(tmp_path: Path) -> None:
    _require_ngspice()
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
    outputs = build_spice_driven_robustness_report(
        tmp_path / "summary",
        detector_next_summary_csv=detector_next_summary,
        n_trials=4,
        case_names=("case_a",),
        robustness_config=_compact_robustness_config(),
    )
    assert Path(outputs["summary_md"]).exists()
    assert Path(outputs["design_md"]).exists()
    assert Path(outputs["summary_metrics_csv"]).exists()
    assert Path(outputs["summary_metrics_json"]).exists()
    assert Path(outputs["sensitivity_ranking_csv"]).exists()
    assert Path(outputs["front_end_tolerances_dir"]).exists()
    assert Path(outputs["coupling_mismatch_dir"]).exists()
    assert Path(outputs["load_mismatch_dir"]).exists()
    assert Path(outputs["leakage_variation_dir"]).exists()
    assert Path(outputs["boundary_variation_dir"]).exists()
    assert Path(outputs["closure_variation_dir"]).exists()
    summary_text = Path(outputs["summary_md"]).read_text(encoding="utf-8")
    assert "SPICE-Driven Robustness Summary" in summary_text
    assert "Most dangerous class" in summary_text
    summary_json = json.loads(Path(outputs["summary_metrics_json"]).read_text(encoding="utf-8"))
    assert "summary_metrics" in summary_json
    assert "sensitivity_ranking_rows" in summary_json
    assert (tmp_path / "summary" / "sensitivity_ranking.png").exists()
    assert (tmp_path / "summary" / "baseline_vs_class_worst_case.png").exists()
    assert (tmp_path / "summary" / FRONT_END_TOLERANCES_KEY / "sweep_results.csv").exists()
    assert (tmp_path / "summary" / BOUNDARY_VARIATION_KEY / "damage_score_heatmap.png").exists()
