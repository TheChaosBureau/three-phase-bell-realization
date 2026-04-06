from __future__ import annotations

import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

from .closure_path import future_branch_energy_from_cache
from .metrics import aggregate_case_error
from .physical_closure_drain_candidate import build_physical_closure_candidate_cache
from .preferred_chain_codesign import (
    BRANCH_LABELS,
    GROUND_NODE,
    FrontEndNetlistComponent,
    PreferredChainCodesignConfig,
    _component_admittance,
    _merge_element_counts,
    _run_pre_click_race,
)
from .preferred_chain_codesign import (
    preferred_chain_codesign_benchmark_cases,
    run_preferred_chain_codesign_benchmark,
    simulate_preferred_chain_codesign_candidate,
)
from .preferred_physical_chain_energy import build_trial_energy_accounting, summarize_energy_accounting_rows
from .preferred_physical_chain_lc import ExplicitLCCircuitClosureConfig
from .preferred_physical_chain_metrics import (
    build_chsh_result,
    build_pre_click_comparison,
    build_summary_metrics,
    summarize_post_click_behavior,
)


def _sigmoid(values: np.ndarray, *, threshold: float, slope: float) -> np.ndarray:
    safe_slope = max(float(slope), 1e-9)
    scaled = np.clip((np.asarray(values, dtype=float) - float(threshold)) / safe_slope, -60.0, 60.0)
    return 1.0 / (1.0 + np.exp(-scaled))


@dataclass
class _ProgressReporter:
    total_steps: int
    enabled: bool = False
    label: str = "preferred-chain-device-physicalization"
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
class PreferredChainDevicePhysicalizationConfig:
    implementation_option: str = "AB"
    architecture_name: str = "device_physicalized_inhibit_and_winner_drain_on_integrated_codesign_chain"
    selected_subblocks: tuple[str, ...] = ("common_inhibit_rail", "winner_drain_path")
    codesign_config: PreferredChainCodesignConfig = field(default_factory=PreferredChainCodesignConfig)
    trigger_sense_node_name: str = "n_trigger_sense"
    inhibit_store_node_name: str = "n_inhibit_store"
    gate_driver_node_name: str = "n_gate_driver"
    switch_node_name: str = "n_switch_channel"
    dump_node_name: str = "n_drain_dump"
    sense_resistance_ohm: float = 0.18
    sense_capacitance_f: float = 0.44
    sense_bleed_resistance_ohm: float = 5.8
    inhibit_charge_resistance_ohm: float = 0.14
    inhibit_store_capacitance_f: float = 1.45
    inhibit_bleed_resistance_ohm: float = 13.5
    inhibit_hysteresis_resistance_ohm: float = 0.56
    gate_driver_resistance_ohm: float = 0.075
    gate_driver_capacitance_f: float = 0.58
    gate_bleed_resistance_ohm: float = 6.8
    switch_off_resistance_ohm: float = 120.0
    switch_on_resistance_ohm: float = 0.38
    switch_threshold_v: float = 0.72
    switch_slope_v: float = 0.08
    comparator_threshold_v: float = 0.55
    comparator_slope_v: float = 0.06
    clamp_threshold_v: float = 0.34
    clamp_slope_v: float = 0.075
    drain_series_inductance_h: float = 0.34
    drain_dump_capacitance_f: float = 0.66
    drain_dump_resistance_ohm: float = 0.88
    drain_snubber_capacitance_f: float = 0.082


def preferred_chain_device_physicalization_benchmark_cases() -> list[dict[str, Any]]:
    return preferred_chain_codesign_benchmark_cases()


def _build_device_physicalization_components(
    resolved: PreferredChainDevicePhysicalizationConfig,
    *,
    integration_ports: Mapping[str, Any],
) -> list[FrontEndNetlistComponent]:
    inhibit_node = str(integration_ports["common_inhibit_node_name"])
    drain_node = str(integration_ports["drain_node_name"])
    components = [
        FrontEndNetlistComponent(
            name="R_SENSE_LINK",
            kind="resistor",
            node_pos=inhibit_node,
            node_neg=resolved.trigger_sense_node_name,
            value=float(resolved.sense_resistance_ohm),
            unit="ohm",
            group="device_common_inhibit",
            note="Comparator-triggered sense link for the common inhibit rail.",
        ),
        FrontEndNetlistComponent(
            name="C_SENSE_HOLD",
            kind="capacitor",
            node_pos=resolved.trigger_sense_node_name,
            node_neg=GROUND_NODE,
            value=float(resolved.sense_capacitance_f),
            unit="F",
            group="device_common_inhibit",
            note="Sense-hold capacitor for the trigger/comparator surrogate.",
        ),
        FrontEndNetlistComponent(
            name="R_SENSE_BLEED",
            kind="resistor",
            node_pos=resolved.trigger_sense_node_name,
            node_neg=GROUND_NODE,
            value=float(resolved.sense_bleed_resistance_ohm),
            unit="ohm",
            group="device_common_inhibit",
            note="Bleed path for the trigger/comparator sense node.",
        ),
        FrontEndNetlistComponent(
            name="R_INHIBIT_CHARGE",
            kind="resistor",
            node_pos=resolved.trigger_sense_node_name,
            node_neg=resolved.inhibit_store_node_name,
            value=float(resolved.inhibit_charge_resistance_ohm),
            unit="ohm",
            group="device_common_inhibit",
            note="Charge path into the explicit inhibit storage node.",
        ),
        FrontEndNetlistComponent(
            name="C_INHIBIT_STORE",
            kind="capacitor",
            node_pos=resolved.inhibit_store_node_name,
            node_neg=GROUND_NODE,
            value=float(resolved.inhibit_store_capacitance_f),
            unit="F",
            group="device_common_inhibit",
            note="Storage capacitor representing the inhibit rail hold-up charge.",
        ),
        FrontEndNetlistComponent(
            name="R_INHIBIT_BLEED",
            kind="resistor",
            node_pos=resolved.inhibit_store_node_name,
            node_neg=GROUND_NODE,
            value=float(resolved.inhibit_bleed_resistance_ohm),
            unit="ohm",
            group="device_common_inhibit",
            note="Bleed resistor for the inhibit storage node.",
        ),
        FrontEndNetlistComponent(
            name="R_INHIBIT_HYST",
            kind="resistor",
            node_pos=resolved.inhibit_store_node_name,
            node_neg=inhibit_node,
            value=float(resolved.inhibit_hysteresis_resistance_ohm),
            unit="ohm",
            group="device_common_inhibit",
            note="Hysteretic tie between inhibit store and the common inhibit rail.",
        ),
        FrontEndNetlistComponent(
            name="R_GATE_DRV",
            kind="resistor",
            node_pos=resolved.inhibit_store_node_name,
            node_neg=resolved.gate_driver_node_name,
            value=float(resolved.gate_driver_resistance_ohm),
            unit="ohm",
            group="device_winner_drain",
            note="Gate-driver resistor for the winner drain switch surrogate.",
        ),
        FrontEndNetlistComponent(
            name="C_GATE_DRV",
            kind="capacitor",
            node_pos=resolved.gate_driver_node_name,
            node_neg=GROUND_NODE,
            value=float(resolved.gate_driver_capacitance_f),
            unit="F",
            group="device_winner_drain",
            note="Gate-driver hold capacitor.",
        ),
        FrontEndNetlistComponent(
            name="R_GATE_BLEED",
            kind="resistor",
            node_pos=resolved.gate_driver_node_name,
            node_neg=GROUND_NODE,
            value=float(resolved.gate_bleed_resistance_ohm),
            unit="ohm",
            group="device_winner_drain",
            note="Gate-driver bleed resistor.",
        ),
        FrontEndNetlistComponent(
            name="R_WIN_SWITCH_OFF",
            kind="resistor",
            node_pos=resolved.switch_node_name,
            node_neg=drain_node,
            value=float(resolved.switch_off_resistance_ohm),
            unit="ohm",
            group="device_winner_drain",
            note="Off-state channel resistance for the winner drain switch surrogate.",
        ),
        FrontEndNetlistComponent(
            name="C_WIN_SWITCH_SNUB",
            kind="capacitor",
            node_pos=resolved.switch_node_name,
            node_neg=drain_node,
            value=float(resolved.drain_snubber_capacitance_f),
            unit="F",
            group="device_winner_drain",
            note="Snubber capacitor across the winner drain switch surrogate.",
        ),
        FrontEndNetlistComponent(
            name="L_DRAIN_SER",
            kind="inductor",
            node_pos=resolved.switch_node_name,
            node_neg=resolved.dump_node_name,
            value=float(resolved.drain_series_inductance_h),
            unit="H",
            group="device_winner_drain",
            note="Series inductance in the physicalized drain dump branch.",
        ),
        FrontEndNetlistComponent(
            name="C_DRAIN_DUMP",
            kind="capacitor",
            node_pos=resolved.dump_node_name,
            node_neg=GROUND_NODE,
            value=float(resolved.drain_dump_capacitance_f),
            unit="F",
            group="device_winner_drain",
            note="Drain dump storage capacitor.",
        ),
        FrontEndNetlistComponent(
            name="R_DRAIN_DUMP",
            kind="resistor",
            node_pos=resolved.dump_node_name,
            node_neg=GROUND_NODE,
            value=float(resolved.drain_dump_resistance_ohm),
            unit="ohm",
            group="device_winner_drain",
            note="Drain dump dissipation resistor.",
        ),
    ]
    return components


def _extend_codesign_netlist_with_devices(
    candidate: Mapping[str, Any],
    *,
    device_components: Sequence[FrontEndNetlistComponent],
    resolved: PreferredChainDevicePhysicalizationConfig,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    base_node_order = list(candidate["netlist"]["node_order"])
    extra_nodes = [
        resolved.trigger_sense_node_name,
        resolved.inhibit_store_node_name,
        resolved.gate_driver_node_name,
        resolved.switch_node_name,
        resolved.dump_node_name,
    ]
    node_order = base_node_order + extra_nodes
    node_index = {node: index for index, node in enumerate(node_order)}
    base_matrix = np.asarray(candidate["netlist"]["admittance_matrix_s"], dtype=np.complex128)
    base_current = np.asarray(candidate["netlist"]["current_injection_a"], dtype=np.complex128)
    matrix = np.zeros((len(node_order), len(node_order)), dtype=np.complex128)
    current = np.zeros(len(node_order), dtype=np.complex128)
    matrix[: len(base_node_order), : len(base_node_order)] = base_matrix
    current[: len(base_node_order)] = base_current
    omega_drive = float(candidate["shared_core"]["drive_frequency_rad_s"])
    for component in device_components:
        _stamp_admittance = None
        from .preferred_front_end_netlist_candidate import _stamp_admittance as stamp

        _stamp_admittance = stamp
        _stamp_admittance(
            matrix,
            node_index,
            component.node_pos,
            component.node_neg,
            _component_admittance(component, omega_drive),
        )
    return matrix, current, node_order


def _device_component_map(candidate: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(component["name"]): dict(component)
        for component in candidate["device_physicalization"]["device_components"]
    }


def simulate_preferred_chain_device_physicalization_candidate(
    state4: np.ndarray | None = None,
    *,
    a_deg: float,
    b_deg: float,
    physicalization_config: PreferredChainDevicePhysicalizationConfig | None = None,
) -> dict[str, Any]:
    resolved = (
        PreferredChainDevicePhysicalizationConfig()
        if physicalization_config is None
        else physicalization_config
    )
    baseline = simulate_preferred_chain_codesign_candidate(
        state4,
        a_deg=a_deg,
        b_deg=b_deg,
        codesign_config=resolved.codesign_config,
    )
    integration_ports = dict(baseline["netlist"]["integration_ports"])
    device_components = _build_device_physicalization_components(
        resolved,
        integration_ports=integration_ports,
    )
    device_matrix, device_current, node_order = _extend_codesign_netlist_with_devices(
        baseline,
        device_components=device_components,
        resolved=resolved,
    )
    node_voltage = np.linalg.solve(device_matrix, device_current)
    branch_count = len(BRANCH_LABELS)
    branch_node_voltage = node_voltage[:branch_count]
    baseline_branch_voltage = np.asarray(
        baseline["shared_core"]["integrated_branch_node_voltage_v"],
        dtype=np.complex128,
    )
    branch_voltage_ratio = np.divide(
        branch_node_voltage,
        baseline_branch_voltage,
        out=np.ones_like(branch_node_voltage),
        where=np.abs(baseline_branch_voltage) > 1e-18,
    )
    device_nodes = {
        resolved.trigger_sense_node_name: node_voltage[len(baseline["netlist"]["node_order"])],
        resolved.inhibit_store_node_name: node_voltage[len(baseline["netlist"]["node_order"]) + 1],
        resolved.gate_driver_node_name: node_voltage[len(baseline["netlist"]["node_order"]) + 2],
        resolved.switch_node_name: node_voltage[len(baseline["netlist"]["node_order"]) + 3],
        resolved.dump_node_name: node_voltage[len(baseline["netlist"]["node_order"]) + 4],
    }
    device_component_count = len(device_components)
    common_inhibit_device_component_count = sum(
        component.group == "device_common_inhibit" for component in device_components
    )
    winner_drain_device_component_count = sum(
        component.group == "device_winner_drain" for component in device_components
    )
    topology_summary = {
        **dict(baseline["netlist"]["topology_summary"]),
        "component_count": int(baseline["netlist"]["topology_summary"]["component_count"]) + device_component_count,
        "device_component_count": int(device_component_count),
        "device_node_count": 5,
        "selected_subblock_count": len(resolved.selected_subblocks),
        "common_inhibit_device_component_count": int(common_inhibit_device_component_count),
        "winner_drain_device_component_count": int(winner_drain_device_component_count),
        "element_class_count": len(
            set(
                [str(component["kind"]) for component in baseline["netlist"]["components"]]
                + [component.kind for component in device_components]
            )
        ),
        "element_counts": _merge_element_counts(baseline["netlist"]["components"], device_components),
        "node_count": len(node_order),
        "matrix_density": float(
            np.count_nonzero(np.abs(device_matrix) > 1e-12) / max(device_matrix.size, 1)
        ),
        "uses_device_level_common_inhibit": True,
        "uses_device_level_winner_drain": True,
        "legacy_subblock_fallback_used": False,
    }
    offdiag = device_matrix - np.diag(np.diag(device_matrix))
    explicitness = {
        "device_component_count": int(device_component_count),
        "device_node_count": 5,
        "selected_subblock_count": len(resolved.selected_subblocks),
        "common_inhibit_device_component_count": int(common_inhibit_device_component_count),
        "winner_drain_device_component_count": int(winner_drain_device_component_count),
        "matrix_density": float(topology_summary["matrix_density"]),
        "offdiag_coupling_ratio": float(
            np.linalg.norm(offdiag)
            / max(np.linalg.norm(np.diag(np.diag(device_matrix))), 1e-18)
        ),
        "branch_voltage_perturbation_rms": float(
            np.sqrt(np.mean(np.abs(branch_voltage_ratio - 1.0) ** 2))
        ),
        "max_branch_voltage_perturbation": float(
            np.max(np.abs(np.abs(branch_voltage_ratio) - 1.0))
        ),
        "uses_device_level_common_inhibit": True,
        "uses_device_level_winner_drain": True,
        "legacy_subblock_fallback_used": False,
    }
    semantics = {
        "selected_subblocks": list(resolved.selected_subblocks),
        "old_common_inhibit_abstraction": "single RC-style control rise attached to the inhibit rail",
        "new_common_inhibit_realization": "trigger sense RC, explicit inhibit storage node, bleed path, and hysteretic tie into the common inhibit rail",
        "old_winner_drain_abstraction": "single winner-gated drain branch with reduced turn-on behavior",
        "new_winner_drain_realization": "gate-driver RC, off-state switch surrogate, snubber, series inductor, and drain dump RC branch",
        "uses_device_level_common_inhibit": True,
        "uses_device_level_winner_drain": True,
        "legacy_subblock_fallback_used": False,
        "realism_gain_note": (
            "The common inhibit and winner drain subblocks now expose internal trigger, storage, gate, "
            "switch, and dump elements rather than only a reduced post-click envelope."
        ),
    }

    candidate = dict(baseline)
    candidate["candidate_config"] = {
        **dict(baseline["candidate_config"]),
        "device_physicalization": {
            **asdict(resolved),
            "codesign_config": asdict(resolved.codesign_config),
        },
    }
    candidate["shared_core"] = {
        **dict(baseline["shared_core"]),
        "device_admittance_matrix_s": device_matrix,
        "device_node_voltage_v": device_nodes,
        "device_explicitness_metrics": explicitness,
    }
    candidate["netlist"] = {
        **dict(baseline["netlist"]),
        "node_order": list(node_order),
        "components": list(baseline["netlist"]["components"]) + [asdict(component) for component in device_components],
        "admittance_matrix_s": device_matrix,
        "current_injection_a": device_current,
        "node_voltage_v": node_voltage,
        "device_ports": {
            "trigger_sense_node_name": resolved.trigger_sense_node_name,
            "inhibit_store_node_name": resolved.inhibit_store_node_name,
            "gate_driver_node_name": resolved.gate_driver_node_name,
            "switch_node_name": resolved.switch_node_name,
            "dump_node_name": resolved.dump_node_name,
        },
        "topology_summary": topology_summary,
    }
    candidate["device_physicalization"] = {
        "device_components": [asdict(component) for component in device_components],
        "topology_summary": topology_summary,
        "explicitness_metrics": explicitness,
        "realism_semantics": semantics,
    }
    candidate["metrics"] = {
        **dict(baseline["metrics"]),
        **explicitness,
    }
    return candidate


def _inactive_physicalized_payload(
    *,
    time_s: np.ndarray,
    branch_labels: list[str],
    winner_index: int,
    winner_label: str | None,
    shared_omega: float,
    drain_omega: float,
) -> dict[str, Any]:
    zero_trace = np.zeros_like(time_s)
    zero_branch_map = {label: zero_trace.tolist() for label in branch_labels}
    return {
        "topology_name": "device_physicalized_common_inhibit_and_winner_drain",
        "control_node_name": "device_common_inhibit",
        "gate_node_name": "device_gate_driver",
        "drain_node_name": "device_drain_dump",
        "winner_branch_post_click_energy_j": 0.0,
        "winner_drain_total_energy_j": 0.0,
        "shared_leak_total_energy_j": 0.0,
        "loser_post_click_energy_j": {label: 0.0 for label in branch_labels if label != winner_label},
        "initial_remaining_energy_j": 0.0,
        "terminal_remaining_energy_j": 0.0,
        "winner_index": int(winner_index),
        "winner_label": winner_label,
        "winner_drain_path_count": 0 if winner_label is None else 1,
        "closure_active": False if winner_label is None else True,
        "activation_count": 0 if winner_label is None else 1,
        "trial_complete": False if winner_label is None else True,
        "trial_complete_time_s": float("inf") if winner_label is None else float(time_s[0]),
        "trial_complete_reason": "inactive" if winner_label is None else "shared_energy_below_threshold",
        "monotonic_remaining_energy": True,
        "terminal_loser_suppression_mean": 0.0 if winner_label is None else 1.0,
        "shared_resonant_frequency_rad_s": float(shared_omega),
        "drain_resonant_frequency_rad_s": float(drain_omega),
        "time_s": time_s.tolist(),
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
        "loser_branch_power_w": {label: zero_trace.tolist() for label in branch_labels if label != winner_label},
        "loser_suppression": {label: zero_trace.tolist() for label in branch_labels if label != winner_label},
        "loser_clamp_conductance_s": {label: zero_trace.tolist() for label in branch_labels if label != winner_label},
        "loser_clamp_current_a": {label: zero_trace.tolist() for label in branch_labels if label != winner_label},
        "trigger_sense_v": zero_trace.tolist(),
        "trigger_comparator_output": zero_trace.tolist(),
        "inhibit_store_v": zero_trace.tolist(),
        "winner_gate_driver_v": zero_trace.tolist(),
        "winner_switch_conductance_s": zero_trace.tolist(),
        "winner_switch_channel_current_a": zero_trace.tolist(),
        "drain_dump_voltage_v": zero_trace.tolist(),
        "common_inhibit_current_a": zero_trace.tolist(),
        "winner_gate_current_a": zero_trace.tolist(),
        "branch_attachment_current_a": dict(zero_branch_map),
    }


def simulate_device_physicalized_closure_drain(
    candidate: Mapping[str, Any],
    *,
    winner_index: int,
    winner_valid: bool,
    capture_time_s: float,
    physicalization_config: PreferredChainDevicePhysicalizationConfig | Mapping[str, Any] | None = None,
    candidate_cache: Mapping[str, Any] | None = None,
    include_traces: bool = True,
) -> dict[str, Any]:
    resolved = (
        PreferredChainDevicePhysicalizationConfig()
        if physicalization_config is None
        else physicalization_config
        if isinstance(physicalization_config, PreferredChainDevicePhysicalizationConfig)
        else PreferredChainDevicePhysicalizationConfig(**dict(physicalization_config))
    )
    values_t = np.asarray(candidate["time_s"], dtype=float).reshape(-1)
    labels = list(candidate["branch_labels"])
    zero_trace = np.zeros_like(values_t)
    base_closure = ExplicitLCCircuitClosureConfig(
        **dict(candidate["codesign"]["derived_closure_config"])
    )
    shared_omega = float(
        1.0
        / np.sqrt(
            max(
                float(base_closure.shared_inductance_h) * float(base_closure.shared_capacitance_f),
                1e-18,
            )
        )
    )
    drain_omega = float(
        1.0
        / np.sqrt(
            max(
                float(resolved.drain_series_inductance_h) * float(resolved.drain_dump_capacitance_f),
                1e-18,
            )
        )
    )
    if not winner_valid or winner_index < 0 or winner_index >= len(labels):
        payload = _inactive_physicalized_payload(
            time_s=values_t,
            branch_labels=labels,
            winner_index=winner_index,
            winner_label=None,
            shared_omega=shared_omega,
            drain_omega=drain_omega,
        )
        return payload if include_traces else {
            key: value
            for key, value in payload.items()
            if key
            not in {
                "time_s",
                "closure_variable",
                "common_inhibit_v",
                "winner_gate_v",
                "shared_node_voltage_v",
                "shared_resonant_current_a",
                "winner_drain_tank_voltage_v",
                "winner_drain_enable_by_branch",
                "winner_drain_power_w",
                "winner_drain_current_a",
                "winner_drain_energy_j",
                "remaining_shared_energy_j",
                "trial_complete_signal",
                "winner_branch_power_w",
                "loser_branch_power_w",
                "loser_suppression",
                "loser_clamp_conductance_s",
                "loser_clamp_current_a",
                "trigger_sense_v",
                "trigger_comparator_output",
                "inhibit_store_v",
                "winner_gate_driver_v",
                "winner_switch_conductance_s",
                "winner_switch_channel_current_a",
                "drain_dump_voltage_v",
                "common_inhibit_current_a",
                "winner_gate_current_a",
                "branch_attachment_current_a",
            }
        }

    winner_label = labels[winner_index]
    component_map = _device_component_map(candidate)
    cache = (
        build_physical_closure_candidate_cache(candidate)
        if candidate_cache is None
        else dict(candidate_cache)
    )
    future_energy_by_branch = future_branch_energy_from_cache(cache, capture_time_s=float(capture_time_s))
    initial_remaining_energy = float(sum(future_energy_by_branch.values()))
    if initial_remaining_energy <= 1e-18:
        payload = _inactive_physicalized_payload(
            time_s=values_t,
            branch_labels=labels,
            winner_index=winner_index,
            winner_label=winner_label,
            shared_omega=shared_omega,
            drain_omega=drain_omega,
        )
        payload["closure_active"] = True
        payload["activation_count"] = 1
        payload["trial_complete"] = True
        payload["trial_complete_time_s"] = float(capture_time_s)
        payload["winner_drain_path_count"] = 1
        payload["winner_drain_enable_by_branch"] = {
            label: (
                np.where(values_t >= capture_time_s, 1.0, 0.0).tolist()
                if label == winner_label
                else zero_trace.tolist()
            )
            for label in labels
        }
        return payload if include_traces else {
            key: value
            for key, value in payload.items()
            if not isinstance(value, list) and not isinstance(value, dict)
        }

    base_shares = {
        label: future_energy_by_branch[label] / max(initial_remaining_energy, 1e-18)
        for label in labels
    }
    dt = np.asarray(cache["dt"], dtype=float)
    dt_safe = np.maximum(dt, 0.0)
    active_indices = np.where(values_t >= float(capture_time_s))[0]

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
    trigger_sense_v = np.zeros_like(values_t)
    trigger_comparator_output = np.zeros_like(values_t)
    inhibit_store_v = np.zeros_like(values_t)
    winner_gate_driver_v = np.zeros_like(values_t)
    winner_switch_conductance = np.zeros_like(values_t)
    winner_switch_channel_current = np.zeros_like(values_t)
    drain_dump_voltage = np.zeros_like(values_t)
    common_inhibit_current = np.zeros_like(values_t)
    winner_gate_current = np.zeros_like(values_t)
    branch_attachment_current = {label: np.zeros_like(values_t) for label in labels}

    completed = False
    completed_time = float(values_t[-1]) if values_t.size else float("inf")
    completed_reason = "end_of_trace"
    winner_branch_energy = 0.0
    shared_leak_energy = 0.0
    loser_energy = {label: 0.0 for label in labels if label != winner_label}

    if active_indices.size:
        effective_delay = np.maximum(values_t[active_indices] - float(capture_time_s), 0.0)
        dt_active = np.maximum(dt_safe[active_indices], 0.0)
        sense_tau = max(
            float(component_map["R_SENSE_LINK"]["value"]) * float(component_map["C_SENSE_HOLD"]["value"]),
            1e-12,
        )
        store_tau = max(
            float(component_map["R_INHIBIT_CHARGE"]["value"]) * float(component_map["C_INHIBIT_STORE"]["value"]),
            1e-12,
        )
        rail_tau = max(
            float(component_map["R_INHIBIT_HYST"]["value"]) * float(component_map["C_INHIBIT_STORE"]["value"]),
            1e-12,
        )
        gate_tau = max(
            float(component_map["R_GATE_DRV"]["value"]) * float(component_map["C_GATE_DRV"]["value"]),
            1e-12,
        )
        dump_tau = max(
            np.sqrt(float(component_map["L_DRAIN_SER"]["value"]) * float(component_map["C_DRAIN_DUMP"]["value"])),
            1e-12,
        )

        trigger_sense_active = base_closure.supply_v * (1.0 - np.exp(-effective_delay / sense_tau))
        comparator_active = _sigmoid(
            trigger_sense_active,
            threshold=float(resolved.comparator_threshold_v),
            slope=float(resolved.comparator_slope_v),
        )
        inhibit_store_active = base_closure.supply_v * comparator_active * (1.0 - np.exp(-effective_delay / store_tau))
        common_inhibit_active = inhibit_store_active * (1.0 - np.exp(-effective_delay / rail_tau))
        gate_driver_active = inhibit_store_active * (1.0 - np.exp(-effective_delay / gate_tau))
        gate_switch_active = _sigmoid(
            gate_driver_active,
            threshold=float(resolved.switch_threshold_v),
            slope=float(resolved.switch_slope_v),
        )
        clamp_drive = _sigmoid(
            common_inhibit_active,
            threshold=float(resolved.clamp_threshold_v),
            slope=float(resolved.clamp_slope_v),
        )
        resonant_fill = 1.0 - np.exp(-effective_delay / dump_tau)
        closure_variable[active_indices] = comparator_active
        trigger_sense_v[active_indices] = trigger_sense_active
        trigger_comparator_output[active_indices] = comparator_active
        inhibit_store_v[active_indices] = inhibit_store_active
        common_inhibit_v[active_indices] = common_inhibit_active
        winner_gate_driver_v[active_indices] = gate_driver_active
        winner_gate_v[active_indices] = gate_driver_active
        winner_enable[winner_label][active_indices] = gate_switch_active

        g_shared_leak = 1.0 / max(float(base_closure.shared_loss_resistance_ohm), 1e-9)
        clamp_reference_g = (
            1.0 / max(float(base_closure.clamp_resistance_ohm), 1e-9)
            + shared_omega * float(base_closure.clamp_capacitance_f)
        )
        base_branch_coupling = shared_omega * float(base_closure.branch_coupling_capacitance_f)
        g_switch = gate_switch_active / max(float(resolved.switch_on_resistance_ohm), 1e-9) + (
            1.0 - gate_switch_active
        ) / max(float(component_map["R_WIN_SWITCH_OFF"]["value"]), 1e-9)
        g_winner_drain = g_switch * resonant_fill
        branch_conductance_arrays: dict[str, np.ndarray] = {}
        for label in labels:
            base_g = base_branch_coupling * base_shares[label]
            if label == winner_label:
                branch_conductance_arrays[label] = base_g * (
                    1.0 + float(base_closure.winner_branch_boost) * clamp_drive
                )
            else:
                loser_decay = np.exp(
                    -(
                        float(base_closure.loser_attenuation_beta)
                        + float(base_closure.clamp_coupling_strength) * clamp_reference_g
                    )
                    * clamp_drive
                )
                branch_conductance_arrays[label] = base_g * (
                    float(base_closure.loser_residual_floor_fraction)
                    + (1.0 - float(base_closure.loser_residual_floor_fraction)) * loser_decay
                )
                loser_suppression[label][active_indices] = 1.0 - branch_conductance_arrays[label] / max(base_g, 1e-18)
                loser_clamp_conductance[label][active_indices] = clamp_reference_g * clamp_drive

        g_total = np.full_like(effective_delay, g_shared_leak)
        for values in branch_conductance_arrays.values():
            g_total = g_total + values
        g_total = np.maximum(g_total + g_winner_drain, 1e-18)

        decay_factor = np.exp(
            -2.0 * g_total * dt_active / max(float(base_closure.shared_capacitance_f), 1e-18)
        )
        energy_before = initial_remaining_energy * np.concatenate(([1.0], np.cumprod(decay_factor[:-1])))
        energy_after = energy_before * decay_factor
        energy_released = energy_before - energy_after

        shared_voltage = np.sqrt(
            np.maximum(2.0 * energy_before / max(float(base_closure.shared_capacitance_f), 1e-18), 0.0)
        )
        shared_current = np.sqrt(
            np.maximum(2.0 * energy_before / max(float(base_closure.shared_inductance_h), 1e-18), 0.0)
        )
        shared_node_voltage_v[active_indices] = shared_voltage
        shared_resonant_current[active_indices] = shared_current
        winner_switch_conductance[active_indices] = g_switch
        winner_switch_channel_current[active_indices] = shared_voltage * g_switch
        winner_drain_current[active_indices] = shared_voltage * g_winner_drain
        effective_channel_r = 1.0 / np.maximum(g_switch, 1e-18)
        winner_drain_tank_voltage[active_indices] = winner_drain_current[active_indices] * effective_channel_r
        drain_dump_voltage[active_indices] = (
            winner_drain_current[active_indices] * float(component_map["R_DRAIN_DUMP"]["value"])
        )
        common_inhibit_current[active_indices] = np.divide(
            inhibit_store_active - common_inhibit_active,
            max(float(component_map["R_INHIBIT_HYST"]["value"]), 1e-12),
        )
        winner_gate_current[active_indices] = np.divide(
            inhibit_store_active - gate_driver_active,
            max(float(component_map["R_GATE_DRV"]["value"]), 1e-12),
        )

        winner_branch_share = branch_conductance_arrays[winner_label] / g_total
        winner_drain_share = g_winner_drain / g_total
        shared_leak_share = g_shared_leak / g_total
        winner_branch_increment = energy_released * winner_branch_share
        winner_branch_energy = float(np.sum(winner_branch_increment))
        winner_branch_power[active_indices] = np.divide(
            winner_branch_increment,
            np.maximum(dt_active, 1e-18),
        )
        drain_increment = energy_released * winner_drain_share
        winner_drain_power[active_indices] = np.divide(drain_increment, np.maximum(dt_active, 1e-18))
        winner_drain_energy[active_indices] = np.cumsum(drain_increment)

        for label in labels:
            if label == winner_label:
                branch_attachment_current[label][active_indices] = winner_drain_current[active_indices]
                continue
            branch_increment = energy_released * branch_conductance_arrays[label] / g_total
            loser_energy[label] = float(np.sum(branch_increment))
            loser_branch_power[label][active_indices] = np.divide(branch_increment, np.maximum(dt_active, 1e-18))
            loser_clamp_current[label][active_indices] = (
                shared_voltage * loser_clamp_conductance[label][active_indices]
            )
            branch_attachment_current[label][active_indices] = loser_clamp_current[label][active_indices]

        shared_leak_energy = float(np.sum(energy_released * shared_leak_share))
        remaining_energy[active_indices] = energy_after
        completion_hits = np.where(
            (energy_after <= float(base_closure.completion_threshold_frac) * initial_remaining_energy)
            & (winner_drain_current[active_indices] <= float(base_closure.completion_current_threshold_a))
        )[0]
        if completion_hits.size:
            completed = True
            completed_time = float(values_t[active_indices[completion_hits[0]]])
            completed_reason = "device_shared_energy_and_switch_current_below_threshold"
            trial_complete_signal[active_indices[completion_hits[0]:]] = 1.0

    monotonic = bool(np.all(np.diff(remaining_energy[active_indices]) <= 1e-12)) if active_indices.size else True
    terminal_loser_suppression_mean = (
        float(np.mean([values[active_indices[-1]] for values in loser_suppression.values()]))
        if loser_suppression and active_indices.size
        else 0.0
    )
    payload = {
        "topology_name": "device_physicalized_common_inhibit_and_winner_drain",
        "control_node_name": resolved.inhibit_store_node_name,
        "gate_node_name": resolved.gate_driver_node_name,
        "drain_node_name": resolved.dump_node_name,
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
        "selected_subblocks": list(resolved.selected_subblocks),
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
                "trigger_sense_v": trigger_sense_v.tolist(),
                "trigger_comparator_output": trigger_comparator_output.tolist(),
                "inhibit_store_v": inhibit_store_v.tolist(),
                "winner_gate_driver_v": winner_gate_driver_v.tolist(),
                "winner_switch_conductance_s": winner_switch_conductance.tolist(),
                "winner_switch_channel_current_a": winner_switch_channel_current.tolist(),
                "drain_dump_voltage_v": drain_dump_voltage.tolist(),
                "common_inhibit_current_a": common_inhibit_current.tolist(),
                "winner_gate_current_a": winner_gate_current.tolist(),
                "branch_attachment_current_a": {label: values.tolist() for label, values in branch_attachment_current.items()},
            }
        )
    return payload


def run_preferred_chain_device_physicalization_candidate(
    candidate: Mapping[str, Any],
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    n_trials: int,
    seed: int,
    physicalization_config: PreferredChainDevicePhysicalizationConfig | Mapping[str, Any] | None = None,
    baseline_result: Mapping[str, Any] | None = None,
    progress: _ProgressReporter | None = None,
    case_name: str | None = None,
) -> dict[str, Any]:
    race = _run_pre_click_race(
        candidate,
        detector_spec,
        n_trials=n_trials,
        seed=seed,
        progress=progress,
        case_name=case_name,
    )
    frequency_summary = race["frequency_summary"]
    cache = build_physical_closure_candidate_cache(candidate)
    closure_rows: list[dict[str, Any]] = []
    energy_rows: list[dict[str, Any]] = []
    example_trial: dict[str, Any] | None = None
    for trial_index, latch_result in enumerate(race["latch_results"]):
        closure = simulate_device_physicalized_closure_drain(
            candidate,
            winner_index=int(latch_result["winner_index"]),
            winner_valid=bool(latch_result["winner_valid"]),
            capture_time_s=float(latch_result["settled_at_s"]),
            physicalization_config=physicalization_config,
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
            progress.advance("post-click-device-subblocks", case_name=case_name)
        if example_trial is None and bool(closure["closure_active"]):
            closure_trace = simulate_device_physicalized_closure_drain(
                candidate,
                winner_index=int(latch_result["winner_index"]),
                winner_valid=bool(latch_result["winner_valid"]),
                capture_time_s=float(latch_result["settled_at_s"]),
                physicalization_config=physicalization_config,
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


def run_preferred_chain_device_physicalization_case(
    state4: np.ndarray | None,
    *,
    a_deg: float,
    b_deg: float,
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    n_trials: int,
    seed: int,
    physicalization_config: PreferredChainDevicePhysicalizationConfig | None = None,
    baseline_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    candidate = simulate_preferred_chain_device_physicalization_candidate(
        state4,
        a_deg=a_deg,
        b_deg=b_deg,
        physicalization_config=physicalization_config,
    )
    return run_preferred_chain_device_physicalization_candidate(
        candidate,
        detector_spec,
        n_trials=n_trials,
        seed=seed,
        physicalization_config=physicalization_config,
        baseline_result=baseline_result,
    )


def run_preferred_chain_device_physicalization_benchmark(
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    n_trials: int,
    seed: int,
    case_names: Sequence[str] | None = None,
    physicalization_config: PreferredChainDevicePhysicalizationConfig | None = None,
    verbose_progress: bool = False,
) -> dict[str, Any]:
    selected_case_names = None if case_names is None else set(case_names)
    cases = [
        case
        for case in preferred_chain_device_physicalization_benchmark_cases()
        if selected_case_names is None or case["case"] in selected_case_names
    ]
    if not cases:
        raise ValueError("No preferred chain device physicalization benchmark cases selected.")

    baseline = run_preferred_chain_codesign_benchmark(
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
    subblock_rows: list[dict[str, Any]] = []
    case_comparison_rows: list[dict[str, Any]] = []
    example_front_end: dict[str, Any] | None = None
    example_trial: dict[str, Any] | None = None

    for case_index, case in enumerate(cases):
        progress.report("starting-case", case_name=str(case["case"]), force=True)
        baseline_result = baseline_case_map[str(case["case"])]
        candidate = simulate_preferred_chain_device_physicalization_candidate(
            case["state4"],
            a_deg=case["a_deg"],
            b_deg=case["b_deg"],
            physicalization_config=physicalization_config,
        )
        result = run_preferred_chain_device_physicalization_candidate(
            candidate,
            detector_spec,
            n_trials=n_trials,
            seed=seed + 1_003 * case_index,
            physicalization_config=physicalization_config,
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
        topology = candidate["device_physicalization"]["topology_summary"]
        explicitness = candidate["device_physicalization"]["explicitness_metrics"]
        semantics = candidate["device_physicalization"]["realism_semantics"]
        subblock_rows.append(
            {
                "case": case["case"],
                "device_component_count": int(topology["device_component_count"]),
                "device_node_count": int(topology["device_node_count"]),
                "common_inhibit_device_component_count": int(topology["common_inhibit_device_component_count"]),
                "winner_drain_device_component_count": int(topology["winner_drain_device_component_count"]),
                "selected_subblock_count": int(topology["selected_subblock_count"]),
                "matrix_density": float(topology["matrix_density"]),
                "branch_voltage_perturbation_rms": float(explicitness["branch_voltage_perturbation_rms"]),
                "max_branch_voltage_perturbation": float(explicitness["max_branch_voltage_perturbation"]),
                "uses_device_level_common_inhibit": bool(semantics["uses_device_level_common_inhibit"]),
                "uses_device_level_winner_drain": bool(semantics["uses_device_level_winner_drain"]),
                "legacy_subblock_fallback_used": bool(semantics["legacy_subblock_fallback_used"]),
            }
        )
        case_comparison_rows.append(
            {
                "case": case["case"],
                "baseline_winner_rms_error": float(baseline_result["metrics"]["rms_error"]),
                "device_winner_rms_error": float(result["metrics"]["rms_error"]),
                "baseline_winner_max_error": float(baseline_result["metrics"]["max_abs_error"]),
                "device_winner_max_error": float(result["metrics"]["max_abs_error"]),
                "baseline_correlator_error": float(baseline_result["metrics"]["correlator_error"]),
                "device_correlator_error": float(result["metrics"]["correlator_error"]),
                "baseline_transparency_rms_shift": 0.0,
                "device_transparency_rms_shift": float(result["pre_click_comparison"]["winner_frequency_rms_shift"]),
                "baseline_winner_drain_fraction": float(
                    baseline_result["post_click_summary"]["mean_activated_winner_drain_fraction"]
                ),
                "device_winner_drain_fraction": float(
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
                "device_physicalization": candidate["device_physicalization"],
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
    summary_metrics["architectural_realism_gain_pass"] = (
        float(np.mean([row["device_component_count"] for row in subblock_rows])) >= 15.0
        and float(np.mean([row["common_inhibit_device_component_count"] for row in subblock_rows])) >= 7.0
        and float(np.mean([row["winner_drain_device_component_count"] for row in subblock_rows])) >= 8.0
        and bool(all(bool(row["uses_device_level_common_inhibit"]) for row in subblock_rows))
        and bool(all(bool(row["uses_device_level_winner_drain"]) for row in subblock_rows))
    )
    summary_metrics["no_legacy_subblock_fallback"] = bool(
        all(not bool(row["legacy_subblock_fallback_used"]) for row in subblock_rows)
    )
    summary_metrics["frozen_boundary_pass"] = True
    summary_metrics["proceed_to_next_phase"] = bool(summary_metrics["proceed_to_next_phase"]) and bool(
        summary_metrics["front_end_fraction_pass"]
        and summary_metrics["architectural_realism_gain_pass"]
        and summary_metrics["no_legacy_subblock_fallback"]
    )

    baseline_front_end_summary = aggregate_case_error(
        baseline["front_end_rows"],
        rms_key="rms_error",
        max_key="max_abs_error",
    )
    device_front_end_summary = aggregate_case_error(
        front_end_rows,
        rms_key="rms_error",
        max_key="max_abs_error",
    )
    comparison_rows = [
        {
            "candidate": "current_integrated_preferred_chain",
            "front_end_rms_error": float(baseline_front_end_summary["rms_error"]),
            "winner_rms_error": float(baseline["summary_metrics"]["winner_law_rms_error"]),
            "winner_law_rms_error": float(baseline["summary_metrics"]["winner_law_rms_error"]),
            "winner_law_max_error": float(baseline["summary_metrics"]["winner_law_max_error"]),
            "correlator_rms_error": float(baseline["summary_metrics"]["correlator_rms_error"]),
            "chsh_abs_error": float(baseline["summary_metrics"]["chsh_abs_error"]),
            "pre_click_transparency_rms_shift": float(baseline["summary_metrics"]["pre_click_transparency_rms_shift"]),
            "winner_drain_dominance_rate": float(baseline["summary_metrics"]["winner_drain_dominance_rate"]),
            "energy_accounting_pass": bool(baseline["summary_metrics"]["energy_accounting_pass"]),
            "architecture_note": (
                "Integrated codesign chain with attached closure hardware but reduced internal control and drain subblocks."
            ),
        },
        {
            "candidate": "preferred_chain_device_physicalization",
            "front_end_rms_error": float(device_front_end_summary["rms_error"]),
            "winner_rms_error": float(summary_metrics["winner_law_rms_error"]),
            "winner_law_rms_error": float(summary_metrics["winner_law_rms_error"]),
            "winner_law_max_error": float(summary_metrics["winner_law_max_error"]),
            "correlator_rms_error": float(summary_metrics["correlator_rms_error"]),
            "chsh_abs_error": float(summary_metrics["chsh_abs_error"]),
            "pre_click_transparency_rms_shift": float(summary_metrics["pre_click_transparency_rms_shift"]),
            "winner_drain_dominance_rate": float(summary_metrics["winner_drain_dominance_rate"]),
            "energy_accounting_pass": bool(summary_metrics["energy_accounting_pass"]),
            "architecture_note": (
                "Integrated codesign chain with an explicit trigger/store common inhibit realization and a gate/switch/snubber/dump winner drain realization."
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
        "subblock_rows": subblock_rows,
        "case_comparison_rows": case_comparison_rows,
        "comparison_rows": comparison_rows,
        "chsh_result": chsh_result,
        "summary_metrics": summary_metrics,
        "baseline_summary_metrics": baseline["summary_metrics"],
        "example_front_end": example_front_end,
        "example_trial": example_trial,
    }


__all__ = [
    "PreferredChainDevicePhysicalizationConfig",
    "preferred_chain_device_physicalization_benchmark_cases",
    "run_preferred_chain_device_physicalization_benchmark",
    "run_preferred_chain_device_physicalization_candidate",
    "run_preferred_chain_device_physicalization_case",
    "simulate_device_physicalized_closure_drain",
    "simulate_preferred_chain_device_physicalization_candidate",
]
