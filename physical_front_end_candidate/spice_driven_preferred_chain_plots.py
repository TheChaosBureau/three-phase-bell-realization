from __future__ import annotations

from typing import Any

from matplotlib.figure import Figure

from .actual_spice_front_end_plots import (
    plot_spice_branch_current,
    plot_spice_branch_power,
    plot_spice_branch_voltage,
)
from .plots import (
    plot_candidate_metric_comparison,
    plot_chsh_exact_vs_empirical,
    plot_correlator_exact_vs_empirical,
    plot_four_branch_export_envelopes,
    plot_four_branch_winner_frequency,
)
from .preferred_chain_device_physicalization_plots import (
    plot_loser_residual_fraction,
    plot_remaining_shared_energy_trace,
    plot_whole_trial_energy_flow,
    plot_winner_drain_fraction,
)


def plot_spice_driven_branch_voltage(example_front_end: dict[str, Any]) -> Figure:
    adapted = {
        "case": example_front_end["case"],
        "branch_labels": list(example_front_end["branch_labels"]),
        "branch_voltage_v": dict(example_front_end["raw_spice_branch_voltage_v"]),
        "time_s": list(example_front_end["raw_spice_time_s"]),
    }
    return plot_spice_branch_voltage(adapted)


def plot_spice_driven_branch_current(example_front_end: dict[str, Any]) -> Figure:
    adapted = {
        "case": example_front_end["case"],
        "branch_labels": list(example_front_end["branch_labels"]),
        "branch_current_a": dict(example_front_end["raw_spice_branch_current_a"]),
        "time_s": list(example_front_end["raw_spice_time_s"]),
    }
    return plot_spice_branch_current(adapted)


def plot_spice_driven_branch_power(example_front_end: dict[str, Any]) -> Figure:
    adapted = {
        "case": example_front_end["case"],
        "branch_labels": list(example_front_end["branch_labels"]),
        "branch_power_w": dict(example_front_end["raw_spice_branch_power_w"]),
        "time_s": list(example_front_end["raw_spice_time_s"]),
    }
    return plot_spice_branch_power(adapted)


def plot_spice_driven_boundary_export(example_front_end: dict[str, Any]) -> Figure:
    adapted = {
        "case": example_front_end["case"],
        "branch_labels": list(example_front_end["branch_labels"]),
        "time_s": list(example_front_end["time_s"]),
        "branch_power_w": dict(example_front_end["branch_power_w"]),
        "export_time_s": list(example_front_end["export_time_s"]),
        "exported_branch_power": dict(example_front_end["exported_branch_power"]),
    }
    return plot_four_branch_export_envelopes(adapted)


def plot_spice_driven_winner_frequency(rows: list[dict[str, Any]]) -> Figure:
    return plot_four_branch_winner_frequency(rows)


def plot_spice_driven_correlator(rows: list[dict[str, Any]]) -> Figure:
    return plot_correlator_exact_vs_empirical(rows)


def plot_spice_driven_chsh(chsh_result: dict[str, Any]) -> Figure:
    return plot_chsh_exact_vs_empirical(chsh_result)


def plot_spice_driven_candidate_comparison(rows: list[dict[str, Any]]) -> Figure:
    adapted = [
        {
            "candidate": row["candidate"],
            "front_end_rms_error": row["front_end_rms_error"],
            "winner_rms_error": row["winner_rms_error"],
            "correlator_rms_error": row["correlator_rms_error"],
        }
        for row in rows
    ]
    return plot_candidate_metric_comparison(adapted)


__all__ = [
    "plot_loser_residual_fraction",
    "plot_remaining_shared_energy_trace",
    "plot_spice_driven_boundary_export",
    "plot_spice_driven_branch_current",
    "plot_spice_driven_branch_power",
    "plot_spice_driven_branch_voltage",
    "plot_spice_driven_candidate_comparison",
    "plot_spice_driven_chsh",
    "plot_spice_driven_correlator",
    "plot_spice_driven_winner_frequency",
    "plot_whole_trial_energy_flow",
    "plot_winner_drain_fraction",
]
