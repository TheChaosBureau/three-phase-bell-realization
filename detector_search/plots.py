from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure


def plot_rate_scan(rate_scan: list[dict], fit_values: np.ndarray | list[float]) -> Figure:
    figure = Figure(figsize=(6, 4), dpi=100)
    axis = figure.subplots()
    powers = [row["power"] for row in rate_scan]
    rates = [row["rate_estimate"] for row in rate_scan]
    axis.plot(powers, rates, "o", label="simulation")
    axis.plot(powers, fit_values, "-", label="linear fit")
    axis.set_xlabel("Absorbed power")
    axis.set_ylabel("Rate")
    axis.set_title("Rate vs Power")
    axis.legend()
    return figure


def plot_rate_residuals(rate_scan: list[dict], fit_values: np.ndarray | list[float]) -> Figure:
    figure = Figure(figsize=(6, 3), dpi=100)
    axis = figure.subplots()
    powers = np.asarray([row["power"] for row in rate_scan], dtype=float)
    rates = np.asarray([row["rate_estimate"] for row in rate_scan], dtype=float)
    fit = np.asarray(fit_values, dtype=float)
    residuals = rates - fit
    axis.axhline(0.0, color="#bbbbbb", linewidth=1)
    axis.plot(powers, residuals, "o-")
    axis.set_xlabel("Absorbed power")
    axis.set_ylabel("Residual")
    axis.set_title("Rate-fit residuals")
    return figure


def plot_waiting_time_histogram(click_times: np.ndarray, mean_wait: float) -> Figure:
    figure = Figure(figsize=(6, 4), dpi=100)
    axis = figure.subplots()
    if click_times.size:
        axis.hist(click_times, bins=min(30, max(click_times.size // 5, 5)), density=True, alpha=0.6)
        x_values = np.linspace(0.0, float(np.max(click_times)), 200)
        axis.plot(x_values, (1.0 / mean_wait) * np.exp(-x_values / mean_wait), linewidth=2)
    axis.set_xlabel("Waiting time")
    axis.set_ylabel("Density")
    axis.set_title("Waiting-time distribution")
    return figure


def plot_race_law(race_rows: list[dict]) -> Figure:
    figure = Figure(figsize=(5, 5), dpi=100)
    axis = figure.subplots()
    target = [row["target_p1"] for row in race_rows]
    empirical = [row["empirical_p1"] for row in race_rows]
    axis.plot([0.0, 1.0], [0.0, 1.0], "--", color="#bbbbbb")
    axis.plot(target, empirical, "o")
    axis.set_xlabel("Target p(branch 1 wins)")
    axis.set_ylabel("Empirical p(branch 1 wins)")
    axis.set_title("Race-law fidelity")
    return figure


def plot_robustness(mismatch_rows: list[dict]) -> Figure:
    figure = Figure(figsize=(6, 4), dpi=100)
    axis = figure.subplots()
    levels = [100.0 * row["level"] for row in mismatch_rows]
    errors = [row["worst_error"] for row in mismatch_rows]
    axis.plot(levels, errors, "o-")
    axis.set_xlabel("Mismatch (%)")
    axis.set_ylabel("Worst race error")
    axis.set_title("Mismatch robustness")
    return figure


def plot_score_histogram(results: list[dict]) -> Figure:
    figure = Figure(figsize=(6, 4), dpi=100)
    axis = figure.subplots()
    scores = [row["metrics"]["score"] for row in results]
    axis.hist(scores, bins=min(20, max(len(scores), 1)))
    axis.set_xlabel("Composite score")
    axis.set_ylabel("Count")
    axis.set_title("Candidate score distribution")
    return figure
