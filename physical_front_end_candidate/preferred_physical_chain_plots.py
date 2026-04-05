from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure

from .plots import (
    plot_chsh_exact_vs_empirical,
    plot_correlator_exact_vs_empirical,
    plot_four_branch_winner_frequency,
    plot_remaining_shared_energy,
)


def plot_preferred_chain_winner_frequency(rows: list[dict]) -> Figure:
    return plot_four_branch_winner_frequency(rows)


def plot_preferred_chain_correlator(rows: list[dict]) -> Figure:
    return plot_correlator_exact_vs_empirical(rows)


def plot_preferred_chain_chsh(chsh_result: dict) -> Figure:
    return plot_chsh_exact_vs_empirical(chsh_result)


def plot_pre_click_transparency(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(8.4, 4.6), dpi=120)
    axes = figure.subplots(1, 2)
    labels = [row["case"] for row in rows]
    axes[0].bar(labels, [row["winner_frequency_rms_shift"] for row in rows], color="#4c78a8")
    axes[0].set_title("Winner-frequency RMS shift")
    axes[0].tick_params(axis="x", rotation=20)
    axes[1].bar(labels, [row["decisive_fraction_shift"] for row in rows], color="#54a24b")
    axes[1].set_title("Decisive-fraction shift")
    axes[1].tick_params(axis="x", rotation=20)
    figure.suptitle("Pre-click transparency vs baseline")
    figure.tight_layout()
    return figure


def plot_winner_drain_fraction(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(7.2, 4.2), dpi=120)
    axis = figure.subplots()
    labels = [row["case"] for row in rows]
    axis.bar(labels, [row["mean_activated_winner_drain_fraction"] for row in rows], color="#4c78a8")
    axis.set_ylabel("Fraction of post-click energy")
    axis.set_title("Winner drain energy fraction")
    axis.tick_params(axis="x", rotation=20)
    figure.tight_layout()
    return figure


def plot_loser_residual_fraction(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(7.2, 4.2), dpi=120)
    axis = figure.subplots()
    labels = [row["case"] for row in rows]
    axis.bar(labels, [row["mean_activated_loser_fraction"] for row in rows], color="#e45756")
    axis.set_ylabel("Fraction of post-click energy")
    axis.set_title("Loser residual energy fraction")
    axis.tick_params(axis="x", rotation=20)
    figure.tight_layout()
    return figure


def plot_remaining_shared_energy_trace(example_trial: dict) -> Figure:
    return plot_remaining_shared_energy(example_trial["physical"])


def plot_whole_trial_energy_flow(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(9.2, 4.8), dpi=120)
    axis = figure.subplots()
    labels = [row["case"] for row in rows]
    positions = np.arange(len(rows), dtype=float)
    stacked_keys = [
        ("mean_pre_click_fraction_of_total", "Pre-click", "#4c78a8"),
        ("mean_winner_branch_fraction_of_total", "Winner branch", "#72b7b2"),
        ("mean_winner_drain_fraction_of_total", "Winner drain", "#f58518"),
        ("mean_loser_fraction_of_total", "Losers", "#e45756"),
        ("mean_shared_leak_fraction_of_total", "Shared leak", "#54a24b"),
        ("mean_terminal_remaining_fraction_of_total", "Terminal remaining", "#b279a2"),
    ]
    baseline = np.zeros(len(rows), dtype=float)
    for key, label, color in stacked_keys:
        values = np.asarray([float(row[key]) for row in rows], dtype=float)
        axis.bar(positions, values, bottom=baseline, color=color, label=label)
        baseline = baseline + values
    axis.set_xticks(positions, labels, rotation=20)
    axis.set_ylabel("Fraction of total trial energy")
    axis.set_title("Whole-trial energy flow summary")
    axis.legend(fontsize=8, ncol=2)
    figure.tight_layout()
    return figure
