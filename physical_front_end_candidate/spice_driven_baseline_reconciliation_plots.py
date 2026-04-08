from __future__ import annotations

from collections import Counter
from typing import Any

from matplotlib.figure import Figure


def _metric_labels(rows: list[dict[str, Any]]) -> list[str]:
    return [str(row["metric"]).replace("_", "\n") for row in rows]


def plot_side_by_side_metric_comparison(rows: list[dict[str, Any]]) -> Figure:
    labels = _metric_labels(rows)
    reference = [float(row["reference_value"]) for row in rows]
    nominal = [float(row["nominal_value"]) for row in rows]
    reproduction = [float(row["reproduction_value"]) for row in rows]
    positions = list(range(len(rows)))
    width = 0.26

    figure = Figure(figsize=(12.0, 5.6), dpi=120)
    axis = figure.subplots()
    axis.bar([pos - width for pos in positions], reference, width=width, label="reference", color="#4c78a8")
    axis.bar(positions, nominal, width=width, label="nominal robustness", color="#e45756")
    axis.bar([pos + width for pos in positions], reproduction, width=width, label="matched reproduction", color="#54a24b")
    axis.set_xticks(positions, labels)
    axis.set_ylabel("Metric value")
    axis.set_title("Baseline Metric Comparison")
    axis.legend(fontsize=8)
    figure.tight_layout()
    return figure


def plot_reproduction_vs_reference(rows: list[dict[str, Any]]) -> Figure:
    labels = _metric_labels(rows)
    deltas = [abs(float(row["reproduction_minus_reference"])) for row in rows]
    figure = Figure(figsize=(10.8, 4.8), dpi=120)
    axis = figure.subplots()
    axis.bar(labels, deltas, color="#54a24b")
    axis.set_ylabel("|reproduction - reference|")
    axis.set_title("Reproduction vs Reference")
    axis.tick_params(axis="x", rotation=20)
    figure.tight_layout()
    return figure


def plot_metric_difference_breakdown(rows: list[dict[str, Any]]) -> Figure:
    labels = _metric_labels(rows)
    nominal_delta = [float(row["nominal_minus_reference"]) for row in rows]
    reproduction_delta = [float(row["reproduction_minus_reference"]) for row in rows]
    positions = list(range(len(rows)))
    width = 0.36

    figure = Figure(figsize=(12.0, 5.6), dpi=120)
    axis = figure.subplots()
    axis.axhline(0.0, color="#666666", linewidth=0.8)
    axis.bar([pos - width / 2.0 for pos in positions], nominal_delta, width=width, label="nominal - reference", color="#e45756")
    axis.bar(
        [pos + width / 2.0 for pos in positions],
        reproduction_delta,
        width=width,
        label="reproduction - reference",
        color="#54a24b",
    )
    axis.set_xticks(positions, labels)
    axis.set_ylabel("Metric delta")
    axis.set_title("Metric Difference Breakdown")
    axis.legend(fontsize=8)
    figure.tight_layout()
    return figure


def plot_configuration_difference_summary(rows: list[dict[str, Any]]) -> Figure:
    mismatch_counts = Counter(str(row["category"]) for row in rows if not bool(row["matches"]))
    match_counts = Counter(str(row["category"]) for row in rows if bool(row["matches"]))
    categories = sorted({str(row["category"]) for row in rows})
    matched = [match_counts.get(category, 0) for category in categories]
    mismatched = [mismatch_counts.get(category, 0) for category in categories]

    figure = Figure(figsize=(9.6, 4.8), dpi=120)
    axis = figure.subplots()
    axis.bar(categories, matched, label="matched", color="#72b7b2")
    axis.bar(categories, mismatched, bottom=matched, label="mismatched", color="#f58518")
    axis.set_ylabel("Setting count")
    axis.set_title("Configuration Difference Summary")
    axis.tick_params(axis="x", rotation=20)
    axis.legend(fontsize=8)
    figure.tight_layout()
    return figure


__all__ = [
    "plot_configuration_difference_summary",
    "plot_metric_difference_breakdown",
    "plot_reproduction_vs_reference",
    "plot_side_by_side_metric_comparison",
]
