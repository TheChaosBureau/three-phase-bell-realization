from __future__ import annotations

import numpy as np
from scipy.linalg import expm

from .config import DampingConfig
from .state import abs2, apply_linear_operator, to_analyzer_basis


def build_damping_operator(phi_rad: float, config: DampingConfig) -> np.ndarray:
    cos_phi = np.cos(phi_rad)
    sin_phi = np.sin(phi_rad)
    rotation = np.array([[cos_phi, -sin_phi], [sin_phi, cos_phi]], dtype=np.float64)
    diagonal = np.diag([config.gamma_plus, config.gamma_minus]).astype(np.float64)
    return rotation @ diagonal @ rotation.T


def finite_window_operator(phi_rad: float, config: DampingConfig) -> np.ndarray:
    return expm(-build_damping_operator(phi_rad, config) * config.window_duration)


def analyzer_decay_factors(config: DampingConfig) -> np.ndarray:
    return np.exp(
        -np.array([config.gamma_plus, config.gamma_minus], dtype=np.float64)
        * config.window_duration
    )


def apply_finite_window(states: np.ndarray, phi_rad: float, config: DampingConfig) -> np.ndarray:
    return apply_linear_operator(states, finite_window_operator(phi_rad, config))


def evolve_with_diagnostics(
    states: np.ndarray,
    phi_rad: float,
    config: DampingConfig,
) -> dict[str, np.ndarray]:
    coords_before = to_analyzer_basis(states, phi_rad)
    states_after = apply_finite_window(states, phi_rad, config)
    coords_after = to_analyzer_basis(states_after, phi_rad)
    branch_loss = np.clip(abs2(coords_before) - abs2(coords_after), 0.0, None)

    return {
        "states_after": states_after,
        "coords_before": coords_before,
        "coords_after": coords_after,
        "branch_loss": branch_loss,
    }
