from __future__ import annotations

from typing import Any

import numpy as np
from matplotlib.figure import Figure

from .plots import (
    plot_candidate_metric_comparison,
    plot_chsh_exact_vs_empirical,
    plot_correlator_exact_vs_empirical,
    plot_four_branch_fraction_comparison,
    plot_four_branch_winner_frequency,
    plot_resonant_mode_diagnostics,
    plot_shared_core_diagnostics,
    plot_winner_drain_power,
)
from .preferred_physical_chain_plots import (
    plot_loser_residual_fraction,
    plot_remaining_shared_energy_trace,
    plot_whole_trial_energy_flow,
    plot_winner_drain_fraction,
)


def plot_lc_shared_core_modal_diagnostics(example_front_end: dict[str, Any]) -> Figure:
    shared = dict(example_front_end["shared_core"])
    return plot_shared_core_diagnostics(
        {
            "state_labels": list(shared["state_labels"]),
            "prepared_state_magnitude": list(shared["prepared_state_magnitude"]),
            "modal_energies": list(shared["modal_energies"]),
        }
    )


def plot_lc_resonant_mode_diagnostics(example_front_end: dict[str, Any]) -> Figure:
    shared = dict(example_front_end["shared_core"])
    return plot_resonant_mode_diagnostics(
        {
            "modal_response_magnitude": list(shared["modal_response_magnitude"]),
            "modal_decay_rates": list(shared["modal_decay_rates"]),
            "mode_overlap_profile": list(shared["mode_overlap_profile"]),
        }
    )


def plot_lc_coupled_port_diagnostics(example_front_end: dict[str, Any]) -> Figure:
    shared = dict(example_front_end["shared_core"])
    figure = Figure(figsize=(9.6, 4.8), dpi=120)
    axes = figure.subplots(1, 2)
    labels = list(example_front_end["branch_labels"])
    node_voltage = np.abs(np.asarray(shared["port_node_voltage_v"], dtype=np.complex128))
    source_current = np.abs(np.asarray(shared["source_current_a"], dtype=np.complex128))
    axes[0].bar(labels, node_voltage, color="#4c78a8", alpha=0.85, label="|V_port|")
    axes[0].plot(labels, source_current, "o", color="#f58518", label="|I_source|")
    axes[0].set_title("Explicit coupled-port node magnitudes")
    axes[0].set_ylabel("Magnitude")
    axes[0].legend(fontsize=8)

    coupling_rows = list(dict(shared["coupling_currents_a"]).items())
    coupling_labels = [label.replace("_", "\n") for label, _ in coupling_rows]
    coupling_magnitude = [abs(value) for _, value in coupling_rows]
    axes[1].bar(coupling_labels, coupling_magnitude, color="#54a24b")
    axes[1].set_title("Bridge / return coupling currents")
    axes[1].set_ylabel("|I_coupling|")
    axes[1].tick_params(axis="x", labelsize=8)
    figure.tight_layout()
    return figure


def plot_lc_front_end_fraction(rows: list[dict[str, Any]]) -> Figure:
    return plot_four_branch_fraction_comparison(rows)


def plot_lc_winner_frequency(rows: list[dict[str, Any]]) -> Figure:
    return plot_four_branch_winner_frequency(rows)


def plot_lc_correlator(rows: list[dict[str, Any]]) -> Figure:
    return plot_correlator_exact_vs_empirical(rows)


def plot_lc_chsh(chsh_result: dict[str, Any]) -> Figure:
    return plot_chsh_exact_vs_empirical(chsh_result)


def plot_lc_candidate_comparison(rows: list[dict[str, Any]]) -> Figure:
    return plot_candidate_metric_comparison(rows)


__all__ = [
    "plot_lc_candidate_comparison",
    "plot_lc_chsh",
    "plot_lc_correlator",
    "plot_lc_coupled_port_diagnostics",
    "plot_lc_front_end_fraction",
    "plot_lc_resonant_mode_diagnostics",
    "plot_lc_shared_core_modal_diagnostics",
    "plot_lc_winner_frequency",
    "plot_loser_residual_fraction",
    "plot_remaining_shared_energy_trace",
    "plot_whole_trial_energy_flow",
    "plot_winner_drain_fraction",
    "plot_winner_drain_power",
]
