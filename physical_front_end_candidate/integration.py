from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict
from typing import Any

import numpy as np

from detector_integration.detectors import latch_first_event, resolve_branch_detector_params, simulate_branch_nucleation, validated_latch_arbiter_config
from detector_integration.sim.metrics import chsh_metrics, four_branch_metrics, two_branch_metrics, winner_frequency_summary
from detector_integration.sim.run_four_branch_latch_integration import DEFAULT_CHSH_SETTINGS

from .boundary_calibration import resolved_calibrated_boundary_config
from .boundary_diagnosis import scale_trace_power, selected_handoff_export_config, trace_to_detector_envelopes, truncate_trace
from .export_interface import (
    HandoffExportConfig,
    PhysicalEnvelopeConfig,
    build_detector_handoff_envelopes,
    render_envelope_traces,
    resolve_envelope_config,
    resolve_handoff_export_config,
)
from .metrics import common_envelope_fidelity_metrics
from .four_branch_candidate import simulate_four_branch_physical_candidate
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


def _materialize_candidate_trace(
    candidate: Mapping[str, Any],
    *,
    export_config: Mapping[str, Any] | None = None,
    boundary_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    branch_labels = list(candidate["branch_labels"])
    physical_envelope_config = resolve_envelope_config(candidate["envelope_config"])
    handoff_config = selected_handoff_export_config() if export_config is None else resolve_handoff_export_config(export_config)
    detector_envelopes = build_detector_handoff_envelopes(
        candidate["branch_power_w"],
        time_s=candidate["time_s"],
        branch_labels=branch_labels,
        envelope_config=physical_envelope_config,
        export_config=handoff_config,
    )
    first_envelope = detector_envelopes[0]
    if first_envelope["kind"] in {"sampled", "sampled_linear"}:
        sample_time_s = np.asarray(first_envelope["time_s"], dtype=float)
    else:
        dt = max(float(first_envelope.get("dt", physical_envelope_config.dt_s)), 1e-6)
        t_max = float(first_envelope.get("t_max", physical_envelope_config.duration_s))
        sample_time_s = np.arange(0.0, t_max + dt, dt, dtype=float)
    exported_branch_power = render_envelope_traces(detector_envelopes, sample_time_s=sample_time_s, branch_labels=branch_labels)
    trace = {
        "candidate": candidate,
        "branch_labels": branch_labels,
        "time_s": sample_time_s.tolist(),
        "export_config": asdict(handoff_config),
        "exported_branch_power": exported_branch_power,
    }
    boundary = resolved_calibrated_boundary_config(boundary_config)
    trace = scale_trace_power(trace, boundary.gain)
    trace = truncate_trace(trace, boundary.exposure_s)
    trace["boundary_config"] = asdict(boundary)
    return trace


def run_four_branch_candidate_handoff(
    candidate: Mapping[str, Any],
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    n_trials: int,
    seed: int,
    boundary_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    trace = _materialize_candidate_trace(candidate, boundary_config=boundary_config)
    detector_envelopes = trace_to_detector_envelopes(trace)
    exact_weights = np.array([candidate["exact_weight"][label] for label in candidate["branch_labels"]], dtype=float)
    rng = np.random.default_rng(seed)
    latch_config = validated_latch_arbiter_config(4)
    winners: list[int] = []
    event_time_rows: list[np.ndarray] = []

    for _ in range(n_trials):
        event_times = np.full(4, np.inf, dtype=float)
        for branch_index in range(4):
            branch_rng = np.random.default_rng(int(rng.integers(0, 2**32 - 1)))
            branch_detector = resolve_branch_detector_params(detector_spec, branch_index)
            click_time = simulate_branch_nucleation(branch_detector, 1.0, detector_envelopes[branch_index], branch_rng)
            if click_time is not None:
                event_times[branch_index] = click_time
        latch_result = latch_first_event(event_times, config=latch_config, rng=rng)
        winners.append(int(latch_result["winner_index"]))
        event_time_rows.append(event_times)

    frequency_summary = winner_frequency_summary(winners, n_branches=4)
    metrics = four_branch_metrics(exact_weights, frequency_summary["frequencies"])
    return {
        "candidate": candidate,
        "trace": trace,
        "detector_envelopes": detector_envelopes,
        "export_config": dict(trace["export_config"]),
        "boundary_config": dict(trace["boundary_config"]),
        "exported_branch_power": dict(trace["exported_branch_power"]),
        "exact_weights": exact_weights,
        "empirical_frequencies": frequency_summary["frequencies"],
        "winner_counts": frequency_summary["counts"],
        "decisive_count": frequency_summary["decisive_count"],
        "timeout_count": frequency_summary["timeout_count"],
        "decisive_fraction": frequency_summary["decisive_fraction"],
        "timeout_fraction": frequency_summary["timeout_fraction"],
        "metrics": metrics,
        "event_times": np.asarray(event_time_rows, dtype=float),
    }


def run_four_branch_physical_handoff(
    state4: np.ndarray | None,
    *,
    a_deg: float,
    b_deg: float,
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    n_trials: int,
    seed: int,
    envelope_config: Mapping[str, Any] | None = None,
    boundary_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    candidate = simulate_four_branch_physical_candidate(state4, a_deg=a_deg, b_deg=b_deg, envelope_config=envelope_config)
    return run_four_branch_candidate_handoff(candidate, detector_spec, n_trials=n_trials, seed=seed, boundary_config=boundary_config)


def run_four_branch_physical_chsh(
    state4: np.ndarray | None,
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    n_trials: int,
    seed: int,
    envelope_config: Mapping[str, Any] | None = None,
    boundary_config: Mapping[str, Any] | None = None,
    settings: Mapping[str, tuple[float, float]] | None = None,
) -> dict[str, Any]:
    active_settings = DEFAULT_CHSH_SETTINGS if settings is None else settings
    exact_correlators: dict[str, float] = {}
    empirical_correlators: dict[str, float] = {}
    rows: list[dict[str, Any]] = []

    for index, (label, (a_deg, b_deg)) in enumerate(active_settings.items()):
        result = run_four_branch_physical_handoff(
            state4,
            a_deg=a_deg,
            b_deg=b_deg,
            detector_spec=detector_spec,
            n_trials=n_trials,
            seed=seed + 1_003 * index,
            envelope_config=envelope_config,
            boundary_config=boundary_config,
        )
        exact_correlators[label] = float(result["metrics"]["correlator_exact"])
        empirical_correlators[label] = float(result["metrics"]["correlator_empirical"])
        rows.append(
            {
                "label": label,
                "a_deg": a_deg,
                "b_deg": b_deg,
                "correlator_exact": float(result["metrics"]["correlator_exact"]),
                "correlator_empirical": float(result["metrics"]["correlator_empirical"]),
                "correlator_error": float(result["metrics"]["correlator_error"]),
                "winner_rms_error": float(result["metrics"]["rms_error"]),
                "decisive_fraction": float(result["decisive_fraction"]),
            }
        )

    return {
        "rows": rows,
        **chsh_metrics(exact_correlators, empirical_correlators),
    }
