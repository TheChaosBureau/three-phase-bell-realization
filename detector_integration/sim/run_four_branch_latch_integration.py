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
from detector_integration.frontends.four_branch import four_branch_weights
from detector_integration.sim.metrics import chsh_metrics, four_branch_metrics, winner_frequency_summary

DEFAULT_CHSH_SETTINGS = {
    "a0b0": (0.0, 22.5),
    "a0b1": (0.0, -22.5),
    "a1b0": (45.0, 22.5),
    "a1b1": (45.0, -22.5),
}


def run_four_branch_latch_trials(
    state4,
    a_deg: float,
    b_deg: float,
    detector_params: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    n_trials: int,
    seed: int,
    envelope_params: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    latch_config: LatchArbiterConfig | None = None,
) -> dict[str, Any]:
    exact_weights = four_branch_weights(np.asarray(state4, dtype=np.complex128), a_deg=float(a_deg), b_deg=float(b_deg))
    rng = np.random.default_rng(seed)
    active_latch_config = validated_latch_arbiter_config(4) if latch_config is None else latch_config
    winners: list[int] = []
    event_time_rows: list[np.ndarray] = []
    pulse_time_rows: list[np.ndarray] = []
    tie_region_count = 0

    for _ in range(n_trials):
        event_times = np.full(4, np.inf, dtype=float)
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

    frequency_summary = winner_frequency_summary(winners, n_branches=4)
    metrics = four_branch_metrics(exact_weights, frequency_summary["frequencies"])
    closure = post_click_closure_placeholder(winners[-1] if winners else -1, 4)
    return {
        "a_deg": float(a_deg),
        "b_deg": float(b_deg),
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


def run_latch_enabled_chsh_trials(
    state4,
    detector_params: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    n_trials: int,
    seed: int,
    envelope_params: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    latch_config: LatchArbiterConfig | None = None,
    settings: Mapping[str, tuple[float, float]] | None = None,
) -> dict[str, Any]:
    active_settings = DEFAULT_CHSH_SETTINGS if settings is None else settings
    exact_correlators: dict[str, float] = {}
    empirical_correlators: dict[str, float] = {}
    rows: list[dict[str, Any]] = []

    for index, (label, (a_deg, b_deg)) in enumerate(active_settings.items()):
        result = run_four_branch_latch_trials(
            state4,
            a_deg=a_deg,
            b_deg=b_deg,
            detector_params=detector_params,
            n_trials=n_trials,
            seed=seed + 1_003 * index,
            envelope_params=envelope_params,
            latch_config=latch_config,
        )
        exact_correlators[label] = float(result["metrics"]["correlator_exact"])
        empirical_correlators[label] = float(result["metrics"]["correlator_empirical"])
        rows.append(
            {
                "label": label,
                "a_deg": a_deg,
                "b_deg": b_deg,
                "correlator_exact": result["metrics"]["correlator_exact"],
                "correlator_empirical": result["metrics"]["correlator_empirical"],
                "correlator_error": result["metrics"]["correlator_error"],
                "rms_error": result["metrics"]["rms_error"],
            }
        )

    return {
        "rows": rows,
        **chsh_metrics(exact_correlators, empirical_correlators),
    }
