from __future__ import annotations

import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

from detector_integration.frontends.four_branch import four_branch_weights
from detector_integration.sim.metrics import four_branch_metrics
from src.analyzer_couplers import AnalyzerCouplers, AnalyzerImperfections
from src.shared_4tank_core import BASIS_LABELS, CoreImperfections, Shared4TankCore, normalize, singlet_state

from .export_interface import amplitude_envelope, build_time_axis, export_contract, resolve_envelope_config
from .metrics import aggregate_case_error, fraction_error_metrics
from .preferred_physical_chain_energy import summarize_energy_accounting_rows
from .preferred_physical_chain_lc import (
    ExplicitLCCircuitClosureConfig,
    preferred_physical_chain_lc_benchmark_cases,
    run_preferred_physical_chain_lc_benchmark,
    run_preferred_physical_chain_lc_candidate,
)
from .preferred_physical_chain_metrics import build_chsh_result, build_summary_metrics

BRANCH_LABELS = list(BASIS_LABELS)
GROUND_NODE = "gnd"


@dataclass
class _ProgressReporter:
    total_steps: int
    enabled: bool = False
    label: str = "preferred-front-end-netlist"
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
class FrontEndNetlistComponent:
    name: str
    kind: str
    node_pos: str
    node_neg: str
    value: float
    unit: str
    group: str
    note: str = ""


@dataclass(frozen=True)
class PreferredFrontEndNetlistConfig:
    implementation_option: str = "C"
    architecture_name: str = "hybrid_preparation_with_explicit_component_netlist"
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
    internal_loss_resistance_ohm: tuple[float, float, float, float] = (16.67, 16.54, 16.79, 16.62)
    bridge_resistance_ohm: float = 10.0
    bridge_capacitance_f: float = 0.42
    side_coupling_capacitance_f: float = 0.035
    return_coupling_capacitance_f: float = 0.014
    hybrid_drive_mix: float = 0.12
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


def _branch_node(label: str) -> str:
    return f"n_{label.replace('+', 'p').replace('-', 'm')}"


def preferred_front_end_netlist_benchmark_cases() -> list[dict[str, Any]]:
    return preferred_physical_chain_lc_benchmark_cases()


def _stamp_admittance(matrix: np.ndarray, node_index: Mapping[str, int], node_pos: str, node_neg: str, admittance: complex) -> None:
    if node_pos != GROUND_NODE:
        i = node_index[node_pos]
        matrix[i, i] += admittance
    if node_neg != GROUND_NODE:
        j = node_index[node_neg]
        matrix[j, j] += admittance
    if node_pos != GROUND_NODE and node_neg != GROUND_NODE:
        i = node_index[node_pos]
        j = node_index[node_neg]
        matrix[i, j] -= admittance
        matrix[j, i] -= admittance


def _component_admittance(component: FrontEndNetlistComponent, omega_drive: float) -> complex:
    if component.kind == "resistor":
        return 1.0 / max(component.value, 1e-12)
    if component.kind == "capacitor":
        return 1j * omega_drive * component.value
    if component.kind == "inductor":
        return 1.0 / (1j * omega_drive * max(component.value, 1e-12))
    raise ValueError(f"Unsupported component kind for admittance stamping: {component.kind}")


def _build_component_netlist(
    resolved: PreferredFrontEndNetlistConfig,
    *,
    source_drive_v: np.ndarray,
    omega_drive: float,
) -> dict[str, Any]:
    branch_nodes = {label: _branch_node(label) for label in BRANCH_LABELS}
    node_order = [branch_nodes[label] for label in BRANCH_LABELS]
    node_index = {node: index for index, node in enumerate(node_order)}

    source_resistance = np.asarray(resolved.source_resistance_ohm, dtype=float)
    source_inductance = np.asarray(resolved.source_inductance_h, dtype=float)
    load_resistance = np.asarray(resolved.load_resistance_ohm, dtype=float)
    readout_caps = np.asarray(resolved.readout_shunt_capacitance_f, dtype=float)
    resonance_offsets = np.asarray(resolved.core_imperfections.resonance_offsets(), dtype=float)
    damping_offsets = np.asarray(resolved.core_imperfections.damping_offsets(), dtype=float)
    tank_inductances = resolved.tank_inductance_h * (1.0 + 0.8 * resonance_offsets)
    tank_capacitances = resolved.tank_capacitance_f * (1.0 - 0.8 * resonance_offsets)
    internal_loss_resistance = np.asarray(resolved.internal_loss_resistance_ohm, dtype=float) / np.maximum(1.0 + 0.5 * damping_offsets, 1e-9)

    components: list[FrontEndNetlistComponent] = []
    source_branches: list[dict[str, Any]] = []
    matrix = np.zeros((len(node_order), len(node_order)), dtype=np.complex128)
    current_injection = np.zeros(len(node_order), dtype=np.complex128)

    for index, label in enumerate(BRANCH_LABELS):
        node = branch_nodes[label]
        components.extend(
            [
                FrontEndNetlistComponent(
                    name=f"R_SRC_{label}",
                    kind="resistor",
                    node_pos=node,
                    node_neg=f"drv_{label}",
                    value=float(source_resistance[index]),
                    unit="ohm",
                    group="drive",
                    note="Series source resistor reduced to Norton equivalent at the solved drive frequency.",
                ),
                FrontEndNetlistComponent(
                    name=f"L_SRC_{label}",
                    kind="inductor",
                    node_pos=f"drv_{label}",
                    node_neg=GROUND_NODE,
                    value=float(source_inductance[index]),
                    unit="H",
                    group="drive",
                    note="Series source inductor reduced to Norton equivalent at the solved drive frequency.",
                ),
                FrontEndNetlistComponent(
                    name=f"L_TANK_{label}",
                    kind="inductor",
                    node_pos=node,
                    node_neg=GROUND_NODE,
                    value=float(tank_inductances[index]),
                    unit="H",
                    group="shared_core",
                    note="Shared resonant storage inductance for the branch-mode node.",
                ),
                FrontEndNetlistComponent(
                    name=f"C_TANK_{label}",
                    kind="capacitor",
                    node_pos=node,
                    node_neg=GROUND_NODE,
                    value=float(tank_capacitances[index]),
                    unit="F",
                    group="shared_core",
                    note="Shared resonant storage capacitance for the branch-mode node.",
                ),
                FrontEndNetlistComponent(
                    name=f"R_LOSS_{label}",
                    kind="resistor",
                    node_pos=node,
                    node_neg=GROUND_NODE,
                    value=float(internal_loss_resistance[index]),
                    unit="ohm",
                    group="shared_core",
                    note="Internal tank loss / damping resistance.",
                ),
                FrontEndNetlistComponent(
                    name=f"R_LOAD_{label}",
                    kind="resistor",
                    node_pos=node,
                    node_neg=GROUND_NODE,
                    value=float(load_resistance[index]),
                    unit="ohm",
                    group="readout",
                    note="Detector-facing load resistance.",
                ),
                FrontEndNetlistComponent(
                    name=f"C_READ_{label}",
                    kind="capacitor",
                    node_pos=node,
                    node_neg=GROUND_NODE,
                    value=float(readout_caps[index]),
                    unit="F",
                    group="readout",
                    note="Readout shunt capacitance at the detector-facing port.",
                ),
            ]
        )
        source_impedance = float(source_resistance[index]) + 1j * omega_drive * float(source_inductance[index])
        current_injection[node_index[node]] += source_drive_v[index] / source_impedance
        source_branches.append(
            {
                "label": label,
                "node": node,
                "source_voltage_v": source_drive_v[index],
                "source_impedance_ohm": source_impedance,
                "norton_current_a": source_drive_v[index] / source_impedance,
            }
        )

    coupling_components = [
        FrontEndNetlistComponent(
            name="R_BRIDGE_PM_MP",
            kind="resistor",
            node_pos=branch_nodes["+-"],
            node_neg=branch_nodes["-+"],
            value=float(resolved.bridge_resistance_ohm),
            unit="ohm",
            group="coupling",
            note="Bridge resistor between the antisymmetric middle branches.",
        ),
        FrontEndNetlistComponent(
            name="C_BRIDGE_PM_MP",
            kind="capacitor",
            node_pos=branch_nodes["+-"],
            node_neg=branch_nodes["-+"],
            value=float(resolved.bridge_capacitance_f * resolved.core_imperfections.coupling_scale),
            unit="F",
            group="coupling",
            note="Bridge capacitor between the antisymmetric middle branches.",
        ),
        FrontEndNetlistComponent(
            name="C_SIDE_PP_PM",
            kind="capacitor",
            node_pos=branch_nodes["++"],
            node_neg=branch_nodes["+-"],
            value=float(resolved.side_coupling_capacitance_f),
            unit="F",
            group="coupling",
            note="Shared-core side coupling capacitor.",
        ),
        FrontEndNetlistComponent(
            name="C_SIDE_PP_MP",
            kind="capacitor",
            node_pos=branch_nodes["++"],
            node_neg=branch_nodes["-+"],
            value=float(resolved.side_coupling_capacitance_f),
            unit="F",
            group="coupling",
            note="Shared-core side coupling capacitor.",
        ),
        FrontEndNetlistComponent(
            name="C_SIDE_MM_PM",
            kind="capacitor",
            node_pos=branch_nodes["--"],
            node_neg=branch_nodes["+-"],
            value=float(resolved.side_coupling_capacitance_f),
            unit="F",
            group="coupling",
            note="Shared-core side coupling capacitor.",
        ),
        FrontEndNetlistComponent(
            name="C_SIDE_MM_MP",
            kind="capacitor",
            node_pos=branch_nodes["--"],
            node_neg=branch_nodes["-+"],
            value=float(resolved.side_coupling_capacitance_f),
            unit="F",
            group="coupling",
            note="Shared-core side coupling capacitor.",
        ),
        FrontEndNetlistComponent(
            name="C_RETURN_PP_MM",
            kind="capacitor",
            node_pos=branch_nodes["++"],
            node_neg=branch_nodes["--"],
            value=float(resolved.return_coupling_capacitance_f),
            unit="F",
            group="coupling",
            note="Return-path capacitor tying the outer branches together.",
        ),
    ]
    components.extend(coupling_components)

    for component in components:
        if component.group == "drive":
            continue
        _stamp_admittance(
            matrix,
            node_index,
            component.node_pos,
            component.node_neg,
            _component_admittance(component, omega_drive),
        )

    for branch in source_branches:
        node = str(branch["node"])
        _stamp_admittance(
            matrix,
            node_index,
            node,
            GROUND_NODE,
            1.0 / branch["source_impedance_ohm"],
        )

    element_counts = Counter(component.kind for component in components)
    coupling_element_count = sum(component.group == "coupling" for component in components)
    matrix_density = float(np.count_nonzero(np.abs(matrix) > 1e-12) / max(matrix.size, 1))
    return {
        "node_order": node_order,
        "node_index": node_index,
        "components": [asdict(component) for component in components],
        "source_branches": source_branches,
        "admittance_matrix_s": matrix,
        "current_injection_a": current_injection,
        "topology_summary": {
            "component_count": len(components),
            "element_class_count": len(element_counts),
            "element_counts": dict(element_counts),
            "coupling_component_count": int(coupling_element_count),
            "node_count": len(node_order),
            "matrix_density": matrix_density,
            "uses_component_netlist": True,
        },
    }


def simulate_preferred_front_end_netlist_candidate(
    state4: np.ndarray | None = None,
    *,
    a_deg: float,
    b_deg: float,
    front_end_config: PreferredFrontEndNetlistConfig | None = None,
    envelope_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    resolved = PreferredFrontEndNetlistConfig() if front_end_config is None else front_end_config
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
    source_drive_v = resolved.source_voltage_scale_v * preparation.drive_vector

    netlist = _build_component_netlist(resolved, source_drive_v=source_drive_v, omega_drive=omega_drive)
    node_voltage = np.linalg.solve(netlist["admittance_matrix_s"], netlist["current_injection_a"])
    explicit_netlist_state = normalize(node_voltage)
    hybrid_state = normalize(
        (1.0 - float(resolved.hybrid_drive_mix)) * preparation.normalized_state
        + float(resolved.hybrid_drive_mix) * explicit_netlist_state
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

    source_branch_map = {entry["label"]: entry for entry in netlist["source_branches"]}
    for index, label in enumerate(BRANCH_LABELS):
        gain = float(resolved.branch_gain_trim[index])
        phase = np.exp(1j * np.deg2rad(float(resolved.branch_phase_deg[index])))
        source_impedance = source_branch_map[label]["source_impedance_ohm"]
        load_resistance = float(resolved.load_resistance_ohm[index])
        open_circuit = gain * phase * branch_output_steady[index] * drive_envelope * float(resolved.source_voltage_scale_v)
        divider = load_resistance / (source_impedance + load_resistance)
        load_voltage = np.abs(open_circuit * divider)
        load_current = load_voltage / max(load_resistance, 1e-9)
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
    topology_summary = dict(netlist["topology_summary"])
    offdiag = netlist["admittance_matrix_s"] - np.diag(np.diag(netlist["admittance_matrix_s"]))
    trivial = np.sqrt(np.maximum(exact, 0.0))
    trivial /= max(float(np.linalg.norm(trivial)), 1e-18)
    branch_output_magnitude = np.abs(branch_output_steady)
    branch_output_magnitude /= max(float(np.linalg.norm(branch_output_magnitude)), 1e-18)
    explicitness = {
        "component_count": int(topology_summary["component_count"]),
        "element_class_count": int(topology_summary["element_class_count"]),
        "coupling_component_count": int(topology_summary["coupling_component_count"]),
        "matrix_density": float(topology_summary["matrix_density"]),
        "offdiag_coupling_ratio": float(np.linalg.norm(offdiag) / max(np.linalg.norm(np.diag(np.diag(netlist["admittance_matrix_s"]))), 1e-18)),
        "direct_exact_weight_overlap": float(np.abs(np.vdot(trivial.astype(np.complex128), branch_output_magnitude.astype(np.complex128)))),
        "netlist_state_delta_norm": float(np.linalg.norm(explicit_netlist_state - preparation.normalized_state)),
        "hybrid_state_delta_norm": float(np.linalg.norm(hybrid_state - preparation.normalized_state)),
        "uses_component_netlist": bool(topology_summary["uses_component_netlist"]),
        "forward_path_uses_exact_weights": False,
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
        "netlist_state": explicit_netlist_state,
        "hybrid_state": hybrid_state,
        "analyzer_matrix": joint_matrix,
        "passive_readout_matrix": passive_readout,
        "branch_output_amplitudes": branch_output_steady,
        "singlet_mode_index": singlet_mode_index,
        "singlet_mode_overlap": float(singlet_overlaps[singlet_mode_index]),
        "mode_overlap_profile": singlet_overlaps.astype(float),
        "explicitness_metrics": explicitness,
        "intended_circuit": {
            "tanks": [asdict(tank) for tank in shared_core.intended_circuit().tanks],
            "couplers": [asdict(coupler) for coupler in shared_core.intended_circuit().couplers],
            "readout_note": "Component-level netlist candidate built from explicit R/L/C branches plus explicit coupling elements and driven through Norton-equivalent source branches.",
        },
    }
    export["netlist"] = {
        "node_order": list(netlist["node_order"]),
        "components": list(netlist["components"]),
        "source_branches": list(netlist["source_branches"]),
        "admittance_matrix_s": netlist["admittance_matrix_s"],
        "current_injection_a": netlist["current_injection_a"],
        "node_voltage_v": node_voltage,
        "analyzer_blocks": [
            {
                "name": "alice_analyzer",
                "kind": "rotation_coupler",
                "matrix": analyzer.alice_matrix(float(a_deg)),
                "angle_deg": float(a_deg),
            },
            {
                "name": "bob_analyzer",
                "kind": "rotation_coupler",
                "matrix": analyzer.bob_matrix(float(b_deg)),
                "angle_deg": float(b_deg),
            },
            {
                "name": "readout_coupler",
                "kind": "passive_multiport",
                "matrix": passive_readout,
                "cross_coupling": float(resolved.readout_cross_coupling),
            },
        ],
        "topology_summary": topology_summary,
    }
    export["metrics"] = {
        **fraction_error_metrics(exact, realized),
        "correlator_exact": float(metric_summary["correlator_exact"]),
        "correlator_realized": float(metric_summary["correlator_empirical"]),
        "correlator_error": float(metric_summary["correlator_error"]),
        **explicitness,
    }
    return export


def run_preferred_front_end_netlist_case(
    state4: np.ndarray | None,
    *,
    a_deg: float,
    b_deg: float,
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    n_trials: int,
    seed: int,
    front_end_config: PreferredFrontEndNetlistConfig | None = None,
    closure_config: ExplicitLCCircuitClosureConfig | Mapping[str, Any] | None = None,
    baseline_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    candidate = simulate_preferred_front_end_netlist_candidate(
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


def run_preferred_front_end_netlist_benchmark(
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    n_trials: int,
    seed: int,
    case_names: Sequence[str] | None = None,
    front_end_config: PreferredFrontEndNetlistConfig | None = None,
    closure_config: ExplicitLCCircuitClosureConfig | Mapping[str, Any] | None = None,
    verbose_progress: bool = False,
) -> dict[str, Any]:
    selected_case_names = None if case_names is None else set(case_names)
    cases = [
        case
        for case in preferred_front_end_netlist_benchmark_cases()
        if selected_case_names is None or case["case"] in selected_case_names
    ]
    if not cases:
        raise ValueError("No preferred front-end netlist benchmark cases selected.")

    baseline = run_preferred_physical_chain_lc_benchmark(
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
    netlist_rows: list[dict[str, Any]] = []
    case_comparison_rows: list[dict[str, Any]] = []
    example_front_end: dict[str, Any] | None = None
    example_trial: dict[str, Any] | None = None

    for case_index, case in enumerate(cases):
        progress.report("starting-case", case_name=str(case["case"]), force=True)
        baseline_result = baseline_case_map[str(case["case"])]
        candidate = simulate_preferred_front_end_netlist_candidate(
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
        topology = candidate["netlist"]["topology_summary"]
        netlist_rows.append(
            {
                "case": case["case"],
                "component_count": int(explicitness["component_count"]),
                "element_class_count": int(explicitness["element_class_count"]),
                "coupling_component_count": int(explicitness["coupling_component_count"]),
                "matrix_density": float(explicitness["matrix_density"]),
                "offdiag_coupling_ratio": float(explicitness["offdiag_coupling_ratio"]),
                "netlist_state_delta_norm": float(explicitness["netlist_state_delta_norm"]),
                "hybrid_state_delta_norm": float(explicitness["hybrid_state_delta_norm"]),
                "uses_component_netlist": bool(explicitness["uses_component_netlist"]),
                "node_count": int(topology["node_count"]),
            }
        )
        case_comparison_rows.append(
            {
                "case": case["case"],
                "baseline_front_end_rms_error": float(baseline_result["front_end_metrics"]["rms_error"]),
                "netlist_front_end_rms_error": float(candidate["metrics"]["rms_error"]),
                "baseline_winner_rms_error": float(baseline_result["metrics"]["rms_error"]),
                "netlist_winner_rms_error": float(result["metrics"]["rms_error"]),
                "baseline_winner_max_error": float(baseline_result["metrics"]["max_abs_error"]),
                "netlist_winner_max_error": float(result["metrics"]["max_abs_error"]),
                "baseline_correlator_error": float(baseline_result["metrics"]["correlator_error"]),
                "netlist_correlator_error": float(result["metrics"]["correlator_error"]),
                "baseline_decisive_fraction": float(baseline_result["decisive_fraction"]),
                "netlist_decisive_fraction": float(result["decisive_fraction"]),
                "baseline_winner_drain_fraction": float(baseline_result["post_click_summary"]["mean_activated_winner_drain_fraction"]),
                "netlist_winner_drain_fraction": float(result["post_click_summary"]["mean_activated_winner_drain_fraction"]),
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
                "netlist": candidate["netlist"],
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
    front_end_fraction = aggregate_case_error(front_end_rows, rms_key="rms_error", max_key="max_abs_error")
    summary_metrics["front_end_fraction_rms_error"] = float(front_end_fraction["rms_error"])
    summary_metrics["front_end_fraction_max_error"] = float(front_end_fraction["max_abs_error"])
    summary_metrics["front_end_fraction_pass"] = (
        float(summary_metrics["front_end_fraction_rms_error"]) < 0.03
        and float(summary_metrics["front_end_fraction_max_error"]) < 0.05
    )
    summary_metrics["architecture_explicitness_pass"] = (
        float(np.mean([row["component_count"] for row in netlist_rows])) >= 28.0
        and float(np.mean([row["coupling_component_count"] for row in netlist_rows])) >= 7.0
        and float(np.mean([row["element_class_count"] for row in netlist_rows])) >= 3.0
        and float(np.mean([row["matrix_density"] for row in netlist_rows])) > 0.25
        and bool(all(bool(row["uses_component_netlist"]) for row in netlist_rows))
    )
    summary_metrics["no_trivial_exact_weight_assignment"] = bool(
        all(not bool(row["result"]["candidate"]["metrics"]["forward_path_uses_exact_weights"]) for row in case_results)
    )
    summary_metrics["frozen_boundary_pass"] = True
    summary_metrics["proceed_to_next_phase"] = bool(summary_metrics["proceed_to_next_phase"]) and bool(
        summary_metrics["front_end_fraction_pass"]
        and summary_metrics["architecture_explicitness_pass"]
        and summary_metrics["no_trivial_exact_weight_assignment"]
    )

    baseline_front_end_summary = aggregate_case_error(baseline["front_end_rows"], rms_key="rms_error", max_key="max_abs_error")
    netlist_front_end_summary = aggregate_case_error(front_end_rows, rms_key="rms_error", max_key="max_abs_error")
    comparison_rows = [
        {
            "candidate": "current_preferred_chain_lc",
            "front_end_rms_error": float(baseline_front_end_summary["rms_error"]),
            "winner_rms_error": float(baseline["summary_metrics"]["winner_law_rms_error"]),
            "winner_law_rms_error": float(baseline["summary_metrics"]["winner_law_rms_error"]),
            "winner_law_max_error": float(baseline["summary_metrics"]["winner_law_max_error"]),
            "correlator_rms_error": float(baseline["summary_metrics"]["correlator_rms_error"]),
            "chsh_abs_error": float(baseline["summary_metrics"]["chsh_abs_error"]),
            "energy_accounting_pass": bool(baseline["summary_metrics"]["energy_accounting_pass"]),
            "winner_drain_dominance_rate": float(baseline["summary_metrics"]["winner_drain_dominance_rate"]),
            "architecture_note": "Hybrid modal preparation plus explicit coupled-port solve with reduced internal netlist structure.",
        },
        {
            "candidate": "preferred_front_end_netlist",
            "front_end_rms_error": float(netlist_front_end_summary["rms_error"]),
            "winner_rms_error": float(summary_metrics["winner_law_rms_error"]),
            "winner_law_rms_error": float(summary_metrics["winner_law_rms_error"]),
            "winner_law_max_error": float(summary_metrics["winner_law_max_error"]),
            "correlator_rms_error": float(summary_metrics["correlator_rms_error"]),
            "chsh_abs_error": float(summary_metrics["chsh_abs_error"]),
            "energy_accounting_pass": bool(summary_metrics["energy_accounting_pass"]),
            "winner_drain_dominance_rate": float(summary_metrics["winner_drain_dominance_rate"]),
            "architecture_note": "Explicit component table with R/L/C source branches, tank storage elements, load ports, and inter-branch couplers solved as a component-level netlist before the frozen downstream chain.",
        },
    ]
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
        "netlist_rows": netlist_rows,
        "case_comparison_rows": case_comparison_rows,
        "comparison_rows": comparison_rows,
        "chsh_result": chsh_result,
        "summary_metrics": summary_metrics,
        "baseline_summary_metrics": baseline["summary_metrics"],
        "example_front_end": example_front_end,
        "example_trial": example_trial,
    }


__all__ = [
    "FrontEndNetlistComponent",
    "PreferredFrontEndNetlistConfig",
    "preferred_front_end_netlist_benchmark_cases",
    "run_preferred_front_end_netlist_benchmark",
    "run_preferred_front_end_netlist_case",
    "simulate_preferred_front_end_netlist_candidate",
]
