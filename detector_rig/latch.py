from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np

from detector_rig.config import LatchRigConfig
from detector_rig.sim import DetectorCell, click_rate
from detector_search.sim.metrics import race_error_metric


@dataclass(frozen=True)
class LatchPulse:
    """Pulse presented to the winner-take-all latch."""

    channel: str
    time_ns: float
    amplitude_v: float
    width_ns: float
    source: str = "synthetic"


def _winner_to_index(channel: str) -> int:
    return {"": 0, "A": 1, "B": 2}[channel]


def _pulse_valid(pulse: LatchPulse, config: LatchRigConfig) -> bool:
    return pulse.amplitude_v >= config.input_threshold_v and pulse.width_ns >= config.min_input_pulse_width_ns


def _choose_cluster_winner(cluster: list[LatchPulse], config: LatchRigConfig) -> tuple[str, bool]:
    valid_a = [pulse.time_ns for pulse in cluster if pulse.channel == "A" and _pulse_valid(pulse, config)]
    valid_b = [pulse.time_ns for pulse in cluster if pulse.channel == "B" and _pulse_valid(pulse, config)]
    if not valid_a and not valid_b:
        return "", False
    if not valid_a:
        return "B", False
    if not valid_b:
        return "A", False
    earliest_a = min(valid_a)
    earliest_b = min(valid_b)
    if abs(earliest_a - earliest_b) <= config.tie_window_ns:
        return config.tie_break_priority, True
    return ("A", False) if earliest_a < earliest_b else ("B", False)


def simulate_latch_sequence(pulses: Iterable[LatchPulse], config: LatchRigConfig) -> dict[str, Any]:
    """Run the latch state machine on a pulse/reset sequence."""

    ordered = sorted(
        list(pulses),
        key=lambda pulse: (pulse.time_ns, 0 if pulse.channel == "reset" else 1, 0 if pulse.channel == config.tie_break_priority else 1),
    )

    armed = True
    winner = ""
    winner_set_time_ns: float | None = None
    settled_time_ns: float | None = None
    rearm_at_ns = -math.inf
    epoch_index = 0
    winner_events: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    masked_rival_count = 0
    masked_total_count = 0
    winner_counts_by_epoch: dict[int, int] = {}

    index = 0
    while index < len(ordered):
        pulse = ordered[index]

        if not armed and pulse.time_ns >= rearm_at_ns:
            armed = True

        if pulse.channel == "reset":
            winner = ""
            winner_set_time_ns = None
            settled_time_ns = None
            armed = False
            rearm_at_ns = pulse.time_ns + config.reset_pulse_ns + 1000.0 * config.rearm_holdoff_us
            event_rows.append(
                {
                    "epoch_index": epoch_index,
                    "event_index": len(event_rows) + 1,
                    "channel": "reset",
                    "time_ns": pulse.time_ns,
                    "amplitude_v": pulse.amplitude_v,
                    "width_ns": pulse.width_ns,
                    "action": "reset",
                    "winner_after_event": "",
                    "winner_valid": 0,
                    "tie_region": 0,
                    "armed_after_event": 0,
                    "rearm_at_ns": rearm_at_ns,
                    "source": pulse.source,
                }
            )
            epoch_index += 1
            index += 1
            continue

        if not armed:
            event_rows.append(
                {
                    "epoch_index": epoch_index,
                    "event_index": len(event_rows) + 1,
                    "channel": pulse.channel,
                    "time_ns": pulse.time_ns,
                    "amplitude_v": pulse.amplitude_v,
                    "width_ns": pulse.width_ns,
                    "action": "ignored_holdoff",
                    "winner_after_event": winner,
                    "winner_valid": int(bool(winner)),
                    "tie_region": 0,
                    "armed_after_event": 0,
                    "rearm_at_ns": rearm_at_ns,
                    "source": pulse.source,
                }
            )
            index += 1
            continue

        if winner:
            action = "masked_rival" if pulse.channel != winner else "masked_same_channel"
            if action == "masked_rival":
                masked_rival_count += 1
            masked_total_count += 1
            event_rows.append(
                {
                    "epoch_index": epoch_index,
                    "event_index": len(event_rows) + 1,
                    "channel": pulse.channel,
                    "time_ns": pulse.time_ns,
                    "amplitude_v": pulse.amplitude_v,
                    "width_ns": pulse.width_ns,
                    "action": action,
                    "winner_after_event": winner,
                    "winner_valid": 1,
                    "tie_region": 0,
                    "armed_after_event": 1,
                    "rearm_at_ns": rearm_at_ns,
                    "source": pulse.source,
                }
            )
            index += 1
            continue

        cluster = [pulse]
        next_index = index + 1
        while next_index < len(ordered):
            next_pulse = ordered[next_index]
            if next_pulse.channel == "reset":
                break
            if next_pulse.time_ns - pulse.time_ns > config.tie_window_ns:
                break
            cluster.append(next_pulse)
            next_index += 1

        winner_channel, tie_region = _choose_cluster_winner(cluster, config)
        if not winner_channel:
            for invalid_pulse in cluster:
                event_rows.append(
                    {
                        "epoch_index": epoch_index,
                        "event_index": len(event_rows) + 1,
                        "channel": invalid_pulse.channel,
                        "time_ns": invalid_pulse.time_ns,
                        "amplitude_v": invalid_pulse.amplitude_v,
                        "width_ns": invalid_pulse.width_ns,
                        "action": "ignored_invalid",
                        "winner_after_event": "",
                        "winner_valid": 0,
                        "tie_region": 0,
                        "armed_after_event": 1,
                        "rearm_at_ns": rearm_at_ns,
                        "source": invalid_pulse.source,
                    }
                )
            index = next_index
            continue

        winner_pulse_position = min(
            position
            for position, candidate in enumerate(cluster)
            if candidate.channel == winner_channel and _pulse_valid(candidate, config)
        )
        winner_pulse = cluster[winner_pulse_position]
        winner = winner_channel
        winner_set_time_ns = winner_pulse.time_ns + config.pickoff_delay_ns + config.propagation_delay_ns
        settled_time_ns = winner_pulse.time_ns + config.pickoff_delay_ns + config.settle_time_ns
        winner_events.append(
            {
                "epoch_index": epoch_index,
                "channel": winner_channel,
                "pulse_time_ns": winner_pulse.time_ns,
                "set_time_ns": winner_set_time_ns,
                "settled_time_ns": settled_time_ns,
                "tie_region": int(tie_region),
            }
        )
        winner_counts_by_epoch[epoch_index] = winner_counts_by_epoch.get(epoch_index, 0) + 1

        for position, cluster_pulse in enumerate(cluster):
            valid = _pulse_valid(cluster_pulse, config)
            if not valid:
                action = "ignored_invalid"
            elif position == winner_pulse_position and cluster_pulse.channel == winner_channel:
                action = "winner_set"
            else:
                action = "masked_rival" if cluster_pulse.channel != winner_channel else "masked_same_channel"
                if action == "masked_rival":
                    masked_rival_count += 1
                masked_total_count += 1
            event_rows.append(
                {
                    "epoch_index": epoch_index,
                    "event_index": len(event_rows) + 1,
                    "channel": cluster_pulse.channel,
                    "time_ns": cluster_pulse.time_ns,
                    "amplitude_v": cluster_pulse.amplitude_v,
                    "width_ns": cluster_pulse.width_ns,
                    "action": action,
                    "winner_after_event": winner,
                    "winner_valid": 1,
                    "tie_region": int(tie_region),
                    "armed_after_event": 1,
                    "rearm_at_ns": rearm_at_ns,
                    "source": cluster_pulse.source,
                }
            )
        index = next_index

    double_winner_count = sum(max(count - 1, 0) for count in winner_counts_by_epoch.values())
    return {
        "winner": winner,
        "winner_index": _winner_to_index(winner),
        "winner_valid": bool(winner),
        "winner_A": winner == "A",
        "winner_B": winner == "B",
        "winner_set_time_ns": winner_set_time_ns,
        "settled_time_ns": settled_time_ns,
        "rearm_at_ns": rearm_at_ns if math.isfinite(rearm_at_ns) else None,
        "masked_rival_count": masked_rival_count,
        "masked_total_count": masked_total_count,
        "double_winner_count": double_winner_count,
        "winner_events": winner_events,
        "event_rows": event_rows,
    }


def summarize_latch_interface(cell_a: DetectorCell, cell_b: DetectorCell, config: LatchRigConfig) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for cell in (cell_a, cell_b):
        loaded_amplitude_v = cell.pulse_amplitude_v * (1.0 - config.input_load_amplitude_loss_rel)
        loaded_width_ns = cell.pulse_width_ns * (1.0 + config.input_load_width_stretch_rel)
        loaded_jitter_ns = math.sqrt(cell.timing_jitter_ns**2 + config.input_load_added_jitter_ns**2)
        rows.append(
            {
                "cell": cell.name,
                "loaded_amplitude_v": loaded_amplitude_v,
                "threshold_margin_v": loaded_amplitude_v - config.input_threshold_v,
                "loaded_width_ns": loaded_width_ns,
                "width_margin_ns": loaded_width_ns - config.min_input_pulse_width_ns,
                "loaded_timing_jitter_ns": loaded_jitter_ns,
            }
        )

    return {
        "rows": rows,
        "summary": {
            "input_load_amplitude_loss_rel": config.input_load_amplitude_loss_rel,
            "input_load_width_stretch_rel": config.input_load_width_stretch_rel,
            "input_load_added_jitter_ns": config.input_load_added_jitter_ns,
            "min_threshold_margin_v": min(row["threshold_margin_v"] for row in rows),
            "min_width_margin_ns": min(row["width_margin_ns"] for row in rows),
        },
    }


def build_timing_case_rows(config: LatchRigConfig) -> list[dict[str, Any]]:
    holdoff_ns = 1000.0 * config.rearm_holdoff_us
    case_pulses = {
        "A_first": [
            LatchPulse("A", 40.0, 1.0, 12.0, source="timing"),
            LatchPulse("B", 52.0, 1.0, 12.0, source="timing"),
        ],
        "B_first": [
            LatchPulse("B", 40.0, 1.0, 12.0, source="timing"),
            LatchPulse("A", 53.0, 1.0, 12.0, source="timing"),
        ],
        "near_simultaneous": [
            LatchPulse("A", 60.0, 1.0, 12.0, source="timing"),
            LatchPulse("B", 60.10, 1.0, 12.0, source="timing"),
        ],
        "reset_rearm": [
            LatchPulse("B", 30.0, 1.0, 12.0, source="timing"),
            LatchPulse("A", 44.0, 1.0, 12.0, source="timing"),
            LatchPulse("reset", 200.0, 1.0, config.reset_pulse_ns, source="timing"),
            LatchPulse("B", 200.0 + config.reset_pulse_ns + 0.5 * holdoff_ns, 1.0, 12.0, source="timing"),
            LatchPulse("A", 200.0 + config.reset_pulse_ns + holdoff_ns + 20.0, 1.0, 12.0, source="timing"),
        ],
    }

    rows: list[dict[str, Any]] = []
    for case_name, pulses in case_pulses.items():
        result = simulate_latch_sequence(pulses, config)
        for pulse in pulses:
            rows.append(
                {
                    "case_name": case_name,
                    "stage": f"input_{pulse.channel}",
                    "time_ns": pulse.time_ns,
                    "winner_valid": 0,
                    "winner_A": 0,
                    "winner_B": 0,
                    "notes": pulse.source,
                }
            )
            if pulse.channel == "reset":
                rows.append(
                    {
                        "case_name": case_name,
                        "stage": "reset_release",
                        "time_ns": pulse.time_ns + config.reset_pulse_ns,
                        "winner_valid": 0,
                        "winner_A": 0,
                        "winner_B": 0,
                        "notes": "reset released",
                    }
                )
                rows.append(
                    {
                        "case_name": case_name,
                        "stage": "rearmed",
                        "time_ns": pulse.time_ns + config.reset_pulse_ns + holdoff_ns,
                        "winner_valid": 0,
                        "winner_A": 0,
                        "winner_B": 0,
                        "notes": "latch ready for new winner",
                    }
                )
        for winner_event in result["winner_events"]:
            rows.append(
                {
                    "case_name": case_name,
                    "stage": "winner_asserted",
                    "time_ns": winner_event["set_time_ns"],
                    "winner_valid": 1,
                    "winner_A": int(winner_event["channel"] == "A"),
                    "winner_B": int(winner_event["channel"] == "B"),
                    "notes": "tie priority applied" if winner_event["tie_region"] else "first arrival wins",
                }
            )
            rows.append(
                {
                    "case_name": case_name,
                    "stage": "latch_settled",
                    "time_ns": winner_event["settled_time_ns"],
                    "winner_valid": 1,
                    "winner_A": int(winner_event["channel"] == "A"),
                    "winner_B": int(winner_event["channel"] == "B"),
                    "notes": "stable hold state",
                }
            )
    return sorted(rows, key=lambda row: (row["case_name"], row["time_ns"], row["stage"]))


def _expected_winner_for_delta(delta_t_ns: float, config: LatchRigConfig) -> tuple[str, bool]:
    if abs(delta_t_ns) <= config.tie_window_ns:
        return config.tie_break_priority, True
    return ("A", False) if delta_t_ns > 0.0 else ("B", False)


def simulate_first_arrival_suite(cell_a: DetectorCell, cell_b: DetectorCell, config: LatchRigConfig) -> dict[str, Any]:
    rng = np.random.default_rng(config.seed + 10)
    base_time_ns = 50.0
    rows: list[dict[str, Any]] = []

    ordered_trials = 0
    ordered_correct = 0
    total_double_winners = 0
    tie_trials = 0

    amplitude_mean_a = cell_a.pulse_amplitude_v * (1.0 - config.input_load_amplitude_loss_rel)
    amplitude_mean_b = cell_b.pulse_amplitude_v * (1.0 - config.input_load_amplitude_loss_rel)
    width_mean_a = cell_a.pulse_width_ns * (1.0 + config.input_load_width_stretch_rel)
    width_mean_b = cell_b.pulse_width_ns * (1.0 + config.input_load_width_stretch_rel)

    for delta_t_ns in config.synthetic_offsets_ns:
        expected_winner, tie_region = _expected_winner_for_delta(delta_t_ns, config)
        counts = {"A": 0, "B": 0, "": 0}
        local_double_winners = 0
        local_settle_times_ns: list[float] = []

        for _ in range(config.synthetic_repeats):
            amplitude_a = float(rng.normal(amplitude_mean_a, 0.01 * cell_a.pulse_amplitude_v))
            amplitude_b = float(rng.normal(amplitude_mean_b, 0.01 * cell_b.pulse_amplitude_v))
            width_a = max(float(rng.normal(width_mean_a, 0.20)), 1.0)
            width_b = max(float(rng.normal(width_mean_b, 0.20)), 1.0)
            pulses = [
                LatchPulse("A", base_time_ns, amplitude_a, width_a, source="first_arrival"),
                LatchPulse("B", base_time_ns + delta_t_ns, amplitude_b, width_b, source="first_arrival"),
            ]
            result = simulate_latch_sequence(pulses, config)
            observed = result["winner_events"][0]["channel"] if result["winner_events"] else ""
            counts[observed] += 1
            local_double_winners += result["double_winner_count"]
            if result["winner_events"]:
                local_settle_times_ns.append(
                    float(result["winner_events"][0]["settled_time_ns"] - result["winner_events"][0]["pulse_time_ns"])
                )

        correct_count = counts[expected_winner]
        if tie_region:
            tie_trials += config.synthetic_repeats
        else:
            ordered_trials += config.synthetic_repeats
            ordered_correct += correct_count
        total_double_winners += local_double_winners
        rows.append(
            {
                "delta_t_ns": delta_t_ns,
                "ordered_case": int(not tie_region),
                "tie_region": int(tie_region),
                "expected_winner": expected_winner,
                "winner_A_count": counts["A"],
                "winner_B_count": counts["B"],
                "winner_none_count": counts[""],
                "correctness_rate": correct_count / max(config.synthetic_repeats, 1),
                "double_winner_count": local_double_winners,
                "mean_settling_time_ns": float(np.mean(local_settle_times_ns)) if local_settle_times_ns else math.nan,
            }
        )

    return {
        "rows": rows,
        "summary": {
            "ordered_capture_accuracy": ordered_correct / max(ordered_trials, 1),
            "tie_region_width_ns": 2.0 * config.tie_window_ns,
            "tie_resolution_winner": config.tie_break_priority,
            "tie_trials": tie_trials,
            "double_winner_count": total_double_winners,
            "settling_time_ns": config.pickoff_delay_ns + config.settle_time_ns,
        },
    }


def simulate_exclusivity_suite(config: LatchRigConfig) -> dict[str, Any]:
    scenarios = [
        (
            "A_first_then_B_retries",
            "A",
            [
                LatchPulse("A", 40.0, 1.0, 12.0, source="exclusivity"),
                LatchPulse("B", 54.0, 1.0, 12.0, source="exclusivity"),
                LatchPulse("B", 66.0, 1.0, 12.0, source="exclusivity"),
                LatchPulse("A", 75.0, 1.0, 12.0, source="exclusivity"),
            ],
        ),
        (
            "B_first_then_A_retries",
            "B",
            [
                LatchPulse("B", 40.0, 1.0, 12.0, source="exclusivity"),
                LatchPulse("A", 53.0, 1.0, 12.0, source="exclusivity"),
                LatchPulse("A", 67.0, 1.0, 12.0, source="exclusivity"),
                LatchPulse("B", 81.0, 1.0, 12.0, source="exclusivity"),
            ],
        ),
        (
            "tie_then_late_retries",
            config.tie_break_priority,
            [
                LatchPulse("A", 50.0, 1.0, 12.0, source="exclusivity"),
                LatchPulse("B", 50.10, 1.0, 12.0, source="exclusivity"),
                LatchPulse("B", 63.0, 1.0, 12.0, source="exclusivity"),
                LatchPulse("A", 77.0, 1.0, 12.0, source="exclusivity"),
            ],
        ),
    ]

    rows: list[dict[str, Any]] = []
    total_double_winners = 0
    total_rival_masked = 0
    total_expected_rival = 0
    hold_successes = 0

    for scenario_name, expected_winner, pulses in scenarios:
        correct_winners = 0
        local_double_winners = 0
        local_rival_masked = 0
        local_hold_successes = 0

        expected_rival_after_capture = sum(1 for pulse in pulses[1:] if pulse.channel != expected_winner)
        total_expected_rival += config.exclusivity_repeats * expected_rival_after_capture

        for _ in range(config.exclusivity_repeats):
            result = simulate_latch_sequence(pulses, config)
            winner_events = result["winner_events"]
            observed = winner_events[0]["channel"] if winner_events else ""
            correct_winners += int(observed == expected_winner)
            local_double_winners += result["double_winner_count"]
            local_rival_masked += result["masked_rival_count"]
            local_hold_successes += int(
                len(winner_events) == 1 and result["winner"] == expected_winner and result["winner_valid"]
            )

        total_double_winners += local_double_winners
        total_rival_masked += local_rival_masked
        hold_successes += local_hold_successes
        rows.append(
            {
                "scenario": scenario_name,
                "expected_winner": expected_winner,
                "winner_correct_fraction": correct_winners / max(config.exclusivity_repeats, 1),
                "double_winner_count": local_double_winners,
                "masked_rival_fraction": local_rival_masked / max(config.exclusivity_repeats * expected_rival_after_capture, 1),
                "hold_success_fraction": local_hold_successes / max(config.exclusivity_repeats, 1),
            }
        )

    return {
        "rows": rows,
        "summary": {
            "double_winner_count": total_double_winners,
            "masked_rival_fraction": total_rival_masked / max(total_expected_rival, 1),
            "hold_success_fraction": hold_successes / max(config.exclusivity_repeats * len(scenarios), 1),
        },
    }


def simulate_reset_suite(config: LatchRigConfig) -> dict[str, Any]:
    holdoff_ns = 1000.0 * config.rearm_holdoff_us
    rearm_interval_us = (config.reset_pulse_ns + holdoff_ns) / 1000.0
    rows: list[dict[str, Any]] = []
    success_count = 0
    retained_memory_count = 0
    post_reset_winners: list[str] = []

    for cycle_index in range(1, config.reset_cycles + 1):
        first_winner = "A" if cycle_index % 2 == 1 else "B"
        second_winner = "B" if first_winner == "A" else "A"
        reset_time_ns = 200.0
        pulses = [
            LatchPulse(first_winner, 40.0, 1.0, 12.0, source="reset"),
            LatchPulse(second_winner, 54.0, 1.0, 12.0, source="reset"),
            LatchPulse("reset", reset_time_ns, 1.0, config.reset_pulse_ns, source="reset"),
            LatchPulse(first_winner, reset_time_ns + config.reset_pulse_ns + 0.5 * holdoff_ns, 1.0, 12.0, source="reset"),
            LatchPulse(second_winner, reset_time_ns + config.reset_pulse_ns + holdoff_ns + 20.0, 1.0, 12.0, source="reset"),
        ]
        result = simulate_latch_sequence(pulses, config)
        winner_events = result["winner_events"]
        early_probe_ignored = any(row["action"] == "ignored_holdoff" for row in result["event_rows"])
        first_observed = winner_events[0]["channel"] if len(winner_events) >= 1 else ""
        second_observed = winner_events[1]["channel"] if len(winner_events) >= 2 else ""
        retained_memory = second_observed == first_observed and second_observed != ""
        retained_memory_count += int(retained_memory)
        post_reset_winners.append(second_observed)
        cycle_success = (
            len(winner_events) == 2
            and first_observed == first_winner
            and second_observed == second_winner
            and early_probe_ignored
            and not retained_memory
        )
        success_count += int(cycle_success)
        rows.append(
            {
                "cycle_index": cycle_index,
                "first_winner_expected": first_winner,
                "first_winner_observed": first_observed,
                "second_winner_expected": second_winner,
                "second_winner_observed": second_observed,
                "reset_cleared": int(len(winner_events) == 2),
                "early_probe_ignored": int(early_probe_ignored),
                "retained_memory": int(retained_memory),
                "rearm_interval_us": rearm_interval_us,
            }
        )

    post_reset_a_fraction = sum(winner == "A" for winner in post_reset_winners) / max(len(post_reset_winners), 1)
    return {
        "rows": rows,
        "summary": {
            "reset_success_fraction": success_count / max(config.reset_cycles, 1),
            "retained_memory_count": retained_memory_count,
            "rearm_latency_us": rearm_interval_us,
            "post_reset_bias_drift": abs(post_reset_a_fraction - 0.5),
        },
    }


def _sample_click_time(rate_hz: float, timeout_s: float, rng: np.random.Generator) -> float | None:
    if rate_hz <= 0.0:
        return None
    sample = float(rng.exponential(1.0 / rate_hz))
    return sample if sample <= timeout_s else None


def _baseline_winner_index(t_a_s: float | None, t_b_s: float | None) -> int:
    if t_a_s is None and t_b_s is None:
        return 0
    if t_a_s is None:
        return 2
    if t_b_s is None or t_a_s < t_b_s:
        return 1
    if t_b_s < t_a_s:
        return 2
    return 1


def _build_detector_pulse(
    channel: str,
    click_time_s: float,
    cell: DetectorCell,
    rng: np.random.Generator,
    config: LatchRigConfig,
) -> LatchPulse:
    amplitude_mean = cell.pulse_amplitude_v * (1.0 - config.input_load_amplitude_loss_rel)
    width_mean = cell.pulse_width_ns * (1.0 + config.input_load_width_stretch_rel)
    jitter_ns = math.sqrt(cell.timing_jitter_ns**2 + config.input_load_added_jitter_ns**2)
    amplitude_v = float(rng.normal(amplitude_mean, 0.01 * cell.pulse_amplitude_v))
    width_ns = max(float(rng.normal(width_mean, 0.20)), 1.0)
    time_ns = 1e9 * click_time_s + config.pickoff_delay_ns + float(rng.normal(cell.timing_offset_ns, jitter_ns))
    return LatchPulse(channel, time_ns, amplitude_v, width_ns, source="detector")


def simulate_race_with_latch(
    cell_a: DetectorCell,
    cell_b: DetectorCell,
    *,
    splits: tuple[tuple[float, float], ...],
    total_power_uw: float,
    n_trials: int,
    timeout_s: float,
    latch_config: LatchRigConfig,
    seed: int,
) -> dict[str, Any]:
    race_rng = np.random.default_rng(seed)
    pulse_rng = np.random.default_rng(seed + 1_000)
    comparison_rows: list[dict[str, Any]] = []
    raw_rows: list[dict[str, Any]] = []
    baseline_p1_values: list[float] = []
    latch_p1_values: list[float] = []
    target_p1_values: list[float] = []

    max_missed_winner_rate = 0.0
    max_branch_bias_shift = 0.0
    max_decisive_fraction_shift = 0.0
    total_double_winners = 0

    for fraction_a, fraction_b in splits:
        power_a = total_power_uw * fraction_a
        power_b = total_power_uw * fraction_b
        rate_a = click_rate(cell_a, power_a)
        rate_b = click_rate(cell_b, power_b)
        baseline_counts = {0: 0, 1: 0, 2: 0}
        latch_counts = {0: 0, 1: 0, 2: 0}
        missed_winner_count = 0

        for trial_index in range(1, n_trials + 1):
            click_time_a_s = _sample_click_time(rate_a, timeout_s, race_rng)
            click_time_b_s = _sample_click_time(rate_b, timeout_s, race_rng)
            baseline_winner = _baseline_winner_index(click_time_a_s, click_time_b_s)
            baseline_counts[baseline_winner] += 1

            pulses: list[LatchPulse] = []
            if click_time_a_s is not None:
                pulses.append(_build_detector_pulse("A", click_time_a_s, cell_a, pulse_rng, latch_config))
            if click_time_b_s is not None:
                pulses.append(_build_detector_pulse("B", click_time_b_s, cell_b, pulse_rng, latch_config))

            latch_result = simulate_latch_sequence(pulses, latch_config)
            latch_winner = latch_result["winner_index"]
            latch_counts[latch_winner] += 1
            total_double_winners += latch_result["double_winner_count"]
            if baseline_winner and not latch_winner:
                missed_winner_count += 1

            raw_rows.append(
                {
                    "split_label": f"{fraction_a:.2f}/{fraction_b:.2f}",
                    "trial_index": trial_index,
                    "power_a_uw": power_a,
                    "power_b_uw": power_b,
                    "baseline_winner": baseline_winner,
                    "latch_winner": latch_winner,
                    "click_time_a_s": "" if click_time_a_s is None else click_time_a_s,
                    "click_time_b_s": "" if click_time_b_s is None else click_time_b_s,
                }
            )

        target_p1 = fraction_a / max(fraction_a + fraction_b, 1e-12)
        baseline_decisive = baseline_counts[1] + baseline_counts[2]
        latch_decisive = latch_counts[1] + latch_counts[2]
        baseline_p1 = baseline_counts[1] / max(baseline_decisive, 1)
        latch_p1 = latch_counts[1] / max(latch_decisive, 1)
        missed_winner_rate = missed_winner_count / max(baseline_decisive, 1)
        branch_bias_shift = abs(latch_p1 - baseline_p1)
        decisive_fraction_shift = abs(latch_decisive / max(n_trials, 1) - baseline_decisive / max(n_trials, 1))

        max_missed_winner_rate = max(max_missed_winner_rate, missed_winner_rate)
        max_branch_bias_shift = max(max_branch_bias_shift, branch_bias_shift)
        max_decisive_fraction_shift = max(max_decisive_fraction_shift, decisive_fraction_shift)
        baseline_p1_values.append(baseline_p1)
        latch_p1_values.append(latch_p1)
        target_p1_values.append(target_p1)
        comparison_rows.append(
            {
                "split_label": f"{fraction_a:.2f}/{fraction_b:.2f}",
                "target_p1": target_p1,
                "baseline_p1": baseline_p1,
                "latch_p1": latch_p1,
                "branch_bias_shift": latch_p1 - baseline_p1,
                "baseline_decisive_fraction": baseline_decisive / max(n_trials, 1),
                "latch_decisive_fraction": latch_decisive / max(n_trials, 1),
                "decisive_fraction_shift": latch_decisive / max(n_trials, 1) - baseline_decisive / max(n_trials, 1),
                "winner_A_count": latch_counts[1],
                "winner_B_count": latch_counts[2],
                "timeout_count": latch_counts[0],
                "missed_winner_rate": missed_winner_rate,
            }
        )

    baseline_metrics = race_error_metric(target_p1_values, baseline_p1_values)
    latch_metrics = race_error_metric(target_p1_values, latch_p1_values)
    return {
        "raw_rows": raw_rows,
        "comparison_rows": comparison_rows,
        "metrics": {
            "baseline_race_rms_error": float(baseline_metrics["race_rms_error"]),
            "baseline_race_max_error": float(baseline_metrics["race_max_error"]),
            "latch_race_rms_error": float(latch_metrics["race_rms_error"]),
            "latch_race_max_error": float(latch_metrics["race_max_error"]),
            "added_race_rms_error": float(latch_metrics["race_rms_error"] - baseline_metrics["race_rms_error"]),
            "max_branch_bias_shift": float(max_branch_bias_shift),
            "max_decisive_fraction_shift": float(max_decisive_fraction_shift),
            "max_missed_winner_rate": float(max_missed_winner_rate),
            "double_winner_count": total_double_winners,
        },
    }
