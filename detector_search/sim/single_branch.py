from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from detector_search.models.base import DetectorModel


def simulate_single_trial(
    model: DetectorModel,
    params: dict[str, float],
    P_abs: float,
    dt: float,
    t_max: float,
    rng,
) -> float | None:
    """
    Run one trial until a click occurs or the trial times out.
    """
    configured = model.with_params(params)
    if configured.__class__.sample_click_time is not DetectorModel.sample_click_time:
        return configured.sample_click_time(P_abs=P_abs, t_max=t_max, rng=rng)

    state = configured.reset(rng)
    n_steps = int(np.ceil(t_max / dt))
    for step_index in range(n_steps):
        state, event = configured.step(state, P_abs=P_abs, dt=dt, rng=rng)
        if event:
            return (step_index + 1) * dt
    return None


def estimate_rate(click_times: Sequence[float], timeout_count: int, t_max: float) -> float:
    observed_time = float(np.sum(click_times)) + timeout_count * t_max
    if observed_time <= 0.0:
        return 0.0
    return len(click_times) / observed_time


def simulate_many_trials(
    model: DetectorModel,
    params: dict[str, float],
    P_abs: float,
    n_trials: int,
    dt: float,
    t_max: float,
    seed: int,
) -> dict[str, float | int | np.ndarray]:
    """
    Simulate multiple single-branch trials and estimate the event rate.
    """
    rng = np.random.default_rng(seed)
    click_times: list[float] = []
    timeout_count = 0
    for _ in range(n_trials):
        click_time = simulate_single_trial(model, params, P_abs=P_abs, dt=dt, t_max=t_max, rng=rng)
        if click_time is None:
            timeout_count += 1
            continue
        click_times.append(click_time)

    click_time_array = np.asarray(click_times, dtype=float)
    rate_estimate = estimate_rate(click_time_array, timeout_count=timeout_count, t_max=t_max)
    return {
        "click_times": click_time_array,
        "timeout_count": timeout_count,
        "n_clicks": int(click_time_array.size),
        "timeout_fraction": timeout_count / max(n_trials, 1),
        "rate_estimate": rate_estimate,
    }
