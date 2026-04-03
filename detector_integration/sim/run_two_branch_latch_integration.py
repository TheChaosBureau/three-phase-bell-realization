from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from detector_integration.detectors.closure_latch import (
    LatchArbiterConfig,
    latch_first_event,
    post_click_closure_placeholder,
    validated_latch_arbiter_config,
)
from detector_integration.detectors.shot_trigger_adapter import (
    resolve_branch_detector_params,
    resolve_branch_envelope_params,
    simulate_branch_nucleation,
)
from detector_integration.frontends.two_branch import two_branch_weights
from detector_integration.sim.metrics import two_branch_metrics, winner_frequency_summary


def run_two_branch_latch_trials(
    state,
    analyzer,
    detector_params: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    n_trials: int,
    seed: int,
    envelope_params: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    latch_config: LatchArbiterConfig | None = None,
) -> dict[str, Any]:
    exact_weights = two_branch_weights(np.asarray(state, dtype=np.complex128), analyzer)
    rng = np.random.default_rng(seed)
    active_latch_config = validated_latch_arbiter_config(2) if latch_config is None else latch_config
    winners: list[int] = []
    event_time_rows: list[np.ndarray] = []
    pulse_time_rows: list[np.ndarray] = []
    tie_region_count = 0

    for _ in range(n_trials):
        event_times = np.full(2, np.inf, dtype=float)
        for branch_index, weight in enumerate(exact_weights):
            branch_rng = np.random.default_rng(int(rng.integers(0, 2**32 - 1)))
            branch_detector = resolve_branch_detector_params(detector_params, branch_index)
            branch_envelope = resolve_branch_envelope_params(envelope_params, branch_index)
            click_time = simulate_branch_nucleation(branch_detector, float(weight), branch_envelope, branch_rng)
            if click_time is not None:
                event_times[branch_index] = click_time

        latch_result = latch_first_event(event_times, config=active_latch_config, rng=rng)
        winners.append(int(latch_result["winner_index"]))
        event_time_rows.append(event_times)
        pulse_time_rows.append(np.asarray(latch_result["pulse_times"], dtype=float))
        tie_region_count += int(bool(latch_result["tie_region"]))

    frequency_summary = winner_frequency_summary(winners, n_branches=2)
    metrics = two_branch_metrics(exact_weights, frequency_summary["frequencies"])
    closure = post_click_closure_placeholder(winners[-1] if winners else -1, 2)
    return {
        "exact_weights": exact_weights,
        "empirical_frequencies": frequency_summary["frequencies"],
        "winner_counts": frequency_summary["counts"],
        "decisive_count": frequency_summary["decisive_count"],
        "timeout_count": frequency_summary["timeout_count"],
        "decisive_fraction": frequency_summary["decisive_fraction"],
        "timeout_fraction": frequency_summary["timeout_fraction"],
        "metrics": metrics,
        "event_times": np.asarray(event_time_rows, dtype=float),
        "pulse_times": np.asarray(pulse_time_rows, dtype=float),
        "tie_region_fraction": tie_region_count / max(n_trials, 1),
        "latch_config": active_latch_config,
        "closure": closure,
    }
