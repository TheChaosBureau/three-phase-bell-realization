from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


def first_event_latch(event_times: np.ndarray) -> int:
    """
    Return the index of the first finite event time, or -1 if no branch fired.
    """
    values = np.asarray(event_times, dtype=float).reshape(-1)
    finite_values = np.where(np.isfinite(values), values, np.inf)
    if not np.isfinite(np.min(finite_values)):
        return -1
    return int(np.argmin(finite_values))


@dataclass(frozen=True)
class LatchArbiterConfig:
    """Timing contract for the latch-enabled detector integration layer."""

    input_delay_s: float = 1.10e-9
    settle_time_s: float = 1.55e-9
    tie_window_s: float = 0.25e-9
    branch_delay_offsets_s: tuple[float, ...] = ()
    branch_jitter_s: tuple[float, ...] = ()
    priority_order: tuple[int, ...] = ()


def validated_latch_arbiter_config(n_branches: int, *, timing_mismatch_rel: float = 0.0) -> LatchArbiterConfig:
    from detector_rig.config import DEFAULT_LATCH_RIG_CONFIG

    rig = DEFAULT_LATCH_RIG_CONFIG
    base_delay_s = 1e-9 * (rig.pickoff_delay_ns + rig.propagation_delay_ns)
    settle_time_s = 1e-9 * (rig.pickoff_delay_ns + rig.settle_time_ns)
    tie_window_s = 1e-9 * rig.tie_window_ns
    jitter_s = 1e-9 * rig.input_load_added_jitter_ns
    delay_skew = timing_mismatch_rel * base_delay_s
    branch_delay_offsets_s = tuple(delay_skew if index % 2 == 0 else -delay_skew for index in range(n_branches))
    branch_jitter_s = tuple(jitter_s for _ in range(n_branches))
    priority_order = tuple(range(n_branches))
    return LatchArbiterConfig(
        input_delay_s=base_delay_s,
        settle_time_s=settle_time_s,
        tie_window_s=tie_window_s,
        branch_delay_offsets_s=branch_delay_offsets_s,
        branch_jitter_s=branch_jitter_s,
        priority_order=priority_order,
    )


def _resolve_branch_values(values: tuple[float, ...], n_branches: int, default: float) -> np.ndarray:
    if not values:
        return np.full(n_branches, default, dtype=float)
    if len(values) != n_branches:
        raise ValueError(f"Expected {n_branches} branch values, got {len(values)}.")
    return np.asarray(values, dtype=float)


def _priority_rank(priority_order: tuple[int, ...], n_branches: int) -> dict[int, int]:
    order = priority_order if priority_order else tuple(range(n_branches))
    return {branch_index: rank for rank, branch_index in enumerate(order)}


def latch_first_event(
    event_times: np.ndarray,
    *,
    config: LatchArbiterConfig | None = None,
    rng: np.random.Generator | None = None,
) -> dict[str, Any]:
    values = np.asarray(event_times, dtype=float).reshape(-1)
    n_branches = int(values.size)
    active_config = LatchArbiterConfig() if config is None else config
    local_rng = np.random.default_rng() if rng is None else rng

    delay_offsets = _resolve_branch_values(active_config.branch_delay_offsets_s, n_branches, 0.0)
    jitter = _resolve_branch_values(active_config.branch_jitter_s, n_branches, 0.0)
    pulse_times = np.full(n_branches, np.inf, dtype=float)
    finite_mask = np.isfinite(values)
    if np.any(finite_mask):
        pulse_times[finite_mask] = values[finite_mask] + active_config.input_delay_s + delay_offsets[finite_mask]
        if np.any(jitter[finite_mask] > 0.0):
            pulse_times[finite_mask] += local_rng.normal(0.0, jitter[finite_mask])

    if not np.isfinite(np.min(pulse_times)):
        return {
            "winner_index": -1,
            "winner_valid": False,
            "pulse_times": pulse_times,
            "closure_active": False,
            "suppressed_indices": [],
            "tie_region": False,
            "settled_at_s": np.inf,
        }

    earliest = float(np.min(pulse_times))
    contender_indices = np.where(np.isfinite(pulse_times) & (pulse_times <= earliest + active_config.tie_window_s))[0]
    rank = _priority_rank(active_config.priority_order, n_branches)
    winner_index = min(contender_indices.tolist(), key=lambda branch_index: (rank.get(branch_index, branch_index), pulse_times[branch_index], branch_index))
    return {
        "winner_index": int(winner_index),
        "winner_valid": True,
        "pulse_times": pulse_times,
        "closure_active": True,
        "suppressed_indices": [index for index in range(n_branches) if index != int(winner_index)],
        "tie_region": bool(contender_indices.size > 1),
        "settled_at_s": earliest + active_config.settle_time_s,
    }


def post_click_closure_placeholder(winner_index: int, n_branches: int) -> dict[str, object]:
    """
    Placeholder post-click closure state for later drain/backaction models.
    """
    return {
        "winner_index": int(winner_index),
        "suppressed_indices": [index for index in range(n_branches) if index != winner_index],
        "closure_active": winner_index >= 0,
    }
