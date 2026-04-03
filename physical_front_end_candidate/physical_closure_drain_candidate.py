from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from .closure_path import (
    ClosureInterpretationConfig,
    closure_interpretations,
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
    branch_coupling_scale_s: float = 0.24
    winner_branch_boost: float = 1.2
    loser_attenuation_beta: float = 8.5
    winner_drain_g_on_s: float = 2.0
    shared_leak_g_s: float = 0.08
    clamp_reference_g_on_s: float = 0.7
    completion_threshold_frac: float = 0.02
    completion_current_threshold_a: float = 0.01


def preferred_common_mode_interpretation() -> ClosureInterpretationConfig:
    for interpretation in closure_interpretations():
        if interpretation.name == "common_mode_inhibit_winner_drain":
            return interpretation
    raise RuntimeError("Preferred common-mode inhibit + winner drain interpretation is unavailable.")


def default_physical_closure_drain_config() -> PhysicalClosureDrainConfig:
    reduced = preferred_common_mode_interpretation()
    return PhysicalClosureDrainConfig(
        control_tau_s=1.0 / max(reduced.alpha_z_s, 1e-9),
        winner_branch_boost=reduced.winner_branch_gain,
        loser_attenuation_beta=reduced.loser_beta,
        winner_drain_g_on_s=2.0,
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
        "reduced_alpha_z_s": float(reduced.alpha_z_s),
        "winner_drain_g_on_s": float(resolved.winner_drain_g_on_s),
        "reduced_winner_drain_rate_s": float(reduced.winner_drain_rate_s),
        "loser_attenuation_beta": float(resolved.loser_attenuation_beta),
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
) -> dict[str, Any]:
    resolved = default_physical_closure_drain_config() if config is None else config
    values_t = np.asarray(time_s, dtype=float).reshape(-1)
    labels = list(branch_labels)
    zero_trace = np.zeros_like(values_t)
    zero_branch_map = {label: zero_trace.tolist() for label in labels}

    if not winner_valid or winner_index < 0 or winner_index >= len(labels):
        return {
            "time_s": values_t.tolist(),
            "control_node_name": resolved.control_node_name,
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
            "winner_branch_post_click_energy_j": 0.0,
            "winner_drain_total_energy_j": 0.0,
            "shared_leak_total_energy_j": 0.0,
            "loser_branch_power_w": dict(zero_branch_map),
            "loser_suppression": dict(zero_branch_map),
            "loser_clamp_conductance_s": dict(zero_branch_map),
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
        }

    winner_label = labels[winner_index]
    future_energy_by_branch: dict[str, float] = {}
    sampled_mask = values_t >= float(capture_time_s)
    sampled_time = values_t[sampled_mask]
    if sampled_time.size == 0 or sampled_time[0] > capture_time_s:
        sampled_time = np.insert(sampled_time, 0, float(capture_time_s))
    for label in labels:
        power = np.asarray(branch_power_w[label], dtype=float)
        sampled_power = np.interp(sampled_time, values_t, power)
        future_energy_by_branch[label] = float(np.trapezoid(sampled_power, x=sampled_time))
    initial_remaining_energy = float(sum(future_energy_by_branch.values()))
    if initial_remaining_energy <= 1e-18:
        unit_step = np.where(values_t >= capture_time_s, 1.0, 0.0)
        winner_enable = {
            label: (unit_step.tolist() if label == winner_label else zero_trace.tolist())
            for label in labels
        }
        return {
            "time_s": values_t.tolist(),
            "control_node_name": resolved.control_node_name,
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
            "winner_branch_post_click_energy_j": 0.0,
            "winner_drain_total_energy_j": 0.0,
            "shared_leak_total_energy_j": 0.0,
            "loser_branch_power_w": {label: zero_trace.tolist() for label in labels if label != winner_label},
            "loser_suppression": {label: unit_step.tolist() for label in labels if label != winner_label},
            "loser_clamp_conductance_s": {label: (resolved.clamp_reference_g_on_s * unit_step).tolist() for label in labels if label != winner_label},
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
        }

    base_shares = {
        label: future_energy_by_branch[label] / max(initial_remaining_energy, 1e-18)
        for label in labels
    }
    dt = np.diff(values_t, append=float(values_t[-1]))
    dt[-1] = dt[-2] if dt.size > 1 else 0.0

    closure_variable = np.zeros_like(values_t)
    common_inhibit_v = np.zeros_like(values_t)
    shared_node_voltage_v = np.zeros_like(values_t)
    remaining_energy = np.zeros_like(values_t)
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

    current_energy = initial_remaining_energy
    winner_branch_energy = 0.0
    shared_leak_energy = 0.0
    loser_energy = {label: 0.0 for label in labels if label != winner_label}
    completed = False
    completed_time = float(values_t[-1])
    completed_reason = "end_of_trace"

    for index, time_value in enumerate(values_t):
        remaining_energy[index] = current_energy
        if time_value < float(capture_time_s):
            continue

        dt_step = max(float(dt[index]), 0.0)
        z_norm = 1.0 - np.exp(-(float(time_value) - float(capture_time_s)) / max(resolved.control_tau_s, 1e-12))
        z_norm = float(np.clip(z_norm, 0.0, 1.0))
        closure_variable[index] = z_norm
        common_inhibit_v[index] = resolved.supply_v * z_norm
        winner_enable[winner_label][index] = z_norm

        branch_conductance: dict[str, float] = {}
        for label in labels:
            base_g = resolved.branch_coupling_scale_s * base_shares[label]
            if label == winner_label:
                branch_conductance[label] = base_g * (1.0 + resolved.winner_branch_boost * z_norm)
            else:
                branch_conductance[label] = base_g * np.exp(-resolved.loser_attenuation_beta * z_norm)
                loser_suppression[label][index] = 1.0 - branch_conductance[label] / max(base_g, 1e-18)
                loser_clamp_conductance[label][index] = resolved.clamp_reference_g_on_s * z_norm

        g_winner_drain = resolved.winner_drain_g_on_s * z_norm
        g_total = max(sum(branch_conductance.values()) + g_winner_drain + resolved.shared_leak_g_s, 1e-18)
        shared_voltage = np.sqrt(max(2.0 * current_energy / max(resolved.shared_capacitance_f, 1e-18), 0.0))
        shared_node_voltage_v[index] = shared_voltage

        energy_released = current_energy * (
            1.0 - np.exp(-2.0 * g_total * dt_step / max(resolved.shared_capacitance_f, 1e-18))
        ) if dt_step > 0.0 else 0.0
        winner_branch_share = branch_conductance[winner_label] / g_total
        winner_drain_share = g_winner_drain / g_total
        shared_leak_share = resolved.shared_leak_g_s / g_total

        winner_branch_increment = energy_released * winner_branch_share
        winner_branch_energy += winner_branch_increment
        winner_branch_power[index] = winner_branch_increment / max(dt_step, 1e-18) if dt_step > 0.0 else 0.0

        drain_increment = energy_released * winner_drain_share
        winner_drain_power[index] = drain_increment / max(dt_step, 1e-18) if dt_step > 0.0 else 0.0
        winner_drain_current[index] = shared_voltage * g_winner_drain
        winner_drain_energy[index] = (winner_drain_energy[index - 1] if index > 0 else 0.0) + drain_increment

        for label in labels:
            if label == winner_label:
                continue
            branch_increment = energy_released * branch_conductance[label] / g_total
            loser_energy[label] += branch_increment
            loser_branch_power[label][index] = branch_increment / max(dt_step, 1e-18) if dt_step > 0.0 else 0.0

        shared_leak_energy += energy_released * shared_leak_share
        current_energy = max(current_energy - energy_released, 0.0)
        remaining_energy[index] = current_energy

        completion_gate = (
            current_energy <= resolved.completion_threshold_frac * initial_remaining_energy
            and winner_drain_current[index] <= resolved.completion_current_threshold_a
        )
        if completion_gate and not completed:
            completed = True
            completed_time = float(time_value)
            completed_reason = "shared_energy_and_drain_current_below_threshold"
        if completed:
            trial_complete_signal[index] = 1.0

    post_capture_mask = np.where(values_t >= float(capture_time_s))[0]
    monotonic = bool(np.all(np.diff(remaining_energy[post_capture_mask]) <= 1e-12)) if post_capture_mask.size else True
    return {
        "time_s": values_t.tolist(),
        "control_node_name": resolved.control_node_name,
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
        "winner_branch_post_click_energy_j": winner_branch_energy,
        "winner_drain_total_energy_j": float(winner_drain_energy[-1]),
        "shared_leak_total_energy_j": shared_leak_energy,
        "loser_branch_power_w": {label: values.tolist() for label, values in loser_branch_power.items()},
        "loser_suppression": {label: values.tolist() for label, values in loser_suppression.items()},
        "loser_clamp_conductance_s": {label: values.tolist() for label, values in loser_clamp_conductance.items()},
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
    }


def run_four_branch_candidate_with_physical_closure(
    candidate: Mapping[str, Any],
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    n_trials: int,
    seed: int,
    config: PhysicalClosureDrainConfig | None = None,
    reduced_interpretation: ClosureInterpretationConfig | None = None,
    race_result: Mapping[str, Any] | None = None,
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
    physical_rows: list[dict[str, Any]] = []
    reduced_rows: list[dict[str, Any]] = []
    example_trial: dict[str, Any] | None = None

    for trial_index, latch_result in enumerate(latch_results):
        physical = simulate_physical_closure_drain(
            time_s=candidate["time_s"],
            branch_power_w=candidate["branch_power_w"],
            branch_labels=candidate["branch_labels"],
            winner_index=int(latch_result["winner_index"]),
            winner_valid=bool(latch_result["winner_valid"]),
            capture_time_s=float(latch_result["settled_at_s"]),
            config=resolved,
        )
        reduced_row = simulate_post_click_closure(
            time_s=candidate["time_s"],
            branch_power_w=candidate["branch_power_w"],
            branch_labels=candidate["branch_labels"],
            winner_index=int(latch_result["winner_index"]),
            winner_valid=bool(latch_result["winner_valid"]),
            capture_time_s=float(latch_result["settled_at_s"]),
            interpretation=reduced,
        )
        physical_rows.append(physical)
        reduced_rows.append(reduced_row)
        if example_trial is None and physical["closure_active"]:
            example_trial = {
                "latch_result": dict(latch_result),
                "physical": physical,
                "reduced": reduced_row,
                "event_times": event_times[trial_index].tolist(),
            }

    initial_remaining = np.asarray([row["initial_remaining_energy_j"] for row in physical_rows], dtype=float)
    winner_drain = np.asarray([row["winner_drain_total_energy_j"] for row in physical_rows], dtype=float)
    loser_energy = np.asarray([sum(row["loser_post_click_energy_j"].values()) for row in physical_rows], dtype=float)
    complete_mask = np.asarray([bool(row["trial_complete"]) for row in physical_rows], dtype=bool)
    completion_times = np.asarray([float(row["trial_complete_time_s"]) for row in physical_rows], dtype=float)
    reduced_winner = np.asarray([row["winner_drain_total_energy_j"] for row in reduced_rows], dtype=float)
    reduced_loser = np.asarray([sum(row["loser_post_click_energy_j"].values()) for row in reduced_rows], dtype=float)
    reduced_complete_mask = np.asarray([bool(row["trial_complete"]) for row in reduced_rows], dtype=bool)
    reduced_completion_times = np.asarray([float(row["trial_complete_time_s"]) for row in reduced_rows], dtype=float)
    transparency_shift = np.zeros_like(np.asarray(frequency_summary["frequencies"], dtype=float))

    comparison_metrics = {
        "winner_fraction_abs_diff": float(
            abs(
                np.mean(np.divide(winner_drain, np.maximum(initial_remaining, 1e-18)))
                - np.mean(np.divide(reduced_winner, np.maximum(initial_remaining, 1e-18)))
            )
        ),
        "loser_fraction_abs_diff": float(
            abs(
                np.mean(np.divide(loser_energy, np.maximum(initial_remaining, 1e-18)))
                - np.mean(np.divide(reduced_loser, np.maximum(initial_remaining, 1e-18)))
            )
        ),
        "completion_rate_abs_diff": float(abs(np.mean(complete_mask) - np.mean(reduced_complete_mask))),
        "completion_time_abs_diff": float(
            abs(
                (float(np.mean(completion_times[complete_mask])) if np.any(complete_mask) else float("inf"))
                - (float(np.mean(reduced_completion_times[reduced_complete_mask])) if np.any(reduced_complete_mask) else float("inf"))
            )
        ),
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
        "physical_rows": physical_rows,
        "reduced_rows": reduced_rows,
        "comparison_metrics": comparison_metrics,
        "closure_metrics": {
            "pre_click_transparency_rms_shift": float(np.sqrt(np.mean(np.square(transparency_shift)))),
            "mean_winner_drain_fraction": float(np.mean(np.divide(winner_drain, np.maximum(initial_remaining, 1e-18)))),
            "mean_loser_fraction": float(np.mean(np.divide(loser_energy, np.maximum(initial_remaining, 1e-18)))),
            "completion_rate": float(np.mean(complete_mask)),
            "mean_completion_time_s": float(np.mean(completion_times[complete_mask])) if np.any(complete_mask) else float("inf"),
            "monotonic_remaining_energy": bool(all(bool(row["monotonic_remaining_energy"]) for row in physical_rows)),
            "mean_terminal_loser_suppression": float(
                np.mean(
                    [
                        np.mean([values[-1] for values in row["loser_suppression"].values()])
                        for row in physical_rows
                        if row["loser_suppression"]
                    ]
                )
            ) if any(row["loser_suppression"] for row in physical_rows) else 0.0,
            "mean_winner_drain_path_count": float(np.mean([row["winner_drain_path_count"] for row in physical_rows])),
        },
        "example_trial": example_trial,
    }
