from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from detector_integration.sim.run_four_branch_latch_integration import DEFAULT_CHSH_SETTINGS
from physical_front_end_candidate.experiments.build_four_branch_resonant_report import build_physical_front_end_four_branch_resonant_report
from physical_front_end_candidate.integration import run_four_branch_candidate_handoff
from physical_front_end_candidate.resonant_four_branch_candidate import benchmark_resonant_four_branch_cases, simulate_resonant_four_branch_candidate
from src.shared_4tank_core import singlet_state

SHOT_TRIGGER_SPEC = {
    "family": "shot_trigger",
    "model_params": {"eps_event": 0.5, "p_trig": 0.8, "lambda_dark": 1e-6, "dead_time": 0.0},
    "gain_scale": 2.0,
}


def test_resonant_four_branch_fractions_sum_to_one() -> None:
    case = benchmark_resonant_four_branch_cases()[0]
    result = simulate_resonant_four_branch_candidate(case["state4"], a_deg=case["a_deg"], b_deg=case["b_deg"])
    fractions = np.array([result["branch_energy_fraction"][label] for label in result["branch_labels"]], dtype=float)
    assert abs(float(np.sum(fractions)) - 1.0) < 1e-12


def test_resonant_candidate_remains_close_to_exact_weights() -> None:
    case = benchmark_resonant_four_branch_cases()[2]
    result = simulate_resonant_four_branch_candidate(case["state4"], a_deg=case["a_deg"], b_deg=case["b_deg"])
    assert result["metrics"]["rms_error"] < 0.03
    assert result["metrics"]["max_abs_error"] < 0.05


def test_resonant_detector_export_remains_frozen_boundary_compatible() -> None:
    case = benchmark_resonant_four_branch_cases()[0]
    candidate = simulate_resonant_four_branch_candidate(case["state4"], a_deg=case["a_deg"], b_deg=case["b_deg"])
    result = run_four_branch_candidate_handoff(candidate, SHOT_TRIGGER_SPEC, n_trials=30, seed=20260403)
    assert result["boundary_config"]["gain"] == 4.0
    assert result["boundary_config"]["exposure_s"] == 5.0
    assert result["export_config"]["mode"] == "piecewise_envelope"
    assert result["export_config"]["piecewise_mode"] == "linear"
    assert abs(float(result["export_config"]["piecewise_bin_width_s"]) - 0.02) < 1e-12


def test_resonant_candidate_integrated_metrics_and_architecture_hold() -> None:
    case = benchmark_resonant_four_branch_cases()[2]
    candidate = simulate_resonant_four_branch_candidate(case["state4"], a_deg=case["a_deg"], b_deg=case["b_deg"])
    result = run_four_branch_candidate_handoff(candidate, SHOT_TRIGGER_SPEC, n_trials=1800, seed=20260403)
    assert result["metrics"]["rms_error"] < 0.03
    assert result["metrics"]["max_abs_error"] < 0.05
    assert result["metrics"]["correlator_error"] < 0.05
    trivial = np.sqrt(np.asarray(result["exact_weights"], dtype=float))
    output_amplitudes = np.abs(np.asarray(candidate["shared_core"]["branch_output_amplitudes"], dtype=np.complex128))
    output_amplitudes /= max(float(np.linalg.norm(output_amplitudes)), 1e-18)
    trivial /= max(float(np.linalg.norm(trivial)), 1e-18)
    assert not np.allclose(output_amplitudes, trivial, atol=1e-4)
    assert np.max(np.asarray(candidate["shared_core"]["modal_decay_rates"], dtype=float)) > 0.0


def test_resonant_candidate_chsh_and_correlator_remain_within_tolerance() -> None:
    exact = {}
    empirical = {}
    rms_errors = []
    for index, (label, (a_deg, b_deg)) in enumerate(DEFAULT_CHSH_SETTINGS.items()):
        candidate = simulate_resonant_four_branch_candidate(singlet_state(), a_deg=a_deg, b_deg=b_deg)
        result = run_four_branch_candidate_handoff(candidate, SHOT_TRIGGER_SPEC, n_trials=1200, seed=20260403 + 1_003 * index)
        exact[label] = float(result["metrics"]["correlator_exact"])
        empirical[label] = float(result["metrics"]["correlator_empirical"])
        rms_errors.append(float(result["metrics"]["rms_error"]))
        assert result["metrics"]["correlator_error"] < 0.05

    exact_s = exact["a0b0"] + exact["a0b1"] + exact["a1b0"] - exact["a1b1"]
    empirical_s = empirical["a0b0"] + empirical["a0b1"] + empirical["a1b0"] - empirical["a1b1"]
    assert float(np.sqrt(np.mean(np.square(rms_errors)))) < 0.03
    assert abs(empirical_s - exact_s) < 0.1


def test_resonant_report_smoke_writes_artifacts_and_comparison(tmp_path: Path) -> None:
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

    outputs = build_physical_front_end_four_branch_resonant_report(
        tmp_path / "summary",
        detector_next_summary_csv=detector_next_summary,
        n_trials=180,
    )

    assert Path(outputs["summary_md"]).exists()
    assert Path(outputs["summary_json"]).exists()
    assert Path(outputs["summary_csv"]).exists()
    assert Path(outputs["design_md"]).exists()
    assert Path(outputs["spice_facing_interface_md"]).exists()
    assert Path(tmp_path / "summary" / "shared_core" / "shared_core_summary.json").exists()
    assert Path(tmp_path / "summary" / "four_branch" / "four_branch_summary.json").exists()
    assert Path(tmp_path / "summary" / "integration" / "integration_summary.json").exists()
    report_text = Path(outputs["summary_md"]).read_text(encoding="utf-8")
    assert "Resonant Four-Branch Front-End Summary" in report_text
    summary = json.loads(Path(outputs["summary_json"]).read_text(encoding="utf-8"))
    assert "summary_metrics" in summary
    assert "comparison_rows" in summary
