from __future__ import annotations

import math
from typing import Any

import numpy as np

from .config import BRANCHES, DetectorParams


def initial_detector_state(params: DetectorParams) -> dict[str, Any]:
    state: dict[str, Any] = {
        "winner": "none",
        "tie_broken": False,
        "dark_triggered": False,
        "h": 0.0,
    }
    for branch in BRANCHES:
        state[f"m_{branch}"] = params.m_bias
        state[f"y_{branch}"] = 0
        state[f"g_{branch}"] = 0.0
        state[f"rfr_{branch}"] = params.reset_value
    return state


def detector_step(
    branch_amplitudes: dict[str, complex],
    detector_state: dict[str, Any],
    params: DetectorParams,
    rng: np.random.Generator,
) -> tuple[dict[str, Any], str | None]:
    if params.mode == "ou_threshold":
        return _detector_step_ou(branch_amplitudes, detector_state, params, rng)
    if params.mode == "poisson_linear":
        return _detector_step_poisson(branch_amplitudes, detector_state, params, rng)
    raise ValueError(f"unknown detector mode: {params.mode}")


def _latch_winner(
    detector_state: dict[str, Any],
    firing_branches: list[str],
    dark_flags: dict[str, bool],
    rng: np.random.Generator,
) -> tuple[dict[str, Any], str]:
    winner = firing_branches[0]
    if len(firing_branches) > 1:
        winner = firing_branches[int(rng.integers(0, len(firing_branches)))]
        detector_state["tie_broken"] = True
    detector_state["winner"] = winner
    detector_state["dark_triggered"] = bool(dark_flags.get(winner, False))
    for branch in BRANCHES:
        detector_state[f"y_{branch}"] = int(branch == winner)
    return detector_state, winner


def _detector_step_ou(
    branch_amplitudes: dict[str, complex],
    detector_state: dict[str, Any],
    params: DetectorParams,
    rng: np.random.Generator,
) -> tuple[dict[str, Any], str | None]:
    if detector_state["winner"] != "none":
        return detector_state, None

    dark_prob = 1.0 - math.exp(-params.dark_rate * params.dt)
    sqrt_dt = math.sqrt(params.dt)
    firing: list[str] = []
    dark_flags: dict[str, bool] = {}

    for branch in BRANCHES:
        amplitude = branch_amplitudes[branch]
        intensity = float(abs(amplitude) ** 2)
        m_key = f"m_{branch}"
        refr_key = f"rfr_{branch}"
        drift = (
            -(detector_state[m_key] - params.m_bias) / params.tau_m
            + params.beta * intensity
            - params.chi_h * detector_state["h"]
            - params.chi_r * detector_state[refr_key]
        )
        detector_state[m_key] = float(
            detector_state[m_key]
            + drift * params.dt
            + params.sigma * sqrt_dt * float(rng.normal())
        )
        dark_fired = bool(rng.random() < dark_prob)
        threshold_fired = detector_state[m_key] >= params.threshold
        if dark_fired or threshold_fired:
            firing.append(branch)
            dark_flags[branch] = dark_fired

    if not firing:
        return detector_state, None
    detector_state, winner = _latch_winner(detector_state, firing, dark_flags, rng)
    return detector_state, winner


def _detector_step_poisson(
    branch_amplitudes: dict[str, complex],
    detector_state: dict[str, Any],
    params: DetectorParams,
    rng: np.random.Generator,
) -> tuple[dict[str, Any], str | None]:
    if detector_state["winner"] != "none":
        return detector_state, None

    firing: list[str] = []
    for branch in BRANCHES:
        intensity = float(abs(branch_amplitudes[branch]) ** 2)
        rate = params.dark_rate + params.alpha_poisson * intensity
        prob = 1.0 - math.exp(-rate * params.dt)
        if rng.random() < prob:
            firing.append(branch)

    if not firing:
        return detector_state, None

    winner = firing[0]
    if len(firing) > 1:
        winner = firing[int(rng.integers(0, len(firing)))]
        detector_state["tie_broken"] = True
    detector_state["winner"] = winner
    detector_state["dark_triggered"] = bool(rng.random() < (1.0 - math.exp(-params.dark_rate * params.dt)))
    for branch in BRANCHES:
        detector_state[f"y_{branch}"] = int(branch == winner)
    return detector_state, winner
