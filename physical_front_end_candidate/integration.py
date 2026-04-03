from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict
from typing import Any

import numpy as np

from detector_integration.detectors import latch_first_event, resolve_branch_detector_params, simulate_branch_nucleation, validated_latch_arbiter_config
from detector_integration.sim.metrics import two_branch_metrics, winner_frequency_summary

from .export_interface import (
    HandoffExportConfig,
    PhysicalEnvelopeConfig,
    build_detector_handoff_envelopes,
    render_envelope_traces,
    resolve_envelope_config,
    resolve_handoff_export_config,
)
from .metrics import common_envelope_fidelity_metrics
from .two_branch_candidate import simulate_two_branch_physical_candidate


def run_two_branch_physical_handoff(
    state: np.ndarray,
    analyzer,
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    n_trials: int,
    seed: int,
    envelope_config: Mapping[str, Any] | None = None,
    export_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    candidate = simulate_two_branch_physical_candidate(state, analyzer, envelope_config=envelope_config)
    branch_labels = list(candidate["branch_labels"])
    physical_envelope_config = resolve_envelope_config(candidate["envelope_config"])
    handoff_config = resolve_handoff_export_config(export_config)
    detector_envelopes = build_detector_handoff_envelopes(
        candidate["branch_power_w"],
        time_s=candidate["time_s"],
        branch_labels=branch_labels,
        envelope_config=physical_envelope_config,
        export_config=handoff_config,
    )
    exported_branch_power = render_envelope_traces(detector_envelopes, sample_time_s=candidate["time_s"], branch_labels=branch_labels)
    exact_weights = np.array([candidate["exact_weight"][label] for label in branch_labels], dtype=float)
    rng = np.random.default_rng(seed)
    latch_config = validated_latch_arbiter_config(2)
    winners: list[int] = []
    event_time_rows: list[np.ndarray] = []

    for _ in range(n_trials):
        event_times = np.full(2, np.inf, dtype=float)
        for branch_index in range(2):
            branch_rng = np.random.default_rng(int(rng.integers(0, 2**32 - 1)))
            branch_detector = resolve_branch_detector_params(detector_spec, branch_index)
            click_time = simulate_branch_nucleation(branch_detector, 1.0, detector_envelopes[branch_index], branch_rng)
            if click_time is not None:
                event_times[branch_index] = click_time
        latch_result = latch_first_event(event_times, config=latch_config, rng=rng)
        winners.append(int(latch_result["winner_index"]))
        event_time_rows.append(event_times)

    frequency_summary = winner_frequency_summary(winners, n_branches=2)
    metrics = two_branch_metrics(exact_weights, frequency_summary["frequencies"])
    common_envelope = common_envelope_fidelity_metrics(branch_labels, exported_branch_power, candidate["exact_weight"])
    return {
        "candidate": candidate,
        "detector_envelopes": detector_envelopes,
        "export_config": asdict(handoff_config),
        "exported_branch_power": exported_branch_power,
        "exact_weights": exact_weights,
        "empirical_frequencies": frequency_summary["frequencies"],
        "winner_counts": frequency_summary["counts"],
        "decisive_fraction": frequency_summary["decisive_fraction"],
        "timeout_fraction": frequency_summary["timeout_fraction"],
        "metrics": metrics,
        "common_envelope": common_envelope,
        "event_times": np.asarray(event_time_rows, dtype=float),
    }
