from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure


def plot_two_branch_fraction_comparison(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(6.0, 5.0), dpi=120)
    axis = figure.subplots()
    exact = [row["exact_p1"] for row in rows]
    surrogate = [row["surrogate_p1"] for row in rows]
    axis.plot([0.0, 1.0], [0.0, 1.0], "--", color="#bbbbbb")
    axis.plot(exact, surrogate, "o", color="#4c78a8")
    for row in rows:
        axis.annotate(row["case"], (row["exact_p1"], row["surrogate_p1"]), fontsize=8, xytext=(4, 4), textcoords="offset points")
    axis.set_xlabel("Exact fraction p1")
    axis.set_ylabel("Surrogate fraction p1")
    axis.set_title("Two-branch exact vs surrogate fractions")
    return figure


def plot_four_branch_fraction_comparison(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(6.0, 5.0), dpi=120)
    axis = figure.subplots()
    exact: list[float] = []
    surrogate: list[float] = []
    for row in rows:
        exact.extend(row["exact_weights"])
        surrogate.extend(row["surrogate_fractions"])
    axis.plot([0.0, 1.0], [0.0, 1.0], "--", color="#bbbbbb")
    axis.plot(exact, surrogate, "o", color="#f58518", alpha=0.8)
    axis.set_xlabel("Exact branch fraction")
    axis.set_ylabel("Surrogate branch fraction")
    axis.set_title("Four-branch exact vs surrogate fractions")
    return figure


def plot_correlator_comparison(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(7.0, 4.0), dpi=120)
    axis = figure.subplots()
    labels = [row["label"] for row in rows]
    exact = [row["correlator_exact"] for row in rows]
    surrogate = [row["correlator_surrogate"] for row in rows]
    positions = np.arange(len(rows))
    axis.plot(positions, exact, "o-", color="#4c78a8", label="exact")
    axis.plot(positions, surrogate, "s--", color="#e45756", label="surrogate")
    axis.set_xticks(positions, labels)
    axis.set_ylabel("Correlator")
    axis.set_title("Correlator exact vs surrogate")
    axis.legend()
    return figure


def plot_chsh_comparison(chsh_result: dict) -> Figure:
    figure = Figure(figsize=(5.0, 4.0), dpi=120)
    axis = figure.subplots()
    axis.bar(["exact", "surrogate"], [chsh_result["exact_s"], chsh_result["surrogate_s"]], color=["#4c78a8", "#f58518"])
    axis.set_ylabel("S")
    axis.set_title("CHSH exact vs surrogate")
    return figure


def plot_integration_winner_frequency(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(6.5, 5.0), dpi=120)
    axis = figure.subplots()
    exact: list[float] = []
    empirical: list[float] = []
    for row in rows:
        exact.extend(row["exact_weights"])
        empirical.extend(row["empirical_frequencies"])
    axis.plot([0.0, 1.0], [0.0, 1.0], "--", color="#bbbbbb")
    axis.plot(exact, empirical, "o", color="#54a24b", alpha=0.8)
    axis.set_xlabel("Exact branch weight")
    axis.set_ylabel("Winner frequency after detector+latch")
    axis.set_title("Integrated exact vs winner frequency")
    return figure
