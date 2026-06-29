from __future__ import annotations

import math
from typing import Any

from .config import BRANCHES, DetectorParams


def apply_post_click_attenuation(
    branch_amplitudes: dict[str, complex],
    detector_state: dict[str, Any],
    params: DetectorParams,
) -> dict[str, complex]:
    winner = detector_state["winner"]
    if winner == "none":
        return dict(branch_amplitudes)

    attenuated: dict[str, complex] = {}
    for branch, amplitude in branch_amplitudes.items():
        if branch == winner:
            scale = math.exp(-params.gamma_g * detector_state[f"g_{branch}"] * params.dt)
        else:
            scale = math.exp(-params.gamma_h * detector_state["h"] * params.dt)
        attenuated[branch] = amplitude * scale
    return attenuated


def advance_closure_state(
    detector_state: dict[str, Any],
    params: DetectorParams,
) -> tuple[dict[str, Any], dict[str, float]]:
    deltas: dict[str, float] = {}
    prev_h = float(detector_state["h"])
    new_h = prev_h + (params.dt / params.tau_h) * (
        -prev_h + params.gain_h * sum(detector_state[f"y_{branch}"] for branch in BRANCHES)
    )
    detector_state["h"] = float(new_h)
    deltas["h"] = abs(new_h - prev_h)

    for branch in BRANCHES:
        g_key = f"g_{branch}"
        prev_g = float(detector_state[g_key])
        new_g = prev_g + (params.dt / params.tau_g) * (
            -prev_g + params.gain_g * detector_state[f"y_{branch}"]
        )
        detector_state[g_key] = float(new_g)
        deltas[g_key] = abs(new_g - prev_g)

        rfr_key = f"rfr_{branch}"
        prev_rfr = float(detector_state[rfr_key])
        new_rfr = prev_rfr + (params.dt / params.tau_r) * (
            -prev_rfr + params.gain_r * detector_state[f"y_{branch}"]
        )
        detector_state[rfr_key] = float(new_rfr)
        deltas[rfr_key] = abs(new_rfr - prev_rfr)

    return detector_state, deltas


def completion_window_satisfied(
    branch_amplitudes: dict[str, complex],
    detector_state: dict[str, Any],
    closure_deltas: dict[str, float],
    min_post_winner_steps: int,
    post_winner_steps: int,
    loser_intensity_threshold: float = 1e-6,
    closure_delta_threshold: float = 1e-6,
) -> bool:
    winner = detector_state["winner"]
    if winner == "none" or post_winner_steps < min_post_winner_steps:
        return False

    loser_intensities = [
        float(abs(branch_amplitudes[branch]) ** 2)
        for branch in BRANCHES
        if branch != winner
    ]
    if any(intensity >= loser_intensity_threshold for intensity in loser_intensities):
        return False
    return max(closure_deltas.values(), default=0.0) < closure_delta_threshold
