from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure


def plot_dark_count_vs_bias(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(6.5, 4.5), dpi=120)
    axis = figure.subplots()
    bias = [row["bias_v"] for row in rows]
    dark = [row["lambda_dark_hz"] for row in rows]
    colors = {"quiet": "#4c78a8", "rare_event": "#f58518", "unstable": "#e45756"}
    for row in rows:
        axis.scatter(row["bias_v"], row["lambda_dark_hz"], color=colors[row["regime"]], s=42)
    axis.plot(bias, dark, color="#777777", linewidth=1.0, alpha=0.8)
    axis.set_xlabel("Bias (V)")
    axis.set_ylabel("Dark count rate (Hz)")
    axis.set_title("Dark count vs bias")
    return figure


def plot_dark_stability(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(6.5, 4.0), dpi=120)
    axis = figure.subplots()
    axis.plot([row["window_index"] for row in rows], [row["estimated_rate_hz"] for row in rows], "o-", color="#4c78a8")
    axis.set_xlabel("Window index")
    axis.set_ylabel("Estimated dark rate (Hz)")
    axis.set_title("Dark-count long-run stability")
    return figure


def plot_rate_scan(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(6.5, 4.5), dpi=120)
    axis = figure.subplots()
    powers = [row["power_uw"] for row in rows]
    observed = [row["observed_rate_hz"] for row in rows]
    fit = [row["fit_rate_hz"] for row in rows]
    std = [row["rate_std_hz"] for row in rows]
    axis.errorbar(powers, observed, yerr=std, fmt="o", color="#4c78a8", capsize=3, label="measured")
    axis.plot(powers, fit, "-", color="#f58518", label="linear fit")
    axis.set_xlabel("Absorbed power (uW)")
    axis.set_ylabel("Click rate (Hz)")
    axis.set_title("Rate vs power")
    axis.legend()
    return figure


def plot_rate_residuals(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(6.5, 4.0), dpi=120)
    axis = figure.subplots()
    axis.axhline(0.0, color="#bbbbbb", linewidth=1.0)
    axis.plot([row["power_uw"] for row in rows], [100.0 * row["relative_residual"] for row in rows], "o-", color="#e45756")
    axis.set_xlabel("Absorbed power (uW)")
    axis.set_ylabel("Relative residual (%)")
    axis.set_title("Rate-fit residuals")
    return figure


def plot_pulse_overlays(time_axis_ns: np.ndarray, waveforms: np.ndarray, overlay_count: int) -> Figure:
    figure = Figure(figsize=(6.5, 4.0), dpi=120)
    axis = figure.subplots()
    for waveform in waveforms[:overlay_count]:
        axis.plot(time_axis_ns, waveform, color="#4c78a8", alpha=0.20)
    axis.set_xlabel("Time (ns)")
    axis.set_ylabel("Pulse amplitude (V)")
    axis.set_title("Pulse overlays")
    return figure


def plot_dead_time_distribution(dead_times_us: np.ndarray) -> Figure:
    figure = Figure(figsize=(6.5, 4.0), dpi=120)
    axis = figure.subplots()
    axis.hist(dead_times_us, bins=min(16, max(dead_times_us.size // 8, 6)), color="#72b7b2", edgecolor="#ffffff")
    axis.set_xlabel("Observed dead time (us)")
    axis.set_ylabel("Count")
    axis.set_title("Dead-time distribution")
    return figure


def plot_dead_time_recovery(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(6.5, 4.0), dpi=120)
    axis = figure.subplots()
    axis.plot([row["interval_us"] for row in rows], [row["rearm_fraction"] for row in rows], "o-", color="#54a24b")
    axis.set_xlabel("Retrigger spacing (us)")
    axis.set_ylabel("Rearm fraction")
    axis.set_title("Reset recovery")
    axis.set_ylim(-0.02, 1.02)
    return figure


def plot_two_cell_matching(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(7.0, 4.4), dpi=120)
    axes = figure.subplots(1, 3)
    labels = [row["cell"] for row in rows]

    axes[0].bar(labels, [row["alpha_fit_hz_per_uw"] for row in rows], color=["#4c78a8", "#f58518"])
    axes[0].set_title("Gain")
    axes[0].set_ylabel("Hz/uW")

    axes[1].bar(labels, [row["lambda_dark_fit_hz"] for row in rows], color=["#4c78a8", "#f58518"])
    axes[1].set_title("Dark rate")
    axes[1].set_ylabel("Hz")

    axes[2].bar(labels, [row["pulse_width_mean_ns"] for row in rows], color=["#4c78a8", "#f58518"])
    axes[2].set_title("Pulse width")
    axes[2].set_ylabel("ns")

    figure.suptitle("Two-cell matching comparison")
    figure.tight_layout()
    return figure


def plot_race_summary(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(6.0, 5.0), dpi=120)
    axis = figure.subplots()
    target = [row["target_p1"] for row in rows]
    empirical = [row["empirical_p1"] for row in rows]
    axis.plot([0.0, 1.0], [0.0, 1.0], "--", color="#bbbbbb")
    axis.plot(target, empirical, "o", color="#4c78a8")
    for row in rows:
        axis.annotate(row["split_label"], (row["target_p1"], row["empirical_p1"]), fontsize=8, xytext=(4, 4), textcoords="offset points")
    axis.set_xlabel("Target P(cell 1 wins)")
    axis.set_ylabel("Empirical P(cell 1 wins)")
    axis.set_title("Winner frequency vs target")
    return figure


def plot_latch_race_comparison(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(6.8, 4.6), dpi=120)
    axis = figure.subplots()
    labels = [row["split_label"] for row in rows]
    target = [row["target_p1"] for row in rows]
    baseline = [row["baseline_p1"] for row in rows]
    latch = [row["latch_p1"] for row in rows]
    axis.plot(labels, target, "o--", color="#bbbbbb", label="target")
    axis.plot(labels, baseline, "o-", color="#4c78a8", label="baseline")
    axis.plot(labels, latch, "o-", color="#f58518", label="with latch")
    axis.set_ylim(-0.02, 1.02)
    axis.set_xlabel("Power split")
    axis.set_ylabel("P(cell A wins)")
    axis.set_title("Baseline vs latch race comparison")
    axis.legend()
    return figure


def plot_reset_cycle_stability(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(6.8, 4.2), dpi=120)
    axis = figure.subplots()
    cycle_index = [row["cycle_index"] for row in rows]
    reset_cleared = [row["reset_cleared"] for row in rows]
    early_probe_ignored = [row["early_probe_ignored"] for row in rows]
    axis.plot(cycle_index, reset_cleared, "-", color="#54a24b", label="reset cleared")
    axis.plot(cycle_index, early_probe_ignored, "-", color="#e45756", label="early probe ignored")
    axis.set_xlabel("Reset cycle")
    axis.set_ylabel("Pass fraction")
    axis.set_ylim(-0.05, 1.05)
    axis.set_title("Reset / re-arm stability")
    axis.legend()
    return figure
