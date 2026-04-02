from __future__ import annotations

import math

import allure
import numpy as np

from src.analyzer_couplers import AnalyzerCouplers, AnalyzerImperfections
from src.benchmarks import (
    angle_sweep,
    benchmark_cases,
    benchmark_table,
    chsh_value,
    coupling_sweep,
    plot_core_spectrum,
    plot_correlator_surface,
    plot_singlet_overlap,
    run_benchmark_case,
    sensitivity_sweep,
)
from src.joint_readout import JointReadout, ReadoutImperfections
from src.shared_4tank_core import (
    BASIS_LABELS,
    CoreImperfections,
    Shared4TankCore,
    singlet_state,
)


def test_shared_core_exposes_singlet_like_mode() -> None:
    core = Shared4TankCore(omega0=1.0, kappa=0.25, gamma=0.01)
    uncoupled = core.analyze_modes(coupled=False)
    coupled = core.analyze_modes(coupled=True)
    preparation = core.prepare_singlet_mode()
    circuit = core.intended_circuit()

    assert np.allclose(uncoupled.eigenvalues, np.ones(4), atol=1e-12)
    assert coupled.singlet_mode_overlap > 0.999999
    assert preparation.singlet_mode_energy > 0.95
    assert preparation.singlet_state_overlap > 0.95
    assert preparation.dominant_mode_index == preparation.singlet_mode_index
    assert [tank.label for tank in circuit.tanks] == list(BASIS_LABELS)
    assert len(circuit.couplers) == 1
    assert {circuit.couplers[0].source, circuit.couplers[0].target} == {"+-", "-+"}


def test_analyzer_couplers_match_rotation_contract() -> None:
    analyzers = AnalyzerCouplers(
        imperfections=AnalyzerImperfections(
            alice_angle_offset_deg=0.2,
            bob_angle_offset_deg=-0.2,
            alice_gain_error=0.01,
            bob_gain_error=-0.01,
            alice_phase_error_deg=1.0,
            bob_phase_error_deg=-1.0,
        )
    )
    amplitude_error, phase_error_deg = analyzers.matrix_error_metrics(33.0, -17.0)

    assert amplitude_error < 0.02
    assert phase_error_deg < 2.0


def test_benchmark_cases_match_theory_within_spec() -> None:
    readout = JointReadout(analyzers=AnalyzerCouplers())
    results = [run_benchmark_case(Shared4TankCore(), readout, case) for case in benchmark_cases()]

    for result in results:
        assert result.rms_error < 0.02
        assert np.max(result.absolute_error) < 0.02
        assert abs(result.correlator - result.case.expected_correlator) < 0.02

    table = benchmark_table(results)
    allure.attach(
        "\n".join(str(row) for row in table),
        name="physical-v0-benchmark-table",
        attachment_type=allure.attachment_type.TEXT,
    )


def test_chsh_linear_demonstrator_reaches_target() -> None:
    readout = JointReadout(analyzers=AnalyzerCouplers())
    s_value = chsh_value(readout, state=singlet_state())
    assert abs(abs(s_value) - 2.0 * math.sqrt(2.0)) < 0.05


def test_nonidealities_survive_modest_imperfections() -> None:
    core = Shared4TankCore(
        omega0=1.0,
        kappa=0.25,
        gamma=0.01,
        imperfections=CoreImperfections(
            lc_mismatch=(0.01, -0.01, 0.01, -0.01),
            damping_imbalance=(0.01, -0.01, 0.005, -0.005),
            coupling_scale=0.99,
            prep_amplitude_imbalance=0.01,
            prep_phase_error_deg=1.0,
        ),
    )
    analyzers = AnalyzerCouplers(
        imperfections=AnalyzerImperfections(
            alice_angle_offset_deg=0.5,
            bob_angle_offset_deg=-0.5,
            alice_gain_error=0.005,
            bob_gain_error=-0.005,
            alice_phase_error_deg=1.0,
            bob_phase_error_deg=-1.0,
        )
    )
    readout = JointReadout(
        analyzers=analyzers,
        imperfections=ReadoutImperfections(
            resistor_tolerance=(0.01, -0.01, 0.01, -0.01),
            branch_gain_error=(0.0, 0.0, 0.0, 0.0),
        ),
    )

    prepared_state = core.prepare_singlet_mode().normalized_state
    results = [run_benchmark_case(core, readout, case, prepared_state=prepared_state) for case in benchmark_cases()]
    s_value = chsh_value(readout, state=prepared_state)

    assert core.prepare_singlet_mode().singlet_mode_energy > 0.95
    assert max(result.rms_error for result in results) < 0.02
    assert abs(abs(s_value) - 2.0 * math.sqrt(2.0)) < 0.05


def test_sweep_outputs_and_plots(save_visual) -> None:
    core = Shared4TankCore()
    readout = JointReadout(analyzers=AnalyzerCouplers())

    spectrum_figure = plot_core_spectrum(core)
    save_visual("physical-v0-core-spectrum", spectrum_figure)

    kappas = np.linspace(0.05, 0.35, 7)
    coupling_rows = coupling_sweep(kappas)
    overlap_figure = plot_singlet_overlap(kappas, coupling_rows)
    save_visual("physical-v0-singlet-overlap", overlap_figure)

    a_values = np.linspace(0.0, 90.0, 19)
    b_values = np.linspace(-45.0, 45.0, 19)
    correlators, theory, delta = angle_sweep(readout, a_values, b_values)
    surface_figure = plot_correlator_surface(a_values, b_values, correlators)
    save_visual("physical-v0-correlator-surface", surface_figure)

    sensitivity_rows = sensitivity_sweep(
        core,
        AnalyzerCouplers(),
        JointReadout(analyzers=AnalyzerCouplers()),
        mismatch_levels=(0.0, 0.005, 0.01),
    )
    allure.attach(
        "\n".join(
            f"level={level:.4f}, rms={rms:.6f}, correlator_error={corr:.6f}"
            for level, rms, corr in sensitivity_rows
        ),
        name="physical-v0-sensitivity-sweep",
        attachment_type=allure.attachment_type.TEXT,
    )

    assert np.max(np.abs(delta)) < 1e-12
    assert all(mode_energy > 0.95 for _, mode_energy, _ in coupling_rows)
    assert all(rms < 0.02 for _, rms, _ in sensitivity_rows)
