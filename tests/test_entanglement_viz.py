import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import entanglement_viz as viz


def test_breathing_envelope_stays_positive_and_bounded():
    samples = [viz.breathing_envelope(t) for t in np.linspace(0.0, viz.T_MAX, 200)]
    assert min(samples) >= 1.0 - viz.BREATH_AMP - 1e-9
    assert max(samples) <= 1.0 + viz.BREATH_AMP + 1e-9
    assert min(samples) > 0.0


def test_handedness_flips_helix_winding_without_changing_radius():
    t_values = np.linspace(0.0, viz.T_MAX, 40)
    x_pos, y_pos = viz.helix_coords(t_values, handedness=1, branch_sign=1, radius_scale=1.0)
    x_neg, y_neg = viz.helix_coords(t_values, handedness=-1, branch_sign=1, radius_scale=1.0)

    assert np.allclose(x_pos, x_neg)
    assert np.allclose(y_pos, -y_neg)
    assert np.allclose(np.hypot(x_pos, y_pos), np.hypot(x_neg, y_neg))


def test_inverted_surface_is_complementary_to_upright_surface():
    phi = np.pi / 7.0
    height_scale = 1.15
    _, _, z_up = viz.analyzer_surface(phi, 0.5, inverted=False, height_scale=height_scale)
    _, _, z_down = viz.analyzer_surface(phi, 0.5, inverted=True, height_scale=height_scale)

    assert np.allclose(z_up + z_down, np.full_like(z_up, 1.0))


def test_viewpoint_flip_is_a_half_turn():
    phi = np.radians(35.0)
    flipped = viz.viewpoint_flipped_angle(phi)
    assert np.isclose((flipped - phi) % (2 * np.pi), np.pi)


def test_complementary_surface_sum_is_flat():
    theta = np.linspace(0.0, 2 * np.pi, 256)
    summed = viz.complementary_surface_sum(theta, np.pi / 5.0, measurement_time=0.5, height_scale=1.0)
    assert np.allclose(summed, np.full_like(theta, 1.0), atol=1e-9)


def test_viewpoint_flip_preserves_surface_shape():
    theta = np.linspace(0.0, 2 * np.pi, 256)
    phi = np.pi / 5.0
    flipped_phi = viz.viewpoint_flipped_angle(phi)
    z_ref = viz.analyzer_surface_height(theta, phi, 0.5, inverted=False, height_scale=1.2)
    z_partner = viz.analyzer_surface_height(theta, flipped_phi, 0.5, inverted=False, height_scale=1.2)

    assert np.allclose(z_ref, z_partner, atol=1e-9)
