from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure


def plot_two_branch_frequency_comparison(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(6, 5), dpi=120)
    axis = figure.subplots()
    exact = [row["exact_p1"] for row in rows]
    empirical = [row["empirical_p1"] for row in rows]
    axis.plot([0.0, 1.0], [0.0, 1.0], "--", color="#bbbbbb")
    axis.plot(exact, empirical, "o")
    for row in rows:
        axis.annotate(row["case"], (row["exact_p1"], row["empirical_p1"]), fontsize=8, xytext=(4, 4), textcoords="offset points")
    axis.set_xlabel("Exact p(branch 1)")
    axis.set_ylabel("Empirical p(branch 1)")
    axis.set_title("Two-branch exact vs empirical winner frequencies")
    return figure


def plot_four_branch_weight_comparison(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(6, 5), dpi=120)
    axis = figure.subplots()
    exact = []
    empirical = []
    for row in rows:
        exact.extend(row["exact_weights"])
        empirical.extend(row["empirical_frequencies"])
    axis.plot([0.0, 1.0], [0.0, 1.0], "--", color="#bbbbbb")
    axis.plot(exact, empirical, "o", alpha=0.8)
    axis.set_xlabel("Exact branch probability")
    axis.set_ylabel("Empirical branch probability")
    axis.set_title("Four-branch exact vs empirical weights")
    return figure


def plot_correlator_comparison(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(7, 4), dpi=120)
    axis = figure.subplots()
    labels = [row["label"] for row in rows]
    exact = [row["correlator_exact"] for row in rows]
    empirical = [row["correlator_empirical"] for row in rows]
    positions = np.arange(len(rows))
    axis.plot(positions, exact, "o-", label="exact")
    axis.plot(positions, empirical, "s--", label="empirical")
    axis.set_xticks(positions, labels)
    axis.set_ylabel("Correlator")
    axis.set_title("Correlator exact vs empirical")
    axis.legend()
    return figure


def plot_chsh_comparison(chsh_result: dict) -> Figure:
    figure = Figure(figsize=(5, 4), dpi=120)
    axis = figure.subplots()
    axis.bar(["exact", "empirical"], [chsh_result["exact_s"], chsh_result["empirical_s"]], color=["#4c78a8", "#f58518"])
    axis.set_ylabel("S")
    axis.set_title("CHSH exact vs empirical")
    return figure


def plot_mismatch_sensitivity(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(7, 4.5), dpi=120)
    axis = figure.subplots()
    kinds = sorted({row["kind"] for row in rows})
    for kind in kinds:
        kind_rows = [row for row in rows if row["kind"] == kind]
        levels = [100.0 * row["level"] for row in kind_rows]
        errors = [row["mean_rms_error"] for row in kind_rows]
        axis.plot(levels, errors, "o-", label=kind)
    axis.set_xlabel("Mismatch (%)")
    axis.set_ylabel("Mean four-branch RMS error")
    axis.set_title("Mismatch sensitivity")
    axis.legend()
    return figure
