from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any

import numpy as np

from detector_integration.frontends.two_branch import two_branch_weights
from src.analyzer_couplers import rotation

from .export_interface import PhysicalEnvelopeConfig, amplitude_envelope, build_time_axis, export_contract, resolve_envelope_config
from .metrics import fraction_error_metrics


@dataclass(frozen=True)
class PhysicalFrontEndConfig:
    """Two-branch physical/SPICE candidate: analyzer matrix into Thevenin-loaded branches."""

    implementation_option: str = "A"
    source_resistance_ohm: tuple[float, float] = (25.0, 25.4)
    load_resistance_ohm: tuple[float, float] = (50.0, 49.7)
    branch_gain_trim: tuple[float, float] = (1.0, 0.996)
    branch_phase_deg: tuple[float, float] = (0.0, 1.2)


def _normalize_state(state: np.ndarray) -> np.ndarray:
    vector = np.asarray(state, dtype=np.complex128).reshape(2)
    norm = float(np.linalg.norm(vector))
    if norm <= 0.0:
        raise ValueError("Two-branch state must be nonzero.")
    return vector / norm


def _normalize_vector(vector: np.ndarray) -> np.ndarray:
    values = np.asarray(vector, dtype=np.complex128).reshape(2)
    norm = float(np.linalg.norm(values))
    if norm <= 0.0:
        raise ValueError("Analyzer basis vector must be nonzero.")
    return values / norm


def _analyzer_matrix(analyzer) -> np.ndarray:
    if isinstance(analyzer, (int, float)):
        return rotation(math.radians(float(analyzer)))
    matrix = np.asarray(analyzer, dtype=np.complex128)
    if matrix.shape == (2, 2):
        return matrix
    if isinstance(analyzer, (list, tuple)) and len(analyzer) == 2:
        rows = [np.conjugate(_normalize_vector(analyzer[0])), np.conjugate(_normalize_vector(analyzer[1]))]
        return np.vstack(rows)
    raise TypeError("Analyzer must be an angle in degrees, a 2x2 matrix, or a pair of basis vectors.")


def representative_physical_cases() -> list[dict[str, Any]]:
    return [
        {"case": "pole_plus_30", "state": np.array([1.0, 0.0], dtype=np.complex128), "analyzer": 30.0},
        {"case": "equator_x_45", "state": np.array([1.0, 1.0], dtype=np.complex128) / np.sqrt(2.0), "analyzer": 45.0},
        {"case": "phase_y_22_5", "state": np.array([1.0, 1.0j], dtype=np.complex128) / np.sqrt(2.0), "analyzer": 22.5},
    ]


def simulate_two_branch_physical_candidate(
    state: np.ndarray,
    analyzer,
    *,
    front_end_config: PhysicalFrontEndConfig | None = None,
    envelope_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_front_end = PhysicalFrontEndConfig() if front_end_config is None else front_end_config
    resolved_envelope = resolve_envelope_config(envelope_config)
    branch_labels = ["branch_1", "branch_2"]

    exact = two_branch_weights(np.asarray(state, dtype=np.complex128), analyzer)
    amplitudes = _analyzer_matrix(analyzer) @ _normalize_state(state)
    drive_envelope = amplitude_envelope(resolved_envelope)
    time_s = build_time_axis(resolved_envelope)

    branch_voltage: dict[str, np.ndarray] = {}
    branch_current: dict[str, np.ndarray] = {}
    branch_power: dict[str, np.ndarray] = {}
    branch_energy: dict[str, float] = {}
    branch_fraction: dict[str, float] = {}

    total_energy = 0.0
    for index, label in enumerate(branch_labels):
        source_r = float(resolved_front_end.source_resistance_ohm[index])
        load_r = float(resolved_front_end.load_resistance_ohm[index])
        gain = float(resolved_front_end.branch_gain_trim[index])
        phase = np.exp(1j * math.radians(float(resolved_front_end.branch_phase_deg[index])))
        open_circuit = gain * amplitudes[index] * phase * drive_envelope
        divider = load_r / (source_r + load_r)
        load_voltage = np.abs(open_circuit) * divider
        load_current = load_voltage / load_r
        power = np.maximum(load_voltage * load_current, 0.0)

        branch_voltage[label] = load_voltage.astype(float)
        branch_current[label] = load_current.astype(float)
        branch_power[label] = power.astype(float)
        branch_energy[label] = float(np.trapezoid(power, x=time_s))
        total_energy += branch_energy[label]

    for label in branch_labels:
        branch_fraction[label] = branch_energy[label] / max(total_energy, 1e-18)

    export = export_contract(
        branch_labels=branch_labels,
        time_s=time_s,
        branch_voltage_v=branch_voltage,
        branch_current_a=branch_current,
        branch_power_w=branch_power,
        branch_energy_j=branch_energy,
        branch_energy_fraction=branch_fraction,
        exact_weight={label: float(value) for label, value in zip(branch_labels, exact, strict=True)},
        envelope_config=resolved_envelope,
    )

    realized = np.array([branch_fraction[label] for label in branch_labels], dtype=float)
    export["candidate_config"] = asdict(resolved_front_end)
    export["metrics"] = fraction_error_metrics(exact, realized)
    return export
