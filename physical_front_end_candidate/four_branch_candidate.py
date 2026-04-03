from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from detector_integration.frontends.four_branch import four_branch_weights
from detector_integration.sim.metrics import four_branch_metrics
from src.shared_4tank_core import singlet_state

from .export_interface import amplitude_envelope, build_time_axis, export_contract, resolve_envelope_config
from .metrics import fraction_error_metrics

BRANCH_LABELS = ["++", "+-", "-+", "--"]


@dataclass(frozen=True)
class FourBranchPhysicalFrontEndConfig:
    """First shared-state four-branch physical/SPICE front-end candidate."""

    implementation_option: str = "A4"
    source_amplitude_scale_v: float = 6.0
    source_resistance_ohm: tuple[float, float, float, float] = (25.0, 25.2, 24.8, 25.1)
    load_resistance_ohm: tuple[float, float, float, float] = (50.0, 49.9, 50.2, 49.8)
    branch_gain_trim: tuple[float, float, float, float] = (1.0, 0.999, 1.001, 0.998)
    branch_phase_deg: tuple[float, float, float, float] = (0.0, 0.8, -0.6, 1.1)


def benchmark_four_branch_physical_cases() -> list[dict[str, Any]]:
    state = singlet_state()
    return [
        {"case": "case_a", "state4": state, "a_deg": 0.0, "b_deg": 0.0},
        {"case": "case_c", "state4": state, "a_deg": 0.0, "b_deg": 45.0},
        {"case": "a0b0", "state4": state, "a_deg": 0.0, "b_deg": 22.5},
        {"case": "a0b1", "state4": state, "a_deg": 0.0, "b_deg": -22.5},
        {"case": "a1b0", "state4": state, "a_deg": 45.0, "b_deg": 22.5},
        {"case": "a1b1", "state4": state, "a_deg": 45.0, "b_deg": -22.5},
    ]


def simulate_four_branch_physical_candidate(
    state4: np.ndarray | None = None,
    *,
    a_deg: float,
    b_deg: float,
    front_end_config: FourBranchPhysicalFrontEndConfig | None = None,
    envelope_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_front_end = FourBranchPhysicalFrontEndConfig() if front_end_config is None else front_end_config
    resolved_envelope = resolve_envelope_config(envelope_config)
    state = singlet_state() if state4 is None else np.asarray(state4, dtype=np.complex128)
    exact = four_branch_weights(state, a_deg=float(a_deg), b_deg=float(b_deg))
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
        base_amplitude = resolved_front_end.source_amplitude_scale_v * np.sqrt(max(float(exact[index]), 0.0))
        open_circuit = base_amplitude * gain * phase * drive_envelope
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
    export["candidate_config"] = asdict(resolved_front_end)
    export["a_deg"] = float(a_deg)
    export["b_deg"] = float(b_deg)
    export["metrics"] = {
        **fraction_error_metrics(exact, realized),
        "correlator_exact": float(correlator_metrics["correlator_exact"]),
        "correlator_realized": float(correlator_metrics["correlator_empirical"]),
        "correlator_error": float(correlator_metrics["correlator_error"]),
    }
    return export
