from __future__ import annotations

from collections import Counter
from typing import Any

import numpy as np
from matplotlib.figure import Figure

from .plots import (
    plot_candidate_metric_comparison,
    plot_chsh_exact_vs_empirical,
    plot_correlator_exact_vs_empirical,
    plot_four_branch_winner_frequency,
)
from .preferred_physical_chain_plots import (
    plot_loser_residual_fraction,
    plot_pre_click_transparency,
    plot_remaining_shared_energy_trace,
    plot_whole_trial_energy_flow,
    plot_winner_drain_fraction,
)


def plot_codesign_topology(example_front_end: dict[str, Any]) -> Figure:
    figure = Figure(figsize=(11.0, 6.0), dpi=120)
    axes = figure.subplots(1, 2)
    axis = axes[0]
    integration_ports = dict(example_front_end["netlist"]["integration_ports"])
    branch_nodes = dict(integration_ports["branch_nodes"])
    positions = {
        branch_nodes["++"]: (0.18, 0.74),
        branch_nodes["+-"]: (0.82, 0.74),
        branch_nodes["-+"]: (0.82, 0.26),
        branch_nodes["--"]: (0.18, 0.26),
        integration_ports["common_inhibit_node_name"]: (0.50, 0.90),
        integration_ports["winner_gate_node_name"]: (0.76, 0.50),
        integration_ports["drain_node_name"]: (0.50, 0.50),
        integration_ports["shared_leak_node_name"]: (0.24, 0.50),
    }
    node_labels = {
        branch_nodes["++"]: "++",
        branch_nodes["+-"]: "+-",
        branch_nodes["-+"]: "-+",
        branch_nodes["--"]: "--",
        integration_ports["common_inhibit_node_name"]: "Inhibit",
        integration_ports["winner_gate_node_name"]: "Gate",
        integration_ports["drain_node_name"]: "Drain",
        integration_ports["shared_leak_node_name"]: "Leak",
    }
    node_colors = {
        "branch": "#f3f7fb",
        "common_inhibit": "#fff2d8",
        "winner_gate": "#fde2e4",
        "drain": "#ffe8cc",
        "shared_leak": "#e3f6e8",
    }
    components = list(example_front_end["netlist"]["components"])
    for component in components:
        node_pos = component["node_pos"]
        node_neg = component["node_neg"]
        if node_pos not in positions or node_neg not in positions:
            continue
        x0, y0 = positions[node_pos]
        x1, y1 = positions[node_neg]
        color = "#c6c6c6"
        linewidth = 1.4
        alpha = 0.6
        if component["group"] == "coupling":
            color = "#54a24b" if component["kind"] == "capacitor" else "#f58518"
            linewidth = 2.0
            alpha = 0.8
        elif component["group"] == "closure":
            color = "#e45756" if "CLAMP" in component["name"] else "#4c78a8"
            linewidth = 1.8
            alpha = 0.75
        axis.plot([x0, x1], [y0, y1], color=color, linewidth=linewidth, alpha=alpha, zorder=1)

    for node_name, (x_pos, y_pos) in positions.items():
        category = "branch"
        if node_name == integration_ports["common_inhibit_node_name"]:
            category = "common_inhibit"
        elif node_name == integration_ports["winner_gate_node_name"]:
            category = "winner_gate"
        elif node_name == integration_ports["drain_node_name"]:
            category = "drain"
        elif node_name == integration_ports["shared_leak_node_name"]:
            category = "shared_leak"
        axis.scatter(
            [x_pos],
            [y_pos],
            s=460 if category == "branch" else 380,
            color=node_colors[category],
            edgecolors="#355070",
            linewidths=1.8,
            zorder=3,
        )
        axis.text(
            x_pos,
            y_pos,
            node_labels[node_name],
            ha="center",
            va="center",
            fontsize=11 if category == "branch" else 9,
            color="#223047",
            zorder=4,
        )

    axis.set_title("Integrated front-end plus closure/drain topology")
    axis.set_xlim(0.04, 0.96)
    axis.set_ylim(0.08, 0.96)
    axis.axis("off")

    counts = Counter(component["kind"] for component in components)
    topology = dict(example_front_end["codesign"]["topology_summary"])
    semantics = dict(example_front_end["codesign"]["integration_semantics"])
    summary_lines = [
        f"nodes: {topology['node_count']}",
        f"front-end components: {topology['front_end_component_count']}",
        f"closure components: {topology['closure_component_count']}",
        f"branch attachments: {topology['closure_attachment_count']}",
        "",
        *[f"{kind}: {count}" for kind, count in sorted(counts.items())],
        "",
        f"shared component table: {semantics['shared_front_end_and_closure_component_table']}",
        f"attached closure present pre-click: {semantics['closure_present_in_pre_click_netlist']}",
        f"post-click derived from attachments: {semantics['post_click_parameters_derived_from_attached_components']}",
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
    axes[1].set_title("Codesign summary")
    axes[1].axis("off")
    figure.tight_layout()
    return figure


def plot_codesign_pre_click_transparency(rows: list[dict[str, Any]]) -> Figure:
    return plot_pre_click_transparency(rows)


def plot_codesign_winner_frequency(rows: list[dict[str, Any]]) -> Figure:
    return plot_four_branch_winner_frequency(rows)


def plot_codesign_correlator(rows: list[dict[str, Any]]) -> Figure:
    return plot_correlator_exact_vs_empirical(rows)


def plot_codesign_chsh(chsh_result: dict[str, Any]) -> Figure:
    return plot_chsh_exact_vs_empirical(chsh_result)


def plot_codesign_candidate_comparison(rows: list[dict[str, Any]]) -> Figure:
    return plot_candidate_metric_comparison(rows)


def plot_codesign_node_voltage_snapshot(example_front_end: dict[str, Any]) -> Figure:
    figure = Figure(figsize=(8.8, 4.8), dpi=120)
    axes = figure.subplots(1, 2)
    branch_labels = list(example_front_end["branch_labels"])
    shared = dict(example_front_end["shared_core"])
    branch_voltage = np.abs(np.asarray(shared["integrated_branch_node_voltage_v"], dtype=np.complex128))
    closure_nodes = dict(shared["closure_node_voltage_v"])
    closure_labels = list(closure_nodes.keys())
    closure_voltage = [abs(complex(value)) for value in closure_nodes.values()]
    axes[0].bar(branch_labels, branch_voltage, color="#4c78a8")
    axes[0].set_title("Integrated branch-node voltage magnitude")
    axes[0].set_ylabel("|V|")
    axes[1].bar(closure_labels, closure_voltage, color="#e45756")
    axes[1].set_title("Attached closure-node voltage magnitude")
    axes[1].tick_params(axis="x", rotation=20)
    figure.tight_layout()
    return figure


__all__ = [
    "plot_codesign_candidate_comparison",
    "plot_codesign_chsh",
    "plot_codesign_correlator",
    "plot_codesign_node_voltage_snapshot",
    "plot_codesign_pre_click_transparency",
    "plot_codesign_topology",
    "plot_codesign_winner_frequency",
    "plot_loser_residual_fraction",
    "plot_remaining_shared_energy_trace",
    "plot_whole_trial_energy_flow",
    "plot_winner_drain_fraction",
]
