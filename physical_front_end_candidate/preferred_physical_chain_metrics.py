from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from detector_integration.sim.metrics import chsh_metrics

from .metrics import aggregate_case_error, correlator_rms_error


def build_pre_click_comparison(
    *,
    exact_weights: Sequence[float],
    baseline_frequencies: Sequence[float],
    integrated_frequencies: Sequence[float],
    baseline_decisive_fraction: float,
    integrated_decisive_fraction: float,
    baseline_timeout_fraction: float,
    integrated_timeout_fraction: float,
) -> dict[str, Any]:
    exact = np.asarray(exact_weights, dtype=float)
    baseline = np.asarray(baseline_frequencies, dtype=float)
    integrated = np.asarray(integrated_frequencies, dtype=float)
    shift = integrated - baseline
    baseline_error = baseline - exact
    integrated_error = integrated - exact
    return {
        "winner_frequency_shift": shift.tolist(),
        "winner_frequency_rms_shift": float(np.sqrt(np.mean(shift**2))),
        "winner_frequency_max_shift": float(np.max(np.abs(shift))),
        "baseline_winner_rms_error": float(np.sqrt(np.mean(baseline_error**2))),
        "integrated_winner_rms_error": float(np.sqrt(np.mean(integrated_error**2))),
        "baseline_winner_max_error": float(np.max(np.abs(baseline_error))),
        "integrated_winner_max_error": float(np.max(np.abs(integrated_error))),
        "decisive_fraction_shift": float(integrated_decisive_fraction - baseline_decisive_fraction),
        "timeout_fraction_shift": float(integrated_timeout_fraction - baseline_timeout_fraction),
    }


def summarize_post_click_behavior(
    closure_rows: Sequence[Mapping[str, Any]],
    energy_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    trial_count = max(len(closure_rows), 1)
    activated_energy_rows = [
        row
        for row in energy_rows
        if bool(row["winner_valid"]) and float(row["initial_remaining_energy_j"]) > 1e-18
    ]
    completion_times = np.asarray(
        [float(row["trial_complete_time_s"]) for row in closure_rows if bool(row["trial_complete"])],
        dtype=float,
    )
    dominance_hits = [
        float(row["winner_drain_fraction_of_post_click"])
        > max(
            float(row["winner_branch_fraction_of_post_click"]),
            float(row["loser_fraction_of_post_click"]),
            float(row["shared_leak_fraction_of_post_click"]),
            float(row["terminal_remaining_fraction_of_post_click"]),
        )
        for row in activated_energy_rows
    ]

    def _mean(rows: Sequence[Mapping[str, Any]], key: str) -> float:
        if not rows:
            return 0.0
        return float(np.mean([float(row[key]) for row in rows]))

    return {
        "trial_count": len(closure_rows),
        "activation_rate": float(np.mean([float(bool(row["closure_active"])) for row in closure_rows])) if closure_rows else 0.0,
        "activated_trial_count": len(activated_energy_rows),
        "mean_winner_drain_fraction": _mean(energy_rows, "winner_drain_fraction_of_post_click"),
        "mean_loser_fraction": _mean(energy_rows, "loser_fraction_of_post_click"),
        "mean_winner_branch_fraction": _mean(energy_rows, "winner_branch_fraction_of_post_click"),
        "mean_shared_leak_fraction": _mean(energy_rows, "shared_leak_fraction_of_post_click"),
        "mean_terminal_remaining_fraction": _mean(energy_rows, "terminal_remaining_fraction_of_post_click"),
        "mean_activated_winner_drain_fraction": _mean(activated_energy_rows, "winner_drain_fraction_of_post_click"),
        "mean_activated_loser_fraction": _mean(activated_energy_rows, "loser_fraction_of_post_click"),
        "mean_activated_winner_branch_fraction": _mean(activated_energy_rows, "winner_branch_fraction_of_post_click"),
        "mean_activated_shared_leak_fraction": _mean(activated_energy_rows, "shared_leak_fraction_of_post_click"),
        "mean_activated_terminal_remaining_fraction": _mean(activated_energy_rows, "terminal_remaining_fraction_of_post_click"),
        "winner_drain_dominance_rate": float(np.mean(dominance_hits)) if dominance_hits else 0.0,
        "winner_drain_dominant": bool(dominance_hits and all(dominance_hits)),
        "completion_rate": float(np.mean([float(bool(row["trial_complete"])) for row in closure_rows])) if closure_rows else 0.0,
        "mean_completion_time_s": float(np.mean(completion_times)) if completion_times.size else float("inf"),
        "monotonic_remaining_energy": bool(all(bool(row["monotonic_remaining_energy"]) for row in closure_rows)),
        "mean_terminal_loser_suppression": (
            float(np.mean([float(row["terminal_loser_suppression_mean"]) for row in closure_rows]))
            if closure_rows
            else 0.0
        ),
    }


def build_chsh_result(case_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    exact_correlators = {
        str(row["case"]): float(row["correlator_exact"])
        for row in case_rows
        if str(row["case"]) in {"a0b0", "a0b1", "a1b0", "a1b1"}
    }
    empirical_correlators = {
        str(row["case"]): float(row["correlator_empirical"])
        for row in case_rows
        if str(row["case"]) in {"a0b0", "a0b1", "a1b0", "a1b1"}
    }
    if set(exact_correlators) != {"a0b0", "a0b1", "a1b0", "a1b1"}:
        return {
            "available": False,
            "rows": [],
            "exact_s": float("nan"),
            "empirical_s": float("nan"),
            "abs_error": float("nan"),
        }
    return {
        "available": True,
        "rows": [
            {
                "label": label,
                "correlator_exact": exact_correlators[label],
                "correlator_empirical": empirical_correlators[label],
                "correlator_error": abs(empirical_correlators[label] - exact_correlators[label]),
            }
            for label in ("a0b0", "a0b1", "a1b0", "a1b1")
        ],
        **chsh_metrics(exact_correlators, empirical_correlators),
    }


def build_summary_metrics(
    case_rows: Sequence[Mapping[str, Any]],
    pre_click_rows: Sequence[Mapping[str, Any]],
    post_click_rows: Sequence[Mapping[str, Any]],
    energy_summary: Mapping[str, Any],
    chsh_result: Mapping[str, Any],
) -> dict[str, Any]:
    winner_aggregate = aggregate_case_error(case_rows, rms_key="winner_rms_error", max_key="winner_max_error")
    pre_click_rms_values = np.asarray(
        [float(row["winner_frequency_rms_shift"]) for row in pre_click_rows],
        dtype=float,
    )
    pre_click_max_values = np.asarray(
        [float(row["winner_frequency_max_shift"]) for row in pre_click_rows],
        dtype=float,
    )
    summary = {
        "winner_law_rms_error": float(winner_aggregate["rms_error"]),
        "winner_law_max_error": float(winner_aggregate["max_abs_error"]),
        "correlator_rms_error": float(correlator_rms_error(case_rows, key="correlator_error")),
        "chsh_exact": float(chsh_result["exact_s"]),
        "chsh_empirical": float(chsh_result["empirical_s"]),
        "chsh_abs_error": float(chsh_result["abs_error"]),
        "pre_click_transparency_rms_shift": float(np.sqrt(np.mean(pre_click_rms_values**2))) if pre_click_rows else 0.0,
        "pre_click_transparency_max_shift": float(np.max(pre_click_max_values)) if pre_click_rows else 0.0,
        "mean_decisive_fraction": float(np.mean([float(row["decisive_fraction"]) for row in case_rows])) if case_rows else 0.0,
        "mean_timeout_fraction": float(np.mean([float(row["timeout_fraction"]) for row in case_rows])) if case_rows else 0.0,
        "mean_activation_rate": float(np.mean([float(row["activation_rate"]) for row in post_click_rows])) if post_click_rows else 0.0,
        "mean_winner_drain_fraction_of_post_click": float(
            np.mean([float(row["mean_activated_winner_drain_fraction"]) for row in post_click_rows])
        )
        if post_click_rows
        else 0.0,
        "mean_loser_fraction_of_post_click": float(
            np.mean([float(row["mean_activated_loser_fraction"]) for row in post_click_rows])
        )
        if post_click_rows
        else 0.0,
        "mean_winner_branch_fraction_of_post_click": float(
            np.mean([float(row["mean_activated_winner_branch_fraction"]) for row in post_click_rows])
        )
        if post_click_rows
        else 0.0,
        "winner_drain_dominance_rate": float(
            np.mean([float(row["winner_drain_dominance_rate"]) for row in post_click_rows])
        )
        if post_click_rows
        else 0.0,
        "completion_rate": float(np.mean([float(row["completion_rate"]) for row in post_click_rows])) if post_click_rows else 0.0,
        "mean_completion_time_s": float(
            np.mean([float(row["mean_completion_time_s"]) for row in post_click_rows if np.isfinite(float(row["mean_completion_time_s"]))])
        )
        if any(np.isfinite(float(row["mean_completion_time_s"])) for row in post_click_rows)
        else float("inf"),
        "monotonic_remaining_energy": bool(all(bool(row["monotonic_remaining_energy"]) for row in post_click_rows)),
        "mean_terminal_loser_suppression": float(
            np.mean([float(row["mean_terminal_loser_suppression"]) for row in post_click_rows])
        )
        if post_click_rows
        else 0.0,
        "mean_pre_click_fraction_of_total": float(energy_summary["mean_pre_click_fraction_of_total"]),
        "mean_initial_remaining_fraction_of_total": float(energy_summary["mean_initial_remaining_fraction_of_total"]),
        "mean_winner_drain_fraction_of_total": float(energy_summary["mean_winner_drain_fraction_of_total"]),
        "mean_loser_fraction_of_total": float(energy_summary["mean_loser_fraction_of_total"]),
        "mean_shared_leak_fraction_of_total": float(energy_summary["mean_shared_leak_fraction_of_total"]),
        "mean_terminal_remaining_fraction_of_total": float(energy_summary["mean_terminal_remaining_fraction_of_total"]),
        "max_energy_balance_abs_fraction": float(energy_summary["max_energy_balance_abs_fraction"]),
        "finite_energy_accounting": bool(energy_summary["finite_outputs"]),
    }
    summary["winner_law_pass"] = (
        float(summary["winner_law_rms_error"]) < 0.03 and float(summary["winner_law_max_error"]) < 0.05
    )
    summary["correlator_pass"] = float(summary["correlator_rms_error"]) < 0.05
    summary["chsh_pass"] = bool(chsh_result["available"]) and float(summary["chsh_abs_error"]) < 0.1
    summary["pre_click_transparency_pass"] = (
        float(summary["pre_click_transparency_rms_shift"]) < 0.01
        and float(summary["pre_click_transparency_max_shift"]) < 0.01
    )
    summary["winner_drain_dominance_pass"] = (
        float(summary["winner_drain_dominance_rate"]) >= 0.99
        and float(summary["mean_winner_drain_fraction_of_post_click"]) > 0.75
    )
    summary["loser_residual_pass"] = float(summary["mean_loser_fraction_of_post_click"]) < 0.05
    summary["monotonic_shared_energy_decay_pass"] = bool(summary["monotonic_remaining_energy"])
    summary["completion_pass"] = float(summary["completion_rate"]) > 0.9
    summary["energy_accounting_pass"] = bool(energy_summary["energy_accounting_pass"])
    summary["proceed_to_next_phase"] = all(
        bool(summary[key])
        for key in (
            "winner_law_pass",
            "correlator_pass",
            "chsh_pass",
            "pre_click_transparency_pass",
            "winner_drain_dominance_pass",
            "loser_residual_pass",
            "monotonic_shared_energy_decay_pass",
            "completion_pass",
            "energy_accounting_pass",
        )
    )
    return summary
