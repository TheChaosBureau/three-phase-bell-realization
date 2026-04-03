from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

from detector_integration.frontends.four_branch import four_branch_weights
from detector_integration.sim.metrics import four_branch_metrics
from src.analyzer_couplers import AnalyzerCouplers, AnalyzerImperfections
from src.shared_4tank_core import BASIS_LABELS, CoreImperfections, Shared4TankCore, normalize, singlet_state

from .export_interface import amplitude_envelope, build_time_axis, export_contract, resolve_envelope_config
from .metrics import fraction_error_metrics

BRANCH_LABELS = list(BASIS_LABELS)


@dataclass(frozen=True)
class ResonantSharedModeFrontEndConfig:
    """Explicit resonant/shared-mode four-branch front-end candidate."""

    implementation_option: str = "A"
    drive_amplitude_v: float = 1.0
    source_amplitude_scale_v: float = 6.0
    omega0: float = 1.0
    kappa: float = 0.27
    gamma: float = 0.008
    mode_q_scale: float = 1.1
    source_resistance_ohm: tuple[float, float, float, float] = (25.0, 25.2, 24.9, 25.1)
    load_resistance_ohm: tuple[float, float, float, float] = (50.0, 49.9, 50.1, 49.8)
    branch_gain_trim: tuple[float, float, float, float] = (1.0, 0.999, 1.001, 0.9985)
    branch_phase_deg: tuple[float, float, float, float] = (0.0, 0.6, -0.4, 0.8)
    core_imperfections: CoreImperfections = field(
        default_factory=lambda: CoreImperfections(
            lc_mismatch=(0.003, -0.002, 0.0015, -0.001),
            damping_imbalance=(0.015, -0.008, 0.01, -0.012),
            coupling_scale=0.996,
            prep_amplitude_imbalance=0.006,
            prep_phase_error_deg=0.45,
        )
    )
    analyzer_imperfections: AnalyzerImperfections = field(
        default_factory=lambda: AnalyzerImperfections(
            alice_angle_offset_deg=0.1,
            bob_angle_offset_deg=-0.08,
            alice_gain_error=0.002,
            bob_gain_error=-0.0015,
            alice_phase_error_deg=0.25,
            bob_phase_error_deg=-0.2,
        )
    )


def benchmark_resonant_four_branch_cases() -> list[dict[str, Any]]:
    state = singlet_state()
    return [
        {"case": "case_a", "state4": state, "a_deg": 0.0, "b_deg": 0.0},
        {"case": "case_c", "state4": state, "a_deg": 0.0, "b_deg": 45.0},
        {"case": "a0b0", "state4": state, "a_deg": 0.0, "b_deg": 22.5},
        {"case": "a0b1", "state4": state, "a_deg": 0.0, "b_deg": -22.5},
        {"case": "a1b0", "state4": state, "a_deg": 45.0, "b_deg": 22.5},
        {"case": "a1b1", "state4": state, "a_deg": 45.0, "b_deg": -22.5},
    ]


def _normalized_eigenbasis(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    eigenvalues, eigenvectors = np.linalg.eig(matrix)
    normalized_vectors = np.asarray([normalize(eigenvectors[:, index]) for index in range(eigenvectors.shape[1])]).T
    return np.asarray(eigenvalues, dtype=np.complex128), np.asarray(normalized_vectors, dtype=np.complex128)


def simulate_resonant_four_branch_candidate(
    state4: np.ndarray | None = None,
    *,
    a_deg: float,
    b_deg: float,
    front_end_config: ResonantSharedModeFrontEndConfig | None = None,
    envelope_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_front_end = ResonantSharedModeFrontEndConfig() if front_end_config is None else front_end_config
    resolved_envelope = resolve_envelope_config(envelope_config)
    target_state = singlet_state() if state4 is None else np.asarray(state4, dtype=np.complex128)
    exact = four_branch_weights(target_state, a_deg=float(a_deg), b_deg=float(b_deg))

    shared_core = Shared4TankCore(
        omega0=resolved_front_end.omega0,
        kappa=resolved_front_end.kappa,
        gamma=resolved_front_end.gamma,
        imperfections=resolved_front_end.core_imperfections,
    )
    analyzer = AnalyzerCouplers(imperfections=resolved_front_end.analyzer_imperfections)

    effective = shared_core.effective_generator()
    modal_eigenvalues, modal_vectors = _normalized_eigenbasis(effective)
    singlet_overlaps = np.abs(np.conjugate(modal_vectors).T @ singlet_state()) ** 2
    singlet_mode_index = int(np.argmax(singlet_overlaps))
    drive_vector = shared_core.preparation_drive(amplitude=resolved_front_end.drive_amplitude_v)
    modal_drive = np.linalg.solve(modal_vectors, drive_vector)
    resonance_detuning = np.real(modal_eigenvalues) - float(np.real(modal_eigenvalues[singlet_mode_index]))
    damping_rates = np.maximum(-np.imag(modal_eigenvalues), shared_core.gamma * 0.2)
    modal_response = modal_drive / (resolved_front_end.mode_q_scale * damping_rates + 1j * resonance_detuning)
    steady_state = modal_vectors @ modal_response
    normalized_state = normalize(steady_state)

    drive_envelope = amplitude_envelope(resolved_envelope)
    time_s = build_time_axis(resolved_envelope)
    joint_matrix = analyzer.joint_matrix(float(a_deg), float(b_deg))
    branch_output_steady = joint_matrix @ normalized_state

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
        open_circuit = resolved_front_end.source_amplitude_scale_v * gain * phase * branch_output_steady[index] * drive_envelope
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
        "modal_eigenvalues": modal_eigenvalues,
        "modal_vectors": modal_vectors,
        "modal_drive": modal_drive,
        "modal_response": modal_response,
        "modal_decay_rates": damping_rates,
        "resonance_detuning": resonance_detuning,
        "prepared_internal_state": normalized_state,
        "steady_state": steady_state,
        "branch_output_amplitudes": branch_output_steady,
        "joint_matrix": joint_matrix,
        "drive_vector": drive_vector,
        "singlet_mode_index": singlet_mode_index,
        "singlet_mode_overlap": float(singlet_overlaps[singlet_mode_index]),
        "mode_overlap_profile": singlet_overlaps.astype(float),
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
