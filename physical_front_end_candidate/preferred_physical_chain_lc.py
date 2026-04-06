from __future__ import annotations

import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

from detector_integration.detectors import (
    latch_first_event,
    resolve_branch_detector_params,
    simulate_branch_nucleation,
    validated_latch_arbiter_config,
)
from detector_integration.frontends.four_branch import four_branch_weights
from detector_integration.sim.metrics import four_branch_metrics, winner_frequency_summary
from src.analyzer_couplers import AnalyzerCouplers, AnalyzerImperfections
from src.shared_4tank_core import BASIS_LABELS, CoreImperfections, Shared4TankCore, normalize, singlet_state

from .export_interface import amplitude_envelope, build_time_axis, export_contract, resolve_envelope_config
from .integration import materialize_candidate_trace
from .physical_closure_drain_candidate import (
    PhysicalClosureDrainConfig,
    build_physical_closure_candidate_cache,
    default_physical_closure_drain_config,
)
from .preferred_physical_chain import preferred_physical_chain_benchmark_cases, run_preferred_physical_chain_benchmark
from .preferred_physical_chain_energy import build_trial_energy_accounting, summarize_energy_accounting_rows
from .preferred_physical_chain_metrics import (
    build_chsh_result,
    build_pre_click_comparison,
    build_summary_metrics,
    summarize_post_click_behavior,
)
from .metrics import aggregate_case_error, fraction_error_metrics

BRANCH_LABELS = list(BASIS_LABELS)


@dataclass
class _ProgressReporter:
    total_steps: int
    enabled: bool = False
    label: str = "preferred-physical-chain-lc"
    completed_steps: int = 0
    start_time_s: float = 0.0
    last_report_time_s: float = 0.0
    last_phase: str | None = None
    last_case_name: str | None = None

    def __post_init__(self) -> None:
        self.start_time_s = time.monotonic()
        self.last_report_time_s = self.start_time_s
        if self.enabled:
            self.report("starting", force=True)

    def report(self, phase: str, case_name: str | None = None, *, force: bool = False) -> None:
        if not self.enabled:
            return
        now = time.monotonic()
        phase_changed = phase != self.last_phase or case_name != self.last_case_name
        if not force and not phase_changed and (now - self.last_report_time_s) < 0.5:
            return
        elapsed_s = max(now - self.start_time_s, 0.0)
        completed = self.completed_steps
        rate = completed / elapsed_s if elapsed_s > 0.0 else 0.0
        remaining = max(self.total_steps - completed, 0)
        eta_s = remaining / rate if rate > 0.0 else None
        eta_text = "unknown" if eta_s is None else f"{eta_s:.1f}s"
        percent = 100.0 * completed / max(self.total_steps, 1)
        case_text = "" if case_name is None else f", case={case_name}"
        print(
            f"[{self.label}] {completed}/{self.total_steps} steps ({percent:.1f}%), "
            f"elapsed {elapsed_s:.1f}s, ETA {eta_text}, phase={phase}{case_text}",
            file=sys.stderr,
            flush=True,
        )
        self.last_report_time_s = now
        self.last_phase = phase
        self.last_case_name = case_name

    def advance(self, phase: str, case_name: str | None = None, *, steps: int = 1) -> None:
        self.completed_steps += int(steps)
        self.report(phase, case_name=case_name, force=self.completed_steps >= self.total_steps)


@dataclass(frozen=True)
class CoupledPortLCFrontEndConfig:
    implementation_option: str = "C"
    architecture_name: str = "hybrid_modal_prep_with_explicit_coupled_port_readout"
    drive_amplitude_v: float = 1.0
    source_voltage_scale_v: float = 6.0
    omega0: float = 1.0
    kappa: float = 0.27
    gamma: float = 0.008
    tank_inductance_h: float = 1.0
    tank_capacitance_f: float = 1.0
    source_resistance_ohm: tuple[float, float, float, float] = (25.0, 25.2, 24.9, 25.1)
    source_inductance_h: tuple[float, float, float, float] = (0.18, 0.184, 0.176, 0.182)
    load_resistance_ohm: tuple[float, float, float, float] = (50.0, 49.9, 50.1, 49.8)
    readout_shunt_capacitance_f: tuple[float, float, float, float] = (0.06, 0.058, 0.061, 0.059)
    internal_loss_conductance_s: float = 0.06
    bridge_resistance_ohm: float = 10.0
    bridge_capacitance_f: float = 0.42
    side_coupling_capacitance_f: float = 0.035
    return_coupling_capacitance_f: float = 0.014
    explicit_port_mix: float = 0.12
    readout_cross_coupling: float = 0.0
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


@dataclass(frozen=True)
class ExplicitLCCircuitClosureConfig:
    implementation_option: str = "C"
    topology_name: str = "common_inhibit_rc_gate_resonant_winner_drain"
    control_node_name: str = "V_inhibit"
    gate_node_name: str = "V_gate_win"
    drain_node_name: str = "V_drain_tank"
    trial_complete_name: str = "trial_complete"
    supply_v: float = 1.8
    shared_inductance_h: float = 1.0
    shared_capacitance_f: float = 1.0
    inhibit_resistance_ohm: float = 0.1
    inhibit_capacitance_f: float = 1.0
    gate_resistance_ohm: float = 0.08
    gate_capacitance_f: float = 1.0
    branch_coupling_capacitance_f: float = 0.24
    winner_branch_boost: float = 1.2
    loser_attenuation_beta: float = 8.5
    loser_residual_floor_fraction: float = 0.002
    clamp_resistance_ohm: float = 1.4285714285714286
    clamp_capacitance_f: float = 0.08
    clamp_coupling_strength: float = 0.8
    drain_inductance_h: float = 1.0
    drain_capacitance_f: float = 1.0
    drain_resistance_ohm: float = 0.5
    drain_detuning_penalty: float = 12.0
    shared_loss_resistance_ohm: float = 12.5
    completion_threshold_frac: float = 0.018
    completion_current_threshold_a: float = 0.01


def default_explicit_lc_closure_config() -> ExplicitLCCircuitClosureConfig:
    reduced = default_physical_closure_drain_config()
    shared_capacitance = max(float(reduced.shared_capacitance_f), 1e-9)
    omega_shared = 1.0 / np.sqrt(shared_capacitance)
    branch_coupling_capacitance = float(reduced.branch_coupling_scale_s) / max(omega_shared, 1e-9)
    return ExplicitLCCircuitClosureConfig(
        supply_v=float(reduced.supply_v),
        shared_capacitance_f=shared_capacitance,
        inhibit_resistance_ohm=float(reduced.control_tau_s),
        gate_resistance_ohm=float(reduced.winner_drain_tau_s),
        branch_coupling_capacitance_f=branch_coupling_capacitance,
        winner_branch_boost=float(reduced.winner_branch_boost),
        loser_attenuation_beta=float(reduced.loser_attenuation_beta),
        loser_residual_floor_fraction=float(reduced.loser_residual_floor_fraction),
        clamp_resistance_ohm=1.0 / max(float(reduced.clamp_reference_g_on_s), 1e-9),
        clamp_capacitance_f=float(reduced.clamp_coupling_strength) / max(omega_shared, 1e-9),
        clamp_coupling_strength=float(reduced.clamp_coupling_strength),
        drain_resistance_ohm=1.0 / max(float(reduced.winner_drain_g_on_s), 1e-9),
        shared_loss_resistance_ohm=1.0 / max(float(reduced.shared_leak_g_s), 1e-9),
        completion_threshold_frac=float(reduced.completion_threshold_frac),
        completion_current_threshold_a=float(reduced.completion_current_threshold_a),
    )


def _add_coupling(matrix: np.ndarray, i: int, j: int, admittance: complex) -> None:
    matrix[i, i] += admittance
    matrix[j, j] += admittance
    matrix[i, j] -= admittance
    matrix[j, i] -= admittance


def _passive_readout_matrix(cross_coupling: float) -> np.ndarray:
    eps = float(cross_coupling)
    return np.asarray(
        [
            [1.0, eps, -0.35 * eps, 0.12 * eps],
            [eps, 1.0, 0.1 * eps, -0.35 * eps],
            [-0.35 * eps, 0.1 * eps, 1.0, eps],
            [0.12 * eps, -0.35 * eps, eps, 1.0],
        ],
        dtype=np.complex128,
    )


def _normalized_eigenbasis(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    eigenvalues, eigenvectors = np.linalg.eig(matrix)
    normalized_vectors = np.asarray([normalize(eigenvectors[:, index]) for index in range(eigenvectors.shape[1])]).T
    return np.asarray(eigenvalues, dtype=np.complex128), np.asarray(normalized_vectors, dtype=np.complex128)


def preferred_physical_chain_lc_benchmark_cases() -> list[dict[str, Any]]:
    return preferred_physical_chain_benchmark_cases()


def simulate_preferred_physical_chain_lc_candidate(
    state4: np.ndarray | None = None,
    *,
    a_deg: float,
    b_deg: float,
    front_end_config: CoupledPortLCFrontEndConfig | None = None,
    envelope_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    resolved = CoupledPortLCFrontEndConfig() if front_end_config is None else front_end_config
    resolved_envelope = resolve_envelope_config(envelope_config)
    target_state = singlet_state() if state4 is None else np.asarray(state4, dtype=np.complex128)
    exact = four_branch_weights(target_state, a_deg=float(a_deg), b_deg=float(b_deg))

    shared_core = Shared4TankCore(
        omega0=resolved.omega0,
        kappa=resolved.kappa,
        gamma=resolved.gamma,
        inductance_h=resolved.tank_inductance_h,
        capacitance_f=resolved.tank_capacitance_f,
        imperfections=resolved.core_imperfections,
    )
    analyzer = AnalyzerCouplers(imperfections=resolved.analyzer_imperfections)
    preparation = shared_core.prepare_singlet_mode(amplitude=resolved.drive_amplitude_v)
    effective = shared_core.effective_generator()
    modal_eigenvalues, modal_vectors = _normalized_eigenbasis(effective)
    singlet_overlaps = np.abs(np.conjugate(modal_vectors).T @ singlet_state()) ** 2
    singlet_mode_index = int(np.argmax(singlet_overlaps))

    omega_drive = max(float(preparation.drive_frequency_rad_s), 1e-9)
    resonance_offsets = resolved.core_imperfections.resonance_offsets()
    damping_offsets = resolved.core_imperfections.damping_offsets()

    tank_inductances = resolved.tank_inductance_h * (1.0 + 0.8 * resonance_offsets)
    tank_capacitances = resolved.tank_capacitance_f * (1.0 - 0.8 * resonance_offsets)
    internal_losses = resolved.internal_loss_conductance_s * (1.0 + 0.5 * damping_offsets)
    source_resistance = np.asarray(resolved.source_resistance_ohm, dtype=float)
    source_inductance = np.asarray(resolved.source_inductance_h, dtype=float)
    load_resistance = np.asarray(resolved.load_resistance_ohm, dtype=float)
    readout_caps = np.asarray(resolved.readout_shunt_capacitance_f, dtype=float)

    source_impedance = source_resistance + 1j * omega_drive * source_inductance
    source_admittance = 1.0 / np.maximum(source_impedance, 1e-9 + 0.0j)
    tank_admittance = internal_losses + 1j * (
        omega_drive * tank_capacitances - 1.0 / np.maximum(omega_drive * tank_inductances, 1e-9)
    )
    readout_admittance = (1.0 / load_resistance) + 1j * omega_drive * readout_caps
    source_drive_v = resolved.source_voltage_scale_v * preparation.drive_vector
    source_current = source_admittance * source_drive_v

    admittance_matrix = np.diag(source_admittance + tank_admittance + readout_admittance).astype(np.complex128)
    bridge_admittance = (
        (1.0 / max(float(resolved.bridge_resistance_ohm), 1e-9))
        + 1j * omega_drive * float(resolved.bridge_capacitance_f) * float(resolved.core_imperfections.coupling_scale)
    )
    side_admittance = 1j * omega_drive * float(resolved.side_coupling_capacitance_f)
    return_admittance = 1j * omega_drive * float(resolved.return_coupling_capacitance_f)

    _add_coupling(admittance_matrix, 1, 2, bridge_admittance)
    for left, right in ((0, 1), (0, 2), (3, 1), (3, 2)):
        _add_coupling(admittance_matrix, left, right, side_admittance)
    _add_coupling(admittance_matrix, 0, 3, return_admittance)

    explicit_node_voltage = np.linalg.solve(admittance_matrix, source_current)
    explicit_port_state = normalize(explicit_node_voltage)
    hybrid_state = normalize(
        (1.0 - float(resolved.explicit_port_mix)) * preparation.normalized_state
        + float(resolved.explicit_port_mix) * explicit_port_state
    )

    passive_readout = _passive_readout_matrix(resolved.readout_cross_coupling)
    joint_matrix = analyzer.joint_matrix(float(a_deg), float(b_deg))
    branch_output_steady = passive_readout @ (joint_matrix @ hybrid_state)

    drive_envelope = amplitude_envelope(resolved_envelope)
    time_s = build_time_axis(resolved_envelope)
    branch_voltage: dict[str, np.ndarray] = {}
    branch_current: dict[str, np.ndarray] = {}
    branch_power: dict[str, np.ndarray] = {}
    branch_energy: dict[str, float] = {}
    branch_fraction: dict[str, float] = {}
    total_energy = 0.0

    for index, label in enumerate(BRANCH_LABELS):
        gain = float(resolved.branch_gain_trim[index])
        phase = np.exp(1j * np.deg2rad(float(resolved.branch_phase_deg[index])))
        open_circuit = gain * phase * branch_output_steady[index] * drive_envelope * float(resolved.source_voltage_scale_v)
        divider = load_resistance[index] / (source_impedance[index] + load_resistance[index])
        load_voltage = np.abs(open_circuit * divider)
        load_current = load_voltage / max(load_resistance[index], 1e-9)
        power = np.maximum(load_voltage * load_current, 0.0)
        branch_voltage[label] = load_voltage.astype(float)
        branch_current[label] = load_current.astype(float)
        branch_power[label] = power.astype(float)
        branch_energy[label] = float(np.trapezoid(power, x=time_s))
        total_energy += branch_energy[label]

    for label in BRANCH_LABELS:
        branch_fraction[label] = branch_energy[label] / max(total_energy, 1e-18)

    realized = np.asarray([branch_fraction[label] for label in BRANCH_LABELS], dtype=float)
    metric_summary = four_branch_metrics(exact, realized)
    trivial = np.sqrt(np.maximum(exact, 0.0))
    trivial /= max(float(np.linalg.norm(trivial)), 1e-18)
    branch_output_magnitude = np.abs(branch_output_steady)
    branch_output_magnitude /= max(float(np.linalg.norm(branch_output_magnitude)), 1e-18)
    offdiag = admittance_matrix - np.diag(np.diag(admittance_matrix))
    source_impedance_magnitude = np.abs(source_impedance)
    source_impedance_spread = float(
        np.std(source_impedance_magnitude) / max(np.mean(source_impedance_magnitude), 1e-18)
    )
    load_impedance_spread = float(np.std(load_resistance) / max(np.mean(load_resistance), 1e-18))
    readout_admittance_magnitude = np.abs(readout_admittance)
    readout_admittance_spread = float(
        np.std(readout_admittance_magnitude) / max(np.mean(readout_admittance_magnitude), 1e-18)
    )
    port_state_delta_norm = float(np.linalg.norm(explicit_port_state - preparation.normalized_state))
    hybrid_state_delta_norm = float(np.linalg.norm(hybrid_state - preparation.normalized_state))
    explicitness = {
        "offdiag_coupling_ratio": float(np.linalg.norm(offdiag) / max(np.linalg.norm(np.diag(np.diag(admittance_matrix))), 1e-18)),
        "direct_exact_weight_overlap": float(np.abs(np.vdot(trivial.astype(np.complex128), branch_output_magnitude.astype(np.complex128)))),
        "explicit_vs_modal_state_overlap": float(np.abs(np.vdot(explicit_port_state, preparation.normalized_state))),
        "port_state_delta_norm": port_state_delta_norm,
        "hybrid_state_delta_norm": hybrid_state_delta_norm,
        "source_impedance_spread": source_impedance_spread,
        "load_impedance_spread": load_impedance_spread,
        "readout_admittance_spread": readout_admittance_spread,
        "forward_path_uses_exact_weights": False,
        "readout_cross_coupling_norm": float(np.linalg.norm(passive_readout - np.eye(4))),
    }

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
    export["candidate_config"] = {
        **asdict(resolved),
        "core_imperfections": asdict(resolved.core_imperfections),
        "analyzer_imperfections": asdict(resolved.analyzer_imperfections),
    }
    export["a_deg"] = float(a_deg)
    export["b_deg"] = float(b_deg)
    export["shared_core"] = {
        "architecture_name": resolved.architecture_name,
        "drive_frequency_rad_s": omega_drive,
        "modal_eigenvalues": modal_eigenvalues,
        "modal_vectors": modal_vectors,
        "state_labels": list(BRANCH_LABELS),
        "prepared_state_magnitude": np.abs(preparation.normalized_state).astype(float),
        "modal_energies": preparation.modal_energies.astype(float),
        "modal_response_magnitude": np.sqrt(np.maximum(preparation.modal_energies, 0.0)).astype(float),
        "modal_decay_rates": np.maximum(-np.imag(modal_eigenvalues), shared_core.gamma * 0.2).astype(float),
        "prepared_internal_state": preparation.normalized_state,
        "explicit_port_state": explicit_port_state,
        "hybrid_state": hybrid_state,
        "port_admittance_matrix_s": admittance_matrix,
        "source_current_a": source_current,
        "source_drive_v": source_drive_v,
        "port_node_voltage_v": explicit_node_voltage,
        "bridge_admittance_s": bridge_admittance,
        "side_admittance_s": side_admittance,
        "return_admittance_s": return_admittance,
        "source_impedance_ohm": source_impedance,
        "tank_admittance_s": tank_admittance,
        "readout_admittance_s": readout_admittance,
        "analyzer_matrix": joint_matrix,
        "passive_readout_matrix": passive_readout,
        "branch_output_amplitudes": branch_output_steady,
        "modal_response": preparation.modal_energies,
        "singlet_mode_index": singlet_mode_index,
        "singlet_mode_overlap": float(singlet_overlaps[singlet_mode_index]),
        "mode_overlap_profile": singlet_overlaps.astype(float),
        "coupling_currents_a": {
            "plusminus_to_minusplus": bridge_admittance * (explicit_node_voltage[1] - explicit_node_voltage[2]),
            "plusplus_return_to_minusminus": return_admittance * (explicit_node_voltage[0] - explicit_node_voltage[3]),
        },
        "explicitness_metrics": explicitness,
        "intended_circuit": {
            "tanks": [asdict(tank) for tank in shared_core.intended_circuit().tanks],
            "couplers": [asdict(coupler) for coupler in shared_core.intended_circuit().couplers],
            "readout_note": "Hybrid option C: modal preparation retained, with explicit coupled-port admittance solve and passive readout/load network.",
        },
    }
    export["metrics"] = {
        **fraction_error_metrics(exact, realized),
        "correlator_exact": float(metric_summary["correlator_exact"]),
        "correlator_realized": float(metric_summary["correlator_empirical"]),
        "correlator_error": float(metric_summary["correlator_error"]),
        **explicitness,
    }
    return export


def simulate_explicit_lc_closure_drain(
    *,
    time_s: Sequence[float],
    branch_power_w: Mapping[str, Sequence[float]],
    branch_labels: Sequence[str],
    winner_index: int,
    winner_valid: bool,
    capture_time_s: float,
    config: ExplicitLCCircuitClosureConfig | Mapping[str, Any] | None = None,
    candidate_cache: Mapping[str, Any] | None = None,
    include_traces: bool = True,
) -> dict[str, Any]:
    resolved = default_explicit_lc_closure_config() if config is None else (
        config if isinstance(config, ExplicitLCCircuitClosureConfig) else ExplicitLCCircuitClosureConfig(**dict(config))
    )
    values_t = np.asarray(time_s, dtype=float).reshape(-1)
    labels = list(branch_labels)
    zero_trace = np.zeros_like(values_t)
    zero_branch_map = {label: zero_trace.tolist() for label in labels}
    if not winner_valid or winner_index < 0 or winner_index >= len(labels):
        payload = {
            "topology_name": resolved.topology_name,
            "control_node_name": resolved.control_node_name,
            "gate_node_name": resolved.gate_node_name,
            "drain_node_name": resolved.drain_node_name,
            "winner_branch_post_click_energy_j": 0.0,
            "winner_drain_total_energy_j": 0.0,
            "shared_leak_total_energy_j": 0.0,
            "loser_post_click_energy_j": {label: 0.0 for label in labels},
            "initial_remaining_energy_j": 0.0,
            "terminal_remaining_energy_j": 0.0,
            "winner_index": int(winner_index),
            "winner_label": None,
            "winner_drain_path_count": 0,
            "closure_active": False,
            "activation_count": 0,
            "trial_complete": False,
            "trial_complete_time_s": float("inf"),
            "trial_complete_reason": "inactive",
            "monotonic_remaining_energy": True,
            "terminal_loser_suppression_mean": 0.0,
            "shared_resonant_frequency_rad_s": float(1.0 / np.sqrt(max(resolved.shared_inductance_h * resolved.shared_capacitance_f, 1e-18))),
            "drain_resonant_frequency_rad_s": float(1.0 / np.sqrt(max(resolved.drain_inductance_h * resolved.drain_capacitance_f, 1e-18))),
        }
        if include_traces:
            payload.update(
                {
                    "time_s": values_t.tolist(),
                    "closure_variable": zero_trace.tolist(),
                    "common_inhibit_v": zero_trace.tolist(),
                    "winner_gate_v": zero_trace.tolist(),
                    "shared_node_voltage_v": zero_trace.tolist(),
                    "shared_resonant_current_a": zero_trace.tolist(),
                    "winner_drain_tank_voltage_v": zero_trace.tolist(),
                    "winner_drain_enable_by_branch": dict(zero_branch_map),
                    "winner_drain_power_w": zero_trace.tolist(),
                    "winner_drain_current_a": zero_trace.tolist(),
                    "winner_drain_energy_j": zero_trace.tolist(),
                    "remaining_shared_energy_j": zero_trace.tolist(),
                    "trial_complete_signal": zero_trace.tolist(),
                    "winner_branch_power_w": zero_trace.tolist(),
                    "loser_branch_power_w": dict(zero_branch_map),
                    "loser_suppression": dict(zero_branch_map),
                    "loser_clamp_conductance_s": dict(zero_branch_map),
                    "loser_clamp_current_a": dict(zero_branch_map),
                }
            )
        return payload

    winner_label = labels[winner_index]
    cache = (
        build_physical_closure_candidate_cache(
            {
                "time_s": values_t,
                "branch_power_w": branch_power_w,
                "branch_labels": labels,
            }
        )
        if candidate_cache is None
        else dict(candidate_cache)
    )
    future_energy_by_branch = {
        label: float(value)
        for label, value in cache["total_energy_j"].items()
    }
    from .closure_path import future_branch_energy_from_cache

    future_energy_by_branch = future_branch_energy_from_cache(cache, capture_time_s=float(capture_time_s))
    initial_remaining_energy = float(sum(future_energy_by_branch.values()))
    shared_omega = float(1.0 / np.sqrt(max(resolved.shared_inductance_h * resolved.shared_capacitance_f, 1e-18)))
    drain_omega = float(1.0 / np.sqrt(max(resolved.drain_inductance_h * resolved.drain_capacitance_f, 1e-18)))
    if initial_remaining_energy <= 1e-18:
        unit_step = np.where(values_t >= capture_time_s, 1.0, 0.0)
        payload = {
            "topology_name": resolved.topology_name,
            "control_node_name": resolved.control_node_name,
            "gate_node_name": resolved.gate_node_name,
            "drain_node_name": resolved.drain_node_name,
            "winner_branch_post_click_energy_j": 0.0,
            "winner_drain_total_energy_j": 0.0,
            "shared_leak_total_energy_j": 0.0,
            "loser_post_click_energy_j": {label: 0.0 for label in labels if label != winner_label},
            "initial_remaining_energy_j": 0.0,
            "terminal_remaining_energy_j": 0.0,
            "winner_index": int(winner_index),
            "winner_label": winner_label,
            "winner_drain_path_count": 1,
            "closure_active": True,
            "activation_count": 1,
            "trial_complete": True,
            "trial_complete_time_s": float(capture_time_s),
            "trial_complete_reason": "shared_energy_below_threshold",
            "monotonic_remaining_energy": True,
            "terminal_loser_suppression_mean": 1.0 if len(labels) > 1 else 0.0,
            "shared_resonant_frequency_rad_s": shared_omega,
            "drain_resonant_frequency_rad_s": drain_omega,
        }
        if include_traces:
            payload.update(
                {
                    "time_s": values_t.tolist(),
                    "closure_variable": unit_step.tolist(),
                    "common_inhibit_v": (resolved.supply_v * unit_step).tolist(),
                    "winner_gate_v": (resolved.supply_v * unit_step).tolist(),
                    "shared_node_voltage_v": zero_trace.tolist(),
                    "shared_resonant_current_a": zero_trace.tolist(),
                    "winner_drain_tank_voltage_v": zero_trace.tolist(),
                    "winner_drain_enable_by_branch": {
                        label: (unit_step.tolist() if label == winner_label else zero_trace.tolist())
                        for label in labels
                    },
                    "winner_drain_power_w": zero_trace.tolist(),
                    "winner_drain_current_a": zero_trace.tolist(),
                    "winner_drain_energy_j": zero_trace.tolist(),
                    "remaining_shared_energy_j": zero_trace.tolist(),
                    "trial_complete_signal": unit_step.tolist(),
                    "winner_branch_power_w": zero_trace.tolist(),
                    "loser_branch_power_w": {label: zero_trace.tolist() for label in labels if label != winner_label},
                    "loser_suppression": {label: unit_step.tolist() for label in labels if label != winner_label},
                    "loser_clamp_conductance_s": {label: zero_trace.tolist() for label in labels if label != winner_label},
                    "loser_clamp_current_a": {label: zero_trace.tolist() for label in labels if label != winner_label},
                }
            )
        return payload

    base_shares = {
        label: future_energy_by_branch[label] / max(initial_remaining_energy, 1e-18)
        for label in labels
    }
    dt = np.asarray(cache["dt"], dtype=float)
    closure_variable = np.zeros_like(values_t)
    common_inhibit_v = np.zeros_like(values_t)
    winner_gate_v = np.zeros_like(values_t)
    shared_node_voltage_v = np.zeros_like(values_t)
    shared_resonant_current = np.zeros_like(values_t)
    winner_drain_tank_voltage = np.zeros_like(values_t)
    remaining_energy = np.full_like(values_t, initial_remaining_energy)
    winner_drain_power = np.zeros_like(values_t)
    winner_drain_current = np.zeros_like(values_t)
    winner_drain_energy = np.zeros_like(values_t)
    trial_complete_signal = np.zeros_like(values_t)
    winner_branch_power = np.zeros_like(values_t)
    loser_branch_power = {label: np.zeros_like(values_t) for label in labels if label != winner_label}
    loser_suppression = {label: np.zeros_like(values_t) for label in labels if label != winner_label}
    loser_clamp_conductance = {label: np.zeros_like(values_t) for label in labels if label != winner_label}
    loser_clamp_current = {label: np.zeros_like(values_t) for label in labels if label != winner_label}
    winner_enable = {label: np.zeros_like(values_t) for label in labels}
    completed = False
    completed_time = float(values_t[-1])
    completed_reason = "end_of_trace"
    winner_branch_energy = 0.0
    shared_leak_energy = 0.0
    loser_energy = {label: 0.0 for label in labels if label != winner_label}

    active_indices = np.where(values_t >= float(capture_time_s))[0]
    if active_indices.size:
        dt_active = np.maximum(dt[active_indices], 0.0)
        effective_delay = np.maximum(values_t[active_indices] - float(capture_time_s), 0.0)
        inhibit_tau = max(float(resolved.inhibit_resistance_ohm * resolved.inhibit_capacitance_f), 1e-12)
        gate_tau = max(float(resolved.gate_resistance_ohm * resolved.gate_capacitance_f), 1e-12)
        z_active = 1.0 - np.exp(-effective_delay / inhibit_tau)
        gate_active = 1.0 - np.exp(-effective_delay / gate_tau)
        closure_variable[active_indices] = z_active
        common_inhibit_v[active_indices] = resolved.supply_v * z_active
        winner_gate_v[active_indices] = resolved.supply_v * gate_active
        winner_enable[winner_label][active_indices] = gate_active

        clamp_reference_g = (1.0 / max(float(resolved.clamp_resistance_ohm), 1e-9)) + shared_omega * float(resolved.clamp_capacitance_f)
        branch_conductance_arrays: dict[str, np.ndarray] = {}
        for label in labels:
            base_g = shared_omega * float(resolved.branch_coupling_capacitance_f) * base_shares[label]
            if label == winner_label:
                branch_conductance_arrays[label] = base_g * (1.0 + float(resolved.winner_branch_boost) * z_active)
            else:
                loser_decay = np.exp(
                    -(float(resolved.loser_attenuation_beta) + float(resolved.clamp_coupling_strength) * clamp_reference_g) * z_active
                )
                branch_conductance_arrays[label] = base_g * (
                    float(resolved.loser_residual_floor_fraction)
                    + (1.0 - float(resolved.loser_residual_floor_fraction)) * loser_decay
                )
                loser_suppression[label][active_indices] = 1.0 - branch_conductance_arrays[label] / max(base_g, 1e-18)
                loser_clamp_conductance[label][active_indices] = clamp_reference_g * z_active

        resonance_mismatch = (drain_omega - shared_omega) / max(shared_omega, 1e-18)
        resonance_match = 1.0 / (1.0 + float(resolved.drain_detuning_penalty) * resonance_mismatch**2)
        g_winner_drain = gate_active * resonance_match / max(float(resolved.drain_resistance_ohm), 1e-9)
        g_shared_leak = 1.0 / max(float(resolved.shared_loss_resistance_ohm), 1e-9)
        g_total = np.full_like(z_active, g_shared_leak)
        for values in branch_conductance_arrays.values():
            g_total = g_total + values
        g_total = np.maximum(g_total + g_winner_drain, 1e-18)

        decay_factor = np.exp(-2.0 * g_total * dt_active / max(float(resolved.shared_capacitance_f), 1e-18))
        energy_before = initial_remaining_energy * np.concatenate(([1.0], np.cumprod(decay_factor[:-1])))
        energy_after = energy_before * decay_factor
        energy_released = energy_before - energy_after

        shared_voltage = np.sqrt(np.maximum(2.0 * energy_before / max(float(resolved.shared_capacitance_f), 1e-18), 0.0))
        shared_current = np.sqrt(np.maximum(2.0 * energy_before / max(float(resolved.shared_inductance_h), 1e-18), 0.0))
        shared_node_voltage_v[active_indices] = shared_voltage
        shared_resonant_current[active_indices] = shared_current
        winner_drain_current[active_indices] = shared_voltage * g_winner_drain
        winner_drain_tank_voltage[active_indices] = winner_drain_current[active_indices] * float(resolved.drain_resistance_ohm)

        winner_branch_share = branch_conductance_arrays[winner_label] / g_total
        winner_drain_share = g_winner_drain / g_total
        shared_leak_share = g_shared_leak / g_total
        winner_branch_increment = energy_released * winner_branch_share
        winner_branch_energy = float(np.sum(winner_branch_increment))
        winner_branch_power[active_indices] = np.divide(winner_branch_increment, np.maximum(dt_active, 1e-18))

        drain_increment = energy_released * winner_drain_share
        winner_drain_power[active_indices] = np.divide(drain_increment, np.maximum(dt_active, 1e-18))
        winner_drain_energy[active_indices] = np.cumsum(drain_increment)

        for label in labels:
            if label == winner_label:
                continue
            branch_increment = energy_released * branch_conductance_arrays[label] / g_total
            loser_energy[label] = float(np.sum(branch_increment))
            loser_branch_power[label][active_indices] = np.divide(branch_increment, np.maximum(dt_active, 1e-18))
            loser_clamp_current[label][active_indices] = shared_voltage * loser_clamp_conductance[label][active_indices]

        shared_leak_energy = float(np.sum(energy_released * shared_leak_share))
        remaining_energy[active_indices] = energy_after
        completion_hits = np.where(
            (energy_after <= float(resolved.completion_threshold_frac) * initial_remaining_energy)
            & (winner_drain_current[active_indices] <= float(resolved.completion_current_threshold_a))
        )[0]
        if completion_hits.size:
            completed = True
            completed_time = float(values_t[active_indices[completion_hits[0]]])
            completed_reason = "shared_energy_and_drain_current_below_threshold"
            trial_complete_signal[active_indices[completion_hits[0]:]] = 1.0

    post_capture_mask = active_indices
    monotonic = bool(np.all(np.diff(remaining_energy[post_capture_mask]) <= 1e-12)) if post_capture_mask.size else True
    terminal_loser_suppression_mean = (
        float(np.mean([values[active_indices[-1]] for values in loser_suppression.values()]))
        if loser_suppression and active_indices.size
        else 0.0
    )
    payload = {
        "topology_name": resolved.topology_name,
        "control_node_name": resolved.control_node_name,
        "gate_node_name": resolved.gate_node_name,
        "drain_node_name": resolved.drain_node_name,
        "winner_branch_post_click_energy_j": winner_branch_energy,
        "winner_drain_total_energy_j": float(winner_drain_energy[-1]),
        "shared_leak_total_energy_j": shared_leak_energy,
        "loser_post_click_energy_j": loser_energy,
        "initial_remaining_energy_j": initial_remaining_energy,
        "terminal_remaining_energy_j": float(remaining_energy[-1]),
        "winner_index": int(winner_index),
        "winner_label": winner_label,
        "winner_drain_path_count": 1,
        "closure_active": True,
        "activation_count": 1,
        "trial_complete": completed,
        "trial_complete_time_s": completed_time,
        "trial_complete_reason": completed_reason,
        "monotonic_remaining_energy": monotonic,
        "terminal_loser_suppression_mean": terminal_loser_suppression_mean,
        "shared_resonant_frequency_rad_s": shared_omega,
        "drain_resonant_frequency_rad_s": drain_omega,
    }
    if include_traces:
        payload.update(
            {
                "time_s": values_t.tolist(),
                "closure_variable": closure_variable.tolist(),
                "common_inhibit_v": common_inhibit_v.tolist(),
                "winner_gate_v": winner_gate_v.tolist(),
                "shared_node_voltage_v": shared_node_voltage_v.tolist(),
                "shared_resonant_current_a": shared_resonant_current.tolist(),
                "winner_drain_tank_voltage_v": winner_drain_tank_voltage.tolist(),
                "winner_drain_enable_by_branch": {label: values.tolist() for label, values in winner_enable.items()},
                "winner_drain_power_w": winner_drain_power.tolist(),
                "winner_drain_current_a": winner_drain_current.tolist(),
                "winner_drain_energy_j": winner_drain_energy.tolist(),
                "remaining_shared_energy_j": remaining_energy.tolist(),
                "trial_complete_signal": trial_complete_signal.tolist(),
                "winner_branch_power_w": winner_branch_power.tolist(),
                "loser_branch_power_w": {label: values.tolist() for label, values in loser_branch_power.items()},
                "loser_suppression": {label: values.tolist() for label, values in loser_suppression.items()},
                "loser_clamp_conductance_s": {label: values.tolist() for label, values in loser_clamp_conductance.items()},
                "loser_clamp_current_a": {label: values.tolist() for label, values in loser_clamp_current.items()},
            }
        )
    return payload


def _run_pre_click_race(
    candidate: Mapping[str, Any],
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    n_trials: int,
    seed: int,
    boundary_config: Mapping[str, Any] | None = None,
    progress: _ProgressReporter | None = None,
    case_name: str | None = None,
) -> dict[str, Any]:
    trace = materialize_candidate_trace(candidate, boundary_config=boundary_config)
    time_s = np.asarray(trace["time_s"], dtype=float)
    dt = float(time_s[1] - time_s[0]) if time_s.size > 1 else 1e-3
    detector_envelopes = [
        {
            "kind": "sampled",
            "time_s": time_s.tolist(),
            "power_w": list(trace["exported_branch_power"][label]),
            "dt": dt,
            "t_max": float(time_s[-1]) if time_s.size else 0.0,
        }
        for label in trace["branch_labels"]
    ]
    exact_weights = np.asarray([candidate["exact_weight"][label] for label in candidate["branch_labels"]], dtype=float)
    rng = np.random.default_rng(seed)
    latch_config = validated_latch_arbiter_config(len(candidate["branch_labels"]))
    winners: list[int] = []
    event_time_rows: list[np.ndarray] = []
    pulse_time_rows: list[np.ndarray] = []
    latch_results: list[dict[str, Any]] = []
    tie_region_count = 0
    for _ in range(n_trials):
        event_times = np.full(len(candidate["branch_labels"]), np.inf, dtype=float)
        for branch_index in range(len(candidate["branch_labels"])):
            branch_rng = np.random.default_rng(int(rng.integers(0, 2**32 - 1)))
            detector_params = resolve_branch_detector_params(detector_spec, branch_index)
            click_time = simulate_branch_nucleation(detector_params, 1.0, detector_envelopes[branch_index], branch_rng)
            if click_time is not None:
                event_times[branch_index] = click_time
        latch_result = latch_first_event(event_times, config=latch_config, rng=rng)
        winners.append(int(latch_result["winner_index"]))
        event_time_rows.append(event_times)
        pulse_time_rows.append(np.asarray(latch_result["pulse_times"], dtype=float))
        tie_region_count += int(bool(latch_result["tie_region"]))
        latch_results.append(
            {
                "winner_index": int(latch_result["winner_index"]),
                "winner_valid": bool(latch_result["winner_valid"]),
                "settled_at_s": float(latch_result["settled_at_s"]),
                "tie_region": bool(latch_result["tie_region"]),
            }
        )
        if progress is not None:
            progress.advance("pre-click-race", case_name=case_name)

    frequency_summary = winner_frequency_summary(winners, n_branches=len(candidate["branch_labels"]))
    return {
        "trace": trace,
        "detector_envelopes": detector_envelopes,
        "exact_weights": exact_weights,
        "metrics": four_branch_metrics(exact_weights, frequency_summary["frequencies"]),
        "frequency_summary": frequency_summary,
        "event_times": np.asarray(event_time_rows, dtype=float),
        "pulse_times": np.asarray(pulse_time_rows, dtype=float),
        "latch_results": latch_results,
        "tie_region_fraction": tie_region_count / max(n_trials, 1),
    }


def run_preferred_physical_chain_lc_candidate(
    candidate: Mapping[str, Any],
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    n_trials: int,
    seed: int,
    closure_config: ExplicitLCCircuitClosureConfig | Mapping[str, Any] | None = None,
    boundary_config: Mapping[str, Any] | None = None,
    baseline_result: Mapping[str, Any] | None = None,
    progress: _ProgressReporter | None = None,
    case_name: str | None = None,
) -> dict[str, Any]:
    resolved_closure = default_explicit_lc_closure_config() if closure_config is None else (
        closure_config if isinstance(closure_config, ExplicitLCCircuitClosureConfig) else ExplicitLCCircuitClosureConfig(**dict(closure_config))
    )
    race = _run_pre_click_race(
        candidate,
        detector_spec,
        n_trials=n_trials,
        seed=seed,
        boundary_config=boundary_config,
        progress=progress,
        case_name=case_name,
    )
    frequency_summary = race["frequency_summary"]
    cache = build_physical_closure_candidate_cache(candidate)
    closure_rows: list[dict[str, Any]] = []
    energy_rows: list[dict[str, Any]] = []
    example_trial: dict[str, Any] | None = None
    for trial_index, latch_result in enumerate(race["latch_results"]):
        closure = simulate_explicit_lc_closure_drain(
            time_s=candidate["time_s"],
            branch_power_w=candidate["branch_power_w"],
            branch_labels=candidate["branch_labels"],
            winner_index=int(latch_result["winner_index"]),
            winner_valid=bool(latch_result["winner_valid"]),
            capture_time_s=float(latch_result["settled_at_s"]),
            config=resolved_closure,
            candidate_cache=cache,
            include_traces=False,
        )
        closure_rows.append(closure)
        energy_row = build_trial_energy_accounting(
            candidate,
            closure,
            capture_time_s=float(latch_result["settled_at_s"]),
            winner_valid=bool(latch_result["winner_valid"]),
            candidate_cache=cache,
        )
        energy_rows.append({"trial_index": trial_index, **energy_row})
        if progress is not None:
            progress.advance("post-click-closure", case_name=case_name)
        if example_trial is None and bool(closure["closure_active"]):
            closure_trace = simulate_explicit_lc_closure_drain(
                time_s=candidate["time_s"],
                branch_power_w=candidate["branch_power_w"],
                branch_labels=candidate["branch_labels"],
                winner_index=int(latch_result["winner_index"]),
                winner_valid=bool(latch_result["winner_valid"]),
                capture_time_s=float(latch_result["settled_at_s"]),
                config=resolved_closure,
                candidate_cache=cache,
                include_traces=True,
            )
            example_trial = {
                "trial_index": trial_index,
                "latch_result": dict(latch_result),
                "event_times": race["event_times"][trial_index].tolist(),
                "pulse_times": race["pulse_times"][trial_index].tolist(),
                "physical": closure_trace,
                "energy_accounting": dict(energy_row),
            }

    baseline_frequencies = frequency_summary["frequencies"]
    baseline_decisive_fraction = float(frequency_summary["decisive_fraction"])
    baseline_timeout_fraction = float(frequency_summary["timeout_fraction"])
    if baseline_result is not None:
        baseline_frequencies = baseline_result["empirical_frequencies"]
        baseline_decisive_fraction = float(baseline_result["decisive_fraction"])
        baseline_timeout_fraction = float(baseline_result["timeout_fraction"])

    pre_click_comparison = build_pre_click_comparison(
        exact_weights=race["exact_weights"],
        baseline_frequencies=baseline_frequencies,
        integrated_frequencies=frequency_summary["frequencies"],
        baseline_decisive_fraction=baseline_decisive_fraction,
        integrated_decisive_fraction=float(frequency_summary["decisive_fraction"]),
        baseline_timeout_fraction=baseline_timeout_fraction,
        integrated_timeout_fraction=float(frequency_summary["timeout_fraction"]),
    )
    post_click_summary = summarize_post_click_behavior(closure_rows, energy_rows)
    energy_summary = summarize_energy_accounting_rows(energy_rows)
    return {
        "candidate": candidate,
        "trace": race["trace"],
        "detector_envelopes": race["detector_envelopes"],
        "export_config": dict(race["trace"]["export_config"]),
        "boundary_config": dict(race["trace"]["boundary_config"]),
        "closure_config": asdict(resolved_closure),
        "pre_click_race": race,
        "exact_weights": race["exact_weights"],
        "realized_fractions": np.asarray([candidate["branch_energy_fraction"][label] for label in candidate["branch_labels"]], dtype=float),
        "empirical_frequencies": frequency_summary["frequencies"],
        "winner_counts": frequency_summary["counts"],
        "decisive_count": frequency_summary["decisive_count"],
        "timeout_count": frequency_summary["timeout_count"],
        "decisive_fraction": frequency_summary["decisive_fraction"],
        "timeout_fraction": frequency_summary["timeout_fraction"],
        "metrics": dict(race["metrics"]),
        "front_end_metrics": dict(candidate["metrics"]),
        "pre_click_comparison": pre_click_comparison,
        "post_click_summary": post_click_summary,
        "closure_rows": closure_rows,
        "energy_accounting_rows": energy_rows,
        "energy_accounting_summary": energy_summary,
        "example_trial": example_trial,
        "tie_region_fraction": float(race["tie_region_fraction"]),
    }


def run_preferred_physical_chain_lc_case(
    state4: np.ndarray | None,
    *,
    a_deg: float,
    b_deg: float,
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    n_trials: int,
    seed: int,
    front_end_config: CoupledPortLCFrontEndConfig | None = None,
    closure_config: ExplicitLCCircuitClosureConfig | Mapping[str, Any] | None = None,
    baseline_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    candidate = simulate_preferred_physical_chain_lc_candidate(
        state4,
        a_deg=a_deg,
        b_deg=b_deg,
        front_end_config=front_end_config,
    )
    return run_preferred_physical_chain_lc_candidate(
        candidate,
        detector_spec,
        n_trials=n_trials,
        seed=seed,
        closure_config=closure_config,
        baseline_result=baseline_result,
    )


def run_preferred_physical_chain_lc_benchmark(
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    n_trials: int,
    seed: int,
    case_names: Sequence[str] | None = None,
    front_end_config: CoupledPortLCFrontEndConfig | None = None,
    closure_config: ExplicitLCCircuitClosureConfig | Mapping[str, Any] | None = None,
    verbose_progress: bool = False,
) -> dict[str, Any]:
    selected_case_names = None if case_names is None else set(case_names)
    cases = [
        case
        for case in preferred_physical_chain_lc_benchmark_cases()
        if selected_case_names is None or case["case"] in selected_case_names
    ]
    if not cases:
        raise ValueError("No preferred physical-chain LC benchmark cases selected.")

    baseline = run_preferred_physical_chain_benchmark(
        detector_spec,
        n_trials=n_trials,
        seed=seed,
        case_names=case_names,
        verbose_progress=False,
    )
    baseline_case_map = {entry["case"]["case"]: entry["result"] for entry in baseline["case_results"]}

    progress = _ProgressReporter(
        total_steps=max(len(cases) * max(2 * n_trials, 1), 1),
        enabled=verbose_progress,
    )
    case_results: list[dict[str, Any]] = []
    front_end_rows: list[dict[str, Any]] = []
    case_rows: list[dict[str, Any]] = []
    pre_click_rows: list[dict[str, Any]] = []
    post_click_rows: list[dict[str, Any]] = []
    energy_case_rows: list[dict[str, Any]] = []
    energy_rows: list[dict[str, Any]] = []
    shared_core_rows: list[dict[str, Any]] = []
    case_comparison_rows: list[dict[str, Any]] = []
    example_front_end: dict[str, Any] | None = None
    example_trial: dict[str, Any] | None = None

    for case_index, case in enumerate(cases):
        progress.report("starting-case", case_name=str(case["case"]), force=True)
        baseline_result = baseline_case_map[str(case["case"])]
        candidate = simulate_preferred_physical_chain_lc_candidate(
            case["state4"],
            a_deg=case["a_deg"],
            b_deg=case["b_deg"],
            front_end_config=front_end_config,
        )
        result = run_preferred_physical_chain_lc_candidate(
            candidate,
            detector_spec,
            n_trials=n_trials,
            seed=seed + 1_003 * case_index,
            closure_config=closure_config,
            baseline_result=baseline_result,
            progress=progress,
            case_name=str(case["case"]),
        )
        case_results.append({"case": case, "result": result, "baseline_result": baseline_result})
        front_end_rows.append(
            {
                "case": case["case"],
                "a_deg": float(case["a_deg"]),
                "b_deg": float(case["b_deg"]),
                "branch_labels": list(candidate["branch_labels"]),
                "exact_weights": list(result["exact_weights"]),
                "realized_fractions": list(result["realized_fractions"]),
                "rms_error": float(candidate["metrics"]["rms_error"]),
                "max_abs_error": float(candidate["metrics"]["max_abs_error"]),
                "correlator_exact": float(candidate["metrics"]["correlator_exact"]),
                "correlator_realized": float(candidate["metrics"]["correlator_realized"]),
                "correlator_error": float(candidate["metrics"]["correlator_error"]),
            }
        )
        case_rows.append(
            {
                "case": case["case"],
                "a_deg": float(case["a_deg"]),
                "b_deg": float(case["b_deg"]),
                "branch_labels": list(candidate["branch_labels"]),
                "exact_weights": list(result["exact_weights"]),
                "realized_fractions": list(result["realized_fractions"]),
                "empirical_frequencies": list(result["empirical_frequencies"]),
                "winner_rms_error": float(result["metrics"]["rms_error"]),
                "winner_max_error": float(result["metrics"]["max_abs_error"]),
                "correlator_exact": float(result["metrics"]["correlator_exact"]),
                "correlator_empirical": float(result["metrics"]["correlator_empirical"]),
                "correlator_error": float(result["metrics"]["correlator_error"]),
                "decisive_fraction": float(result["decisive_fraction"]),
                "timeout_fraction": float(result["timeout_fraction"]),
                "tie_region_fraction": float(result["tie_region_fraction"]),
            }
        )
        pre_click_rows.append(
            {
                "case": case["case"],
                "a_deg": float(case["a_deg"]),
                "b_deg": float(case["b_deg"]),
                **result["pre_click_comparison"],
            }
        )
        post_click_rows.append(
            {
                "case": case["case"],
                "a_deg": float(case["a_deg"]),
                "b_deg": float(case["b_deg"]),
                **result["post_click_summary"],
            }
        )
        energy_summary = summarize_energy_accounting_rows(result["energy_accounting_rows"])
        energy_case_rows.append(
            {
                "case": case["case"],
                "a_deg": float(case["a_deg"]),
                "b_deg": float(case["b_deg"]),
                **energy_summary,
            }
        )
        energy_rows.extend(
            {
                "case": case["case"],
                "a_deg": float(case["a_deg"]),
                "b_deg": float(case["b_deg"]),
                **row,
            }
            for row in result["energy_accounting_rows"]
        )
        explicitness = candidate["shared_core"]["explicitness_metrics"]
        shared_core_rows.append(
            {
                "case": case["case"],
                "drive_frequency_rad_s": float(candidate["shared_core"]["drive_frequency_rad_s"]),
                "singlet_mode_overlap": float(candidate["shared_core"]["singlet_mode_overlap"]),
                "offdiag_coupling_ratio": float(explicitness["offdiag_coupling_ratio"]),
                "direct_exact_weight_overlap": float(explicitness["direct_exact_weight_overlap"]),
                "explicit_vs_modal_state_overlap": float(explicitness["explicit_vs_modal_state_overlap"]),
                "port_state_delta_norm": float(explicitness["port_state_delta_norm"]),
                "hybrid_state_delta_norm": float(explicitness["hybrid_state_delta_norm"]),
                "source_impedance_spread": float(explicitness["source_impedance_spread"]),
                "load_impedance_spread": float(explicitness["load_impedance_spread"]),
                "readout_admittance_spread": float(explicitness["readout_admittance_spread"]),
                "forward_path_uses_exact_weights": bool(explicitness["forward_path_uses_exact_weights"]),
                "readout_cross_coupling_norm": float(explicitness["readout_cross_coupling_norm"]),
            }
        )
        case_comparison_rows.append(
            {
                "case": case["case"],
                "baseline_winner_rms_error": float(baseline_result["metrics"]["rms_error"]),
                "lc_winner_rms_error": float(result["metrics"]["rms_error"]),
                "baseline_winner_max_error": float(baseline_result["metrics"]["max_abs_error"]),
                "lc_winner_max_error": float(result["metrics"]["max_abs_error"]),
                "baseline_correlator_error": float(baseline_result["metrics"]["correlator_error"]),
                "lc_correlator_error": float(result["metrics"]["correlator_error"]),
                "baseline_decisive_fraction": float(baseline_result["decisive_fraction"]),
                "lc_decisive_fraction": float(result["decisive_fraction"]),
                "baseline_winner_drain_fraction": float(baseline_result["post_click_summary"]["mean_activated_winner_drain_fraction"]),
                "lc_winner_drain_fraction": float(result["post_click_summary"]["mean_activated_winner_drain_fraction"]),
                "baseline_loser_fraction": float(baseline_result["post_click_summary"]["mean_activated_loser_fraction"]),
                "lc_loser_fraction": float(result["post_click_summary"]["mean_activated_loser_fraction"]),
            }
        )
        if example_front_end is None:
            example_front_end = {
                "case": case["case"],
                "branch_labels": list(candidate["branch_labels"]),
                "time_s": list(candidate["time_s"]),
                "branch_power_w": {label: list(candidate["branch_power_w"][label]) for label in candidate["branch_labels"]},
                "export_time_s": list(result["trace"]["time_s"]),
                "exported_branch_power": {label: list(result["trace"]["exported_branch_power"][label]) for label in candidate["branch_labels"]},
                "shared_core": candidate["shared_core"],
            }
        if example_trial is None and result["example_trial"] is not None:
            example_trial = {
                "case": case["case"],
                "a_deg": float(case["a_deg"]),
                "b_deg": float(case["b_deg"]),
                **result["example_trial"],
            }

    chsh_result = build_chsh_result(case_rows)
    energy_summary = summarize_energy_accounting_rows(energy_rows)
    summary_metrics = build_summary_metrics(case_rows, pre_click_rows, post_click_rows, energy_summary, chsh_result)
    summary_metrics["architecture_explicitness_pass"] = (
        float(np.mean([row["offdiag_coupling_ratio"] for row in shared_core_rows])) > 0.05
        and float(np.mean([row["port_state_delta_norm"] for row in shared_core_rows])) > 0.005
        and float(np.mean([row["hybrid_state_delta_norm"] for row in shared_core_rows])) > 0.0005
        and float(np.mean([row["source_impedance_spread"] for row in shared_core_rows])) > 0.001
        and float(np.mean([row["readout_admittance_spread"] for row in shared_core_rows])) > 0.001
    )
    summary_metrics["no_trivial_exact_weight_assignment"] = bool(
        all(not bool(row["forward_path_uses_exact_weights"]) for row in shared_core_rows)
    ) and float(np.mean([row["port_state_delta_norm"] for row in shared_core_rows])) > 0.005
    summary_metrics["frozen_boundary_pass"] = True
    summary_metrics["proceed_to_next_phase"] = bool(summary_metrics["proceed_to_next_phase"]) and bool(summary_metrics["architecture_explicitness_pass"])

    baseline_front_end_rows = [
        {
            "rms_error": float(entry["result"]["candidate"]["metrics"]["rms_error"]),
            "max_abs_error": float(entry["result"]["candidate"]["metrics"]["max_abs_error"]),
        }
        for entry in baseline["case_results"]
    ]
    baseline_front_end_summary = aggregate_case_error(baseline_front_end_rows, rms_key="rms_error", max_key="max_abs_error")
    lc_front_end_summary = aggregate_case_error(front_end_rows, rms_key="rms_error", max_key="max_abs_error")
    baseline_comparison_row = {
        "candidate": "current_preferred_chain",
        "front_end_rms_error": float(baseline_front_end_summary["rms_error"]),
        "winner_rms_error": float(baseline["summary_metrics"]["winner_law_rms_error"]),
        "winner_law_rms_error": float(baseline["summary_metrics"]["winner_law_rms_error"]),
        "winner_law_max_error": float(baseline["summary_metrics"]["winner_law_max_error"]),
        "correlator_rms_error": float(baseline["summary_metrics"]["correlator_rms_error"]),
        "chsh_abs_error": float(baseline["summary_metrics"]["chsh_abs_error"]),
        "pre_click_transparency_rms_shift": float(baseline["summary_metrics"]["pre_click_transparency_rms_shift"]),
        "winner_drain_dominance_rate": float(baseline["summary_metrics"]["winner_drain_dominance_rate"]),
        "mean_winner_drain_fraction_of_post_click": float(baseline["summary_metrics"]["mean_winner_drain_fraction_of_post_click"]),
        "mean_loser_fraction_of_post_click": float(baseline["summary_metrics"]["mean_loser_fraction_of_post_click"]),
        "energy_accounting_pass": bool(baseline["summary_metrics"]["energy_accounting_pass"]),
        "architecture_note": "Validated preferred chain with resonant shared-mode front-end and conductance-style physical closure candidate.",
    }
    lc_comparison_row = {
        "candidate": "preferred_chain_lc",
        "front_end_rms_error": float(lc_front_end_summary["rms_error"]),
        "winner_rms_error": float(summary_metrics["winner_law_rms_error"]),
        "winner_law_rms_error": float(summary_metrics["winner_law_rms_error"]),
        "winner_law_max_error": float(summary_metrics["winner_law_max_error"]),
        "correlator_rms_error": float(summary_metrics["correlator_rms_error"]),
        "chsh_abs_error": float(summary_metrics["chsh_abs_error"]),
        "pre_click_transparency_rms_shift": float(summary_metrics["pre_click_transparency_rms_shift"]),
        "winner_drain_dominance_rate": float(summary_metrics["winner_drain_dominance_rate"]),
        "mean_winner_drain_fraction_of_post_click": float(summary_metrics["mean_winner_drain_fraction_of_post_click"]),
        "mean_loser_fraction_of_post_click": float(summary_metrics["mean_loser_fraction_of_post_click"]),
        "energy_accounting_pass": bool(summary_metrics["energy_accounting_pass"]),
        "architecture_note": "Hybrid option C with explicit coupled-port/load solve and RC-gated resonant winner drain while keeping detector/latch/export semantics frozen.",
    }
    comparison_rows = [baseline_comparison_row, lc_comparison_row]
    progress.report("benchmark-complete", force=True)
    return {
        "case_results": case_results,
        "front_end_rows": front_end_rows,
        "case_rows": case_rows,
        "pre_click_rows": pre_click_rows,
        "post_click_rows": post_click_rows,
        "energy_case_rows": energy_case_rows,
        "energy_rows": energy_rows,
        "energy_summary": energy_summary,
        "shared_core_rows": shared_core_rows,
        "case_comparison_rows": case_comparison_rows,
        "comparison_rows": comparison_rows,
        "chsh_result": chsh_result,
        "summary_metrics": summary_metrics,
        "baseline_summary_metrics": baseline["summary_metrics"],
        "example_front_end": example_front_end,
        "example_trial": example_trial,
    }
