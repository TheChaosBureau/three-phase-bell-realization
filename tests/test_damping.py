from __future__ import annotations

import numpy as np

from sim.config import DampingConfig, SourceConfig
from sim.damping import apply_finite_window
from sim.state import rotation_matrix, sample_source_states, to_analyzer_basis


def test_rotation_matrix_round_trip() -> None:
    phi = np.deg2rad(37.5)
    state = np.array([1.0 + 0.0j, 0.25 - 0.5j])
    rotated = to_analyzer_basis(state, phi)
    restored = rotation_matrix(phi) @ rotated
    assert np.allclose(restored, state)


def test_isotropic_damping_is_angle_invariant() -> None:
    state = np.array([1.0 + 0.0j, 0.5 + 0.25j])
    config = DampingConfig(gamma_plus=2.0, gamma_minus=2.0, window_fraction=0.25)

    updated_a = apply_finite_window(state, np.deg2rad(12.5), config)
    updated_b = apply_finite_window(state, np.deg2rad(67.5), config)

    assert np.allclose(updated_a, updated_b)


def test_damping_reduces_norm() -> None:
    source = sample_source_states(SourceConfig(sample_count=16))
    config = DampingConfig(gamma_plus=4.0, gamma_minus=1.0, window_fraction=0.25)
    updated = apply_finite_window(source, np.deg2rad(45.0), config)
    assert np.all(np.linalg.norm(updated, axis=1) <= np.linalg.norm(source, axis=1) + 1e-12)
