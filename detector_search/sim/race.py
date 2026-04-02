from __future__ import annotations

import numpy as np

from detector_search.models.base import DetectorModel

from .single_branch import simulate_single_trial


def simulate_two_branch_race(
    model: DetectorModel,
    params1: dict[str, float],
    params2: dict[str, float],
    P1: float,
    P2: float,
    dt: float,
    t_max: float,
    rng,
) -> tuple[int, float | None, float | None]:
    """
    Run a two-branch race and return the winner plus individual click times.
    """
    seed1 = int(rng.integers(0, 2**32 - 1))
    seed2 = int(rng.integers(0, 2**32 - 1))
    t1 = simulate_single_trial(model, params1, P_abs=P1, dt=dt, t_max=t_max, rng=np.random.default_rng(seed1))
    t2 = simulate_single_trial(model, params2, P_abs=P2, dt=dt, t_max=t_max, rng=np.random.default_rng(seed2))

    if t1 is None and t2 is None:
        return 0, None, None
    if t1 is None:
        return 2, None, t2
    if t2 is None:
        return 1, t1, None
    if t1 < t2:
        return 1, t1, t2
    if t2 < t1:
        return 2, t1, t2
    return 0, t1, t2


def simulate_many_races(
    model: DetectorModel,
    params1: dict[str, float],
    params2: dict[str, float],
    P1: float,
    P2: float,
    n_trials: int,
    dt: float,
    t_max: float,
    seed: int,
) -> dict[str, float | int]:
    """
    Estimate empirical two-branch winner frequencies from many races.
    """
    rng = np.random.default_rng(seed)
    winner_counts = {0: 0, 1: 0, 2: 0}
    for _ in range(n_trials):
        winner, _, _ = simulate_two_branch_race(
            model,
            params1=params1,
            params2=params2,
            P1=P1,
            P2=P2,
            dt=dt,
            t_max=t_max,
            rng=rng,
        )
        winner_counts[winner] += 1

    decisive = winner_counts[1] + winner_counts[2]
    p1_win = winner_counts[1] / decisive if decisive else 0.5
    return {
        "winner_0": winner_counts[0],
        "winner_1": winner_counts[1],
        "winner_2": winner_counts[2],
        "decisive_fraction": decisive / max(n_trials, 1),
        "p1_win": p1_win,
    }
