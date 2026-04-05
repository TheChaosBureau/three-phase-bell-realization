from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from .closure_path import build_post_click_candidate_cache, future_branch_energy_from_cache


def build_trial_energy_accounting(
    candidate: Mapping[str, Any],
    closure_row: Mapping[str, Any],
    *,
    capture_time_s: float,
    winner_valid: bool,
    candidate_cache: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    labels = list(candidate["branch_labels"])
    cache = (
        build_post_click_candidate_cache(
            time_s=candidate["time_s"],
            branch_power_w=candidate["branch_power_w"],
            branch_labels=labels,
        )
        if candidate_cache is None
        else dict(candidate_cache)
    )
    total_by_branch = {
        label: float(candidate["branch_energy_j"][label])
        for label in labels
    }
    total_front_end_energy = float(sum(total_by_branch.values()))
    future_by_branch = (
        future_branch_energy_from_cache(cache, capture_time_s=float(capture_time_s))
        if winner_valid
        else {label: 0.0 for label in labels}
    )
    pre_click_by_branch = {
        label: max(total_by_branch[label] - float(future_by_branch[label]), 0.0)
        for label in labels
    }
    pre_click_total = float(sum(pre_click_by_branch.values()))

    initial_remaining = float(closure_row["initial_remaining_energy_j"])
    winner_branch_post_click = float(closure_row["winner_branch_post_click_energy_j"])
    winner_drain = float(closure_row["winner_drain_total_energy_j"])
    loser_post_click_by_branch = {
        label: float(value)
        for label, value in dict(closure_row["loser_post_click_energy_j"]).items()
    }
    loser_total = float(sum(loser_post_click_by_branch.values()))
    shared_leak = float(closure_row.get("shared_leak_total_energy_j", 0.0))
    terminal_remaining = float(closure_row.get("terminal_remaining_energy_j", 0.0))
    post_click_accounted = winner_branch_post_click + winner_drain + loser_total + shared_leak + terminal_remaining
    tracked_total = pre_click_total + post_click_accounted
    energy_balance_error = tracked_total - total_front_end_energy
    total_denom = max(total_front_end_energy, 1e-18)
    post_click_denom = max(initial_remaining, 1e-18)

    finite_values = np.asarray(
        [
            total_front_end_energy,
            pre_click_total,
            initial_remaining,
            winner_branch_post_click,
            winner_drain,
            loser_total,
            shared_leak,
            terminal_remaining,
            tracked_total,
            energy_balance_error,
        ],
        dtype=float,
    )
    return {
        "winner_valid": bool(winner_valid),
        "winner_index": int(closure_row["winner_index"]),
        "winner_label": closure_row["winner_label"],
        "capture_time_s": float(capture_time_s),
        "trial_complete": bool(closure_row["trial_complete"]),
        "trial_complete_time_s": float(closure_row["trial_complete_time_s"]),
        "monotonic_remaining_energy": bool(closure_row["monotonic_remaining_energy"]),
        "total_front_end_energy_j": total_front_end_energy,
        "pre_click_total_energy_j": pre_click_total,
        "pre_click_branch_energy_j": pre_click_by_branch,
        "future_branch_energy_j": future_by_branch,
        "initial_remaining_energy_j": initial_remaining,
        "post_click_winner_branch_energy_j": winner_branch_post_click,
        "post_click_winner_drain_energy_j": winner_drain,
        "post_click_loser_energy_j": loser_total,
        "post_click_loser_energy_by_branch_j": loser_post_click_by_branch,
        "post_click_shared_leak_energy_j": shared_leak,
        "terminal_remaining_shared_energy_j": terminal_remaining,
        "post_click_accounted_energy_j": post_click_accounted,
        "tracked_total_energy_j": tracked_total,
        "energy_balance_error_j": energy_balance_error,
        "pre_click_fraction_of_total": pre_click_total / total_denom,
        "initial_remaining_fraction_of_total": initial_remaining / total_denom,
        "winner_branch_fraction_of_total": winner_branch_post_click / total_denom,
        "winner_drain_fraction_of_total": winner_drain / total_denom,
        "loser_fraction_of_total": loser_total / total_denom,
        "shared_leak_fraction_of_total": shared_leak / total_denom,
        "terminal_remaining_fraction_of_total": terminal_remaining / total_denom,
        "winner_branch_fraction_of_post_click": winner_branch_post_click / post_click_denom,
        "winner_drain_fraction_of_post_click": winner_drain / post_click_denom,
        "loser_fraction_of_post_click": loser_total / post_click_denom,
        "shared_leak_fraction_of_post_click": shared_leak / post_click_denom,
        "terminal_remaining_fraction_of_post_click": terminal_remaining / post_click_denom,
        "finite": bool(np.all(np.isfinite(finite_values))),
    }


def summarize_energy_accounting_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "trial_count": 0,
            "winner_valid_fraction": 0.0,
            "completion_rate": 0.0,
            "monotonic_remaining_energy": True,
            "mean_total_front_end_energy_j": 0.0,
            "mean_pre_click_fraction_of_total": 0.0,
            "mean_initial_remaining_fraction_of_total": 0.0,
            "mean_winner_branch_fraction_of_total": 0.0,
            "mean_winner_drain_fraction_of_total": 0.0,
            "mean_loser_fraction_of_total": 0.0,
            "mean_shared_leak_fraction_of_total": 0.0,
            "mean_terminal_remaining_fraction_of_total": 0.0,
            "mean_winner_branch_fraction_of_post_click": 0.0,
            "mean_winner_drain_fraction_of_post_click": 0.0,
            "mean_loser_fraction_of_post_click": 0.0,
            "mean_shared_leak_fraction_of_post_click": 0.0,
            "mean_terminal_remaining_fraction_of_post_click": 0.0,
            "mean_energy_balance_abs_error_j": 0.0,
            "max_energy_balance_abs_error_j": 0.0,
            "mean_energy_balance_abs_fraction": 0.0,
            "max_energy_balance_abs_fraction": 0.0,
            "finite_outputs": True,
            "energy_accounting_pass": True,
        }

    def _mean(key: str) -> float:
        return float(np.mean([float(row[key]) for row in rows]))

    abs_balance_errors = np.asarray([abs(float(row["energy_balance_error_j"])) for row in rows], dtype=float)
    balance_abs_fractions = np.asarray(
        [
            abs(float(row["energy_balance_error_j"])) / max(float(row["total_front_end_energy_j"]), 1e-18)
            for row in rows
        ],
        dtype=float,
    )
    completion_times = np.asarray(
        [float(row["trial_complete_time_s"]) for row in rows if bool(row["trial_complete"])],
        dtype=float,
    )
    finite_outputs = bool(all(bool(row["finite"]) for row in rows))
    monotonic_remaining_energy = bool(all(bool(row["monotonic_remaining_energy"]) for row in rows))
    max_balance_abs_fraction = float(np.max(balance_abs_fractions))
    return {
        "trial_count": len(rows),
        "winner_valid_fraction": _mean("winner_valid"),
        "completion_rate": _mean("trial_complete"),
        "mean_completion_time_s": float(np.mean(completion_times)) if completion_times.size else float("inf"),
        "monotonic_remaining_energy": monotonic_remaining_energy,
        "mean_total_front_end_energy_j": _mean("total_front_end_energy_j"),
        "mean_pre_click_fraction_of_total": _mean("pre_click_fraction_of_total"),
        "mean_initial_remaining_fraction_of_total": _mean("initial_remaining_fraction_of_total"),
        "mean_winner_branch_fraction_of_total": _mean("winner_branch_fraction_of_total"),
        "mean_winner_drain_fraction_of_total": _mean("winner_drain_fraction_of_total"),
        "mean_loser_fraction_of_total": _mean("loser_fraction_of_total"),
        "mean_shared_leak_fraction_of_total": _mean("shared_leak_fraction_of_total"),
        "mean_terminal_remaining_fraction_of_total": _mean("terminal_remaining_fraction_of_total"),
        "mean_winner_branch_fraction_of_post_click": _mean("winner_branch_fraction_of_post_click"),
        "mean_winner_drain_fraction_of_post_click": _mean("winner_drain_fraction_of_post_click"),
        "mean_loser_fraction_of_post_click": _mean("loser_fraction_of_post_click"),
        "mean_shared_leak_fraction_of_post_click": _mean("shared_leak_fraction_of_post_click"),
        "mean_terminal_remaining_fraction_of_post_click": _mean("terminal_remaining_fraction_of_post_click"),
        "mean_energy_balance_abs_error_j": float(np.mean(abs_balance_errors)),
        "max_energy_balance_abs_error_j": float(np.max(abs_balance_errors)),
        "mean_energy_balance_abs_fraction": float(np.mean(balance_abs_fractions)),
        "max_energy_balance_abs_fraction": max_balance_abs_fraction,
        "finite_outputs": finite_outputs,
        "energy_accounting_pass": finite_outputs and monotonic_remaining_energy and max_balance_abs_fraction < 1e-6,
    }
