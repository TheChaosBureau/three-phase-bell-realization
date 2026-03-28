from __future__ import annotations

import numpy as np

from .config import EPSILON, SourceConfig


def abs2(values: np.ndarray) -> np.ndarray:
    return np.abs(values) ** 2


def rotation_matrix(phi_rad: float) -> np.ndarray:
    cos_phi = np.cos(phi_rad)
    sin_phi = np.sin(phi_rad)
    return np.array([[cos_phi, -sin_phi], [sin_phi, cos_phi]], dtype=np.float64)


def apply_linear_operator(states: np.ndarray, operator: np.ndarray) -> np.ndarray:
    array = np.asarray(states, dtype=np.complex128)
    if array.ndim == 1:
        return operator @ array
    return array @ operator.T


def to_analyzer_basis(states: np.ndarray, phi_rad: float) -> np.ndarray:
    return apply_linear_operator(states, rotation_matrix(-phi_rad))


def from_analyzer_basis(coords: np.ndarray, phi_rad: float) -> np.ndarray:
    return apply_linear_operator(coords, rotation_matrix(phi_rad))


def normalize_states(states: np.ndarray, target_radius: float = 1.0) -> np.ndarray:
    array = np.asarray(states, dtype=np.complex128)
    norms = np.linalg.norm(array, axis=-1, keepdims=True)
    safe_norms = np.where(norms > EPSILON, norms, 1.0)
    return target_radius * array / safe_norms


def sample_source_states(config: SourceConfig) -> np.ndarray:
    rng = np.random.default_rng(config.seed)
    angles = rng.uniform(0.0, 2.0 * np.pi, size=config.sample_count)

    states = np.empty((config.sample_count, 2), dtype=np.complex128)
    states[:, 0] = np.cos(angles)
    states[:, 1] = np.sin(angles)

    if config.amplitude_imbalance:
        states[:, 0] *= 1.0 + config.amplitude_imbalance
        states[:, 1] *= 1.0 - config.amplitude_imbalance

    if config.random_relative_phase:
        relative_phase = rng.uniform(0.0, 2.0 * np.pi, size=config.sample_count)
        states[:, 1] *= np.exp(1j * relative_phase)
    elif config.relative_phase_rad:
        states[:, 1] *= np.exp(1j * config.relative_phase_rad)

    if config.random_global_phase:
        global_phase = rng.uniform(0.0, 2.0 * np.pi, size=config.sample_count)
        states *= np.exp(1j * global_phase)[:, None]

    if config.noise_std > 0.0:
        noise = config.noise_std * (
            rng.normal(size=states.shape) + 1j * rng.normal(size=states.shape)
        )
        states += noise

    return normalize_states(states, target_radius=config.radius)
