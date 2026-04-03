from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

from detector_integration.frontends.four_branch import four_branch_weights
from detector_integration.sim.metrics import four_branch_metrics
from src.analyzer_couplers import AnalyzerCouplers, AnalyzerImperfections
from src.shared_4tank_core import BASIS_LABELS, CoreImperfections, Shared4TankCore, singlet_state

from .export_interface import amplitude_envelope, build_time_axis, export_contract, resolve_envelope_config
from .metrics import fraction_error_metrics

BRANCH_LABELS = list(BASIS_LABELS)


@dataclass(frozen=True)
class RefinedSharedCoreFrontEndConfig:
    """Refined four-branch candidate with an explicit internal shared-core solve."""

    implementation_option: str = "A"
    drive_amplitude_v: float = 1.0
    source_amplitude_scale_v: float = 6.0
    omega0: float = 1.0
    kappa: float = 0.25
    gamma: float = 0.01
    source_resistance_ohm: tuple[float, float, float, float] = (25.0, 25.3, 24.9, 25.1)
    load_resistance_ohm: tuple[float, float, float, float] = (50.0, 49.8, 50.1, 49.9)
    branch_gain_trim: tuple[float, float, float, float] = (1.0, 0.9985, 1.0015, 0.999)
    branch_phase_deg: tuple[float, float, float, float] = (0.0, 0.7, -0.5, 0.9)
    core_imperfections: CoreImperfections = field(
        default_factory=lambda: CoreImperfections(
            lc_mismatch=(0.004, -0.003, 0.002, -0.002),
            damping_imbalance=(0.02, -0.01, 0.01, -0.015),
            coupling_scale=0.992,
            prep_amplitude_imbalance=0.01,
            prep_phase_error_deg=0.8,
        )
    )
    analyzer_imperfections: AnalyzerImperfections = field(
        default_factory=lambda: AnalyzerImperfections(
            alice_angle_offset_deg=0.15,
            bob_angle_offset_deg=-0.1,
            alice_gain_error=0.003,
            bob_gain_error=-0.002,
            alice_phase_error_deg=0.4,
            bob_phase_error_deg=-0.3,
        )
    )


def benchmark_refined_four_branch_cases() -> list[dict[str, Any]]:
    state = singlet_state()
    return [
        {"case": "case_a", "state4": state, "a_deg": 0.0, "b_deg": 0.0},
        {"case": "case_c", "state4": state, "a_deg": 0.0, "b_deg": 45.0},
        {"case": "a0b0", "state4": state, "a_deg": 0.0, "b_deg": 22.5},
        {"case": "a0b1", "state4": state, "a_deg": 0.0, "b_deg": -22.5},
        {"case": "a1b0", "state4": state, "a_deg": 45.0, "b_deg": 22.5},
        {"case": "a1b1", "state4": state, "a_deg": 45.0, "b_deg": -22.5},
    ]


def simulate_refined_four_branch_candidate(
    state4: np.ndarray | None = None,
    *,
    a_deg: float,
    b_deg: float,
    front_end_config: RefinedSharedCoreFrontEndConfig | None = None,
    envelope_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_front_end = RefinedSharedCoreFrontEndConfig() if front_end_config is None else front_end_config
    resolved_envelope = resolve_envelope_config(envelope_config)
    target_state = singlet_state() if state4 is None else np.asarray(state4, dtype=np.complex128)
    exact = four_branch_weights(target_state, a_deg=float(a_deg), b_deg=float(b_deg))

    shared_core = Shared4TankCore(
        omega0=resolved_front_end.omega0,
        kappa=resolved_front_end.kappa,
        gamma=resolved_front_end.gamma,
        imperfections=resolved_front_end.core_imperfections,
    )
    preparation = shared_core.prepare_singlet_mode(amplitude=resolved_front_end.drive_amplitude_v)
    analyzer = AnalyzerCouplers(imperfections=resolved_front_end.analyzer_imperfections)
    joint_matrix = analyzer.joint_matrix(float(a_deg), float(b_deg))
    internal_state = np.asarray(preparation.normalized_state, dtype=np.complex128)
    branch_output_amplitudes = joint_matrix @ internal_state

    drive_envelope = amplitude_envelope(resolved_envelope)
    time_s = build_time_axis(resolved_envelope)
    branch_voltage: dict[str, np.ndarray] = {}
    branch_current: dict[str, np.ndarray] = {}
    branch_power: dict[str, np.ndarray] = {}
    branch_energy: dict[str, float] = {}
    branch_fraction: dict[str, float] = {}

    total_energy = 0.0
    for index, label in enumerate(BRANCH_LABELS):
        source_r = float(resolved_front_end.source_resistance_ohm[index])
        load_r = float(resolved_front_end.load_resistance_ohm[index])
        gain = float(resolved_front_end.branch_gain_trim[index])
        phase = np.exp(1j * np.deg2rad(float(resolved_front_end.branch_phase_deg[index])))
        open_circuit = resolved_front_end.source_amplitude_scale_v * gain * phase * branch_output_amplitudes[index] * drive_envelope
        divider = load_r / (source_r + load_r)
        load_voltage = np.abs(open_circuit) * divider
        load_current = load_voltage / load_r
        power = np.maximum(load_voltage * load_current, 0.0)
        branch_voltage[label] = load_voltage.astype(float)
        branch_current[label] = load_current.astype(float)
        branch_power[label] = power.astype(float)
        branch_energy[label] = float(np.trapezoid(power, x=time_s))
        total_energy += branch_energy[label]

    for label in BRANCH_LABELS:
        branch_fraction[label] = branch_energy[label] / max(total_energy, 1e-18)

    export = export_contract(
        branch_labels=BRANCH_LABELS,
        time_s=time_s,
        branch_voltage_v=branch_voltage,
        branch_current_a=branch_current,
        branch_power_w=branch_power,
        branch_energy_j=branch_energy,
        branch_energy_fraction=branch_fraction,
        exact_weight={label: float(value) for label, value in zip(BRANCH_LABELS, exact, strict=True)},
        envelope_config=resolved_envelope,
    )
    realized = np.array([branch_fraction[label] for label in BRANCH_LABELS], dtype=float)
    correlator_metrics = four_branch_metrics(exact, realized)
    export["candidate_config"] = {
        **asdict(resolved_front_end),
        "core_imperfections": asdict(resolved_front_end.core_imperfections),
        "analyzer_imperfections": asdict(resolved_front_end.analyzer_imperfections),
    }
    export["a_deg"] = float(a_deg)
    export["b_deg"] = float(b_deg)
    export["shared_core"] = {
        "prepared_internal_state": internal_state,
        "steady_state": np.asarray(preparation.steady_state, dtype=np.complex128),
        "branch_output_amplitudes": np.asarray(branch_output_amplitudes, dtype=np.complex128),
        "joint_matrix": np.asarray(joint_matrix, dtype=np.complex128),
        "drive_vector": np.asarray(preparation.drive_vector, dtype=np.complex128),
        "modal_energies": np.asarray(preparation.modal_energies, dtype=float),
        "dominant_mode_index": int(preparation.dominant_mode_index),
        "singlet_mode_index": int(preparation.singlet_mode_index),
        "singlet_mode_energy": float(preparation.singlet_mode_energy),
        "singlet_state_overlap": float(preparation.singlet_state_overlap),
        "drive_frequency_rad_s": float(preparation.drive_frequency_rad_s),
        "intended_circuit": {
            "tanks": [asdict(tank) for tank in shared_core.intended_circuit().tanks],
            "couplers": [asdict(coupler) for coupler in shared_core.intended_circuit().couplers],
            "readout_note": shared_core.intended_circuit().readout_note,
        },
    }
    export["metrics"] = {
        **fraction_error_metrics(exact, realized),
        "correlator_exact": float(correlator_metrics["correlator_exact"]),
        "correlator_realized": float(correlator_metrics["correlator_empirical"]),
        "correlator_error": float(correlator_metrics["correlator_error"]),
    }
    return export
