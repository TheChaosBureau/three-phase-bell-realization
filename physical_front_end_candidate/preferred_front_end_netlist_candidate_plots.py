from __future__ import annotations

from collections import Counter
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
)
from .preferred_physical_chain_plots import plot_whole_trial_energy_flow


def plot_netlist_topology(example_front_end: dict[str, Any]) -> Figure:
    figure = Figure(figsize=(10.2, 5.6), dpi=120)
    axes = figure.subplots(1, 2)
    axis = axes[0]
    positions = {
        "++": (0.2, 0.8),
        "+-": (0.8, 0.8),
        "-+": (0.8, 0.2),
        "--": (0.2, 0.2),
    }
    for label, (x_pos, y_pos) in positions.items():
        axis.scatter([x_pos], [y_pos], s=420, color="#f3f7fb", edgecolors="#4c78a8", linewidths=2.0, zorder=3)
        axis.text(x_pos, y_pos, label, ha="center", va="center", fontsize=12, color="#1f3a5f", zorder=4)
        axis.plot([x_pos, x_pos], [y_pos, y_pos - 0.12], color="#bbbbbb", linewidth=1.2, zorder=1)
        axis.text(x_pos, y_pos - 0.16, "R/L/C\nbranch", ha="center", va="top", fontsize=8, color="#666666")

    components = list(example_front_end["netlist"]["components"])
    coupling_components = [component for component in components if component["group"] == "coupling"]
    for component in coupling_components:
        left = component["node_pos"].replace("n_", "").replace("p", "+").replace("m", "-")
        right = component["node_neg"].replace("n_", "").replace("p", "+").replace("m", "-")
        if left not in positions or right not in positions:
            continue
        x0, y0 = positions[left]
        x1, y1 = positions[right]
        color = "#54a24b" if component["kind"] == "capacitor" else "#f58518"
        axis.plot([x0, x1], [y0, y1], color=color, linewidth=2.0, alpha=0.8, zorder=2)

    axis.set_title("Component-level front-end topology")
    axis.set_xlim(0.0, 1.0)
    axis.set_ylim(0.0, 1.0)
    axis.axis("off")

    counts = Counter(component["kind"] for component in components)
    summary_lines = [
        f"nodes: {example_front_end['netlist']['topology_summary']['node_count']}",
        f"components: {example_front_end['netlist']['topology_summary']['component_count']}",
        f"couplers: {example_front_end['netlist']['topology_summary']['coupling_component_count']}",
        "",
        *[f"{kind}: {count}" for kind, count in sorted(counts.items())],
    ]
    axes[1].text(
        0.02,
        0.98,
        "\n".join(summary_lines),
        ha="left",
        va="top",
        fontsize=10,
        family="monospace",
        color="#1f1f1f",
    )
    axes[1].set_title("Netlist element counts")
    axes[1].axis("off")
    figure.tight_layout()
    return figure


def plot_netlist_modal_diagnostics(example_front_end: dict[str, Any]) -> Figure:
    shared = dict(example_front_end["shared_core"])
    return plot_shared_core_diagnostics(
        {
            "state_labels": list(shared["state_labels"]),
            "prepared_state_magnitude": list(shared["prepared_state_magnitude"]),
            "modal_energies": list(shared["modal_energies"]),
        }
    )


def plot_netlist_resonant_mode_diagnostics(example_front_end: dict[str, Any]) -> Figure:
    shared = dict(example_front_end["shared_core"])
    return plot_resonant_mode_diagnostics(
        {
            "modal_response_magnitude": list(shared["modal_response_magnitude"]),
            "modal_decay_rates": list(shared["modal_decay_rates"]),
            "mode_overlap_profile": list(shared["mode_overlap_profile"]),
        }
    )


def plot_netlist_node_magnitudes(example_front_end: dict[str, Any]) -> Figure:
    figure = Figure(figsize=(8.4, 4.6), dpi=120)
    axes = figure.subplots(1, 2)
    labels = list(example_front_end["branch_labels"])
    node_voltage = np.abs(np.asarray(example_front_end["netlist"]["node_voltage_v"], dtype=np.complex128))
    source_current = np.abs(
        np.asarray([row["norton_current_a"] for row in example_front_end["netlist"]["source_branches"]], dtype=np.complex128)
    )
    axes[0].bar(labels, node_voltage, color="#4c78a8")
    axes[0].set_title("Solved node voltage magnitude")
    axes[0].set_ylabel("|V|")
    axes[1].bar(labels, source_current, color="#f58518")
    axes[1].set_title("Norton drive current magnitude")
    axes[1].set_ylabel("|I|")
    figure.tight_layout()
    return figure


def plot_netlist_front_end_fraction(rows: list[dict[str, Any]]) -> Figure:
    return plot_four_branch_fraction_comparison(rows)


def plot_netlist_winner_frequency(rows: list[dict[str, Any]]) -> Figure:
    return plot_four_branch_winner_frequency(rows)


def plot_netlist_correlator(rows: list[dict[str, Any]]) -> Figure:
    return plot_correlator_exact_vs_empirical(rows)


def plot_netlist_chsh(chsh_result: dict[str, Any]) -> Figure:
    return plot_chsh_exact_vs_empirical(chsh_result)


def plot_netlist_candidate_comparison(rows: list[dict[str, Any]]) -> Figure:
    return plot_candidate_metric_comparison(rows)


__all__ = [
    "plot_netlist_candidate_comparison",
    "plot_netlist_chsh",
    "plot_netlist_correlator",
    "plot_netlist_front_end_fraction",
    "plot_netlist_modal_diagnostics",
    "plot_netlist_node_magnitudes",
    "plot_netlist_resonant_mode_diagnostics",
    "plot_netlist_topology",
    "plot_netlist_winner_frequency",
    "plot_whole_trial_energy_flow",
]
