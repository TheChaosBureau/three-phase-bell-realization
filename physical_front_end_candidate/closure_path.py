from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from detector_integration.detectors import latch_first_event, resolve_branch_detector_params, simulate_branch_nucleation, validated_latch_arbiter_config
from detector_integration.sim.metrics import four_branch_metrics, winner_frequency_summary

from .boundary_diagnosis import trace_to_detector_envelopes
from .integration import materialize_candidate_trace


@dataclass(frozen=True)
class ClosureInterpretationConfig:
    name: str
    label: str
    closure_variable_name: str
    description: str
    alpha_z_s: float
    idle_drain_rate_s: float
    winner_drain_rate_s: float
    loser_beta: float
    winner_branch_gain: float
    winner_drain_gain: float
    completion_threshold_frac: float


def closure_interpretations() -> tuple[ClosureInterpretationConfig, ...]:
    return (
        ClosureInterpretationConfig(
            name="winner_gated_common_shunt",
            label="Winner-gated common shunt",
            closure_variable_name="Z",
            description="Winner-valid enables a shared shunt whose closure state redirects common energy into a winner-associated drain.",
            alpha_z_s=9.0,
            idle_drain_rate_s=0.15,
            winner_drain_rate_s=2.1,
            loser_beta=7.0,
            winner_branch_gain=1.15,
            winner_drain_gain=5.0,
            completion_threshold_frac=0.02,
        ),
        ClosureInterpretationConfig(
            name="shared_bias_collapse",
            label="Shared bias collapse",
            closure_variable_name="Z",
            description="Winner-valid collapses a shared bias node, suppressing losers while opening a winner drain path.",
            alpha_z_s=6.0,
            idle_drain_rate_s=0.10,
            winner_drain_rate_s=1.7,
            loser_beta=6.0,
            winner_branch_gain=1.05,
            winner_drain_gain=4.2,
            completion_threshold_frac=0.025,
        ),
        ClosureInterpretationConfig(
            name="common_mode_inhibit_winner_drain",
            label="Common-mode inhibit + winner drain",
            closure_variable_name="Z",
            description="A common-mode inhibit line rises after capture, heavily suppressing losers and strongly enabling a winner-only drain.",
            alpha_z_s=10.0,
            idle_drain_rate_s=0.18,
            winner_drain_rate_s=2.4,
            loser_beta=8.5,
            winner_branch_gain=1.2,
            winner_drain_gain=5.8,
            completion_threshold_frac=0.018,
        ),
        ClosureInterpretationConfig(
            name="zero_sequence_closure",
            label="Zero-sequence-like closure",
            closure_variable_name="Z",
            description="A zero-sequence-like closure state rises globally, attenuating non-winning branches while steering residual energy to the winner channel.",
            alpha_z_s=7.0,
            idle_drain_rate_s=0.12,
            winner_drain_rate_s=1.9,
            loser_beta=7.8,
            winner_branch_gain=1.12,
            winner_drain_gain=5.4,
            completion_threshold_frac=0.022,
        ),
        ClosureInterpretationConfig(
            name="coupled_port_recombination_drain",
            label="Coupled-port recombination drain",
            closure_variable_name="Z",
            description="Winner capture activates a recombination-like drain coupled to the shared ports, leaving only a small suppressed loser residual.",
            alpha_z_s=8.0,
            idle_drain_rate_s=0.16,
            winner_drain_rate_s=2.0,
            loser_beta=7.2,
            winner_branch_gain=1.1,
            winner_drain_gain=5.1,
            completion_threshold_frac=0.02,
        ),
    )


def _future_branch_energy(
    time_s: np.ndarray,
    branch_power_w: Mapping[str, Sequence[float]],
    *,
    branch_labels: Sequence[str],
    capture_time_s: float,
) -> dict[str, float]:
    if capture_time_s >= float(time_s[-1]):
        return {label: 0.0 for label in branch_labels}
    mask = time_s >= capture_time_s
    sampled_time = time_s[mask]
    if sampled_time.size == 0 or sampled_time[0] > capture_time_s:
        sampled_time = np.insert(sampled_time, 0, capture_time_s)
    energies: dict[str, float] = {}
    for label in branch_labels:
        power = np.asarray(branch_power_w[label], dtype=float)
        sampled_power = np.interp(sampled_time, time_s, power)
        energies[label] = float(np.trapezoid(sampled_power, x=sampled_time))
    return energies


def simulate_post_click_closure(
    *,
    time_s: Sequence[float],
    branch_power_w: Mapping[str, Sequence[float]],
    branch_labels: Sequence[str],
    winner_index: int,
    winner_valid: bool,
    capture_time_s: float,
    interpretation: ClosureInterpretationConfig,
) -> dict[str, Any]:
    values_t = np.asarray(time_s, dtype=float).reshape(-1)
    labels = list(branch_labels)
    if not winner_valid or winner_index < 0 or winner_index >= len(labels):
        zero_trace = np.zeros_like(values_t)
        return {
            "time_s": values_t.tolist(),
            "activation_count": 0,
            "closure_active": False,
            "winner_index": int(winner_index),
            "winner_label": None,
            "closure_variable": zero_trace.tolist(),
            "remaining_shared_energy_j": zero_trace.tolist(),
            "winner_drain_power_w": zero_trace.tolist(),
            "winner_drain_energy_j": zero_trace.tolist(),
            "loser_suppression": {label: zero_trace.tolist() for label in labels},
            "loser_post_click_energy_j": {label: 0.0 for label in labels},
            "winner_branch_post_click_energy_j": 0.0,
            "winner_drain_total_energy_j": 0.0,
            "initial_remaining_energy_j": 0.0,
            "trial_complete": False,
            "trial_complete_time_s": float("inf"),
            "monotonic_remaining_energy": True,
        }

    winner_label = labels[winner_index]
    future_energies = _future_branch_energy(values_t, branch_power_w, branch_labels=labels, capture_time_s=float(capture_time_s))
    initial_remaining_energy = float(sum(future_energies.values()))
    if initial_remaining_energy <= 1e-18:
        return {
            "time_s": values_t.tolist(),
            "activation_count": 1,
            "closure_active": True,
            "winner_index": int(winner_index),
            "winner_label": winner_label,
            "closure_variable": np.where(values_t >= capture_time_s, 1.0, 0.0).tolist(),
            "remaining_shared_energy_j": np.zeros_like(values_t).tolist(),
            "winner_drain_power_w": np.zeros_like(values_t).tolist(),
            "winner_drain_energy_j": np.zeros_like(values_t).tolist(),
            "loser_suppression": {label: np.zeros_like(values_t).tolist() for label in labels if label != winner_label},
            "loser_post_click_energy_j": {label: 0.0 for label in labels if label != winner_label},
            "winner_branch_post_click_energy_j": 0.0,
            "winner_drain_total_energy_j": 0.0,
            "initial_remaining_energy_j": 0.0,
            "trial_complete": True,
            "trial_complete_time_s": float(capture_time_s),
            "monotonic_remaining_energy": True,
        }

    base_shares = {label: future_energies[label] / initial_remaining_energy for label in labels}
    dt = np.diff(values_t, append=float(values_t[-1]))
    dt[-1] = dt[-2] if dt.size > 1 else 0.0

    z_trace = np.zeros_like(values_t)
    remaining_energy = np.zeros_like(values_t)
    winner_drain_power = np.zeros_like(values_t)
    winner_drain_energy = np.zeros_like(values_t)
    loser_suppression = {label: np.zeros_like(values_t) for label in labels if label != winner_label}
    loser_energy = {label: 0.0 for label in labels if label != winner_label}
    winner_branch_energy = 0.0
    current_z = 0.0
    current_w = initial_remaining_energy
    completed_time = float(values_t[-1])
    completed = False

    for index, time_value in enumerate(values_t):
        remaining_energy[index] = current_w
        if time_value < capture_time_s:
            continue
        dt_step = max(float(dt[index]), 0.0)
        current_z = 1.0 - (1.0 - current_z) * np.exp(-interpretation.alpha_z_s * dt_step)
        z_trace[index] = current_z

        release_rate = interpretation.idle_drain_rate_s + interpretation.winner_drain_rate_s * current_z
        energy_released = current_w * (1.0 - np.exp(-release_rate * dt_step)) if dt_step > 0.0 else 0.0

        loser_strengths = {
            label: base_shares[label] * np.exp(-interpretation.loser_beta * current_z)
            for label in labels
            if label != winner_label
        }
        winner_branch_strength = base_shares[winner_label] * (1.0 + interpretation.winner_branch_gain * current_z)
        winner_drain_strength = interpretation.winner_drain_gain * current_z
        total_strength = winner_branch_strength + winner_drain_strength + sum(loser_strengths.values())
        total_strength = max(total_strength, 1e-18)

        winner_branch_share = winner_branch_strength / total_strength
        winner_drain_share = winner_drain_strength / total_strength
        winner_branch_energy += energy_released * winner_branch_share
        drain_increment = energy_released * winner_drain_share
        winner_drain_power[index] = drain_increment / max(dt_step, 1e-18) if dt_step > 0.0 else 0.0
        winner_drain_energy[index] = (winner_drain_energy[index - 1] if index > 0 else 0.0) + drain_increment

        for label, strength in loser_strengths.items():
            loser_suppression[label][index] = 1.0 - strength / max(base_shares[label], 1e-18)
            loser_energy[label] += energy_released * strength / total_strength
            if index > 0 and loser_suppression[label][index] <= 0.0:
                loser_suppression[label][index] = loser_suppression[label][index - 1]

        current_w = max(current_w - energy_released, 0.0)
        remaining_energy[index] = current_w
        if not completed and current_w <= interpretation.completion_threshold_frac * initial_remaining_energy:
            completed = True
            completed_time = float(time_value)

    monotonic = bool(np.all(np.diff(remaining_energy[np.where(values_t >= capture_time_s)[0]]) <= 1e-12)) if np.any(values_t >= capture_time_s) else True
    return {
        "time_s": values_t.tolist(),
        "activation_count": 1,
        "closure_active": True,
        "winner_index": int(winner_index),
        "winner_label": winner_label,
        "closure_variable": z_trace.tolist(),
        "remaining_shared_energy_j": remaining_energy.tolist(),
        "winner_drain_power_w": winner_drain_power.tolist(),
        "winner_drain_energy_j": winner_drain_energy.tolist(),
        "loser_suppression": {label: values.tolist() for label, values in loser_suppression.items()},
        "loser_post_click_energy_j": loser_energy,
        "winner_branch_post_click_energy_j": winner_branch_energy,
        "winner_drain_total_energy_j": float(winner_drain_energy[-1]),
        "initial_remaining_energy_j": initial_remaining_energy,
        "trial_complete": completed,
        "trial_complete_time_s": completed_time,
        "monotonic_remaining_energy": monotonic,
    }


def run_four_branch_candidate_with_closure(
    candidate: Mapping[str, Any],
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    interpretation: ClosureInterpretationConfig,
    n_trials: int,
    seed: int,
    race_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    race = (
        simulate_four_branch_candidate_pre_click_race(candidate, detector_spec, n_trials=n_trials, seed=seed)
        if race_result is None
        else dict(race_result)
    )
    trace = race["trace"]
    detector_envelopes = race["detector_envelopes"]
    exact_weights = np.asarray(race["exact_weights"], dtype=float)
    frequency_summary = race["frequency_summary"]
    event_time_rows = np.asarray(race["event_times"], dtype=float)
    latch_results = list(race["latch_results"])
    closure_rows: list[dict[str, Any]] = []
    example_trial: dict[str, Any] | None = None

    for trial_index, latch_result in enumerate(latch_results):
        closure = simulate_post_click_closure(
            time_s=candidate["time_s"],
            branch_power_w=candidate["branch_power_w"],
            branch_labels=candidate["branch_labels"],
            winner_index=int(latch_result["winner_index"]),
            winner_valid=bool(latch_result["winner_valid"]),
            capture_time_s=float(latch_result["settled_at_s"]),
            interpretation=interpretation,
        )
        closure_rows.append(closure)
        if example_trial is None and closure["closure_active"]:
            example_trial = {
                "latch_result": dict(latch_result),
                "closure": closure,
                "event_times": event_time_rows[trial_index].tolist(),
            }

    initial_remaining = np.asarray([row["initial_remaining_energy_j"] for row in closure_rows], dtype=float)
    winner_drain = np.asarray([row["winner_drain_total_energy_j"] for row in closure_rows], dtype=float)
    loser_energy = np.asarray([sum(row["loser_post_click_energy_j"].values()) for row in closure_rows], dtype=float)
    complete_mask = np.asarray([bool(row["trial_complete"]) for row in closure_rows], dtype=bool)
    completion_times = np.asarray([float(row["trial_complete_time_s"]) for row in closure_rows], dtype=float)
    transparency_shift = np.zeros_like(np.asarray(frequency_summary["frequencies"], dtype=float))
    return {
        "candidate": candidate,
        "trace": trace,
        "detector_envelopes": detector_envelopes,
        "interpretation": asdict(interpretation),
        "exact_weights": exact_weights,
        "empirical_frequencies": frequency_summary["frequencies"],
        "winner_counts": frequency_summary["counts"],
        "decisive_count": frequency_summary["decisive_count"],
        "timeout_count": frequency_summary["timeout_count"],
        "decisive_fraction": frequency_summary["decisive_fraction"],
        "timeout_fraction": frequency_summary["timeout_fraction"],
        "metrics": dict(race["metrics"]),
        "baseline": {
            "empirical_frequencies": list(frequency_summary["frequencies"]),
            "metrics": dict(race["metrics"]),
            "transparency_shift": transparency_shift,
        },
        "closure_rows": closure_rows,
        "closure_metrics": {
            "activation_rate": float(np.mean([float(row["closure_active"]) for row in closure_rows])),
            "mean_initial_remaining_energy_j": float(np.mean(initial_remaining)),
            "mean_winner_drain_energy_j": float(np.mean(winner_drain)),
            "mean_loser_post_click_energy_j": float(np.mean(loser_energy)),
            "mean_winner_drain_fraction": float(np.mean(np.divide(winner_drain, np.maximum(initial_remaining, 1e-18)))),
            "mean_loser_fraction": float(np.mean(np.divide(loser_energy, np.maximum(initial_remaining, 1e-18)))),
            "completion_rate": float(np.mean(complete_mask)),
            "mean_completion_time_s": float(np.mean(completion_times[complete_mask])) if np.any(complete_mask) else float("inf"),
            "monotonic_remaining_energy": bool(all(bool(row["monotonic_remaining_energy"]) for row in closure_rows)),
            "pre_click_transparency_rms_shift": float(np.sqrt(np.mean(np.square(transparency_shift)))),
        },
        "event_times": event_time_rows,
        "example_trial": example_trial,
        "pre_click_race": race,
    }


def simulate_four_branch_candidate_pre_click_race(
    candidate: Mapping[str, Any],
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    n_trials: int,
    seed: int,
) -> dict[str, Any]:
    trace = materialize_candidate_trace(candidate)
    detector_envelopes = trace_to_detector_envelopes(trace)
    exact_weights = np.array([candidate["exact_weight"][label] for label in candidate["branch_labels"]], dtype=float)
    rng = np.random.default_rng(seed)
    latch_config = validated_latch_arbiter_config(len(candidate["branch_labels"]))
    winners: list[int] = []
    event_time_rows: list[np.ndarray] = []
    latch_results: list[dict[str, Any]] = []

    for _ in range(n_trials):
        event_times = np.full(len(candidate["branch_labels"]), np.inf, dtype=float)
        for branch_index in range(len(candidate["branch_labels"])):
            branch_rng = np.random.default_rng(int(rng.integers(0, 2**32 - 1)))
            detector_params = resolve_branch_detector_params(detector_spec, branch_index)
            click_time = simulate_branch_nucleation(detector_params, 1.0, detector_envelopes[branch_index], branch_rng)
            if click_time is not None:
                event_times[branch_index] = click_time
        latch_result = latch_first_event(event_times, config=latch_config, rng=rng)
        winners.append(int(latch_result["winner_index"]))
        event_time_rows.append(event_times)
        latch_results.append(
            {
                "winner_index": int(latch_result["winner_index"]),
                "winner_valid": bool(latch_result["winner_valid"]),
                "settled_at_s": float(latch_result["settled_at_s"]),
            }
        )

    frequency_summary = winner_frequency_summary(winners, n_branches=len(candidate["branch_labels"]))
    metrics = four_branch_metrics(exact_weights, frequency_summary["frequencies"])
    return {
        "candidate": candidate,
        "trace": trace,
        "detector_envelopes": detector_envelopes,
        "exact_weights": exact_weights,
        "frequency_summary": frequency_summary,
        "winners": winners,
        "metrics": metrics,
        "latch_results": latch_results,
        "event_times": np.asarray(event_time_rows, dtype=float),
    }
