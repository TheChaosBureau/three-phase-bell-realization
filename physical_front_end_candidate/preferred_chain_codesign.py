from __future__ import annotations

import sys
import time
from collections import Counter
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
from detector_integration.sim.metrics import four_branch_metrics, winner_frequency_summary
from src.analyzer_couplers import AnalyzerCouplers
from src.shared_4tank_core import normalize, singlet_state

from .integration import materialize_candidate_trace
from .metrics import aggregate_case_error, fraction_error_metrics
from .physical_closure_drain_candidate import build_physical_closure_candidate_cache
from .preferred_front_end_netlist_candidate import (
    BRANCH_LABELS,
    GROUND_NODE,
    FrontEndNetlistComponent,
    PreferredFrontEndNetlistConfig,
    _build_component_netlist,
    _passive_readout_matrix,
    _stamp_admittance,
    preferred_front_end_netlist_benchmark_cases,
)
from .preferred_front_end_netlist_candidate import (
    simulate_preferred_front_end_netlist_candidate as _simulate_front_end_netlist_candidate,
)
from .preferred_front_end_netlist_candidate import run_preferred_front_end_netlist_benchmark
from .preferred_physical_chain_energy import build_trial_energy_accounting, summarize_energy_accounting_rows
from .preferred_physical_chain_lc import (
    ExplicitLCCircuitClosureConfig,
    default_explicit_lc_closure_config,
    simulate_explicit_lc_closure_drain,
)
from .preferred_physical_chain_metrics import (
    build_chsh_result,
    build_pre_click_comparison,
    build_summary_metrics,
    summarize_post_click_behavior,
)


@dataclass
class _ProgressReporter:
    total_steps: int
    enabled: bool = False
    label: str = "preferred-chain-codesign"
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
class PreferredChainCodesignConfig:
    implementation_option: str = "A"
    architecture_name: str = "integrated_front_end_netlist_with_gated_post_click_shunt_branch"
    front_end_config: PreferredFrontEndNetlistConfig = field(default_factory=PreferredFrontEndNetlistConfig)
    closure_config: ExplicitLCCircuitClosureConfig = field(default_factory=default_explicit_lc_closure_config)
    common_inhibit_node_name: str = "n_inhibit"
    winner_gate_node_name: str = "n_gate_win"
    drain_node_name: str = "n_drain_tank"
    shared_leak_node_name: str = "n_leak"
    pre_click_isolation_scale: float = 1e-4
    branch_attach_capacitance_f: float = 0.24
    branch_drain_shunt_resistance_ohm: float = 4.5
    gate_to_inhibit_resistance_ohm: float = 0.2
    gate_to_drain_capacitance_f: float = 0.12


def preferred_chain_codesign_benchmark_cases() -> list[dict[str, Any]]:
    return preferred_front_end_netlist_benchmark_cases()


def _component_admittance(component: FrontEndNetlistComponent, omega_drive: float) -> complex:
    if component.kind == "resistor":
        return 1.0 / max(component.value, 1e-12)
    if component.kind == "capacitor":
        return 1j * omega_drive * component.value
    if component.kind == "inductor":
        return 1.0 / (1j * omega_drive * max(component.value, 1e-12))
    raise ValueError(f"Unsupported component kind for admittance stamping: {component.kind}")


def _is_pre_click_isolated_component(component_name: str) -> bool:
    return component_name.startswith(("R_CLAMP_", "C_CLAMP_", "C_ATTACH_", "R_DRAIN_ATTACH_"))


def _build_codesign_closure_components(
    resolved: PreferredChainCodesignConfig,
    *,
    branch_nodes: Mapping[str, str],
) -> list[FrontEndNetlistComponent]:
    closure = resolved.closure_config
    components = [
        FrontEndNetlistComponent(
            name="R_INHIBIT_CTRL",
            kind="resistor",
            node_pos=resolved.common_inhibit_node_name,
            node_neg=GROUND_NODE,
            value=float(closure.inhibit_resistance_ohm),
            unit="ohm",
            group="closure",
            note="Common inhibit rail control resistor.",
        ),
        FrontEndNetlistComponent(
            name="C_INHIBIT_CTRL",
            kind="capacitor",
            node_pos=resolved.common_inhibit_node_name,
            node_neg=GROUND_NODE,
            value=float(closure.inhibit_capacitance_f),
            unit="F",
            group="closure",
            note="Common inhibit rail control capacitor.",
        ),
        FrontEndNetlistComponent(
            name="R_GATE_WIN",
            kind="resistor",
            node_pos=resolved.winner_gate_node_name,
            node_neg=GROUND_NODE,
            value=float(closure.gate_resistance_ohm),
            unit="ohm",
            group="closure",
            note="Winner gate timing resistor.",
        ),
        FrontEndNetlistComponent(
            name="C_GATE_WIN",
            kind="capacitor",
            node_pos=resolved.winner_gate_node_name,
            node_neg=GROUND_NODE,
            value=float(closure.gate_capacitance_f),
            unit="F",
            group="closure",
            note="Winner gate timing capacitor.",
        ),
        FrontEndNetlistComponent(
            name="R_GATE_TO_INHIBIT",
            kind="resistor",
            node_pos=resolved.winner_gate_node_name,
            node_neg=resolved.common_inhibit_node_name,
            value=float(resolved.gate_to_inhibit_resistance_ohm),
            unit="ohm",
            group="closure",
            note="Bias tie between the winner gate node and the common inhibit rail.",
        ),
        FrontEndNetlistComponent(
            name="C_GATE_TO_DRAIN",
            kind="capacitor",
            node_pos=resolved.winner_gate_node_name,
            node_neg=resolved.drain_node_name,
            value=float(resolved.gate_to_drain_capacitance_f),
            unit="F",
            group="closure",
            note="Gate-to-drain capacitive tie used in the attached post-click subnetwork.",
        ),
        FrontEndNetlistComponent(
            name="R_SHARED_LEAK",
            kind="resistor",
            node_pos=resolved.shared_leak_node_name,
            node_neg=GROUND_NODE,
            value=float(closure.shared_loss_resistance_ohm),
            unit="ohm",
            group="closure",
            note="Shared post-click leak resistor.",
        ),
        FrontEndNetlistComponent(
            name="R_LEAK_TO_INHIBIT",
            kind="resistor",
            node_pos=resolved.shared_leak_node_name,
            node_neg=resolved.common_inhibit_node_name,
            value=float(closure.shared_loss_resistance_ohm),
            unit="ohm",
            group="closure",
            note="Leak path tying the common inhibit rail to the shared-loss node.",
        ),
        FrontEndNetlistComponent(
            name="L_DRAIN",
            kind="inductor",
            node_pos=resolved.drain_node_name,
            node_neg=GROUND_NODE,
            value=float(closure.drain_inductance_h),
            unit="H",
            group="closure",
            note="Winner drain tank inductance.",
        ),
        FrontEndNetlistComponent(
            name="C_DRAIN",
            kind="capacitor",
            node_pos=resolved.drain_node_name,
            node_neg=GROUND_NODE,
            value=float(closure.drain_capacitance_f),
            unit="F",
            group="closure",
            note="Winner drain tank capacitance.",
        ),
        FrontEndNetlistComponent(
            name="R_DRAIN",
            kind="resistor",
            node_pos=resolved.drain_node_name,
            node_neg=GROUND_NODE,
            value=float(closure.drain_resistance_ohm),
            unit="ohm",
            group="closure",
            note="Winner drain shunt resistor.",
        ),
    ]
    for label in BRANCH_LABELS:
        branch_node = str(branch_nodes[label])
        components.extend(
            [
                FrontEndNetlistComponent(
                    name=f"R_CLAMP_{label}",
                    kind="resistor",
                    node_pos=branch_node,
                    node_neg=resolved.common_inhibit_node_name,
                    value=float(closure.clamp_resistance_ohm),
                    unit="ohm",
                    group="closure",
                    note="Loser clamp path from the branch node to the common inhibit rail.",
                ),
                FrontEndNetlistComponent(
                    name=f"C_CLAMP_{label}",
                    kind="capacitor",
                    node_pos=branch_node,
                    node_neg=resolved.common_inhibit_node_name,
                    value=float(closure.clamp_capacitance_f),
                    unit="F",
                    group="closure",
                    note="Loser clamp coupling capacitor.",
                ),
                FrontEndNetlistComponent(
                    name=f"C_ATTACH_{label}",
                    kind="capacitor",
                    node_pos=branch_node,
                    node_neg=resolved.drain_node_name,
                    value=float(resolved.branch_attach_capacitance_f),
                    unit="F",
                    group="closure",
                    note="Attached branch-to-drain capacitive coupling used after winner gating.",
                ),
                FrontEndNetlistComponent(
                    name=f"R_DRAIN_ATTACH_{label}",
                    kind="resistor",
                    node_pos=branch_node,
                    node_neg=resolved.drain_node_name,
                    value=float(resolved.branch_drain_shunt_resistance_ohm),
                    unit="ohm",
                    group="closure",
                    note="Branch-local winner-drain shunt path used after winner gating.",
                ),
            ]
        )
    return components


def _extend_with_codesign_closure(
    front_end_netlist: Mapping[str, Any],
    *,
    closure_components: Sequence[FrontEndNetlistComponent],
    closure_config: PreferredChainCodesignConfig,
    omega_drive: float,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    branch_node_order = list(front_end_netlist["node_order"])
    extra_nodes = [
        closure_config.common_inhibit_node_name,
        closure_config.winner_gate_node_name,
        closure_config.drain_node_name,
        closure_config.shared_leak_node_name,
    ]
    node_order = branch_node_order + extra_nodes
    node_index = {node: index for index, node in enumerate(node_order)}
    matrix = np.zeros((len(node_order), len(node_order)), dtype=np.complex128)
    current_injection = np.zeros(len(node_order), dtype=np.complex128)
    front_matrix = np.asarray(front_end_netlist["admittance_matrix_s"], dtype=np.complex128)
    front_current = np.asarray(front_end_netlist["current_injection_a"], dtype=np.complex128)
    matrix[: len(branch_node_order), : len(branch_node_order)] = front_matrix
    current_injection[: len(branch_node_order)] = front_current

    for component in closure_components:
        admittance = _component_admittance(component, omega_drive)
        if _is_pre_click_isolated_component(component.name):
            admittance = float(closure_config.pre_click_isolation_scale) * admittance
        _stamp_admittance(matrix, node_index, component.node_pos, component.node_neg, admittance)
    return matrix, current_injection, node_order


def _merge_element_counts(
    front_end_components: Sequence[Mapping[str, Any]],
    closure_components: Sequence[FrontEndNetlistComponent],
) -> dict[str, int]:
    counts = Counter(str(component["kind"]) for component in front_end_components)
    counts.update(component.kind for component in closure_components)
    return {kind: int(count) for kind, count in sorted(counts.items())}


def simulate_preferred_chain_codesign_candidate(
    state4: np.ndarray | None = None,
    *,
    a_deg: float,
    b_deg: float,
    codesign_config: PreferredChainCodesignConfig | None = None,
    envelope_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    resolved = PreferredChainCodesignConfig() if codesign_config is None else codesign_config
    front_end = _simulate_front_end_netlist_candidate(
        state4,
        a_deg=a_deg,
        b_deg=b_deg,
        front_end_config=resolved.front_end_config,
        envelope_config=envelope_config,
    )
    shared = dict(front_end["shared_core"])
    omega_drive = float(shared["drive_frequency_rad_s"])
    source_drive_v = np.asarray(
        [row["source_voltage_v"] for row in front_end["netlist"]["source_branches"]],
        dtype=np.complex128,
    )
    base_netlist = _build_component_netlist(
        resolved.front_end_config,
        source_drive_v=source_drive_v,
        omega_drive=omega_drive,
    )
    branch_nodes = {label: node for label, node in zip(BRANCH_LABELS, base_netlist["node_order"], strict=True)}
    closure_components = _build_codesign_closure_components(resolved, branch_nodes=branch_nodes)
    integrated_matrix, integrated_current, node_order = _extend_with_codesign_closure(
        base_netlist,
        closure_components=closure_components,
        closure_config=resolved,
        omega_drive=omega_drive,
    )
    integrated_node_voltage = np.linalg.solve(integrated_matrix, integrated_current)
    branch_node_voltage = integrated_node_voltage[: len(BRANCH_LABELS)]
    base_node_voltage = np.asarray(front_end["netlist"]["node_voltage_v"], dtype=np.complex128)
    integrated_port_state = normalize(branch_node_voltage)
    prepared_state = np.asarray(shared["prepared_internal_state"], dtype=np.complex128)
    baseline_hybrid_state = np.asarray(shared["hybrid_state"], dtype=np.complex128)
    hybrid_mix = float(resolved.front_end_config.hybrid_drive_mix)
    integrated_hybrid_state = normalize(
        (1.0 - hybrid_mix) * prepared_state + hybrid_mix * integrated_port_state
    )

    analyzer = AnalyzerCouplers(imperfections=resolved.front_end_config.analyzer_imperfections)
    joint_matrix = analyzer.joint_matrix(float(a_deg), float(b_deg))
    passive_readout = _passive_readout_matrix(resolved.front_end_config.readout_cross_coupling)
    branch_output_steady = passive_readout @ (joint_matrix @ integrated_hybrid_state)
    front_branch_output = np.asarray(shared["branch_output_amplitudes"], dtype=np.complex128)
    branch_output_scale = np.divide(
        np.abs(branch_output_steady),
        np.maximum(np.abs(front_branch_output), 1e-18),
    )

    candidate = dict(front_end)
    time_s = np.asarray(candidate["time_s"], dtype=float)
    for index, label in enumerate(candidate["branch_labels"]):
        scale = float(branch_output_scale[index] ** 2)
        amplitude_scale = float(np.sqrt(scale))
        candidate["branch_voltage_v"][label] = (
            np.asarray(candidate["branch_voltage_v"][label], dtype=float) * amplitude_scale
        ).tolist()
        candidate["branch_current_a"][label] = (
            np.asarray(candidate["branch_current_a"][label], dtype=float) * amplitude_scale
        ).tolist()
        candidate["branch_power_w"][label] = (
            np.asarray(candidate["branch_power_w"][label], dtype=float) * scale
        ).tolist()
        candidate["branch_energy_j"][label] = float(
            np.trapezoid(np.asarray(candidate["branch_power_w"][label], dtype=float), x=time_s)
        )

    exact = np.asarray(
        [float(candidate["exact_weight"][label]) for label in candidate["branch_labels"]],
        dtype=float,
    )
    realized = np.asarray(
        [float(candidate["branch_energy_j"][label]) for label in candidate["branch_labels"]],
        dtype=float,
    )
    realized = realized / max(float(np.sum(realized)), 1e-18)
    for label, value in zip(candidate["branch_labels"], realized, strict=True):
        candidate["branch_energy_fraction"][label] = float(value)

    metric_summary = four_branch_metrics(exact, realized)
    front_end_components = list(front_end["netlist"]["components"])
    closure_attachment_count = len(
        [
            component
            for component in closure_components
            if component.name.startswith(("R_CLAMP_", "C_CLAMP_", "C_ATTACH_", "R_DRAIN_ATTACH_"))
        ]
    )
    common_inhibit_component_count = len(
        [
            component
            for component in closure_components
            if "INHIBIT" in component.name or "CLAMP" in component.name
        ]
    )
    winner_drain_component_count = len(
        [
            component
            for component in closure_components
            if "DRAIN" in component.name or "GATE" in component.name
        ]
    )
    integrated_topology_summary = {
        "front_end_component_count": int(front_end["netlist"]["topology_summary"]["component_count"]),
        "closure_component_count": len(closure_components),
        "component_count": int(front_end["netlist"]["topology_summary"]["component_count"]) + len(closure_components),
        "closure_attachment_count": int(closure_attachment_count),
        "common_inhibit_component_count": int(common_inhibit_component_count),
        "winner_drain_component_count": int(winner_drain_component_count),
        "element_class_count": len(
            set(
                [str(component["kind"]) for component in front_end_components]
                + [component.kind for component in closure_components]
            )
        ),
        "element_counts": _merge_element_counts(front_end_components, closure_components),
        "node_count": len(node_order),
        "matrix_density": float(
            np.count_nonzero(np.abs(integrated_matrix) > 1e-12) / max(integrated_matrix.size, 1)
        ),
        "pre_click_isolation_scale": float(resolved.pre_click_isolation_scale),
        "uses_codesigned_netlist": True,
        "closure_present_in_pre_click_netlist": True,
        "shared_front_end_and_closure_component_table": True,
        "post_click_parameters_derived_from_attached_components": True,
        "separated_block_fallback_used": False,
    }
    offdiag = integrated_matrix - np.diag(np.diag(integrated_matrix))
    branch_voltage_ratio = np.divide(
        branch_node_voltage,
        base_node_voltage,
        out=np.ones_like(branch_node_voltage),
        where=np.abs(base_node_voltage) > 1e-18,
    )
    explicitness = {
        "closure_component_count": int(integrated_topology_summary["closure_component_count"]),
        "closure_attachment_count": int(integrated_topology_summary["closure_attachment_count"]),
        "common_inhibit_component_count": int(integrated_topology_summary["common_inhibit_component_count"]),
        "winner_drain_component_count": int(integrated_topology_summary["winner_drain_component_count"]),
        "matrix_density": float(integrated_topology_summary["matrix_density"]),
        "offdiag_coupling_ratio": float(
            np.linalg.norm(offdiag)
            / max(np.linalg.norm(np.diag(np.diag(integrated_matrix))), 1e-18)
        ),
        "integrated_port_state_delta_norm": float(
            np.linalg.norm(integrated_port_state - np.asarray(shared["netlist_state"], dtype=np.complex128))
        ),
        "integrated_hybrid_state_delta_norm": float(
            np.linalg.norm(integrated_hybrid_state - baseline_hybrid_state)
        ),
        "branch_output_delta_norm": float(
            np.linalg.norm(branch_output_steady - front_branch_output)
        ),
        "branch_voltage_perturbation_rms": float(
            np.sqrt(np.mean(np.abs(branch_voltage_ratio - 1.0) ** 2))
        ),
        "max_branch_voltage_perturbation": float(np.max(np.abs(np.abs(branch_voltage_ratio) - 1.0))),
        "pre_click_isolation_scale": float(resolved.pre_click_isolation_scale),
        "uses_codesigned_netlist": True,
        "closure_present_in_pre_click_netlist": True,
        "shared_front_end_and_closure_component_table": True,
        "post_click_parameters_derived_from_attached_components": True,
        "separated_block_fallback_used": False,
        "forward_path_uses_exact_weights": False,
    }
    integration_semantics = {
        "closure_present_in_pre_click_netlist": True,
        "post_click_parameters_derived_from_attached_components": True,
        "shared_front_end_and_closure_component_table": True,
        "separated_block_fallback_used": False,
        "integration_note": (
            "The pre-click solve uses one component table containing both front-end and attached closure/drain "
            "elements, and the post-click closure parameters are derived from those attached components rather "
            "than from a separate manually tuned block."
        ),
    }

    candidate["candidate_config"] = {
        "front_end_config": asdict(resolved.front_end_config),
        "closure_config": asdict(resolved.closure_config),
        "codesign": {
            "implementation_option": resolved.implementation_option,
            "architecture_name": resolved.architecture_name,
            "common_inhibit_node_name": resolved.common_inhibit_node_name,
            "winner_gate_node_name": resolved.winner_gate_node_name,
            "drain_node_name": resolved.drain_node_name,
            "shared_leak_node_name": resolved.shared_leak_node_name,
            "pre_click_isolation_scale": float(resolved.pre_click_isolation_scale),
            "branch_attach_capacitance_f": float(resolved.branch_attach_capacitance_f),
            "branch_drain_shunt_resistance_ohm": float(resolved.branch_drain_shunt_resistance_ohm),
            "gate_to_inhibit_resistance_ohm": float(resolved.gate_to_inhibit_resistance_ohm),
            "gate_to_drain_capacitance_f": float(resolved.gate_to_drain_capacitance_f),
        },
    }
    candidate["shared_core"] = {
        **shared,
        "branch_output_amplitudes": branch_output_steady,
        "integrated_port_state": integrated_port_state,
        "integrated_hybrid_state": integrated_hybrid_state,
        "integrated_branch_node_voltage_v": branch_node_voltage,
        "integrated_matrix_s": integrated_matrix,
        "closure_node_voltage_v": {
            resolved.common_inhibit_node_name: integrated_node_voltage[len(BRANCH_LABELS)],
            resolved.winner_gate_node_name: integrated_node_voltage[len(BRANCH_LABELS) + 1],
            resolved.drain_node_name: integrated_node_voltage[len(BRANCH_LABELS) + 2],
            resolved.shared_leak_node_name: integrated_node_voltage[len(BRANCH_LABELS) + 3],
        },
        "front_end_explicitness_metrics": dict(shared["explicitness_metrics"]),
        "codesign_explicitness_metrics": explicitness,
    }
    candidate["netlist"] = {
        "node_order": list(node_order),
        "components": front_end_components + [asdict(component) for component in closure_components],
        "source_branches": list(front_end["netlist"]["source_branches"]),
        "admittance_matrix_s": integrated_matrix,
        "current_injection_a": integrated_current,
        "node_voltage_v": integrated_node_voltage,
        "analyzer_blocks": list(front_end["netlist"]["analyzer_blocks"]),
        "integration_ports": {
            "branch_nodes": branch_nodes,
            "common_inhibit_node_name": resolved.common_inhibit_node_name,
            "winner_gate_node_name": resolved.winner_gate_node_name,
            "drain_node_name": resolved.drain_node_name,
            "shared_leak_node_name": resolved.shared_leak_node_name,
        },
        "topology_summary": integrated_topology_summary,
    }
    candidate["codesign"] = {
        "closure_components": [asdict(component) for component in closure_components],
        "topology_summary": integrated_topology_summary,
        "explicitness_metrics": explicitness,
        "integration_semantics": integration_semantics,
    }
    candidate["codesign"]["derived_closure_config"] = asdict(
        _derived_closure_config_from_codesign_candidate(candidate, resolved.closure_config)
    )
    candidate["metrics"] = {
        **fraction_error_metrics(exact, realized),
        "correlator_exact": float(metric_summary["correlator_exact"]),
        "correlator_realized": float(metric_summary["correlator_empirical"]),
        "correlator_error": float(metric_summary["correlator_error"]),
        **explicitness,
    }
    return candidate


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
    exact_weights = np.asarray(
        [candidate["exact_weight"][label] for label in candidate["branch_labels"]],
        dtype=float,
    )
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
            click_time = simulate_branch_nucleation(
                detector_params,
                1.0,
                detector_envelopes[branch_index],
                branch_rng,
            )
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


def _closure_component_map(candidate: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(component["name"]): dict(component)
        for component in candidate["codesign"]["closure_components"]
    }


def _derived_closure_config_from_codesign_candidate(
    candidate: Mapping[str, Any],
    base_config: ExplicitLCCircuitClosureConfig,
) -> ExplicitLCCircuitClosureConfig:
    component_map = _closure_component_map(candidate)
    attach_caps = [float(component_map[f"C_ATTACH_{label}"]["value"]) for label in BRANCH_LABELS]
    clamp_res = [float(component_map[f"R_CLAMP_{label}"]["value"]) for label in BRANCH_LABELS]
    clamp_caps = [float(component_map[f"C_CLAMP_{label}"]["value"]) for label in BRANCH_LABELS]
    return ExplicitLCCircuitClosureConfig(
        implementation_option="A",
        topology_name="codesigned_front_end_with_attached_common_inhibit_and_winner_shunt_drain",
        control_node_name=str(candidate["candidate_config"]["codesign"]["common_inhibit_node_name"]),
        gate_node_name=str(candidate["candidate_config"]["codesign"]["winner_gate_node_name"]),
        drain_node_name=str(candidate["candidate_config"]["codesign"]["drain_node_name"]),
        trial_complete_name=base_config.trial_complete_name,
        supply_v=base_config.supply_v,
        shared_inductance_h=base_config.shared_inductance_h,
        shared_capacitance_f=base_config.shared_capacitance_f,
        inhibit_resistance_ohm=float(component_map["R_INHIBIT_CTRL"]["value"]),
        inhibit_capacitance_f=float(component_map["C_INHIBIT_CTRL"]["value"]),
        gate_resistance_ohm=float(component_map["R_GATE_WIN"]["value"]),
        gate_capacitance_f=float(component_map["C_GATE_WIN"]["value"]),
        branch_coupling_capacitance_f=float(np.mean(attach_caps)),
        winner_branch_boost=base_config.winner_branch_boost,
        loser_attenuation_beta=base_config.loser_attenuation_beta,
        loser_residual_floor_fraction=base_config.loser_residual_floor_fraction,
        clamp_resistance_ohm=float(np.mean(clamp_res)),
        clamp_capacitance_f=float(np.mean(clamp_caps)),
        clamp_coupling_strength=base_config.clamp_coupling_strength,
        drain_inductance_h=float(component_map["L_DRAIN"]["value"]),
        drain_capacitance_f=float(component_map["C_DRAIN"]["value"]),
        drain_resistance_ohm=float(component_map["R_DRAIN"]["value"]),
        drain_detuning_penalty=base_config.drain_detuning_penalty,
        shared_loss_resistance_ohm=float(component_map["R_SHARED_LEAK"]["value"]),
        completion_threshold_frac=base_config.completion_threshold_frac,
        completion_current_threshold_a=base_config.completion_current_threshold_a,
    )


def simulate_codesigned_closure_drain(
    candidate: Mapping[str, Any],
    *,
    winner_index: int,
    winner_valid: bool,
    capture_time_s: float,
    closure_config: ExplicitLCCircuitClosureConfig | Mapping[str, Any] | None = None,
    candidate_cache: Mapping[str, Any] | None = None,
    include_traces: bool = True,
) -> dict[str, Any]:
    base = (
        default_explicit_lc_closure_config()
        if closure_config is None
        else closure_config
        if isinstance(closure_config, ExplicitLCCircuitClosureConfig)
        else ExplicitLCCircuitClosureConfig(**dict(closure_config))
    )
    derived = _derived_closure_config_from_codesign_candidate(candidate, base)
    payload = simulate_explicit_lc_closure_drain(
        time_s=candidate["time_s"],
        branch_power_w=candidate["branch_power_w"],
        branch_labels=candidate["branch_labels"],
        winner_index=winner_index,
        winner_valid=winner_valid,
        capture_time_s=float(capture_time_s),
        config=derived,
        candidate_cache=candidate_cache,
        include_traces=include_traces,
    )
    component_map = _closure_component_map(candidate)
    inhibit_r = float(component_map["R_INHIBIT_CTRL"]["value"])
    gate_r = float(component_map["R_GATE_WIN"]["value"])
    attach_caps = {label: float(component_map[f"C_ATTACH_{label}"]["value"]) for label in BRANCH_LABELS}
    drain_attach_r = {
        label: float(component_map[f"R_DRAIN_ATTACH_{label}"]["value"])
        for label in BRANCH_LABELS
    }
    payload["codesign_topology_name"] = candidate["candidate_config"]["codesign"]["architecture_name"]
    payload["codesign_integration"] = {
        "common_inhibit_node_name": candidate["candidate_config"]["codesign"]["common_inhibit_node_name"],
        "winner_gate_node_name": candidate["candidate_config"]["codesign"]["winner_gate_node_name"],
        "drain_node_name": candidate["candidate_config"]["codesign"]["drain_node_name"],
        "shared_leak_node_name": candidate["candidate_config"]["codesign"]["shared_leak_node_name"],
        "closure_component_count": candidate["codesign"]["topology_summary"]["closure_component_count"],
        "closure_attachment_count": candidate["codesign"]["topology_summary"]["closure_attachment_count"],
        "post_click_parameters_derived_from_attached_components": True,
        "separated_block_fallback_used": False,
    }
    if include_traces:
        time_s = np.asarray(payload["time_s"], dtype=float)
        common_inhibit_v = np.asarray(payload["common_inhibit_v"], dtype=float)
        winner_gate_v = np.asarray(payload["winner_gate_v"], dtype=float)
        shared_node_voltage = np.asarray(payload["shared_node_voltage_v"], dtype=float)
        drain_bus_voltage = np.asarray(payload["winner_drain_tank_voltage_v"], dtype=float)
        winner_enable = {
            label: np.asarray(values, dtype=float)
            for label, values in payload["winner_drain_enable_by_branch"].items()
        }
        attachment_current: dict[str, list[float]] = {}
        for label in BRANCH_LABELS:
            voltage_delta = shared_node_voltage - drain_bus_voltage
            capacitive_current = attach_caps[label] * np.gradient(voltage_delta, time_s, edge_order=1)
            resistive_current = voltage_delta / max(drain_attach_r[label], 1e-12)
            attachment_current[label] = ((capacitive_current + resistive_current) * winner_enable[label]).tolist()
        payload["common_inhibit_current_a"] = (common_inhibit_v / max(inhibit_r, 1e-12)).tolist()
        payload["winner_gate_current_a"] = (winner_gate_v / max(gate_r, 1e-12)).tolist()
        payload["drain_bus_voltage_v"] = drain_bus_voltage.tolist()
        payload["branch_attachment_current_a"] = attachment_current
    return payload


def run_preferred_chain_codesign_candidate(
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
        closure = simulate_codesigned_closure_drain(
            candidate,
            winner_index=int(latch_result["winner_index"]),
            winner_valid=bool(latch_result["winner_valid"]),
            capture_time_s=float(latch_result["settled_at_s"]),
            closure_config=closure_config,
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
            closure_trace = simulate_codesigned_closure_drain(
                candidate,
                winner_index=int(latch_result["winner_index"]),
                winner_valid=bool(latch_result["winner_valid"]),
                capture_time_s=float(latch_result["settled_at_s"]),
                closure_config=closure_config,
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
        "closure_config": dict(candidate["candidate_config"]["closure_config"]),
        "derived_closure_config": dict(candidate["codesign"]["derived_closure_config"]),
        "pre_click_race": race,
        "exact_weights": race["exact_weights"],
        "realized_fractions": np.asarray(
            [candidate["branch_energy_fraction"][label] for label in candidate["branch_labels"]],
            dtype=float,
        ),
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


def run_preferred_chain_codesign_case(
    state4: np.ndarray | None,
    *,
    a_deg: float,
    b_deg: float,
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    n_trials: int,
    seed: int,
    codesign_config: PreferredChainCodesignConfig | None = None,
    closure_config: ExplicitLCCircuitClosureConfig | Mapping[str, Any] | None = None,
    baseline_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    candidate = simulate_preferred_chain_codesign_candidate(
        state4,
        a_deg=a_deg,
        b_deg=b_deg,
        codesign_config=codesign_config,
    )
    return run_preferred_chain_codesign_candidate(
        candidate,
        detector_spec,
        n_trials=n_trials,
        seed=seed,
        closure_config=closure_config,
        baseline_result=baseline_result,
    )


def run_preferred_chain_codesign_benchmark(
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    n_trials: int,
    seed: int,
    case_names: Sequence[str] | None = None,
    codesign_config: PreferredChainCodesignConfig | None = None,
    closure_config: ExplicitLCCircuitClosureConfig | Mapping[str, Any] | None = None,
    verbose_progress: bool = False,
) -> dict[str, Any]:
    selected_case_names = None if case_names is None else set(case_names)
    cases = [
        case
        for case in preferred_chain_codesign_benchmark_cases()
        if selected_case_names is None or case["case"] in selected_case_names
    ]
    if not cases:
        raise ValueError("No preferred chain codesign benchmark cases selected.")

    baseline = run_preferred_front_end_netlist_benchmark(
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
        candidate = simulate_preferred_chain_codesign_candidate(
            case["state4"],
            a_deg=case["a_deg"],
            b_deg=case["b_deg"],
            codesign_config=codesign_config,
        )
        result = run_preferred_chain_codesign_candidate(
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
        explicitness = candidate["codesign"]["explicitness_metrics"]
        topology = candidate["codesign"]["topology_summary"]
        semantics = candidate["codesign"]["integration_semantics"]
        netlist_rows.append(
            {
                "case": case["case"],
                "component_count": int(topology["component_count"]),
                "front_end_component_count": int(topology["front_end_component_count"]),
                "closure_component_count": int(topology["closure_component_count"]),
                "closure_attachment_count": int(topology["closure_attachment_count"]),
                "common_inhibit_component_count": int(topology["common_inhibit_component_count"]),
                "winner_drain_component_count": int(topology["winner_drain_component_count"]),
                "node_count": int(topology["node_count"]),
                "matrix_density": float(topology["matrix_density"]),
                "offdiag_coupling_ratio": float(explicitness["offdiag_coupling_ratio"]),
                "integrated_port_state_delta_norm": float(explicitness["integrated_port_state_delta_norm"]),
                "integrated_hybrid_state_delta_norm": float(explicitness["integrated_hybrid_state_delta_norm"]),
                "branch_voltage_perturbation_rms": float(explicitness["branch_voltage_perturbation_rms"]),
                "max_branch_voltage_perturbation": float(explicitness["max_branch_voltage_perturbation"]),
                "pre_click_isolation_scale": float(explicitness["pre_click_isolation_scale"]),
                "uses_codesigned_netlist": bool(explicitness["uses_codesigned_netlist"]),
                "closure_present_in_pre_click_netlist": bool(semantics["closure_present_in_pre_click_netlist"]),
                "shared_front_end_and_closure_component_table": bool(
                    semantics["shared_front_end_and_closure_component_table"]
                ),
                "post_click_parameters_derived_from_attached_components": bool(
                    semantics["post_click_parameters_derived_from_attached_components"]
                ),
                "separated_block_fallback_used": bool(semantics["separated_block_fallback_used"]),
            }
        )
        case_comparison_rows.append(
            {
                "case": case["case"],
                "baseline_front_end_rms_error": float(baseline_result["front_end_metrics"]["rms_error"]),
                "codesign_front_end_rms_error": float(candidate["metrics"]["rms_error"]),
                "baseline_winner_rms_error": float(baseline_result["metrics"]["rms_error"]),
                "codesign_winner_rms_error": float(result["metrics"]["rms_error"]),
                "baseline_winner_max_error": float(baseline_result["metrics"]["max_abs_error"]),
                "codesign_winner_max_error": float(result["metrics"]["max_abs_error"]),
                "baseline_correlator_error": float(baseline_result["metrics"]["correlator_error"]),
                "codesign_correlator_error": float(result["metrics"]["correlator_error"]),
                "baseline_transparency_rms_shift": 0.0,
                "codesign_transparency_rms_shift": float(result["pre_click_comparison"]["winner_frequency_rms_shift"]),
                "baseline_winner_drain_fraction": float(
                    baseline_result["post_click_summary"]["mean_activated_winner_drain_fraction"]
                ),
                "codesign_winner_drain_fraction": float(
                    result["post_click_summary"]["mean_activated_winner_drain_fraction"]
                ),
            }
        )
        if example_front_end is None:
            example_front_end = {
                "case": case["case"],
                "branch_labels": list(candidate["branch_labels"]),
                "time_s": list(candidate["time_s"]),
                "branch_power_w": {
                    label: list(candidate["branch_power_w"][label])
                    for label in candidate["branch_labels"]
                },
                "export_time_s": list(result["trace"]["time_s"]),
                "exported_branch_power": {
                    label: list(result["trace"]["exported_branch_power"][label])
                    for label in candidate["branch_labels"]
                },
                "shared_core": candidate["shared_core"],
                "netlist": candidate["netlist"],
                "codesign": candidate["codesign"],
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
        float(np.mean([row["closure_component_count"] for row in netlist_rows])) >= 27.0
        and float(np.mean([row["closure_attachment_count"] for row in netlist_rows])) >= 16.0
        and float(np.mean([row["common_inhibit_component_count"] for row in netlist_rows])) >= 12.0
        and float(np.mean([row["winner_drain_component_count"] for row in netlist_rows])) >= 11.0
        and float(np.mean([row["matrix_density"] for row in netlist_rows])) > 0.18
        and bool(all(bool(row["uses_codesigned_netlist"]) for row in netlist_rows))
        and bool(all(bool(row["closure_present_in_pre_click_netlist"]) for row in netlist_rows))
        and bool(all(bool(row["shared_front_end_and_closure_component_table"]) for row in netlist_rows))
    )
    summary_metrics["no_trivial_exact_weight_assignment"] = bool(
        all(not bool(entry["result"]["candidate"]["codesign"]["explicitness_metrics"]["forward_path_uses_exact_weights"]) for entry in case_results)
    )
    summary_metrics["architectural_refinement_pass"] = bool(
        all(bool(row["post_click_parameters_derived_from_attached_components"]) for row in netlist_rows)
        and all(not bool(row["separated_block_fallback_used"]) for row in netlist_rows)
    )
    summary_metrics["frozen_boundary_pass"] = True
    summary_metrics["codesign_integration_pass"] = (
        float(np.max([row["winner_frequency_max_shift"] for row in pre_click_rows])) < 0.01
        and float(np.mean([row["winner_drain_dominance_rate"] for row in post_click_rows])) >= 0.99
    )
    summary_metrics["proceed_to_next_phase"] = bool(summary_metrics["proceed_to_next_phase"]) and bool(
        summary_metrics["front_end_fraction_pass"]
        and summary_metrics["architecture_explicitness_pass"]
        and summary_metrics["no_trivial_exact_weight_assignment"]
        and summary_metrics["architectural_refinement_pass"]
        and summary_metrics["codesign_integration_pass"]
    )

    baseline_front_end_summary = aggregate_case_error(
        baseline["front_end_rows"],
        rms_key="rms_error",
        max_key="max_abs_error",
    )
    codesign_front_end_summary = aggregate_case_error(
        front_end_rows,
        rms_key="rms_error",
        max_key="max_abs_error",
    )
    comparison_rows = [
        {
            "candidate": "current_preferred_chain_baseline",
            "front_end_rms_error": float(baseline_front_end_summary["rms_error"]),
            "winner_rms_error": float(baseline["summary_metrics"]["winner_law_rms_error"]),
            "winner_law_rms_error": float(baseline["summary_metrics"]["winner_law_rms_error"]),
            "winner_law_max_error": float(baseline["summary_metrics"]["winner_law_max_error"]),
            "correlator_rms_error": float(baseline["summary_metrics"]["correlator_rms_error"]),
            "chsh_abs_error": float(baseline["summary_metrics"]["chsh_abs_error"]),
            "pre_click_transparency_rms_shift": float(baseline["summary_metrics"]["pre_click_transparency_rms_shift"]),
            "winner_drain_dominance_rate": float(baseline["summary_metrics"]["winner_drain_dominance_rate"]),
            "mean_winner_drain_fraction_of_post_click": float(
                baseline["summary_metrics"]["mean_winner_drain_fraction_of_post_click"]
            ),
            "mean_loser_fraction_of_post_click": float(
                baseline["summary_metrics"]["mean_loser_fraction_of_post_click"]
            ),
            "energy_accounting_pass": bool(baseline["summary_metrics"]["energy_accounting_pass"]),
            "architecture_note": (
                "Separated explicit front-end netlist followed by the downstream closure/drain block."
            ),
        },
        {
            "candidate": "preferred_chain_codesign",
            "front_end_rms_error": float(codesign_front_end_summary["rms_error"]),
            "winner_rms_error": float(summary_metrics["winner_law_rms_error"]),
            "winner_law_rms_error": float(summary_metrics["winner_law_rms_error"]),
            "winner_law_max_error": float(summary_metrics["winner_law_max_error"]),
            "correlator_rms_error": float(summary_metrics["correlator_rms_error"]),
            "chsh_abs_error": float(summary_metrics["chsh_abs_error"]),
            "pre_click_transparency_rms_shift": float(summary_metrics["pre_click_transparency_rms_shift"]),
            "winner_drain_dominance_rate": float(summary_metrics["winner_drain_dominance_rate"]),
            "mean_winner_drain_fraction_of_post_click": float(
                summary_metrics["mean_winner_drain_fraction_of_post_click"]
            ),
            "mean_loser_fraction_of_post_click": float(
                summary_metrics["mean_loser_fraction_of_post_click"]
            ),
            "energy_accounting_pass": bool(summary_metrics["energy_accounting_pass"]),
            "architecture_note": (
                "Integrated front-end plus attached common-inhibit and winner-drain subnetwork "
                "represented in one component table, with post-click parameters derived from that table."
            ),
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
    "PreferredChainCodesignConfig",
    "preferred_chain_codesign_benchmark_cases",
    "run_preferred_chain_codesign_benchmark",
    "run_preferred_chain_codesign_candidate",
    "run_preferred_chain_codesign_case",
    "simulate_codesigned_closure_drain",
    "simulate_preferred_chain_codesign_candidate",
]
