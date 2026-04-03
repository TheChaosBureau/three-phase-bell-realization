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


def plot_gamma_overlay(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(7.0, 4.5), dpi=120)
    axis = figure.subplots()
    for row in rows:
        axis.plot(row["time_s"], row["gamma_branch_1"], label=f"{row['case']} / gamma_1")
        axis.plot(row["time_s"], row["gamma_branch_2"], "--", label=f"{row['case']} / gamma_2")
    axis.set_xlabel("Time (s)")
    axis.set_ylabel("Gamma(t)")
    axis.set_title("Common-envelope normalized branch power")
    axis.legend(fontsize=7, ncol=2)
    return figure


def plot_mode_error_comparison(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(7.0, 4.5), dpi=120)
    axes = figure.subplots(1, 2)
    labels = [row["mode_label"] for row in rows]
    rms = [row["winner_rms_error"] for row in rows]
    max_err = [row["winner_max_error"] for row in rows]
    axes[0].bar(labels, rms, color="#4c78a8")
    axes[0].set_title("RMS winner-law error")
    axes[0].tick_params(axis="x", rotation=20)
    axes[1].bar(labels, max_err, color="#e45756")
    axes[1].set_title("Max winner-law error")
    axes[1].tick_params(axis="x", rotation=20)
    figure.suptitle("Export-mode winner-law error")
    figure.tight_layout()
    return figure


def plot_mode_case_residuals(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(8.0, 4.8), dpi=120)
    axes = figure.subplots(1, 2)
    cases = list(dict.fromkeys(row["case"] for row in rows))
    mode_labels = sorted({row["mode_label"] for row in rows})
    x = np.arange(len(cases), dtype=float)
    width = 0.8 / max(len(mode_labels), 1)
    for mode_index, mode_label in enumerate(mode_labels):
        mode_row_map = {row["case"]: row for row in rows if row["mode_label"] == mode_label}
        mode_rows = [mode_row_map[case] for case in cases if case in mode_row_map]
        offsets = x + (mode_index - 0.5 * (len(mode_labels) - 1)) * width
        axes[0].bar(offsets[: len(mode_rows)], [row["rms_error"] for row in mode_rows], width=width, label=mode_label)
        axes[1].bar(offsets[: len(mode_rows)], [row["max_abs_error"] for row in mode_rows], width=width, label=mode_label)
    for axis in axes:
        axis.set_xticks(x)
        axis.set_xticklabels(cases, rotation=20)
    axes[0].set_title("Case RMS error")
    axes[1].set_title("Case max abs error")
    axes[0].legend(fontsize=8)
    figure.suptitle("Export-mode residual summary")
    figure.tight_layout()
    return figure


def plot_gain_sweep(rows: list[dict], *, metric_key: str, title: str, ylabel: str) -> Figure:
    figure = Figure(figsize=(6.8, 4.4), dpi=120)
    axis = figure.subplots()
    for case in list(dict.fromkeys(row["case"] for row in rows)):
        case_rows = sorted((row for row in rows if row["case"] == case), key=lambda row: float(row["gain"]))
        axis.plot([row["gain"] for row in case_rows], [row[metric_key] for row in case_rows], marker="o", label=case)
    axis.set_xscale("log", base=2)
    axis.set_xlabel("Power-scale gain")
    axis.set_ylabel(ylabel)
    axis.set_title(title)
    axis.legend(fontsize=8)
    return figure


def plot_exposure_sweep(rows: list[dict], *, metric_key: str, title: str, ylabel: str) -> Figure:
    figure = Figure(figsize=(6.8, 4.4), dpi=120)
    axis = figure.subplots()
    for case in list(dict.fromkeys(row["case"] for row in rows)):
        case_rows = sorted((row for row in rows if row["case"] == case), key=lambda row: float(row["exposure_s"]))
        axis.plot([row["exposure_s"] for row in case_rows], [row[metric_key] for row in case_rows], marker="o", label=case)
    axis.set_xlabel("Exposure window (s)")
    axis.set_ylabel(ylabel)
    axis.set_title(title)
    axis.legend(fontsize=8)
    return figure


def plot_expected_click_summary(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(7.2, 4.5), dpi=120)
    axes = figure.subplots(1, 2)
    sorted_rows = sorted(rows, key=lambda row: float(row["gain"]))
    axes[0].plot([row["gain"] for row in sorted_rows], [row["mean_mu"] for row in sorted_rows], marker="o", color="#4c78a8")
    axes[0].set_xscale("log", base=2)
    axes[0].set_title("Mean expected click count")
    axes[0].set_xlabel("Power-scale gain")
    axes[0].set_ylabel("Mean mu")
    decisive_key = "decisive_fraction" if "decisive_fraction" in rows[0] else "mean_decisive_fraction"
    axes[1].scatter([row["mean_mu"] for row in rows], [row[decisive_key] for row in rows], color="#54a24b")
    axes[1].set_title("Decisive fraction vs mean mu")
    axes[1].set_xlabel("Mean mu")
    axes[1].set_ylabel("Decisive fraction")
    figure.tight_layout()
    return figure


def plot_synthetic_vs_physical(rows: list[dict], *, metric_key: str, title: str, ylabel: str) -> Figure:
    figure = Figure(figsize=(6.8, 4.4), dpi=120)
    axis = figure.subplots()
    for family in ["physical_export", "synthetic_common_envelope"]:
        family_rows = sorted((row for row in rows if row["trace_kind"] == family), key=lambda row: float(row["gain"]))
        axis.plot(
            [row["gain"] for row in family_rows],
            [row[metric_key] for row in family_rows],
            marker="o",
            label=family.replace("_", " "),
        )
    axis.set_xscale("log", base=2)
    axis.set_xlabel("Power-scale gain")
    axis.set_ylabel(ylabel)
    axis.set_title(title)
    axis.legend(fontsize=8)
    return figure


def plot_diagnosis_summary(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(7.0, 4.5), dpi=120)
    axes = figure.subplots(1, 2)
    labels = [row["label"] for row in rows]
    axes[0].bar(labels, [row["winner_rms_error"] for row in rows], color="#4c78a8")
    axes[0].set_title("Winner-law RMS error")
    axes[0].tick_params(axis="x", rotation=20)
    axes[1].bar(labels, [row["decisive_fraction"] for row in rows], color="#54a24b")
    axes[1].set_title("Decisive fraction")
    axes[1].tick_params(axis="x", rotation=20)
    figure.suptitle("Boundary diagnosis summary")
    figure.tight_layout()
    return figure


def plot_calibrated_frequency(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(6.0, 5.0), dpi=120)
    axis = figure.subplots()
    exact = [row["exact_p1"] for row in rows]
    empirical = [row["empirical_p1"] for row in rows]
    axis.plot([0.0, 1.0], [0.0, 1.0], "--", color="#bbbbbb")
    axis.plot(exact, empirical, "o", color="#4c78a8")
    for row in rows:
        axis.annotate(row["case"], (row["exact_p1"], row["empirical_p1"]), fontsize=8, xytext=(4, 4), textcoords="offset points")
    axis.set_xlabel("Exact branch 1 weight")
    axis.set_ylabel("Calibrated empirical winner frequency")
    axis.set_title("Calibrated exact vs empirical winner law")
    return figure


def plot_calibrated_frequency_with_ci(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(6.2, 5.0), dpi=120)
    axis = figure.subplots()
    exact = np.asarray([row["exact_p1"] for row in rows], dtype=float)
    empirical = np.asarray([row["empirical_p1"] for row in rows], dtype=float)
    ci95 = np.asarray([row["empirical_p1_ci95"] for row in rows], dtype=float)
    axis.plot([0.0, 1.0], [0.0, 1.0], "--", color="#bbbbbb")
    axis.errorbar(exact, empirical, yerr=ci95, fmt="o", color="#4c78a8", ecolor="#9ecae9", capsize=3)
    for row in rows:
        axis.annotate(row["case"], (row["exact_p1"], row["empirical_p1"]), fontsize=8, xytext=(4, 4), textcoords="offset points")
    axis.set_xlabel("Exact branch 1 weight")
    axis.set_ylabel("Empirical winner frequency")
    axis.set_title("High-stat calibrated winner law")
    return figure


def plot_decisive_counts(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(7.2, 4.6), dpi=120)
    axes = figure.subplots(1, 2)
    labels = [row["case"] for row in rows]
    axes[0].bar(labels, [row["decisive_count"] for row in rows], color="#4c78a8")
    axes[0].set_title("Decisive event count")
    axes[0].tick_params(axis="x", rotation=20)
    axes[1].bar(labels, [row["decisive_fraction"] for row in rows], color="#54a24b")
    axes[1].set_title("Decisive fraction")
    axes[1].tick_params(axis="x", rotation=20)
    figure.tight_layout()
    return figure


def plot_prior_vs_rerun(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(7.2, 4.8), dpi=120)
    axes = figure.subplots(1, 2)
    labels = [row["label"] for row in rows]
    axes[0].bar(labels, [row["winner_rms_error"] for row in rows], color="#4c78a8")
    axes[0].set_title("Winner-law RMS error")
    axes[0].tick_params(axis="x", rotation=20)
    axes[1].bar(labels, [row["decisive_fraction"] for row in rows], color="#54a24b")
    axes[1].set_title("Decisive fraction")
    axes[1].tick_params(axis="x", rotation=20)
    figure.tight_layout()
    return figure
