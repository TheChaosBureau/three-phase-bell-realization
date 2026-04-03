from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure


def plot_fraction_comparison(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(6.0, 5.0), dpi=120)
    axis = figure.subplots()
    exact = [row["exact_p1"] for row in rows]
    realized = [row["realized_p1"] for row in rows]
    axis.plot([0.0, 1.0], [0.0, 1.0], "--", color="#bbbbbb")
    axis.plot(exact, realized, "o", color="#4c78a8")
    for row in rows:
        axis.annotate(row["case"], (row["exact_p1"], row["realized_p1"]), fontsize=8, xytext=(4, 4), textcoords="offset points")
    axis.set_xlabel("Exact branch 1 weight")
    axis.set_ylabel("Physical candidate branch 1 fraction")
    axis.set_title("Exact vs physical front-end fractions")
    return figure


def plot_power_envelopes(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(7.0, 4.5), dpi=120)
    axis = figure.subplots()
    for row in rows:
        axis.plot(row["time_s"], row["branch_power_1"], label=f"{row['case']} / branch_1")
        axis.plot(row["time_s"], row["branch_power_2"], "--", label=f"{row['case']} / branch_2")
    axis.set_xlabel("Time (s)")
    axis.set_ylabel("Power (W)")
    axis.set_title("Physical front-end branch power envelopes")
    axis.legend(fontsize=7, ncol=2)
    return figure


def plot_export_comparison(row: dict) -> Figure:
    figure = Figure(figsize=(7.0, 4.0), dpi=120)
    axis = figure.subplots()
    axis.plot(row["time_s"], row["branch_power_1"], color="#4c78a8", label="physical branch_1")
    axis.plot(row["time_s"], row["export_power_1"], "--", color="#4c78a8", label="detector export branch_1")
    axis.plot(row["time_s"], row["branch_power_2"], color="#f58518", label="physical branch_2")
    axis.plot(row["time_s"], row["export_power_2"], "--", color="#f58518", label="detector export branch_2")
    axis.set_xlabel("Time (s)")
    axis.set_ylabel("Power (W)")
    axis.set_title("Physical vs detector-facing exported envelopes")
    axis.legend(fontsize=8)
    return figure


def plot_winner_frequency(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(6.0, 5.0), dpi=120)
    axis = figure.subplots()
    exact = [row["exact_p1"] for row in rows]
    empirical = [row["empirical_p1"] for row in rows]
    axis.plot([0.0, 1.0], [0.0, 1.0], "--", color="#bbbbbb")
    axis.plot(exact, empirical, "o", color="#54a24b")
    for row in rows:
        axis.annotate(row["case"], (row["exact_p1"], row["empirical_p1"]), fontsize=8, xytext=(4, 4), textcoords="offset points")
    axis.set_xlabel("Exact branch 1 weight")
    axis.set_ylabel("Winner frequency after detector+latch")
    axis.set_title("Integrated winner frequency vs target")
    return figure


def plot_error_summary(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(7.0, 4.2), dpi=120)
    axes = figure.subplots(1, 2)
    labels = [row["case"] for row in rows]
    rms = [row["rms_error"] for row in rows]
    max_err = [row["max_abs_error"] for row in rows]
    axes[0].bar(labels, rms, color="#72b7b2")
    axes[0].set_title("RMS error")
    axes[0].tick_params(axis="x", rotation=20)
    axes[1].bar(labels, max_err, color="#e45756")
    axes[1].set_title("Max abs error")
    axes[1].tick_params(axis="x", rotation=20)
    figure.suptitle("Physical front-end residual summary")
    figure.tight_layout()
    return figure
