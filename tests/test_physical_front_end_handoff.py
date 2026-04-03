from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from detector_integration.detectors import simulate_branch_nucleation
from physical_front_end_candidate.experiments.build_handoff_report import build_physical_front_end_handoff_report
from physical_front_end_candidate.export_interface import build_detector_handoff_envelopes, render_envelope_traces, resolve_envelope_config
from physical_front_end_candidate.integration import run_two_branch_physical_handoff
from physical_front_end_candidate.metrics import energy_preservation_metrics, finite_export_metrics
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


def test_direct_trace_export_is_valid_and_finite() -> None:
    case = representative_physical_cases()[0]
    candidate = simulate_two_branch_physical_candidate(case["state"], case["analyzer"])
    envelopes = build_detector_handoff_envelopes(
        candidate["branch_power_w"],
        time_s=candidate["time_s"],
        branch_labels=candidate["branch_labels"],
        envelope_config=resolve_envelope_config(candidate["envelope_config"]),
        export_config={"mode": "direct_trace"},
    )
    assert all(envelope["kind"] == "sampled" for envelope in envelopes)
    metrics = finite_export_metrics([candidate["branch_power_w"][label] for label in candidate["branch_labels"]])
    assert metrics["finite"] is True
    assert metrics["nonnegative_with_tolerance"] is True


def test_piecewise_export_preserves_branch_energy() -> None:
    case = representative_physical_cases()[0]
    candidate = simulate_two_branch_physical_candidate(case["state"], case["analyzer"])
    envelopes = build_detector_handoff_envelopes(
        candidate["branch_power_w"],
        time_s=candidate["time_s"],
        branch_labels=candidate["branch_labels"],
        envelope_config=resolve_envelope_config(candidate["envelope_config"]),
        export_config={"mode": "piecewise_envelope", "piecewise_mode": "constant", "piecewise_bin_width_s": 5e-3},
    )
    exported = render_envelope_traces(envelopes, sample_time_s=candidate["time_s"], branch_labels=candidate["branch_labels"])
    for label in candidate["branch_labels"]:
        metrics = energy_preservation_metrics(candidate["time_s"], candidate["branch_power_w"][label], exported[label])
        assert metrics["rel_error"] < 0.02


def test_all_export_modes_are_consumable_by_detector_adapter() -> None:
    case = representative_physical_cases()[0]
    candidate = simulate_two_branch_physical_candidate(case["state"], case["analyzer"])
    configs = [
        {"mode": "direct_trace"},
        {"mode": "piecewise_envelope", "piecewise_mode": "linear", "piecewise_bin_width_s": 5e-3},
        {"mode": "exponential_fit"},
    ]
    for config in configs:
        envelopes = build_detector_handoff_envelopes(
            candidate["branch_power_w"],
            time_s=candidate["time_s"],
            branch_labels=candidate["branch_labels"],
            envelope_config=resolve_envelope_config(candidate["envelope_config"]),
            export_config=config,
        )
        click_time = simulate_branch_nucleation(INTEGRATION_SPEC, 1.0, envelopes[0], np.random.default_rng(20260403))
        assert click_time is None or click_time >= 0.0


def test_winner_law_metrics_are_reported_consistently_across_modes() -> None:
    case = representative_physical_cases()[0]
    configs = [
        {"mode": "direct_trace"},
        {"mode": "piecewise_envelope", "piecewise_mode": "constant", "piecewise_bin_width_s": 5e-3},
        {"mode": "exponential_fit"},
    ]
    results = [
        run_two_branch_physical_handoff(case["state"], case["analyzer"], INTEGRATION_SPEC, n_trials=120, seed=20260403 + index, export_config=config)
        for index, config in enumerate(configs)
    ]
    for result in results:
        assert result["metrics"]["rms_error"] >= 0.0
        assert result["metrics"]["max_abs_error"] >= 0.0
        assert result["common_envelope"]["rms_difference"] >= 0.0


def test_handoff_report_smoke_writes_artifacts(tmp_path: Path) -> None:
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

    outputs = build_physical_front_end_handoff_report(
        tmp_path / "handoff",
        detector_next_summary_csv=detector_next_summary,
        n_trials=12,
    )

    assert Path(outputs["summary_md"]).exists()
    assert Path(outputs["summary_json"]).exists()
    assert Path(outputs["summary_csv"]).exists()
    assert Path(outputs["comparison_csv"]).exists()
    assert Path(outputs["handoff_design_note_md"]).exists()
    summary = json.loads(Path(outputs["summary_json"]).read_text(encoding="utf-8"))
    assert "selected_mode" in summary
    assert "comparison_rows" in summary
