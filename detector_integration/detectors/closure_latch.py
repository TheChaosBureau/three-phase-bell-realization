from __future__ import annotations

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


def post_click_closure_placeholder(winner_index: int, n_branches: int) -> dict[str, object]:
    """
    Placeholder post-click closure state for later drain/backaction models.
    """
    return {
        "winner_index": int(winner_index),
        "suppressed_indices": [index for index in range(n_branches) if index != winner_index],
        "closure_active": winner_index >= 0,
    }
