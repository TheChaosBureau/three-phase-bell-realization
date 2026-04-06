from __future__ import annotations

import ctypes.util
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from detector_integration.frontends.four_branch import four_branch_weights
from detector_integration.sim.metrics import four_branch_metrics
from src.analyzer_couplers import AnalyzerCouplers
from src.shared_4tank_core import Shared4TankCore, singlet_state

from .metrics import aggregate_case_error, correlator_rms_error, fraction_error_metrics
from .preferred_chain_device_physicalization import (
    preferred_chain_device_physicalization_benchmark_cases,
    simulate_preferred_chain_device_physicalization_candidate,
)
from .preferred_front_end_netlist_candidate import (
    BRANCH_LABELS,
    GROUND_NODE,
    PreferredFrontEndNetlistConfig,
    _branch_node,
    _build_component_netlist,
    _passive_readout_matrix,
)
from .preferred_physical_chain_metrics import build_chsh_result


@dataclass
class _ProgressReporter:
    total_steps: int
    enabled: bool = False
    label: str = "actual-spice-front-end"
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
class ActualSpiceFrontEndConfig:
    implementation_option: str = "C"
    architecture_name: str = "actual_pyspice_shared_front_end"
    spice_engine: str = "PySpice+ngspice"
    baseline_candidate: str = "preferred_chain_device_physicalization"
    front_end_config: PreferredFrontEndNetlistConfig = field(default_factory=PreferredFrontEndNetlistConfig)
    target_carrier_hz: float = 2_000.0
    settle_cycles: int = 10
    measurement_cycles: int = 8
    samples_per_cycle: int = 200
    use_behavioral_analyzer_readout: bool = True
    use_real_analyzer_projection: bool = True
    load_probe_scale: float = 1.0


def _require_pyspice() -> dict[str, Any]:
    try:
        from PySpice.Spice.Netlist import Circuit
        from PySpice.Unit import u_F, u_H, u_Ohm
    except Exception as exc:  # pragma: no cover - exercised in environment-dependent tests
        raise RuntimeError(
            "PySpice is not available. Install PySpice and ensure ngspice is present."
        ) from exc

    libngspice = ctypes.util.find_library("ngspice") or ctypes.util.find_library("libngspice")
    if not libngspice:  # pragma: no cover - exercised in environment-dependent tests
        raise RuntimeError(
            "PySpice is installed, but libngspice is not available to the dynamic linker. "
            "Install ngspice and ensure its shared library directory is on LD_LIBRARY_PATH."
        )
    return {
        "Circuit": Circuit,
        "u_F": u_F,
        "u_H": u_H,
        "u_Ohm": u_Ohm,
        "libngspice": libngspice,
    }


def _safe_spice_token(token: str) -> str:
    return (
        token.replace("+", "p")
        .replace("-", "m")
        .replace("/", "_")
        .replace(":", "_")
        .replace(".", "_")
    )


def _safe_spice_node(node: str) -> str:
    return node if node == GROUND_NODE else _safe_spice_token(node)


def _safe_spice_name(name: str) -> str:
    return _safe_spice_token(name)


def _scaled_component_value(kind: str, value: float, *, omega_scale: float) -> float:
    if kind in {"inductor", "capacitor"}:
        return float(value) / max(float(omega_scale), 1e-18)
    return float(value)


def actual_spice_front_end_benchmark_cases() -> list[dict[str, Any]]:
    return preferred_chain_device_physicalization_benchmark_cases()


def _build_spice_circuit(
    *,
    state4: np.ndarray | None,
    a_deg: float,
    b_deg: float,
    resolved: ActualSpiceFrontEndConfig,
) -> dict[str, Any]:
    spice = _require_pyspice()
    Circuit = spice["Circuit"]
    u_F = spice["u_F"]
    u_H = spice["u_H"]
    u_Ohm = spice["u_Ohm"]

    front_end = resolved.front_end_config
    target_state = singlet_state() if state4 is None else np.asarray(state4, dtype=np.complex128)
    exact = np.asarray(four_branch_weights(target_state, a_deg=float(a_deg), b_deg=float(b_deg)), dtype=float)

    shared_core = Shared4TankCore(
        omega0=front_end.omega0,
        kappa=front_end.kappa,
        gamma=front_end.gamma,
        inductance_h=front_end.tank_inductance_h,
        capacitance_f=front_end.tank_capacitance_f,
        imperfections=front_end.core_imperfections,
    )
    analyzer = AnalyzerCouplers(imperfections=front_end.analyzer_imperfections)
    preparation = shared_core.prepare_singlet_mode(amplitude=front_end.drive_amplitude_v)
    omega_drive = max(float(preparation.drive_frequency_rad_s), 1e-12)
    source_drive_v = front_end.source_voltage_scale_v * preparation.drive_vector
    base_netlist = _build_component_netlist(front_end, source_drive_v=source_drive_v, omega_drive=omega_drive)

    omega_target = 2.0 * np.pi * max(float(resolved.target_carrier_hz), 1e-12)
    omega_scale = omega_target / omega_drive
    period_s = 1.0 / max(float(resolved.target_carrier_hz), 1e-12)
    settle_cycles = max(int(resolved.settle_cycles), 1)
    measurement_cycles = max(int(resolved.measurement_cycles), 1)
    total_cycles = settle_cycles + measurement_cycles
    step_time_s = period_s / max(int(resolved.samples_per_cycle), 8)
    end_time_s = total_cycles * period_s

    circuit = Circuit(f"actual_spice_front_end_a{a_deg:.3f}_b{b_deg:.3f}")
    source_current_phasors: dict[str, complex] = {}
    source_current_waveform: dict[str, dict[str, float]] = {}
    for branch in base_netlist["source_branches"]:
        label = str(branch["label"])
        node = _safe_spice_node(str(branch["node"]))
        current = complex(branch["norton_current_a"])
        amplitude = abs(current)
        phase_rad = float(np.angle(current))
        expression = f"({amplitude:.12g})*sin(2*pi*{float(resolved.target_carrier_hz):.12g}*time + ({phase_rad:.12g}))"
        circuit.B(_safe_spice_name(f"ISRC_{label}"), node, circuit.gnd, current_expression=expression)
        source_current_phasors[label] = current
        source_current_waveform[label] = {
            "amplitude_a": float(amplitude),
            "phase_rad": phase_rad,
            "expression": expression,
        }

    for component in base_netlist["components"]:
        component_name = _safe_spice_name(str(component["name"]))
        node_pos = circuit.gnd if component["node_pos"] == GROUND_NODE else _safe_spice_node(str(component["node_pos"]))
        node_neg = circuit.gnd if component["node_neg"] == GROUND_NODE else _safe_spice_node(str(component["node_neg"]))
        if component["group"] == "readout":
            continue
        value = _scaled_component_value(str(component["kind"]), float(component["value"]), omega_scale=omega_scale)
        if component["kind"] == "resistor":
            circuit.R(component_name, node_pos, node_neg, value @ u_Ohm)
        elif component["kind"] == "inductor":
            circuit.L(component_name, node_pos, node_neg, value @ u_H)
        elif component["kind"] == "capacitor":
            circuit.C(component_name, node_pos, node_neg, value @ u_F)
        else:  # pragma: no cover - the input component table is frozen to R/L/C
            raise ValueError(f"Unsupported SPICE component kind: {component['kind']}")

    passive_readout = _passive_readout_matrix(front_end.readout_cross_coupling)
    analyzer_matrix = analyzer.joint_matrix(float(a_deg), float(b_deg))
    branch_transform = passive_readout @ analyzer_matrix
    if resolved.use_real_analyzer_projection:
        branch_transform = np.real(branch_transform)

    output_probe_map: dict[str, dict[str, Any]] = {}
    for index, label in enumerate(BRANCH_LABELS):
        output_node = _safe_spice_node(f"out_{label}")
        if resolved.use_behavioral_analyzer_readout:
            expression = " + ".join(
                f"({float(branch_transform[index, column]):.8g})*V({_safe_spice_node(_branch_node(BRANCH_LABELS[column]))})"
                for column in range(len(BRANCH_LABELS))
            )
            circuit.B(_safe_spice_name(f"MIX_{label}"), output_node, circuit.gnd, voltage_expression=expression)
        else:
            expression = f"V({_safe_spice_node(_branch_node(label))})"
            circuit.B(_safe_spice_name(f"MIX_{label}"), output_node, circuit.gnd, voltage_expression=expression)
        load_value = max(float(front_end.load_resistance_ohm[index]) / max(float(resolved.load_probe_scale), 1e-12), 1e-9)
        readout_cap = _scaled_component_value(
            "capacitor",
            float(front_end.readout_shunt_capacitance_f[index]),
            omega_scale=omega_scale,
        )
        circuit.R(_safe_spice_name(f"LOAD_{label}"), output_node, circuit.gnd, load_value @ u_Ohm)
        circuit.C(_safe_spice_name(f"READ_{label}"), output_node, circuit.gnd, readout_cap @ u_F)
        output_probe_map[label] = {
            "node": output_node,
            "load_resistance_ohm": load_value,
            "readout_shunt_capacitance_f": readout_cap,
            "behavioral_source_expression": expression,
        }

    component_count = len(base_netlist["components"]) + 4 + 4
    topology_summary = {
        "component_count": component_count,
        "core_component_count": len(base_netlist["components"]),
        "coupling_component_count": int(base_netlist["topology_summary"]["coupling_component_count"]),
        "core_node_count": int(base_netlist["topology_summary"]["node_count"]),
        "output_probe_count": 4,
        "behavioral_source_count": 4,
        "uses_actual_spice": True,
        "uses_behavioral_analyzer_readout": bool(resolved.use_behavioral_analyzer_readout),
        "uses_real_analyzer_projection": bool(resolved.use_real_analyzer_projection),
        "probeable_branch_outputs": True,
    }
    return {
        "circuit": circuit,
        "circuit_text": str(circuit),
        "exact": exact,
        "shared_core": shared_core,
        "analyzer": analyzer,
        "preparation": preparation,
        "source_drive_v": source_drive_v,
        "source_current_phasors": source_current_phasors,
        "source_current_waveform": source_current_waveform,
        "branch_transform": branch_transform,
        "output_probe_map": output_probe_map,
        "base_netlist": base_netlist,
        "spice_engine_library": str(spice["libngspice"]),
        "omega_drive": omega_drive,
        "target_carrier_hz": float(resolved.target_carrier_hz),
        "period_s": period_s,
        "step_time_s": step_time_s,
        "end_time_s": end_time_s,
        "settle_cycles": settle_cycles,
        "measurement_cycles": measurement_cycles,
        "topology_summary": topology_summary,
    }


def simulate_actual_spice_front_end_candidate(
    state4: np.ndarray | None = None,
    *,
    a_deg: float,
    b_deg: float,
    spice_config: ActualSpiceFrontEndConfig | Mapping[str, Any] | None = None,
    baseline_candidate: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    resolved = (
        ActualSpiceFrontEndConfig()
        if spice_config is None
        else spice_config
        if isinstance(spice_config, ActualSpiceFrontEndConfig)
        else ActualSpiceFrontEndConfig(**dict(spice_config))
    )
    built = _build_spice_circuit(state4=state4, a_deg=a_deg, b_deg=b_deg, resolved=resolved)
    if baseline_candidate is None:
        baseline_candidate = simulate_preferred_chain_device_physicalization_candidate(
            state4,
            a_deg=float(a_deg),
            b_deg=float(b_deg),
        )

    simulator = built["circuit"].simulator(temperature=25, nominal_temperature=25)
    analysis = simulator.transient(step_time=built["step_time_s"], end_time=built["end_time_s"])

    time_s = np.asarray(analysis.time, dtype=float).reshape(-1)
    measurement_start_s = time_s[-1] - float(built["measurement_cycles"]) * float(built["period_s"])
    measurement_mask = time_s >= measurement_start_s
    measurement_time_s = time_s[measurement_mask]

    branch_voltage_v: dict[str, np.ndarray] = {}
    branch_current_a: dict[str, np.ndarray] = {}
    branch_power_w: dict[str, np.ndarray] = {}
    branch_energy_j: dict[str, float] = {}
    branch_energy_fraction: dict[str, float] = {}
    cumulative_energy_j: dict[str, np.ndarray] = {}
    raw_output_voltage_v: dict[str, np.ndarray] = {}
    total_energy = 0.0

    for label in BRANCH_LABELS:
        output_node = str(built["output_probe_map"][label]["node"])
        load_resistance = float(built["output_probe_map"][label]["load_resistance_ohm"])
        voltage = np.asarray(analysis[output_node], dtype=float).reshape(-1)
        current = voltage / max(load_resistance, 1e-12)
        power = np.maximum(voltage * current, 0.0)
        energy = float(np.trapezoid(power[measurement_mask], x=measurement_time_s))
        raw_output_voltage_v[label] = voltage
        branch_voltage_v[label] = voltage[measurement_mask]
        branch_current_a[label] = current[measurement_mask]
        branch_power_w[label] = power[measurement_mask]
        branch_energy_j[label] = energy
        cumulative_energy_j[label] = np.asarray(
            [
                float(np.trapezoid(power[measurement_mask][: index + 1], x=measurement_time_s[: index + 1]))
                for index in range(measurement_time_s.size)
            ],
            dtype=float,
        )
        total_energy += energy

    for label in BRANCH_LABELS:
        branch_energy_fraction[label] = branch_energy_j[label] / max(total_energy, 1e-18)

    core_node_voltage_v = {
        label: np.asarray(analysis[_safe_spice_node(_branch_node(label))], dtype=float).reshape(-1)
        for label in BRANCH_LABELS
    }
    source_current_a = {
        label: np.asarray(
            built["source_current_waveform"][label]["amplitude_a"]
            * np.sin(
                2.0 * np.pi * float(built["target_carrier_hz"]) * time_s
                + float(built["source_current_waveform"][label]["phase_rad"])
            ),
            dtype=float,
        )
        for label in BRANCH_LABELS
    }

    realized = np.asarray([branch_energy_fraction[label] for label in BRANCH_LABELS], dtype=float)
    baseline = np.asarray([float(baseline_candidate["branch_energy_fraction"][label]) for label in BRANCH_LABELS], dtype=float)
    exact = np.asarray([float(built["exact"][index]) for index in range(len(BRANCH_LABELS))], dtype=float)

    exact_metric_summary = four_branch_metrics(exact, realized)
    baseline_fraction_metrics = fraction_error_metrics(baseline, realized)
    exact_fraction_metrics = fraction_error_metrics(exact, realized)
    drive_current_magnitude = np.asarray([abs(built["source_current_phasors"][label]) for label in BRANCH_LABELS], dtype=float)
    if float(np.linalg.norm(drive_current_magnitude)) > 1e-18:
        drive_current_magnitude /= float(np.linalg.norm(drive_current_magnitude))
    exact_amplitude = np.sqrt(np.maximum(exact, 0.0))
    if float(np.linalg.norm(exact_amplitude)) > 1e-18:
        exact_amplitude /= float(np.linalg.norm(exact_amplitude))

    finite_traces = bool(
        np.all(np.isfinite(time_s))
        and all(np.all(np.isfinite(values)) for values in branch_voltage_v.values())
        and all(np.all(np.isfinite(values)) for values in branch_current_a.values())
        and all(np.all(np.isfinite(values)) for values in branch_power_w.values())
        and all(np.all(np.isfinite(values)) for values in core_node_voltage_v.values())
    )
    explicitness = {
        "component_count": int(built["topology_summary"]["component_count"]),
        "core_component_count": int(built["topology_summary"]["core_component_count"]),
        "coupling_component_count": int(built["topology_summary"]["coupling_component_count"]),
        "output_probe_count": int(built["topology_summary"]["output_probe_count"]),
        "behavioral_source_count": int(built["topology_summary"]["behavioral_source_count"]),
        "uses_actual_spice": True,
        "actual_spice_run_succeeded": True,
        "probeable_branch_outputs": True,
        "finite_output_traces": finite_traces,
        "drive_uses_exact_weights": False,
        "uses_behavioral_analyzer_readout": bool(built["topology_summary"]["uses_behavioral_analyzer_readout"]),
        "uses_real_analyzer_projection": bool(built["topology_summary"]["uses_real_analyzer_projection"]),
        "drive_current_exact_overlap": float(np.dot(drive_current_magnitude, exact_amplitude)),
    }

    return {
        "branch_labels": list(BRANCH_LABELS),
        "a_deg": float(a_deg),
        "b_deg": float(b_deg),
        "time_s": measurement_time_s.tolist(),
        "branch_voltage_v": {label: branch_voltage_v[label].tolist() for label in BRANCH_LABELS},
        "branch_current_a": {label: branch_current_a[label].tolist() for label in BRANCH_LABELS},
        "branch_power_w": {label: branch_power_w[label].tolist() for label in BRANCH_LABELS},
        "branch_energy_j": branch_energy_j,
        "branch_energy_fraction": branch_energy_fraction,
        "exact_weight": {label: float(exact[index]) for index, label in enumerate(BRANCH_LABELS)},
        "baseline_branch_energy_fraction": {label: float(baseline[index]) for index, label in enumerate(BRANCH_LABELS)},
        "raw_waveforms": {
            "time_s": time_s.tolist(),
            "measurement_start_s": float(measurement_start_s),
            "measurement_end_s": float(time_s[-1]) if time_s.size else 0.0,
            "core_node_voltage_v": {label: core_node_voltage_v[label].tolist() for label in BRANCH_LABELS},
            "output_node_voltage_v": {label: raw_output_voltage_v[label].tolist() for label in BRANCH_LABELS},
            "source_current_a": {label: source_current_a[label].tolist() for label in BRANCH_LABELS},
        },
        "processed_traces": {
            "measurement_time_s": measurement_time_s.tolist(),
            "cumulative_branch_energy_j": {label: cumulative_energy_j[label].tolist() for label in BRANCH_LABELS},
        },
        "spice": {
            "engine": resolved.spice_engine,
            "engine_library": built["spice_engine_library"],
            "netlist_text": built["circuit_text"],
            "target_carrier_hz": float(built["target_carrier_hz"]),
            "step_time_s": float(built["step_time_s"]),
            "end_time_s": float(built["end_time_s"]),
            "settle_cycles": int(built["settle_cycles"]),
            "measurement_cycles": int(built["measurement_cycles"]),
            "probe_nodes": {
                "core": {label: _safe_spice_node(_branch_node(label)) for label in BRANCH_LABELS},
                "output": {label: str(built["output_probe_map"][label]["node"]) for label in BRANCH_LABELS},
            },
            "output_probe_map": built["output_probe_map"],
            "branch_transform_matrix": np.asarray(built["branch_transform"]).tolist(),
            "source_current_waveform": built["source_current_waveform"],
            "source_drive_vector_v": [complex(value) for value in built["source_drive_v"]],
            "measurement_window_s": {
                "start": float(measurement_start_s),
                "end": float(time_s[-1]) if time_s.size else 0.0,
            },
        },
        "shared_core": {
            "architecture_name": resolved.architecture_name,
            "drive_frequency_rad_s": float(built["omega_drive"]),
            "prepared_state_magnitude": np.abs(np.asarray(built["preparation"].normalized_state, dtype=np.complex128)).astype(float).tolist(),
            "modal_energies": np.asarray(built["preparation"].modal_energies, dtype=float).tolist(),
            "source_drive_vector_v": [complex(value) for value in built["source_drive_v"]],
            "explicitness_metrics": explicitness,
        },
        "netlist": {
            "components": list(built["base_netlist"]["components"]),
            "source_branches": list(built["base_netlist"]["source_branches"]),
            "topology_summary": dict(built["topology_summary"]),
            "node_order": list(built["base_netlist"]["node_order"]),
        },
        "candidate_config": {
            **asdict(resolved),
            "front_end_config": {
                **asdict(resolved.front_end_config),
                "core_imperfections": asdict(resolved.front_end_config.core_imperfections),
                "analyzer_imperfections": asdict(resolved.front_end_config.analyzer_imperfections),
            },
        },
        "metrics": {
            "rms_error": float(baseline_fraction_metrics["rms_error"]),
            "max_abs_error": float(baseline_fraction_metrics["max_abs_error"]),
            "exact_rms_error": float(exact_fraction_metrics["rms_error"]),
            "exact_max_abs_error": float(exact_fraction_metrics["max_abs_error"]),
            "correlator_exact": float(exact_metric_summary["correlator_exact"]),
            "correlator_empirical": float(exact_metric_summary["correlator_empirical"]),
            "correlator_error": float(exact_metric_summary["correlator_error"]),
            **explicitness,
        },
    }


def run_actual_spice_front_end_case(
    state4: np.ndarray | None = None,
    *,
    a_deg: float,
    b_deg: float,
    spice_config: ActualSpiceFrontEndConfig | Mapping[str, Any] | None = None,
    baseline_candidate: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return simulate_actual_spice_front_end_candidate(
        state4,
        a_deg=a_deg,
        b_deg=b_deg,
        spice_config=spice_config,
        baseline_candidate=baseline_candidate,
    )


def run_actual_spice_front_end_benchmark(
    *,
    case_names: Sequence[str] | None = None,
    spice_config: ActualSpiceFrontEndConfig | Mapping[str, Any] | None = None,
    verbose_progress: bool = False,
) -> dict[str, Any]:
    resolved = (
        ActualSpiceFrontEndConfig()
        if spice_config is None
        else spice_config
        if isinstance(spice_config, ActualSpiceFrontEndConfig)
        else ActualSpiceFrontEndConfig(**dict(spice_config))
    )
    selected_case_names = None if case_names is None else set(case_names)
    cases = [
        case
        for case in actual_spice_front_end_benchmark_cases()
        if selected_case_names is None or str(case["case"]) in selected_case_names
    ]
    if not cases:
        raise ValueError("No actual SPICE front-end benchmark cases selected.")

    progress = _ProgressReporter(total_steps=max(len(cases), 1), enabled=verbose_progress)
    case_results: list[dict[str, Any]] = []
    front_end_rows: list[dict[str, Any]] = []
    probe_rows: list[dict[str, Any]] = []
    case_comparison_rows: list[dict[str, Any]] = []
    example_front_end: dict[str, Any] | None = None

    for case in cases:
        progress.report("simulate-case", case_name=str(case["case"]), force=True)
        baseline_candidate = simulate_preferred_chain_device_physicalization_candidate(
            case["state4"],
            a_deg=float(case["a_deg"]),
            b_deg=float(case["b_deg"]),
        )
        result = simulate_actual_spice_front_end_candidate(
            case["state4"],
            a_deg=float(case["a_deg"]),
            b_deg=float(case["b_deg"]),
            spice_config=resolved,
            baseline_candidate=baseline_candidate,
        )
        case_results.append({"case": case, "result": result, "baseline_candidate": baseline_candidate})

        exact_weights = [float(result["exact_weight"][label]) for label in BRANCH_LABELS]
        baseline_fractions = [float(result["baseline_branch_energy_fraction"][label]) for label in BRANCH_LABELS]
        realized_fractions = [float(result["branch_energy_fraction"][label]) for label in BRANCH_LABELS]
        front_end_rows.append(
            {
                "case": str(case["case"]),
                "a_deg": float(case["a_deg"]),
                "b_deg": float(case["b_deg"]),
                "branch_labels": list(BRANCH_LABELS),
                "exact_weights": exact_weights,
                "baseline_fractions": baseline_fractions,
                "realized_fractions": realized_fractions,
                "rms_error": float(result["metrics"]["rms_error"]),
                "max_abs_error": float(result["metrics"]["max_abs_error"]),
                "exact_rms_error": float(result["metrics"]["exact_rms_error"]),
                "exact_max_abs_error": float(result["metrics"]["exact_max_abs_error"]),
                "correlator_exact": float(result["metrics"]["correlator_exact"]),
                "correlator_empirical": float(result["metrics"]["correlator_empirical"]),
                "correlator_error": float(result["metrics"]["correlator_error"]),
            }
        )
        probe_rows.append(
            {
                "case": str(case["case"]),
                "engine": str(result["spice"]["engine"]),
                "engine_library": str(result["spice"]["engine_library"]),
                "target_carrier_hz": float(result["spice"]["target_carrier_hz"]),
                "step_time_s": float(result["spice"]["step_time_s"]),
                "end_time_s": float(result["spice"]["end_time_s"]),
                "component_count": int(result["shared_core"]["explicitness_metrics"]["component_count"]),
                "core_component_count": int(result["shared_core"]["explicitness_metrics"]["core_component_count"]),
                "coupling_component_count": int(result["shared_core"]["explicitness_metrics"]["coupling_component_count"]),
                "output_probe_count": int(result["shared_core"]["explicitness_metrics"]["output_probe_count"]),
                "behavioral_source_count": int(result["shared_core"]["explicitness_metrics"]["behavioral_source_count"]),
                "uses_actual_spice": bool(result["shared_core"]["explicitness_metrics"]["uses_actual_spice"]),
                "actual_spice_run_succeeded": bool(result["shared_core"]["explicitness_metrics"]["actual_spice_run_succeeded"]),
                "probeable_branch_outputs": bool(result["shared_core"]["explicitness_metrics"]["probeable_branch_outputs"]),
                "finite_output_traces": bool(result["shared_core"]["explicitness_metrics"]["finite_output_traces"]),
                "drive_uses_exact_weights": bool(result["shared_core"]["explicitness_metrics"]["drive_uses_exact_weights"]),
            }
        )
        case_comparison_rows.append(
            {
                "case": str(case["case"]),
                "baseline_front_end_rms_error": float(
                    fraction_error_metrics(
                        exact_weights,
                        baseline_fractions,
                    )["rms_error"]
                ),
                "spice_front_end_rms_error": float(result["metrics"]["rms_error"]),
                "baseline_front_end_exact_rms_error": float(
                    fraction_error_metrics(
                        exact_weights,
                        baseline_fractions,
                    )["rms_error"]
                ),
                "spice_front_end_exact_rms_error": float(result["metrics"]["exact_rms_error"]),
                "baseline_correlator_error": float(baseline_candidate["metrics"]["correlator_error"]),
                "spice_correlator_error": float(result["metrics"]["correlator_error"]),
            }
        )
        if example_front_end is None:
            example_front_end = {
                "case": str(case["case"]),
                "branch_labels": list(BRANCH_LABELS),
                "time_s": list(result["time_s"]),
                "branch_voltage_v": {label: list(result["branch_voltage_v"][label]) for label in BRANCH_LABELS},
                "branch_current_a": {label: list(result["branch_current_a"][label]) for label in BRANCH_LABELS},
                "branch_power_w": {label: list(result["branch_power_w"][label]) for label in BRANCH_LABELS},
                "raw_waveforms": dict(result["raw_waveforms"]),
                "processed_traces": dict(result["processed_traces"]),
                "spice": dict(result["spice"]),
                "netlist": dict(result["netlist"]),
                "shared_core": dict(result["shared_core"]),
            }
        progress.advance("simulate-case-complete", case_name=str(case["case"]))

    chsh_result = build_chsh_result(front_end_rows)
    front_end_aggregate = aggregate_case_error(front_end_rows, rms_key="rms_error", max_key="max_abs_error")
    exact_aggregate = aggregate_case_error(front_end_rows, rms_key="exact_rms_error", max_key="exact_max_abs_error")

    summary_metrics = {
        "front_end_fraction_rms_error": float(front_end_aggregate["rms_error"]),
        "front_end_fraction_max_error": float(front_end_aggregate["max_abs_error"]),
        "exact_fraction_rms_error": float(exact_aggregate["rms_error"]),
        "exact_fraction_max_error": float(exact_aggregate["max_abs_error"]),
        "correlator_rms_error": float(correlator_rms_error(front_end_rows, key="correlator_error")),
        "chsh_exact": float(chsh_result["exact_s"]),
        "chsh_empirical": float(chsh_result["empirical_s"]),
        "chsh_abs_error": float(chsh_result["abs_error"]),
        "actual_spice_execution_pass": bool(all(bool(row["actual_spice_run_succeeded"]) for row in probe_rows)),
        "finite_output_pass": bool(all(bool(row["finite_output_traces"]) for row in probe_rows)),
        "probeability_pass": bool(all(bool(row["probeable_branch_outputs"]) for row in probe_rows)),
        "architecture_explicitness_pass": bool(
            float(np.mean([float(row["component_count"]) for row in probe_rows])) >= 32.0
            and float(np.mean([float(row["coupling_component_count"]) for row in probe_rows])) >= 7.0
            and float(np.mean([float(row["output_probe_count"]) for row in probe_rows])) >= 4.0
            and bool(all(bool(row["uses_actual_spice"]) for row in probe_rows))
        ),
        "no_trivial_exact_weight_assignment": bool(all(not bool(row["drive_uses_exact_weights"]) for row in probe_rows)),
    }
    summary_metrics["front_end_fraction_pass"] = (
        float(summary_metrics["front_end_fraction_rms_error"]) < 0.03
        and float(summary_metrics["front_end_fraction_max_error"]) < 0.05
    )
    summary_metrics["correlator_pass"] = float(summary_metrics["correlator_rms_error"]) < 0.05
    summary_metrics["chsh_pass"] = bool(chsh_result["available"]) and float(summary_metrics["chsh_abs_error"]) < 0.1
    summary_metrics["proceed_to_next_phase"] = all(
        bool(summary_metrics[key])
        for key in (
            "front_end_fraction_pass",
            "actual_spice_execution_pass",
            "finite_output_pass",
            "probeability_pass",
            "architecture_explicitness_pass",
            "no_trivial_exact_weight_assignment",
            "correlator_pass",
            "chsh_pass",
        )
    )

    baseline_front_end_rows = [
        {
            "rms_error": float(fraction_error_metrics(row["exact_weights"], row["baseline_fractions"])["rms_error"]),
            "max_abs_error": float(fraction_error_metrics(row["exact_weights"], row["baseline_fractions"])["max_abs_error"]),
        }
        for row in front_end_rows
    ]
    baseline_front_end_summary = aggregate_case_error(baseline_front_end_rows)
    comparison_rows = [
        {
            "candidate": "current_preferred_chain_device_physicalization_front_end",
            "front_end_rms_error": float(baseline_front_end_summary["rms_error"]),
            "exact_fraction_rms_error": float(baseline_front_end_summary["rms_error"]),
            "correlator_rms_error": float(
                correlator_rms_error(
                    [
                        {"correlator_error": float(entry["baseline_candidate"]["metrics"]["correlator_error"])}
                        for entry in case_results
                    ]
                )
            ),
            "chsh_abs_error": float(
                build_chsh_result(
                    [
                        {
                            "case": str(entry["case"]["case"]),
                            "correlator_exact": float(entry["baseline_candidate"]["metrics"]["correlator_exact"]),
                            "correlator_empirical": float(entry["baseline_candidate"]["metrics"]["correlator_realized"]),
                        }
                        for entry in case_results
                    ]
                )["abs_error"]
            ),
            "engine": "analytical_reference",
            "architecture_note": "Current preferred-chain device-physicalized front-end export used as the frozen front-end benchmark target.",
        },
        {
            "candidate": "actual_spice_front_end",
            "front_end_rms_error": float(summary_metrics["front_end_fraction_rms_error"]),
            "exact_fraction_rms_error": float(summary_metrics["exact_fraction_rms_error"]),
            "correlator_rms_error": float(summary_metrics["correlator_rms_error"]),
            "chsh_abs_error": float(summary_metrics["chsh_abs_error"]),
            "engine": str(resolved.spice_engine),
            "architecture_note": "Actual ngspice transient of the explicit shared-core R/L/C network with behavioral analyzer/readout projection and direct load-branch power integration.",
        },
    ]
    progress.report("benchmark-complete", force=True)
    return {
        "case_results": case_results,
        "front_end_rows": front_end_rows,
        "probe_rows": probe_rows,
        "case_comparison_rows": case_comparison_rows,
        "comparison_rows": comparison_rows,
        "chsh_result": chsh_result,
        "summary_metrics": summary_metrics,
        "example_front_end": example_front_end,
    }


__all__ = [
    "ActualSpiceFrontEndConfig",
    "actual_spice_front_end_benchmark_cases",
    "run_actual_spice_front_end_benchmark",
    "run_actual_spice_front_end_case",
    "simulate_actual_spice_front_end_candidate",
]
