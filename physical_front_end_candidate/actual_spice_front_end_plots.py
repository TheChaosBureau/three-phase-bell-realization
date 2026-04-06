from __future__ import annotations

from typing import Any

import numpy as np
from matplotlib.figure import Figure

from .plots import (
    plot_candidate_metric_comparison,
    plot_chsh_exact_vs_empirical,
    plot_correlator_exact_vs_empirical,
    plot_four_branch_fraction_comparison,
)


def _plot_branch_trace(example_front_end: dict[str, Any], *, key: str, ylabel: str, title: str) -> Figure:
    figure = Figure(figsize=(8.2, 4.8), dpi=120)
    axis = figure.subplots()
    colors = {"++": "#4c78a8", "+-": "#f58518", "-+": "#54a24b", "--": "#e45756"}
    time_s = np.asarray(example_front_end["time_s"], dtype=float)
    for label in example_front_end["branch_labels"]:
        values = np.asarray(example_front_end[key][label], dtype=float)
        axis.plot(time_s, values, color=colors.get(label), label=label)
    axis.set_xlabel("Time (s)")
    axis.set_ylabel(ylabel)
    axis.set_title(title)
    axis.legend(fontsize=8)
    figure.tight_layout()
    return figure


def plot_spice_netlist_topology(example_front_end: dict[str, Any]) -> Figure:
    figure = Figure(figsize=(10.8, 5.6), dpi=120)
    axes = figure.subplots(1, 2)
    axis = axes[0]

    core_positions = {
        "++": (0.18, 0.78),
        "+-": (0.48, 0.78),
        "-+": (0.48, 0.28),
        "--": (0.18, 0.28),
    }
    output_positions = {
        "++": (0.82, 0.78),
        "+-": (1.12, 0.78),
        "-+": (1.12, 0.28),
        "--": (0.82, 0.28),
    }
    for label, (x_pos, y_pos) in core_positions.items():
        axis.scatter([x_pos], [y_pos], s=360, color="#eef4fb", edgecolors="#4c78a8", linewidths=2.0, zorder=3)
        axis.text(x_pos, y_pos, f"core {label}", ha="center", va="center", fontsize=10, color="#1f3a5f")
        axis.plot([x_pos - 0.1, x_pos], [y_pos, y_pos], color="#999999", linewidth=1.3, zorder=1)
        axis.text(x_pos - 0.12, y_pos, "Isrc", ha="right", va="center", fontsize=8, color="#666666")
    for label, (x_pos, y_pos) in output_positions.items():
        axis.scatter([x_pos], [y_pos], s=360, color="#f6fbef", edgecolors="#54a24b", linewidths=2.0, zorder=3)
        axis.text(x_pos, y_pos, f"out {label}", ha="center", va="center", fontsize=10, color="#24502b")
        axis.plot([x_pos, x_pos], [y_pos, y_pos - 0.15], color="#999999", linewidth=1.2)
        axis.text(x_pos, y_pos - 0.18, "Rload/Cread", ha="center", va="top", fontsize=8, color="#666666")
        core_x, core_y = core_positions[label]
        axis.annotate(
            "",
            xy=(x_pos - 0.09, y_pos),
            xytext=(core_x + 0.09, core_y),
            arrowprops={"arrowstyle": "->", "color": "#f58518", "linewidth": 1.6},
        )
    coupling_edges = [
        ("++", "+-"),
        ("++", "-+"),
        ("--", "+-"),
        ("--", "-+"),
        ("+-", "-+"),
        ("++", "--"),
    ]
    for left, right in coupling_edges:
        x0, y0 = core_positions[left]
        x1, y1 = core_positions[right]
        axis.plot([x0, x1], [y0, y1], color="#54a24b", linewidth=2.0, alpha=0.8, zorder=2)

    axis.set_xlim(0.0, 1.3)
    axis.set_ylim(0.05, 1.0)
    axis.set_title("Actual SPICE front-end topology / node map")
    axis.axis("off")

    topology = dict(example_front_end["netlist"]["topology_summary"])
    summary_lines = [
        f"engine: {example_front_end['spice']['engine']}",
        f"carrier_hz: {float(example_front_end['spice']['target_carrier_hz']):.1f}",
        "",
        f"components: {topology['component_count']}",
        f"core components: {topology['core_component_count']}",
        f"couplers: {topology['coupling_component_count']}",
        f"output probes: {topology['output_probe_count']}",
        f"behavioral sources: {topology['behavioral_source_count']}",
        "",
        "probe nodes:",
        *[f"{label}: {example_front_end['spice']['probe_nodes']['output'][label]}" for label in example_front_end["branch_labels"]],
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
    axes[1].set_title("Probe map")
    axes[1].axis("off")
    figure.tight_layout()
    return figure


def plot_spice_branch_voltage(example_front_end: dict[str, Any]) -> Figure:
    return _plot_branch_trace(
        example_front_end,
        key="branch_voltage_v",
        ylabel="Voltage (V)",
        title=f"Representative branch voltage traces: {example_front_end['case']}",
    )


def plot_spice_branch_current(example_front_end: dict[str, Any]) -> Figure:
    return _plot_branch_trace(
        example_front_end,
        key="branch_current_a",
        ylabel="Current (A)",
        title=f"Representative branch current traces: {example_front_end['case']}",
    )


def plot_spice_branch_power(example_front_end: dict[str, Any]) -> Figure:
    return _plot_branch_trace(
        example_front_end,
        key="branch_power_w",
        ylabel="Power (W)",
        title=f"Representative branch power traces: {example_front_end['case']}",
    )


def plot_spice_exact_vs_fraction(rows: list[dict[str, Any]]) -> Figure:
    return plot_four_branch_fraction_comparison(rows)


def plot_spice_case_comparison(rows: list[dict[str, Any]]) -> Figure:
    figure = Figure(figsize=(9.4, 4.8), dpi=120)
    axes = figure.subplots(1, 2)
    labels = [row["case"] for row in rows]
    x = np.arange(len(labels), dtype=float)
    width = 0.36
    axes[0].bar(x - width / 2.0, [row["baseline_front_end_rms_error"] for row in rows], width=width, color="#bdbdbd", label="baseline")
    axes[0].bar(x + width / 2.0, [row["spice_front_end_rms_error"] for row in rows], width=width, color="#4c78a8", label="spice")
    axes[0].set_xticks(x, labels, rotation=20)
    axes[0].set_title("Case RMS error vs current baseline")
    axes[0].set_ylabel("RMS error")
    axes[0].legend(fontsize=8)
    axes[1].bar(x - width / 2.0, [row["baseline_correlator_error"] for row in rows], width=width, color="#bdbdbd", label="baseline")
    axes[1].bar(x + width / 2.0, [row["spice_correlator_error"] for row in rows], width=width, color="#f58518", label="spice")
    axes[1].set_xticks(x, labels, rotation=20)
    axes[1].set_title("Case correlator error")
    axes[1].set_ylabel("|dE|")
    axes[1].legend(fontsize=8)
    figure.tight_layout()
    return figure


def plot_spice_residual_summary(rows: list[dict[str, Any]]) -> Figure:
    figure = Figure(figsize=(9.6, 4.8), dpi=120)
    axes = figure.subplots(1, 3)
    labels = [row["case"] for row in rows]
    axes[0].bar(labels, [row["rms_error"] for row in rows], color="#4c78a8")
    axes[0].set_title("Baseline-target RMS error")
    axes[0].tick_params(axis="x", rotation=20)
    axes[1].bar(labels, [row["max_abs_error"] for row in rows], color="#e45756")
    axes[1].set_title("Baseline-target max error")
    axes[1].tick_params(axis="x", rotation=20)
    axes[2].bar(labels, [row["exact_rms_error"] for row in rows], color="#54a24b")
    axes[2].set_title("Exact-target RMS error")
    axes[2].tick_params(axis="x", rotation=20)
    figure.suptitle("Actual SPICE front-end residual summary")
    figure.tight_layout()
    return figure


def plot_spice_candidate_comparison(rows: list[dict[str, Any]]) -> Figure:
    adapted = [
        {
            "candidate": row["candidate"],
            "front_end_rms_error": row["front_end_rms_error"],
            "winner_rms_error": row["exact_fraction_rms_error"],
            "correlator_rms_error": row["correlator_rms_error"],
        }
        for row in rows
    ]
    return plot_candidate_metric_comparison(adapted)


def plot_spice_correlator(rows: list[dict[str, Any]]) -> Figure:
    return plot_correlator_exact_vs_empirical(rows)


def plot_spice_chsh(chsh_result: dict[str, Any]) -> Figure:
    return plot_chsh_exact_vs_empirical(chsh_result)


__all__ = [
    "plot_spice_branch_current",
    "plot_spice_branch_power",
    "plot_spice_branch_voltage",
    "plot_spice_candidate_comparison",
    "plot_spice_case_comparison",
    "plot_spice_chsh",
    "plot_spice_correlator",
    "plot_spice_exact_vs_fraction",
    "plot_spice_netlist_topology",
    "plot_spice_residual_summary",
]
