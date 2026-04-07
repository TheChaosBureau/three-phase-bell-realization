from __future__ import annotations

import ctypes.util
import json
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("PySpice")

from physical_front_end_candidate.experiments.build_spice_driven_preferred_chain_report import (
    build_spice_driven_preferred_chain_report,
)
from physical_front_end_candidate.spice_driven_preferred_chain import (
    run_spice_driven_preferred_chain_benchmark,
    run_spice_driven_preferred_chain_case,
    simulate_spice_driven_preferred_chain_candidate,
    spice_driven_preferred_chain_benchmark_cases,
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


def test_spice_driven_trace_ingestion_and_adapter_metadata_are_present() -> None:
    _require_ngspice()
    case = spice_driven_preferred_chain_benchmark_cases()[0]
    candidate = simulate_spice_driven_preferred_chain_candidate(
        case["state4"],
        a_deg=case["a_deg"],
        b_deg=case["b_deg"],
    )
    adapter = candidate["spice_boundary_adapter"]
    assert adapter["derived_from_actual_spice_traces"]
    assert adapter["upstream_artifact_kind"] == "actual_ngspice_generated_front_end_trace"
    assert adapter["power_alignment_scale"] > 0.0
    assert "actual_spice_front_end" in candidate


def test_spice_driven_boundary_export_is_finite_and_frozen() -> None:
    _require_ngspice()
    case = spice_driven_preferred_chain_benchmark_cases()[1]
    result = run_spice_driven_preferred_chain_case(
        case["state4"],
        a_deg=case["a_deg"],
        b_deg=case["b_deg"],
        detector_spec=SHOT_TRIGGER_SPEC,
        n_trials=32,
        seed=20260411,
    )
    assert result["export_config"]["mode"] == "piecewise_envelope"
    assert result["export_config"]["piecewise_mode"] == "linear"
    assert result["boundary_config"]["gain"] == 4.0
    assert result["boundary_config"]["exposure_s"] == 5.0
    assert all(np.all(np.isfinite(values)) for values in result["trace"]["exported_branch_power"].values())


def test_spice_driven_downstream_chain_runs_with_decisive_output() -> None:
    _require_ngspice()
    case = spice_driven_preferred_chain_benchmark_cases()[2]
    result = run_spice_driven_preferred_chain_case(
        case["state4"],
        a_deg=case["a_deg"],
        b_deg=case["b_deg"],
        detector_spec=SHOT_TRIGGER_SPEC,
        n_trials=120,
        seed=20260411,
    )
    assert result["decisive_fraction"] > 0.9
    assert result["timeout_fraction"] < 0.1
    assert result["post_click_summary"]["winner_drain_dominant"]


def test_spice_driven_post_click_and_energy_accounting_remain_valid() -> None:
    _require_ngspice()
    case = spice_driven_preferred_chain_benchmark_cases()[3]
    result = run_spice_driven_preferred_chain_case(
        case["state4"],
        a_deg=case["a_deg"],
        b_deg=case["b_deg"],
        detector_spec=SHOT_TRIGGER_SPEC,
        n_trials=120,
        seed=20260411,
    )
    post = result["post_click_summary"]
    energy = result["energy_accounting_summary"]
    assert post["winner_drain_dominance_rate"] >= 0.99
    assert post["mean_activated_loser_fraction"] < 0.05
    assert post["monotonic_remaining_energy"]
    assert energy["energy_accounting_pass"]
    assert energy["max_energy_balance_abs_fraction"] < 1e-6


def test_spice_driven_progress_output_can_be_enabled(capsys) -> None:
    _require_ngspice()
    run_spice_driven_preferred_chain_benchmark(
        SHOT_TRIGGER_SPEC,
        n_trials=2,
        seed=20260411,
        case_names=("case_a",),
        verbose_progress=True,
    )
    captured = capsys.readouterr()
    assert "spice-driven-preferred-chain" in captured.err
    assert "simulate-actual-spice-front-end" in captured.err
    assert "pre-click-race" in captured.err


def test_spice_driven_suite_meets_ticket_acceptance() -> None:
    _require_ngspice()
    summary = run_spice_driven_preferred_chain_benchmark(
        SHOT_TRIGGER_SPEC,
        n_trials=360,
        seed=20260403,
    )
    metrics = summary["summary_metrics"]
    assert metrics["front_end_fraction_pass"]
    assert metrics["winner_law_pass"]
    assert metrics["correlator_pass"]
    assert metrics["chsh_pass"]
    assert metrics["pre_click_transparency_pass"]
    assert metrics["winner_drain_dominance_pass"]
    assert metrics["loser_residual_pass"]
    assert metrics["energy_accounting_pass"]
    assert metrics["actual_spice_execution_pass"]
    assert metrics["spice_trace_ingestion_pass"]
    assert metrics["boundary_export_pass"]
    assert metrics["actual_spice_driven_pass"]
    assert metrics["proceed_to_next_phase"]


def test_spice_driven_report_smoke_writes_required_artifacts(tmp_path: Path) -> None:
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
    outputs = build_spice_driven_preferred_chain_report(
        tmp_path / "summary",
        detector_next_summary_csv=detector_next_summary,
        n_trials=12,
        case_names=("case_a",),
    )
    assert Path(outputs["summary_md"]).exists()
    assert Path(outputs["summary_json"]).exists()
    assert Path(outputs["summary_csv"]).exists()
    assert Path(outputs["design_md"]).exists()
    assert Path(outputs["candidate_comparison_csv"]).exists()
    assert Path(outputs["front_end_dir"]).exists()
    assert Path(outputs["boundary_dir"]).exists()
    assert Path(outputs["full_chain_dir"]).exists()
    assert Path(outputs["post_click_dir"]).exists()
    assert Path(outputs["energy_dir"]).exists()

    summary_text = Path(outputs["summary_md"]).read_text(encoding="utf-8")
    assert "SPICE-Driven Preferred Chain Summary" in summary_text
    assert "actual ngspice-generated shared front-end traces" in summary_text
    summary_json = json.loads(Path(outputs["summary_json"]).read_text(encoding="utf-8"))
    assert "summary_metrics" in summary_json
    assert "boundary_export_rows" in summary_json
    assert (tmp_path / "summary" / "front_end_traces" / "representative_spice_branch_voltage_traces.png").exists()
    assert (tmp_path / "summary" / "front_end_traces" / "representative_spice_branch_current_traces.png").exists()
    assert (tmp_path / "summary" / "front_end_traces" / "representative_spice_branch_power_traces.png").exists()
    assert (tmp_path / "summary" / "boundary_export" / "detector_facing_exported_envelopes_derived_from_spice.png").exists()
    assert (tmp_path / "summary" / "full_chain" / "winner_frequency_exact_vs_empirical.png").exists()
    assert (tmp_path / "summary" / "post_click" / "winner_drain_energy_fraction.png").exists()
    assert (tmp_path / "summary" / "energy_accounting" / "whole_trial_energy_flow_summary.png").exists()
