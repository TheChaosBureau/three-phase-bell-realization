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


def plot_device_subblock_component_summary(example_front_end: dict[str, Any]) -> Figure:
    figure = Figure(figsize=(9.6, 4.8), dpi=120)
    axes = figure.subplots(1, 2)
    components = list(example_front_end["device_physicalization"]["device_components"])
    counts = Counter(component["group"] for component in components)
    axes[0].bar(
        list(counts.keys()),
        list(counts.values()),
        color=["#4c78a8", "#f58518"],
    )
    axes[0].set_title("Device-level subblock component counts")
    axes[0].tick_params(axis="x", rotation=20)

    topology = dict(example_front_end["device_physicalization"]["topology_summary"])
    summary_lines = [
        f"total components: {topology['component_count']}",
        f"device components: {topology['device_component_count']}",
        f"device nodes: {topology['device_node_count']}",
        f"selected subblocks: {topology['selected_subblock_count']}",
        "",
        f"common inhibit components: {topology['common_inhibit_device_component_count']}",
        f"winner drain components: {topology['winner_drain_device_component_count']}",
        f"matrix density: {topology['matrix_density']:.3f}",
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
    axes[1].set_title("Subblock summary")
    axes[1].axis("off")
    figure.tight_layout()
    return figure


def plot_device_subblock_node_snapshot(example_front_end: dict[str, Any]) -> Figure:
    figure = Figure(figsize=(8.8, 4.8), dpi=120)
    axes = figure.subplots(1, 2)
    closure_nodes = dict(example_front_end["shared_core"]["closure_node_voltage_v"])
    device_nodes = dict(example_front_end["shared_core"]["device_node_voltage_v"])
    axes[0].bar(
        list(closure_nodes.keys()),
        [abs(complex(value)) for value in closure_nodes.values()],
        color="#e45756",
    )
    axes[0].set_title("Codesign closure node voltage magnitude")
    axes[0].tick_params(axis="x", rotation=20)
    axes[1].bar(
        list(device_nodes.keys()),
        [abs(complex(value)) for value in device_nodes.values()],
        color="#54a24b",
    )
    axes[1].set_title("Physicalized device node voltage magnitude")
    axes[1].tick_params(axis="x", rotation=20)
    figure.tight_layout()
    return figure


def plot_device_subblock_internal_signals(example_trial: dict[str, Any]) -> Figure:
    physical = dict(example_trial["physical"])
    figure = Figure(figsize=(11.0, 7.2), dpi=120)
    axes = figure.subplots(2, 3)
    time_s = physical["time_s"]
    axes[0, 0].plot(time_s, physical["trigger_sense_v"], color="#4c78a8")
    axes[0, 0].plot(time_s, physical["trigger_comparator_output"], color="#f58518")
    axes[0, 0].set_title("Sense / comparator")

    axes[0, 1].plot(time_s, physical["inhibit_store_v"], color="#54a24b")
    axes[0, 1].plot(time_s, physical["common_inhibit_v"], color="#e45756")
    axes[0, 1].set_title("Inhibit storage / rail")

    axes[0, 2].plot(time_s, physical["winner_gate_driver_v"], color="#72b7b2")
    axes[0, 2].plot(time_s, physical["winner_gate_v"], color="#b279a2")
    axes[0, 2].set_title("Gate driver")

    axes[1, 0].plot(time_s, physical["winner_switch_conductance_s"], color="#f58518")
    axes[1, 0].set_title("Winner switch conductance")

    axes[1, 1].plot(time_s, physical["winner_switch_channel_current_a"], color="#4c78a8")
    axes[1, 1].plot(time_s, physical["winner_drain_current_a"], color="#54a24b")
    axes[1, 1].set_title("Switch / drain current")

    axes[1, 2].plot(time_s, physical["drain_dump_voltage_v"], color="#e45756")
    axes[1, 2].plot(time_s, physical["winner_drain_tank_voltage_v"], color="#72b7b2")
    axes[1, 2].set_title("Dump / drain voltage")

    for axis in axes.ravel():
        axis.set_xlabel("Time (s)")
    figure.tight_layout()
    return figure


def plot_device_pre_click_transparency(rows: list[dict[str, Any]]) -> Figure:
    return plot_pre_click_transparency(rows)


def plot_device_winner_frequency(rows: list[dict[str, Any]]) -> Figure:
    return plot_four_branch_winner_frequency(rows)


def plot_device_correlator(rows: list[dict[str, Any]]) -> Figure:
    return plot_correlator_exact_vs_empirical(rows)


def plot_device_chsh(chsh_result: dict[str, Any]) -> Figure:
    return plot_chsh_exact_vs_empirical(chsh_result)


def plot_device_candidate_comparison(rows: list[dict[str, Any]]) -> Figure:
    return plot_candidate_metric_comparison(rows)


__all__ = [
    "plot_device_candidate_comparison",
    "plot_device_chsh",
    "plot_device_correlator",
    "plot_device_pre_click_transparency",
    "plot_device_subblock_component_summary",
    "plot_device_subblock_internal_signals",
    "plot_device_subblock_node_snapshot",
    "plot_device_winner_frequency",
    "plot_loser_residual_fraction",
    "plot_remaining_shared_energy_trace",
    "plot_whole_trial_energy_flow",
    "plot_winner_drain_fraction",
]
