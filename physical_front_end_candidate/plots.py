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


def plot_four_branch_fraction_comparison(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(8.2, 5.0), dpi=120)
    axis = figure.subplots()
    branch_labels = rows[0]["branch_labels"]
    positions = np.arange(len(rows), dtype=float)
    width = 0.18
    colors = ["#4c78a8", "#f58518", "#54a24b", "#e45756"]
    for index, label in enumerate(branch_labels):
        exact = [row["exact_weights"][index] for row in rows]
        realized = [row["realized_fractions"][index] for row in rows]
        offset = (index - 1.5) * width
        axis.bar(positions + offset, exact, width=width, color=colors[index], alpha=0.35, label=f"{label} exact")
        axis.plot(positions + offset, realized, "o", color=colors[index], label=f"{label} realized")
    axis.set_xticks(positions, [row["case"] for row in rows], rotation=20)
    axis.set_ylabel("Branch fraction")
    axis.set_title("Exact vs realized four-branch energy fractions")
    axis.legend(fontsize=7, ncol=2)
    figure.tight_layout()
    return figure


def plot_four_branch_power_traces(row: dict) -> Figure:
    figure = Figure(figsize=(8.0, 4.8), dpi=120)
    axis = figure.subplots()
    colors = {"++": "#4c78a8", "+-": "#f58518", "-+": "#54a24b", "--": "#e45756"}
    for label in row["branch_labels"]:
        axis.plot(row["time_s"], row["branch_power_w"][label], label=label, color=colors.get(label))
    axis.set_xlabel("Time (s)")
    axis.set_ylabel("Power (W)")
    axis.set_title(f"Four-branch power traces: {row['case']}")
    axis.legend(fontsize=8)
    return figure


def plot_four_branch_export_envelopes(row: dict) -> Figure:
    figure = Figure(figsize=(8.0, 4.8), dpi=120)
    axis = figure.subplots()
    colors = {"++": "#4c78a8", "+-": "#f58518", "-+": "#54a24b", "--": "#e45756"}
    for label in row["branch_labels"]:
        axis.plot(row["time_s"], row["branch_power_w"][label], color=colors.get(label), alpha=0.4)
        axis.plot(row["export_time_s"], row["exported_branch_power"][label], "--", color=colors.get(label), label=label)
    axis.set_xlabel("Time (s)")
    axis.set_ylabel("Power (W)")
    axis.set_title(f"Detector-facing exported envelopes: {row['case']}")
    axis.legend(fontsize=8)
    return figure


def plot_four_branch_winner_frequency(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(8.2, 5.0), dpi=120)
    axis = figure.subplots()
    branch_labels = rows[0]["branch_labels"]
    positions = np.arange(len(rows), dtype=float)
    width = 0.18
    colors = ["#4c78a8", "#f58518", "#54a24b", "#e45756"]
    for index, label in enumerate(branch_labels):
        exact = [row["exact_weights"][index] for row in rows]
        empirical = [row["empirical_frequencies"][index] for row in rows]
        offset = (index - 1.5) * width
        axis.bar(positions + offset, exact, width=width, color=colors[index], alpha=0.35, label=f"{label} exact")
        axis.plot(positions + offset, empirical, "o", color=colors[index], label=f"{label} empirical")
    axis.set_xticks(positions, [row["case"] for row in rows], rotation=20)
    axis.set_ylabel("Winner frequency")
    axis.set_title("Exact vs empirical four-branch winner frequencies")
    axis.legend(fontsize=7, ncol=2)
    figure.tight_layout()
    return figure


def plot_correlator_exact_vs_empirical(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(6.8, 4.6), dpi=120)
    axis = figure.subplots()
    exact = [row["correlator_exact"] for row in rows]
    empirical = [row["correlator_empirical"] for row in rows]
    axis.plot([-1.0, 1.0], [-1.0, 1.0], "--", color="#bbbbbb")
    axis.plot(exact, empirical, "o", color="#4c78a8")
    for row in rows:
        axis.annotate(row["case"], (row["correlator_exact"], row["correlator_empirical"]), fontsize=8, xytext=(4, 4), textcoords="offset points")
    axis.set_xlabel("Exact correlator")
    axis.set_ylabel("Empirical correlator")
    axis.set_title("Correlator exact vs empirical")
    return figure


def plot_chsh_exact_vs_empirical(chsh_result: dict) -> Figure:
    figure = Figure(figsize=(5.8, 4.4), dpi=120)
    axis = figure.subplots()
    labels = ["Exact", "Empirical"]
    values = [float(chsh_result["exact_s"]), float(chsh_result["empirical_s"])]
    axis.bar(labels, values, color=["#4c78a8", "#54a24b"])
    axis.set_ylabel("CHSH S")
    axis.set_title("Exact vs empirical CHSH")
    return figure


def plot_four_branch_residual_summary(front_rows: list[dict], integration_rows: list[dict], chsh_result: dict) -> Figure:
    figure = Figure(figsize=(9.2, 4.8), dpi=120)
    axes = figure.subplots(1, 3)
    labels = [row["case"] for row in front_rows]
    axes[0].bar(labels, [row["rms_error"] for row in front_rows], color="#4c78a8")
    axes[0].set_title("Front-end RMS error")
    axes[0].tick_params(axis="x", rotation=20)
    axes[1].bar(labels, [row["rms_error"] for row in integration_rows], color="#54a24b")
    axes[1].set_title("Winner-law RMS error")
    axes[1].tick_params(axis="x", rotation=20)
    axes[2].bar(["Correlator RMS", "CHSH abs"], [float(np.sqrt(np.mean(np.square([row["correlator_error"] for row in integration_rows])))), float(chsh_result["abs_error"])], color=["#f58518", "#e45756"])
    axes[2].set_title("Integrated residuals")
    figure.tight_layout()
    return figure


def plot_shared_core_diagnostics(row: dict) -> Figure:
    figure = Figure(figsize=(9.0, 4.8), dpi=120)
    axes = figure.subplots(1, 2)
    state_labels = row["state_labels"]
    state_magnitude = np.asarray(row["prepared_state_magnitude"], dtype=float)
    mode_energies = np.asarray(row["modal_energies"], dtype=float)
    axes[0].bar(state_labels, state_magnitude, color="#4c78a8")
    axes[0].set_title("Prepared internal state magnitude")
    axes[0].set_ylabel("|x_k|")
    axes[1].bar([f"mode_{index}" for index in range(len(mode_energies))], mode_energies, color="#54a24b")
    axes[1].set_title("Shared-core modal energies")
    axes[1].tick_params(axis="x", rotation=20)
    figure.tight_layout()
    return figure


def plot_candidate_metric_comparison(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(9.0, 4.8), dpi=120)
    axes = figure.subplots(1, 3)
    labels = [row["candidate"] for row in rows]
    axes[0].bar(labels, [row["front_end_rms_error"] for row in rows], color=["#bbbbbb", "#4c78a8"])
    axes[0].set_title("Front-end RMS error")
    axes[1].bar(labels, [row["winner_rms_error"] for row in rows], color=["#bbbbbb", "#54a24b"])
    axes[1].set_title("Winner-law RMS error")
    axes[2].bar(labels, [row["correlator_rms_error"] for row in rows], color=["#bbbbbb", "#f58518"])
    axes[2].set_title("Correlator RMS error")
    figure.tight_layout()
    return figure


def plot_resonant_mode_diagnostics(row: dict) -> Figure:
    figure = Figure(figsize=(10.0, 4.8), dpi=120)
    axes = figure.subplots(1, 3)
    labels = [f"mode_{index}" for index in range(len(row["modal_response_magnitude"]))]
    axes[0].bar(labels, row["modal_response_magnitude"], color="#4c78a8")
    axes[0].set_title("Modal response magnitude")
    axes[0].tick_params(axis="x", rotation=20)
    axes[1].bar(labels, row["modal_decay_rates"], color="#54a24b")
    axes[1].set_title("Modal decay rates")
    axes[1].tick_params(axis="x", rotation=20)
    axes[2].bar(labels, row["mode_overlap_profile"], color="#f58518")
    axes[2].set_title("Singlet overlap by mode")
    axes[2].tick_params(axis="x", rotation=20)
    figure.tight_layout()
    return figure


def plot_closure_variable(row: dict, *, variable_name: str = "Z") -> Figure:
    figure = Figure(figsize=(6.8, 4.2), dpi=120)
    axis = figure.subplots()
    axis.plot(row["time_s"], row["closure_variable"], color="#4c78a8")
    axis.set_xlabel("Time (s)")
    axis.set_ylabel(variable_name)
    axis.set_title(f"{variable_name}(t) after winner capture")
    return figure


def plot_remaining_shared_energy(row: dict) -> Figure:
    figure = Figure(figsize=(6.8, 4.2), dpi=120)
    axis = figure.subplots()
    axis.plot(row["time_s"], row["remaining_shared_energy_j"], color="#54a24b")
    axis.set_xlabel("Time (s)")
    axis.set_ylabel("Remaining shared energy (J)")
    axis.set_title("Remaining shared energy vs time")
    return figure


def plot_winner_drain_accumulation(row: dict) -> Figure:
    figure = Figure(figsize=(6.8, 4.2), dpi=120)
    axis = figure.subplots()
    axis.plot(row["time_s"], row["winner_drain_energy_j"], color="#f58518")
    axis.set_xlabel("Time (s)")
    axis.set_ylabel("Winner drain energy (J)")
    axis.set_title("Winner drain energy accumulation")
    return figure


def plot_loser_suppression(row: dict) -> Figure:
    figure = Figure(figsize=(7.4, 4.4), dpi=120)
    axis = figure.subplots()
    for label, values in row["loser_suppression"].items():
        axis.plot(row["time_s"], values, label=label)
    axis.set_xlabel("Time (s)")
    axis.set_ylabel("Suppression")
    axis.set_title("Loser suppression traces")
    axis.legend(fontsize=8)
    return figure


def plot_post_click_energy_partition(rows: list[dict]) -> Figure:
    figure = Figure(figsize=(8.2, 4.6), dpi=120)
    axes = figure.subplots(1, 2)
    labels = [row["label"] for row in rows]
    axes[0].bar(labels, [row["mean_winner_drain_fraction"] for row in rows], color="#4c78a8")
    axes[0].set_title("Winner drain fraction")
    axes[0].tick_params(axis="x", rotation=20)
    axes[1].bar(labels, [row["mean_loser_fraction"] for row in rows], color="#e45756")
    axes[1].set_title("Loser residual fraction")
    axes[1].tick_params(axis="x", rotation=20)
    figure.tight_layout()
    return figure


def plot_winner_drain_power(row: dict) -> Figure:
    figure = Figure(figsize=(6.8, 4.2), dpi=120)
    axis = figure.subplots()
    axis.plot(row["time_s"], row["winner_drain_power_w"], color="#f58518")
    axis.set_xlabel("Time (s)")
    axis.set_ylabel("Winner drain power (W)")
    axis.set_title("Winner drain power vs time")
    return figure


def plot_closure_semantics_comparison(physical_row: dict, reduced_row: dict, *, variable_name: str = "Z") -> Figure:
    figure = Figure(figsize=(8.8, 4.4), dpi=120)
    axes = figure.subplots(1, 2)
    axes[0].plot(reduced_row["time_s"], reduced_row["closure_variable"], color="#bbbbbb", label="reduced")
    axes[0].plot(physical_row["time_s"], physical_row["closure_variable"], color="#4c78a8", label="physical")
    axes[0].set_xlabel("Time (s)")
    axes[0].set_ylabel(variable_name)
    axes[0].set_title(f"{variable_name}(t) comparison")
    axes[0].legend(fontsize=8)
    axes[1].plot(reduced_row["time_s"], reduced_row["remaining_shared_energy_j"], color="#bbbbbb", label="reduced")
    axes[1].plot(physical_row["time_s"], physical_row["remaining_shared_energy_j"], color="#54a24b", label="physical")
    axes[1].set_xlabel("Time (s)")
    axes[1].set_ylabel("Remaining shared energy (J)")
    axes[1].set_title("Shared-energy decay comparison")
    axes[1].legend(fontsize=8)
    figure.tight_layout()
    return figure
