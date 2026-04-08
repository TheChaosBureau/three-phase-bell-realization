from __future__ import annotations

import ctypes.util
import json
from pathlib import Path

import pytest

pytest.importorskip("PySpice")

from physical_front_end_candidate.experiments.build_spice_driven_baseline_reconciliation_report import (
    build_spice_driven_baseline_reconciliation_report,
)
from physical_front_end_candidate.spice_driven_baseline_reconciliation import (
    BaselineRunSpec,
    run_spice_driven_baseline_reconciliation,
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


def _compact_specs() -> tuple[BaselineRunSpec, BaselineRunSpec]:
    return (
        BaselineRunSpec(
            label="reference_small",
            source_kind="preferred_chain",
            n_trials=6,
            seed=20260411,
            case_names=("case_a",),
        ),
        BaselineRunSpec(
            label="nominal_small",
            source_kind="robustness_baseline_only",
            n_trials=4,
            seed=20260412,
            case_names=("case_a",),
        ),
    )


def test_spice_driven_baseline_reconciliation_classifies_configuration_mismatch() -> None:
    _require_ngspice()
    reference_spec, nominal_spec = _compact_specs()
    summary = run_spice_driven_baseline_reconciliation(
        SHOT_TRIGGER_SPEC,
        reference_spec=reference_spec,
        nominal_spec=nominal_spec,
    )
    assert summary["summary_metrics"]["reproduction_matches_reference"] is True
    assert summary["root_cause"]["classification"] == "configuration mismatch"
    mismatches = {row["setting_key"] for row in summary["comparison_rows"] if not row["matches"]}
    assert mismatches == {"driver", "n_trials", "seed", "source_kind"}


def test_spice_driven_baseline_reconciliation_compares_all_major_dimensions() -> None:
    _require_ngspice()
    reference_spec, nominal_spec = _compact_specs()
    summary = run_spice_driven_baseline_reconciliation(
        SHOT_TRIGGER_SPEC,
        reference_spec=reference_spec,
        nominal_spec=nominal_spec,
    )
    keys = {row["setting_key"] for row in summary["comparison_rows"]}
    assert keys == {
        "benchmark_cases",
        "n_trials",
        "seed",
        "source_kind",
        "driver",
        "trace_ingestion_path",
        "trace_preprocessing",
        "boundary_settings",
        "detector_spec",
        "latch_settings",
        "spice_front_end_artifact_identity",
        "spice_front_end_config",
        "closure_drain_config",
        "metric_aggregation_logic",
    }


def test_spice_driven_baseline_reconciliation_progress_output_can_be_enabled(capsys) -> None:
    _require_ngspice()
    reference_spec, nominal_spec = _compact_specs()
    run_spice_driven_baseline_reconciliation(
        SHOT_TRIGGER_SPEC,
        reference_spec=reference_spec,
        nominal_spec=nominal_spec,
        verbose_progress=True,
    )
    captured = capsys.readouterr()
    assert "spice-driven-baseline-reconciliation" in captured.err
    assert "reference-complete" in captured.err
    assert "reproduction-complete" in captured.err


def test_spice_driven_baseline_reconciliation_report_smoke_writes_required_artifacts(tmp_path: Path) -> None:
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
    reference_spec, nominal_spec = _compact_specs()
    outputs = build_spice_driven_baseline_reconciliation_report(
        tmp_path / "summary",
        detector_next_summary_csv=detector_next_summary,
        reference_spec=reference_spec,
        nominal_spec=nominal_spec,
        verbose_progress=False,
    )
    assert Path(outputs["summary_md"]).exists()
    assert Path(outputs["reconciliation_note"]).exists()
    assert Path(outputs["comparison_csv"]).exists()
    assert Path(outputs["metric_csv"]).exists()
    assert Path(outputs["summary_metrics_json"]).exists()
    assert Path(outputs["summary_metrics_csv"]).exists()
    assert Path(outputs["comparison_dir"]).exists()
    assert Path(outputs["reproduction_dir"]).exists()
    summary_text = Path(outputs["summary_md"]).read_text(encoding="utf-8")
    assert "SPICE-Driven Baseline Reconciliation Summary" in summary_text
    assert "Root-cause classification" in summary_text
    note_text = Path(outputs["reconciliation_note"]).read_text(encoding="utf-8")
    assert "Settings That Differed" in note_text
    assert "Reproduction matches the earlier SPICE-driven baseline: True." in note_text
    summary_json = json.loads(Path(outputs["summary_metrics_json"]).read_text(encoding="utf-8"))
    assert summary_json["root_cause"]["classification"] == "configuration mismatch"
    assert "summary" not in summary_json["reproduction_run"]
    assert "summary" not in summary_json["reference_run"]
    assert "summary" not in summary_json["nominal_run"]
    assert (tmp_path / "summary" / "baseline_metric_comparison.png").exists()
    assert (tmp_path / "summary" / "reproduction_vs_reference.png").exists()
    assert (tmp_path / "summary" / "metric_difference_breakdown.png").exists()
    assert (tmp_path / "summary" / "configuration_difference_summary.png").exists()
    assert (tmp_path / "summary" / "comparison" / "reference_signature.json").exists()
    assert (tmp_path / "summary" / "comparison" / "nominal_signature.json").exists()
    assert (tmp_path / "summary" / "reproduction" / "reproduction_signature.json").exists()
