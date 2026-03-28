from __future__ import annotations

import numpy as np
import pandas as pd

from sim.metrics import (
    branch_weights,
    complementary_residual_quality,
    compute_chsh,
    residual_branch_quality,
)


def test_branch_weights_and_purity_for_pure_branch() -> None:
    post = np.array([[1.0 + 0.0j, 0.0 + 0.0j], [0.0 + 0.0j, 2.0 + 0.0j]])
    weights = branch_weights(post)
    q_plus, q_minus, purity = residual_branch_quality(post)

    assert np.allclose(weights, np.array([[1.0, 0.0], [0.0, 1.0]]))
    assert np.allclose(q_plus, np.array([1.0, 0.0]))
    assert np.allclose(q_minus, np.array([0.0, 1.0]))
    assert np.allclose(purity, np.array([1.0, 1.0]))


def test_complementary_quality_tracks_opposite_of_extracted_branch() -> None:
    pre = np.array([[2.0 + 0.0j, 0.5 + 0.0j]])
    post = np.array([[0.1 + 0.0j, 1.0 + 0.0j]])
    value = complementary_residual_quality(pre, post)
    assert value[0] > 0.98


def test_compute_chsh_uses_canonical_angle_set() -> None:
    frame = pd.DataFrame(
        [
            {"rule": "residual_classifier", "window_fraction": 0.25, "anisotropy_ratio": 4.0, "angle_a_deg": 0.0, "angle_b_deg": 22.5, "correlation": 0.7},
            {"rule": "residual_classifier", "window_fraction": 0.25, "anisotropy_ratio": 4.0, "angle_a_deg": 0.0, "angle_b_deg": 67.5, "correlation": -0.1},
            {"rule": "residual_classifier", "window_fraction": 0.25, "anisotropy_ratio": 4.0, "angle_a_deg": 45.0, "angle_b_deg": 22.5, "correlation": 0.6},
            {"rule": "residual_classifier", "window_fraction": 0.25, "anisotropy_ratio": 4.0, "angle_a_deg": 45.0, "angle_b_deg": 67.5, "correlation": 0.5},
        ]
    )
    summary = compute_chsh(frame)
    assert np.isclose(summary.iloc[0]["chsh"], abs(0.7 - (-0.1) + 0.6 + 0.5))
