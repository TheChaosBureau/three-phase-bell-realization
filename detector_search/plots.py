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


def plot_model_diagnostic_panel(
    model_name: str,
    result: dict,
    waiting_click_times: np.ndarray,
    waiting_power: float,
) -> Figure:
    figure = Figure(figsize=(11, 8), dpi=120)
    axes = figure.subplots(2, 2)
    metrics = result["metrics"]

    powers = np.asarray([row["power"] for row in result["rate_scan"]], dtype=float)
    rates = np.asarray([row["rate_estimate"] for row in result["rate_scan"]], dtype=float)
    fit = metrics["lambda_dark_fit"] + metrics["alpha_fit"] * powers
    axes[0, 0].plot(powers, rates, "o", label="simulation")
    axes[0, 0].plot(powers, fit, "-", label="linear fit")
    axes[0, 0].set_title("Rate vs Power")
    axes[0, 0].set_xlabel("Absorbed power")
    axes[0, 0].set_ylabel("Rate")
    axes[0, 0].legend()

    target = np.asarray([row["target_p1"] for row in result["race_rows"]], dtype=float)
    empirical = np.asarray([row["empirical_p1"] for row in result["race_rows"]], dtype=float)
    axes[0, 1].plot([0.0, 1.0], [0.0, 1.0], "--", color="#bbbbbb")
    axes[0, 1].plot(target, empirical, "o")
    axes[0, 1].set_title("Race-Law Fidelity")
    axes[0, 1].set_xlabel("Target p(branch 1 wins)")
    axes[0, 1].set_ylabel("Empirical p(branch 1 wins)")

    levels = [100.0 * row["level"] for row in result["mismatch_rows"]]
    errors = [row["worst_error"] for row in result["mismatch_rows"]]
    axes[1, 0].plot(levels, errors, "o-")
    axes[1, 0].set_title("Mismatch Robustness")
    axes[1, 0].set_xlabel("Mismatch (%)")
    axes[1, 0].set_ylabel("Worst race error")

    axes[1, 1].set_title(f"Waiting Times at P={waiting_power:g}")
    if waiting_click_times.size:
        bins = min(30, max(waiting_click_times.size // 6, 5))
        axes[1, 1].hist(waiting_click_times, bins=bins, density=True, alpha=0.6, color="#4c78a8")
        mean_wait = float(np.mean(waiting_click_times))
        x_values = np.linspace(0.0, float(np.max(waiting_click_times)), 200)
        axes[1, 1].plot(x_values, (1.0 / mean_wait) * np.exp(-x_values / mean_wait), linewidth=2, color="#d62728")
    axes[1, 1].set_xlabel("Waiting time")
    axes[1, 1].set_ylabel("Density")

    waiting_row = min(
        result["waiting_time_rows"],
        key=lambda row: abs(float(row["power"]) - waiting_power),
    )
    text_lines = [
        f"score={metrics['score']:.3f}",
        f"linearity={metrics['linearity_rms_rel']:.3f}",
        f"race={metrics['race_rms_error']:.3f}",
        f"dark={metrics['lambda_dark_fit']:.3f}",
        f"mismatch={metrics['mismatch_penalty']:.3f}",
        f"CV={waiting_row['coefficient_of_variation']:.3f}",
        f"KS={waiting_row['ks_distance']:.3f}",
        f"asym amp={metrics['branch_asymmetry_amplification']:.3f}",
    ]
    axes[1, 1].text(
        0.97,
        0.97,
        "\n".join(text_lines),
        transform=axes[1, 1].transAxes,
        ha="right",
        va="top",
        fontsize=9,
        bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "#cccccc"},
    )

    figure.suptitle(f"{model_name}: best candidate diagnostics", fontsize=14)
    figure.tight_layout()
    return figure


def plot_winner_region(
    x_values: np.ndarray,
    y_values: np.ndarray,
    score_grid: np.ndarray,
    race_grid: np.ndarray,
    *,
    xlabel: str,
    ylabel: str,
    title: str,
) -> Figure:
    figure = Figure(figsize=(11, 4.5), dpi=120)
    axes = figure.subplots(1, 2)

    extent = [float(np.min(x_values)), float(np.max(x_values)), float(np.min(y_values)), float(np.max(y_values))]
    score_image = axes[0].imshow(
        score_grid,
        origin="lower",
        aspect="auto",
        extent=extent,
        cmap="viridis",
    )
    axes[0].set_title("Composite score")
    axes[0].set_xlabel(xlabel)
    axes[0].set_ylabel(ylabel)
    figure.colorbar(score_image, ax=axes[0], label="score")

    race_image = axes[1].imshow(
        race_grid,
        origin="lower",
        aspect="auto",
        extent=extent,
        cmap="magma_r",
    )
    axes[1].set_title("Race RMS error")
    axes[1].set_xlabel(xlabel)
    axes[1].set_ylabel(ylabel)
    figure.colorbar(race_image, ax=axes[1], label="race error")

    figure.suptitle(title, fontsize=14)
    figure.tight_layout()
    return figure


def plot_integration_mapping(
    angle_values_deg: np.ndarray,
    target_probs: np.ndarray,
    empirical_probs: np.ndarray,
    *,
    title: str,
) -> Figure:
    figure = Figure(figsize=(11, 4.5), dpi=120)
    axes = figure.subplots(1, 2)

    axes[0].plot([0.0, 1.0], [0.0, 1.0], "--", color="#bbbbbb")
    axes[0].plot(target_probs, empirical_probs, "o")
    axes[0].set_xlabel("Target branch-1 weight")
    axes[0].set_ylabel("Empirical branch-1 win frequency")
    axes[0].set_title("Weight-to-winner mapping")

    axes[1].plot(angle_values_deg, target_probs, label="target", linewidth=2)
    axes[1].plot(angle_values_deg, empirical_probs, "o-", label="empirical", linewidth=1.5)
    axes[1].set_xlabel("Analyzer angle (deg)")
    axes[1].set_ylabel("Branch-1 probability")
    axes[1].set_ylim(-0.02, 1.02)
    axes[1].set_title("2-branch integration surrogate")
    axes[1].legend()

    figure.suptitle(title, fontsize=14)
    figure.tight_layout()
    return figure
