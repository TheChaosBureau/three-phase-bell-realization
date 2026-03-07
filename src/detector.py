from __future__ import annotations
import random

from .types import AnalyzerOutputs, DetectorState


def branch_powers(outputs: AnalyzerOutputs) -> tuple[float, float]:
    return (abs(outputs.u) ** 2, abs(outputs.v) ** 2)


def step_detector(
    state: DetectorState,
    p_plus: float,
    p_minus: float,
    eta: float,
    kappa: float,
    threshold: float,
    dt: float,
    t_now: float,
) -> DetectorState:
    if state.clicked:
        return state

    state.xi_plus += dt * (eta * p_plus - kappa * state.xi_plus)
    state.xi_minus += dt * (eta * p_minus - kappa * state.xi_minus)

    plus_hit = state.xi_plus >= threshold
    minus_hit = state.xi_minus >= threshold

    if plus_hit and not minus_hit:
        state.clicked = True
        state.outcome = +1
        state.click_time = t_now
    elif minus_hit and not plus_hit:
        state.clicked = True
        state.outcome = -1
        state.click_time = t_now
    elif plus_hit and minus_hit:
        # tie-breaker: larger integrated energy wins
        state.clicked = True
        state.outcome = +1 if state.xi_plus >= state.xi_minus else -1
        state.click_time = t_now

    return state


def sample_from_joint_probs(probs: dict[str, float], rng: random.Random) -> tuple[int, int]:
    labels = ["++", "+-", "-+", "--"]
    weights = [probs[k] for k in labels]
    label = rng.choices(labels, weights=weights, k=1)[0]

    if label == "++":
        return (+1, +1)
    if label == "+-":
        return (+1, -1)
    if label == "-+":
        return (-1, +1)
    return (-1, -1)