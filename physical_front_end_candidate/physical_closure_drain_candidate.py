from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from typing import Any

import numpy as np

from .closure_path import (
    ClosureInterpretationConfig,
    build_post_click_candidate_cache,
    closure_interpretations,
    future_branch_energy_from_cache,
    simulate_four_branch_candidate_pre_click_race,
    simulate_post_click_closure,
)


@dataclass(frozen=True)
class PhysicalClosureDrainConfig:
    topology_option: str = "A"
    topology_name: str = "common_inhibit_rail_winner_gated_shunt_drain"
    control_node_name: str = "V_inhibit"
    winner_select_name: str = "SEL_WIN[k]"
    trial_complete_name: str = "trial_complete"
    supply_v: float = 1.8
    shared_capacitance_f: float = 1.0
    control_tau_s: float = 0.1
    inhibit_onset_delay_s: float = 0.0
    inhibit_saturation_fraction: float = 1.0
    branch_coupling_scale_s: float = 0.24
    winner_branch_boost: float = 1.2
    loser_attenuation_beta: float = 8.5
    loser_residual_floor_fraction: float = 0.002
    clamp_coupling_strength: float = 0.8
    winner_drain_g_on_s: float = 2.0
    winner_drain_tau_s: float = 0.08
    winner_drain_saturation_fraction: float = 1.0
    shared_leak_g_s: float = 0.08
    clamp_reference_g_on_s: float = 0.7
    completion_threshold_frac: float = 0.02
    completion_current_threshold_a: float = 0.01


def preferred_common_mode_interpretation() -> ClosureInterpretationConfig:
    for interpretation in closure_interpretations():
        if interpretation.name == "common_mode_inhibit_winner_drain":
            return interpretation
    raise RuntimeError("Preferred common-mode inhibit + winner drain interpretation is unavailable.")


def build_physical_closure_candidate_cache(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return build_post_click_candidate_cache(
        time_s=candidate["time_s"],
        branch_power_w=candidate["branch_power_w"],
        branch_labels=candidate["branch_labels"],
    )


def default_physical_closure_drain_config() -> PhysicalClosureDrainConfig:
    reduced = preferred_common_mode_interpretation()
    return PhysicalClosureDrainConfig(
        control_tau_s=1.0 / max(reduced.alpha_z_s, 1e-9),
        winner_branch_boost=reduced.winner_branch_gain,
        loser_attenuation_beta=reduced.loser_beta,
        winner_drain_g_on_s=2.0,
        winner_drain_tau_s=1.0 / max(reduced.alpha_z_s * 1.25, 1e-9),
        completion_threshold_frac=reduced.completion_threshold_frac,
    )


def reduced_to_physical_mapping_summary(
    config: PhysicalClosureDrainConfig | None = None,
    *,
    reduced_interpretation: ClosureInterpretationConfig | None = None,
) -> dict[str, Any]:
    resolved = default_physical_closure_drain_config() if config is None else config
    reduced = preferred_common_mode_interpretation() if reduced_interpretation is None else reduced_interpretation
    return {
        "topology_option": resolved.topology_option,
        "topology_name": resolved.topology_name,
        "reduced_interpretation": reduced.name,
        "control_node_name": resolved.control_node_name,
        "winner_select_name": resolved.winner_select_name,
        "trial_complete_name": resolved.trial_complete_name,
        "reduced_closure_variable": reduced.closure_variable_name,
        "control_tau_s": float(resolved.control_tau_s),
        "inhibit_onset_delay_s": float(resolved.inhibit_onset_delay_s),
        "inhibit_saturation_fraction": float(resolved.inhibit_saturation_fraction),
        "reduced_alpha_z_s": float(reduced.alpha_z_s),
        "winner_drain_g_on_s": float(resolved.winner_drain_g_on_s),
        "winner_drain_tau_s": float(resolved.winner_drain_tau_s),
        "winner_drain_saturation_fraction": float(resolved.winner_drain_saturation_fraction),
        "reduced_winner_drain_rate_s": float(reduced.winner_drain_rate_s),
        "loser_attenuation_beta": float(resolved.loser_attenuation_beta),
        "loser_residual_floor_fraction": float(resolved.loser_residual_floor_fraction),
        "clamp_coupling_strength": float(resolved.clamp_coupling_strength),
        "clamp_reference_g_on_s": float(resolved.clamp_reference_g_on_s),
        "reduced_loser_beta": float(reduced.loser_beta),
        "winner_branch_boost": float(resolved.winner_branch_boost),
        "reduced_winner_branch_gain": float(reduced.winner_branch_gain),
        "completion_threshold_frac": float(resolved.completion_threshold_frac),
        "reduced_completion_threshold_frac": float(reduced.completion_threshold_frac),
        "mapping_note": "Common inhibit rail maps the reduced Z(t), loser branch conductances collapse with the same monotone control, and a winner-selected shunt drain dominates post-click discharge.",
    }


def simulate_physical_closure_drain(
    *,
    time_s: Sequence[float],
    branch_power_w: Mapping[str, Sequence[float]],
    branch_labels: Sequence[str],
    winner_index: int,
    winner_valid: bool,
    capture_time_s: float,
    config: PhysicalClosureDrainConfig | None = None,
    candidate_cache: Mapping[str, Any] | None = None,
    include_traces: bool = True,
) -> dict[str, Any]:
    resolved = default_physical_closure_drain_config() if config is None else config
    values_t = np.asarray(time_s, dtype=float).reshape(-1)
    labels = list(branch_labels)
    zero_trace = np.zeros_like(values_t)
    zero_branch_map = {label: zero_trace.tolist() for label in labels}

    if not winner_valid or winner_index < 0 or winner_index >= len(labels):
        payload = {
            "control_node_name": resolved.control_node_name,
            "winner_branch_post_click_energy_j": 0.0,
            "winner_drain_total_energy_j": 0.0,
            "shared_leak_total_energy_j": 0.0,
            "loser_post_click_energy_j": {label: 0.0 for label in labels},
            "initial_remaining_energy_j": 0.0,
            "winner_index": int(winner_index),
            "winner_label": None,
            "winner_drain_path_count": 0,
            "closure_active": False,
            "activation_count": 0,
            "trial_complete": False,
            "trial_complete_time_s": float("inf"),
            "trial_complete_reason": "inactive",
            "monotonic_remaining_energy": True,
            "terminal_loser_suppression_mean": 0.0,
        }
        if include_traces:
            payload.update(
                {
                    "time_s": values_t.tolist(),
                    "closure_variable": zero_trace.tolist(),
                    "common_inhibit_v": zero_trace.tolist(),
                    "shared_node_voltage_v": zero_trace.tolist(),
                    "winner_drain_enable_by_branch": dict(zero_branch_map),
                    "winner_drain_power_w": zero_trace.tolist(),
                    "winner_drain_current_a": zero_trace.tolist(),
                    "winner_drain_energy_j": zero_trace.tolist(),
                    "remaining_shared_energy_j": zero_trace.tolist(),
                    "trial_complete_signal": zero_trace.tolist(),
                    "winner_branch_power_w": zero_trace.tolist(),
                    "loser_branch_power_w": dict(zero_branch_map),
                    "loser_suppression": dict(zero_branch_map),
                    "loser_clamp_conductance_s": dict(zero_branch_map),
                }
            )
        return payload

    winner_label = labels[winner_index]
    cache = (
        build_post_click_candidate_cache(time_s=values_t, branch_power_w=branch_power_w, branch_labels=labels)
        if candidate_cache is None
        else dict(candidate_cache)
    )
    future_energy_by_branch = future_branch_energy_from_cache(cache, capture_time_s=float(capture_time_s))
    initial_remaining_energy = float(sum(future_energy_by_branch.values()))
    if initial_remaining_energy <= 1e-18:
        unit_step = np.where(values_t >= capture_time_s, 1.0, 0.0)
        winner_enable = {
            label: (unit_step.tolist() if label == winner_label else zero_trace.tolist())
            for label in labels
        }
        payload = {
            "control_node_name": resolved.control_node_name,
            "winner_branch_post_click_energy_j": 0.0,
            "winner_drain_total_energy_j": 0.0,
            "shared_leak_total_energy_j": 0.0,
            "loser_post_click_energy_j": {label: 0.0 for label in labels if label != winner_label},
            "initial_remaining_energy_j": 0.0,
            "winner_index": int(winner_index),
            "winner_label": winner_label,
            "winner_drain_path_count": 1,
            "closure_active": True,
            "activation_count": 1,
            "trial_complete": True,
            "trial_complete_time_s": float(capture_time_s),
            "trial_complete_reason": "shared_energy_below_threshold",
            "monotonic_remaining_energy": True,
            "terminal_loser_suppression_mean": 1.0 if len(labels) > 1 else 0.0,
        }
        if include_traces:
            payload.update(
                {
                    "time_s": values_t.tolist(),
                    "closure_variable": unit_step.tolist(),
                    "common_inhibit_v": (resolved.supply_v * unit_step).tolist(),
                    "shared_node_voltage_v": zero_trace.tolist(),
                    "winner_drain_enable_by_branch": winner_enable,
                    "winner_drain_power_w": zero_trace.tolist(),
                    "winner_drain_current_a": zero_trace.tolist(),
                    "winner_drain_energy_j": zero_trace.tolist(),
                    "remaining_shared_energy_j": zero_trace.tolist(),
                    "trial_complete_signal": unit_step.tolist(),
                    "winner_branch_power_w": zero_trace.tolist(),
                    "loser_branch_power_w": {label: zero_trace.tolist() for label in labels if label != winner_label},
                    "loser_suppression": {label: unit_step.tolist() for label in labels if label != winner_label},
                    "loser_clamp_conductance_s": {label: (resolved.clamp_reference_g_on_s * unit_step).tolist() for label in labels if label != winner_label},
                }
            )
        return payload

    base_shares = {
        label: future_energy_by_branch[label] / max(initial_remaining_energy, 1e-18)
        for label in labels
    }
    dt = np.asarray(cache["dt"], dtype=float)

    closure_variable = np.zeros_like(values_t)
    common_inhibit_v = np.zeros_like(values_t)
    shared_node_voltage_v = np.zeros_like(values_t)
    remaining_energy = np.full_like(values_t, initial_remaining_energy)
    winner_drain_power = np.zeros_like(values_t)
    winner_drain_current = np.zeros_like(values_t)
    winner_drain_energy = np.zeros_like(values_t)
    trial_complete_signal = np.zeros_like(values_t)
    winner_branch_power = np.zeros_like(values_t)
    loser_branch_power = {label: np.zeros_like(values_t) for label in labels if label != winner_label}
    loser_suppression = {label: np.zeros_like(values_t) for label in labels if label != winner_label}
    loser_clamp_conductance = {label: np.zeros_like(values_t) for label in labels if label != winner_label}
    winner_enable = {
        label: np.zeros_like(values_t)
        for label in labels
    }

    completed = False
    completed_time = float(values_t[-1])
    completed_reason = "end_of_trace"
    winner_branch_energy = 0.0
    shared_leak_energy = 0.0
    loser_energy = {label: 0.0 for label in labels if label != winner_label}

    active_indices = np.where(values_t >= float(capture_time_s))[0]
    if active_indices.size:
        dt_active = np.maximum(dt[active_indices], 0.0)
        effective_delay = np.maximum(values_t[active_indices] - float(capture_time_s) - float(resolved.inhibit_onset_delay_s), 0.0)
        z_active = resolved.inhibit_saturation_fraction * (
            1.0 - np.exp(-effective_delay / max(resolved.control_tau_s, 1e-12))
        )
        z_active = np.clip(z_active, 0.0, 1.0)
        drain_gate = resolved.winner_drain_saturation_fraction * (
            1.0 - np.exp(-effective_delay / max(resolved.winner_drain_tau_s, 1e-12))
        )
        drain_gate = np.clip(drain_gate, 0.0, 1.5)
        closure_variable[active_indices] = z_active
        common_inhibit_v[active_indices] = resolved.supply_v * z_active
        winner_enable[winner_label][active_indices] = drain_gate

        branch_conductance_arrays: dict[str, np.ndarray] = {}
        for label in labels:
            base_g = resolved.branch_coupling_scale_s * base_shares[label]
            if label == winner_label:
                branch_conductance_arrays[label] = base_g * (1.0 + resolved.winner_branch_boost * z_active)
            else:
                loser_decay = np.exp(
                    -(resolved.loser_attenuation_beta + resolved.clamp_coupling_strength * resolved.clamp_reference_g_on_s) * z_active
                )
                branch_conductance_arrays[label] = base_g * (
                    resolved.loser_residual_floor_fraction
                    + (1.0 - resolved.loser_residual_floor_fraction) * loser_decay
                )
                loser_suppression[label][active_indices] = 1.0 - branch_conductance_arrays[label] / max(base_g, 1e-18)
                loser_clamp_conductance[label][active_indices] = resolved.clamp_reference_g_on_s * z_active

        g_winner_drain = resolved.winner_drain_g_on_s * drain_gate
        g_total = np.full_like(z_active, resolved.shared_leak_g_s)
        for values in branch_conductance_arrays.values():
            g_total = g_total + values
        g_total = np.maximum(g_total + g_winner_drain, 1e-18)

        decay_factor = np.exp(-2.0 * g_total * dt_active / max(resolved.shared_capacitance_f, 1e-18))
        energy_before = initial_remaining_energy * np.concatenate(([1.0], np.cumprod(decay_factor[:-1])))
        energy_after = energy_before * decay_factor
        energy_released = energy_before - energy_after

        shared_voltage = np.sqrt(np.maximum(2.0 * energy_before / max(resolved.shared_capacitance_f, 1e-18), 0.0))
        shared_node_voltage_v[active_indices] = shared_voltage
        winner_drain_current[active_indices] = shared_voltage * g_winner_drain

        winner_branch_share = branch_conductance_arrays[winner_label] / g_total
        winner_drain_share = g_winner_drain / g_total
        shared_leak_share = resolved.shared_leak_g_s / g_total

        winner_branch_increment = energy_released * winner_branch_share
        winner_branch_energy = float(np.sum(winner_branch_increment))
        winner_branch_power[active_indices] = np.divide(winner_branch_increment, np.maximum(dt_active, 1e-18))

        drain_increment = energy_released * winner_drain_share
        winner_drain_power[active_indices] = np.divide(drain_increment, np.maximum(dt_active, 1e-18))
        winner_drain_energy[active_indices] = np.cumsum(drain_increment)

        for label in labels:
            if label == winner_label:
                continue
            branch_increment = energy_released * branch_conductance_arrays[label] / g_total
            loser_energy[label] = float(np.sum(branch_increment))
            loser_branch_power[label][active_indices] = np.divide(branch_increment, np.maximum(dt_active, 1e-18))

        shared_leak_energy = float(np.sum(energy_released * shared_leak_share))
        remaining_energy[active_indices] = energy_after

        completion_hits = np.where(
            (energy_after <= resolved.completion_threshold_frac * initial_remaining_energy)
            & (winner_drain_current[active_indices] <= resolved.completion_current_threshold_a)
        )[0]
        if completion_hits.size:
            completed = True
            completed_time = float(values_t[active_indices[completion_hits[0]]])
            completed_reason = "shared_energy_and_drain_current_below_threshold"
            trial_complete_signal[active_indices[completion_hits[0]:]] = 1.0

    post_capture_mask = active_indices
    monotonic = bool(np.all(np.diff(remaining_energy[post_capture_mask]) <= 1e-12)) if post_capture_mask.size else True
    terminal_loser_suppression_mean = (
        float(np.mean([values[active_indices[-1]] for values in loser_suppression.values()]))
        if loser_suppression and active_indices.size
        else 0.0
    )
    payload = {
        "control_node_name": resolved.control_node_name,
        "winner_branch_post_click_energy_j": winner_branch_energy,
        "winner_drain_total_energy_j": float(winner_drain_energy[-1]),
        "shared_leak_total_energy_j": shared_leak_energy,
        "loser_post_click_energy_j": loser_energy,
        "initial_remaining_energy_j": initial_remaining_energy,
        "winner_index": int(winner_index),
        "winner_label": winner_label,
        "winner_drain_path_count": 1,
        "closure_active": True,
        "activation_count": 1,
        "trial_complete": completed,
        "trial_complete_time_s": completed_time,
        "trial_complete_reason": completed_reason,
        "monotonic_remaining_energy": monotonic,
        "terminal_loser_suppression_mean": terminal_loser_suppression_mean,
    }
    if include_traces:
        payload.update(
            {
                "time_s": values_t.tolist(),
                "closure_variable": closure_variable.tolist(),
                "common_inhibit_v": common_inhibit_v.tolist(),
                "shared_node_voltage_v": shared_node_voltage_v.tolist(),
                "winner_drain_enable_by_branch": {label: values.tolist() for label, values in winner_enable.items()},
                "winner_drain_power_w": winner_drain_power.tolist(),
                "winner_drain_current_a": winner_drain_current.tolist(),
                "winner_drain_energy_j": winner_drain_energy.tolist(),
                "remaining_shared_energy_j": remaining_energy.tolist(),
                "trial_complete_signal": trial_complete_signal.tolist(),
                "winner_branch_power_w": winner_branch_power.tolist(),
                "loser_branch_power_w": {label: values.tolist() for label, values in loser_branch_power.items()},
                "loser_suppression": {label: values.tolist() for label, values in loser_suppression.items()},
                "loser_clamp_conductance_s": {label: values.tolist() for label, values in loser_clamp_conductance.items()},
            }
        )
    return payload


def run_four_branch_candidate_with_physical_closure(
    candidate: Mapping[str, Any],
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    n_trials: int,
    seed: int,
    config: PhysicalClosureDrainConfig | None = None,
    reduced_interpretation: ClosureInterpretationConfig | None = None,
    race_result: Mapping[str, Any] | None = None,
    candidate_cache: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    resolved = default_physical_closure_drain_config() if config is None else config
    reduced = preferred_common_mode_interpretation() if reduced_interpretation is None else reduced_interpretation
    race = (
        simulate_four_branch_candidate_pre_click_race(candidate, detector_spec, n_trials=n_trials, seed=seed)
        if race_result is None
        else dict(race_result)
    )
    frequency_summary = race["frequency_summary"]
    event_times = np.asarray(race["event_times"], dtype=float)
    latch_results = list(race["latch_results"])
    cache = (
        build_post_click_candidate_cache(
            time_s=candidate["time_s"],
            branch_power_w=candidate["branch_power_w"],
            branch_labels=candidate["branch_labels"],
        )
        if candidate_cache is None
        else dict(candidate_cache)
    )
    example_trial: dict[str, Any] | None = None
    total_initial_remaining = 0.0
    total_winner_drain = 0.0
    total_loser_energy = 0.0
    total_winner_fraction = 0.0
    total_loser_fraction = 0.0
    total_completion_count = 0
    total_completion_time = 0.0
    total_reduced_completion_count = 0
    total_reduced_completion_time = 0.0
    all_monotonic = True
    total_terminal_loser_suppression = 0.0
    terminal_loser_suppression_count = 0
    total_winner_drain_path_count = 0.0
    total_reduced_winner_fraction = 0.0
    total_reduced_loser_fraction = 0.0
    activated_trial_count = 0
    total_activated_winner_fraction = 0.0
    total_activated_loser_fraction = 0.0
    total_activated_terminal_loser_suppression = 0.0

    for trial_index, latch_result in enumerate(latch_results):
        physical = simulate_physical_closure_drain(
            time_s=candidate["time_s"],
            branch_power_w=candidate["branch_power_w"],
            branch_labels=candidate["branch_labels"],
            winner_index=int(latch_result["winner_index"]),
            winner_valid=bool(latch_result["winner_valid"]),
            capture_time_s=float(latch_result["settled_at_s"]),
            config=resolved,
            candidate_cache=cache,
            include_traces=False,
        )
        reduced_row = simulate_post_click_closure(
            time_s=candidate["time_s"],
            branch_power_w=candidate["branch_power_w"],
            branch_labels=candidate["branch_labels"],
            winner_index=int(latch_result["winner_index"]),
            winner_valid=bool(latch_result["winner_valid"]),
            capture_time_s=float(latch_result["settled_at_s"]),
            interpretation=reduced,
            candidate_cache=cache,
            include_traces=False,
        )
        initial_remaining = float(physical["initial_remaining_energy_j"])
        winner_drain = float(physical["winner_drain_total_energy_j"])
        loser_energy = float(sum(physical["loser_post_click_energy_j"].values()))
        reduced_winner = float(reduced_row["winner_drain_total_energy_j"])
        reduced_loser = float(sum(reduced_row["loser_post_click_energy_j"].values()))
        denom = max(initial_remaining, 1e-18)
        total_initial_remaining += initial_remaining
        total_winner_drain += winner_drain
        total_loser_energy += loser_energy
        total_winner_fraction += winner_drain / denom
        total_loser_fraction += loser_energy / denom
        total_reduced_winner_fraction += reduced_winner / denom
        total_reduced_loser_fraction += reduced_loser / denom
        total_winner_drain_path_count += float(physical["winner_drain_path_count"])
        all_monotonic = all_monotonic and bool(physical["monotonic_remaining_energy"])
        if physical["winner_index"] >= 0 and physical["winner_label"] is not None:
            activated_trial_count += 1
            total_activated_winner_fraction += winner_drain / denom
            total_activated_loser_fraction += loser_energy / denom
            total_terminal_loser_suppression += float(physical["terminal_loser_suppression_mean"])
            total_activated_terminal_loser_suppression += float(physical["terminal_loser_suppression_mean"])
            terminal_loser_suppression_count += 1
        if bool(physical["trial_complete"]):
            total_completion_count += 1
            total_completion_time += float(physical["trial_complete_time_s"])
        if bool(reduced_row["trial_complete"]):
            total_reduced_completion_count += 1
            total_reduced_completion_time += float(reduced_row["trial_complete_time_s"])
        if example_trial is None and physical["closure_active"]:
            physical_trace = simulate_physical_closure_drain(
                time_s=candidate["time_s"],
                branch_power_w=candidate["branch_power_w"],
                branch_labels=candidate["branch_labels"],
                winner_index=int(latch_result["winner_index"]),
                winner_valid=bool(latch_result["winner_valid"]),
                capture_time_s=float(latch_result["settled_at_s"]),
                config=resolved,
                candidate_cache=cache,
                include_traces=True,
            )
            reduced_trace = simulate_post_click_closure(
                time_s=candidate["time_s"],
                branch_power_w=candidate["branch_power_w"],
                branch_labels=candidate["branch_labels"],
                winner_index=int(latch_result["winner_index"]),
                winner_valid=bool(latch_result["winner_valid"]),
                capture_time_s=float(latch_result["settled_at_s"]),
                interpretation=reduced,
                candidate_cache=cache,
                include_traces=True,
            )
            example_trial = {
                "latch_result": dict(latch_result),
                "physical": physical_trace,
                "reduced": reduced_trace,
                "event_times": event_times[trial_index].tolist(),
            }

    transparency_shift = np.zeros_like(np.asarray(frequency_summary["frequencies"], dtype=float))
    trial_count = max(len(latch_results), 1)
    mean_winner_fraction = total_winner_fraction / trial_count
    mean_loser_fraction = total_loser_fraction / trial_count
    mean_reduced_winner_fraction = total_reduced_winner_fraction / trial_count
    mean_reduced_loser_fraction = total_reduced_loser_fraction / trial_count
    winner_path_activation_rate = activated_trial_count / trial_count
    mean_activated_winner_fraction = total_activated_winner_fraction / activated_trial_count if activated_trial_count > 0 else 0.0
    mean_activated_loser_fraction = total_activated_loser_fraction / activated_trial_count if activated_trial_count > 0 else 0.0
    mean_activated_terminal_loser_suppression = (
        total_activated_terminal_loser_suppression / activated_trial_count if activated_trial_count > 0 else 0.0
    )
    completion_rate = total_completion_count / trial_count
    reduced_completion_rate = total_reduced_completion_count / trial_count
    mean_completion_time = total_completion_time / total_completion_count if total_completion_count > 0 else float("inf")
    mean_reduced_completion_time = (
        total_reduced_completion_time / total_reduced_completion_count if total_reduced_completion_count > 0 else float("inf")
    )

    if np.isinf(mean_completion_time) and np.isinf(mean_reduced_completion_time):
        completion_time_abs_diff = 0.0
    else:
        completion_time_abs_diff = float(abs(mean_completion_time - mean_reduced_completion_time))

    comparison_metrics = {
        "winner_fraction_abs_diff": float(abs(mean_winner_fraction - mean_reduced_winner_fraction)),
        "loser_fraction_abs_diff": float(abs(mean_loser_fraction - mean_reduced_loser_fraction)),
        "completion_rate_abs_diff": float(abs(completion_rate - reduced_completion_rate)),
        "completion_time_abs_diff": completion_time_abs_diff,
    }
    if example_trial is not None:
        physical = example_trial["physical"]
        reduced_row = example_trial["reduced"]
        comparison_metrics["example_closure_rms_diff"] = float(
            np.sqrt(
                np.mean(
                    np.square(
                        np.asarray(physical["closure_variable"], dtype=float)
                        - np.asarray(reduced_row["closure_variable"], dtype=float)
                    )
                )
            )
        )
        comparison_metrics["example_remaining_energy_rms_diff"] = float(
            np.sqrt(
                np.mean(
                    np.square(
                        np.asarray(physical["remaining_shared_energy_j"], dtype=float)
                        - np.asarray(reduced_row["remaining_shared_energy_j"], dtype=float)
                    )
                )
            )
        )

    return {
        "candidate": candidate,
        "pre_click_race": race,
        "config": asdict(resolved),
        "reduced_mapping": reduced_to_physical_mapping_summary(resolved, reduced_interpretation=reduced),
        "empirical_frequencies": frequency_summary["frequencies"],
        "winner_counts": frequency_summary["counts"],
        "decisive_count": frequency_summary["decisive_count"],
        "timeout_count": frequency_summary["timeout_count"],
        "decisive_fraction": frequency_summary["decisive_fraction"],
        "timeout_fraction": frequency_summary["timeout_fraction"],
        "metrics": dict(race["metrics"]),
        "comparison_metrics": comparison_metrics,
        "closure_metrics": {
            "trial_count": trial_count,
            "pre_click_transparency_rms_shift": float(np.sqrt(np.mean(np.square(transparency_shift)))),
            "mean_initial_remaining_energy_j": total_initial_remaining / trial_count,
            "mean_winner_drain_energy_j": total_winner_drain / trial_count,
            "mean_loser_post_click_energy_j": total_loser_energy / trial_count,
            "mean_winner_drain_fraction": mean_winner_fraction,
            "mean_loser_fraction": mean_loser_fraction,
            "winner_path_activation_rate": winner_path_activation_rate,
            "activated_trial_count": activated_trial_count,
            "mean_activated_winner_drain_fraction": mean_activated_winner_fraction,
            "mean_activated_loser_fraction": mean_activated_loser_fraction,
            "mean_activated_terminal_loser_suppression": mean_activated_terminal_loser_suppression,
            "completion_rate": completion_rate,
            "mean_completion_time_s": mean_completion_time,
            "monotonic_remaining_energy": all_monotonic,
            "mean_terminal_loser_suppression": (
                total_terminal_loser_suppression / terminal_loser_suppression_count
                if terminal_loser_suppression_count > 0
                else 0.0
            ),
            "mean_winner_drain_path_count": total_winner_drain_path_count / trial_count,
        },
        "example_trial": example_trial,
    }


def tuned_physical_closure_drain_config(**updates: float) -> PhysicalClosureDrainConfig:
    return replace(default_physical_closure_drain_config(), **updates)
