from __future__ import annotations

import ctypes.util
import json
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("PySpice")

from physical_front_end_candidate.actual_spice_front_end import (
    actual_spice_front_end_benchmark_cases,
    run_actual_spice_front_end_benchmark,
    run_actual_spice_front_end_case,
    simulate_actual_spice_front_end_candidate,
)
from physical_front_end_candidate.experiments.build_actual_spice_front_end_report import (
    build_actual_spice_front_end_report,
)


def _require_ngspice() -> None:
    libngspice = ctypes.util.find_library("ngspice") or ctypes.util.find_library("libngspice")
    if not libngspice:
        pytest.skip("ngspice shared library is not available in this environment")


def test_actual_spice_front_end_netlist_contains_real_spice_elements() -> None:
    _require_ngspice()
    case = actual_spice_front_end_benchmark_cases()[0]
    candidate = simulate_actual_spice_front_end_candidate(
        case["state4"],
        a_deg=case["a_deg"],
        b_deg=case["b_deg"],
    )
    netlist_text = str(candidate["spice"]["netlist_text"])
    assert "RLOAD_pp" in netlist_text
    assert "BMIX_pp" in netlist_text
    assert "BISRC_pm" in netlist_text
    assert "C_BRIDGE_PM_MP" in netlist_text or "CC_BRIDGE_PM_MP" in netlist_text


def test_actual_spice_front_end_case_runs_and_traces_are_finite() -> None:
    _require_ngspice()
    case = actual_spice_front_end_benchmark_cases()[1]
    result = run_actual_spice_front_end_case(
        case["state4"],
        a_deg=case["a_deg"],
        b_deg=case["b_deg"],
    )
    fractions = np.asarray([result["branch_energy_fraction"][label] for label in result["branch_labels"]], dtype=float)
    assert np.all(np.isfinite(fractions))
    assert np.all(fractions >= 0.0)
    assert abs(float(np.sum(fractions)) - 1.0) < 1e-9
    assert len(result["time_s"]) > 10
    assert result["shared_core"]["explicitness_metrics"]["actual_spice_run_succeeded"]
    assert result["shared_core"]["explicitness_metrics"]["probeable_branch_outputs"]


def test_actual_spice_front_end_energy_integral_matches_processed_trace() -> None:
    _require_ngspice()
    case = actual_spice_front_end_benchmark_cases()[2]
    result = simulate_actual_spice_front_end_candidate(
        case["state4"],
        a_deg=case["a_deg"],
        b_deg=case["b_deg"],
    )
    for label in result["branch_labels"]:
        cumulative = np.asarray(result["processed_traces"]["cumulative_branch_energy_j"][label], dtype=float)
        assert cumulative.size == len(result["time_s"])
        assert cumulative[-1] == pytest.approx(float(result["branch_energy_j"][label]), rel=1e-5, abs=1e-12)


def test_actual_spice_front_end_is_not_a_trivial_exact_weight_wrapper() -> None:
    _require_ngspice()
    case = actual_spice_front_end_benchmark_cases()[3]
    candidate = simulate_actual_spice_front_end_candidate(
        case["state4"],
        a_deg=case["a_deg"],
        b_deg=case["b_deg"],
    )
    explicitness = candidate["shared_core"]["explicitness_metrics"]
    topology = candidate["netlist"]["topology_summary"]
    assert explicitness["uses_actual_spice"]
    assert not explicitness["drive_uses_exact_weights"]
    assert explicitness["component_count"] >= 32
    assert topology["coupling_component_count"] >= 7
    assert topology["output_probe_count"] == 4


def test_actual_spice_front_end_progress_output_can_be_enabled(capsys) -> None:
    _require_ngspice()
    run_actual_spice_front_end_benchmark(case_names=("case_a",), verbose_progress=True)
    captured = capsys.readouterr()
    assert "actual-spice-front-end" in captured.err
    assert "simulate-case" in captured.err


def test_actual_spice_front_end_suite_meets_ticket_acceptance() -> None:
    _require_ngspice()
    summary = run_actual_spice_front_end_benchmark()
    metrics = summary["summary_metrics"]
    assert metrics["front_end_fraction_pass"]
    assert metrics["actual_spice_execution_pass"]
    assert metrics["finite_output_pass"]
    assert metrics["probeability_pass"]
    assert metrics["architecture_explicitness_pass"]
    assert metrics["no_trivial_exact_weight_assignment"]
    assert metrics["correlator_pass"]
    assert metrics["chsh_pass"]
    assert metrics["proceed_to_next_phase"]


def test_actual_spice_front_end_report_smoke_writes_required_artifacts(tmp_path: Path) -> None:
    _require_ngspice()
    outputs = build_actual_spice_front_end_report(tmp_path / "summary", case_names=("case_a",))

    assert Path(outputs["summary_md"]).exists()
    assert Path(outputs["summary_json"]).exists()
    assert Path(outputs["summary_csv"]).exists()
    assert Path(outputs["design_md"]).exists()
    assert Path(outputs["candidate_comparison_csv"]).exists()
    assert Path(outputs["netlist_dir"]).exists()
    assert Path(outputs["raw_waveforms_dir"]).exists()
    assert Path(outputs["processed_traces_dir"]).exists()
    assert Path(outputs["front_end_metrics_dir"]).exists()

    summary_text = Path(outputs["summary_md"]).read_text(encoding="utf-8")
    assert "Actual SPICE Front-End Summary" in summary_text
    summary_json = json.loads(Path(outputs["summary_json"]).read_text(encoding="utf-8"))
    assert "summary_metrics" in summary_json
    assert "front_end_rows" in summary_json
    assert (tmp_path / "summary" / "front_end_metrics" / "netlist_topology_node_map.png").exists()
    assert (tmp_path / "summary" / "front_end_metrics" / "representative_branch_voltage_traces.png").exists()
    assert (tmp_path / "summary" / "front_end_metrics" / "representative_branch_current_traces.png").exists()
    assert (tmp_path / "summary" / "front_end_metrics" / "representative_branch_power_traces.png").exists()
    assert (tmp_path / "summary" / "front_end_metrics" / "exact_vs_spice_branch_energy_fractions.png").exists()
    assert (tmp_path / "summary" / "front_end_metrics" / "benchmark_case_comparison_summary.png").exists()
    assert (tmp_path / "summary" / "front_end_metrics" / "residual_error_summary.png").exists()
