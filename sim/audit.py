from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .definitions import (
    FAILURE_MODE_DEFINITIONS,
    GATE_DEFINITIONS,
    METRIC_DEFINITIONS,
    PRIMARY_WINDOW_FRACTION,
    READOUT_RULE_DEFINITIONS,
    render_metrics_markdown,
    render_readout_rules_markdown,
)
from .disambiguation import (
    DISAMBIGUATION_METRIC_DEFINITIONS,
    GROUP_KEYS as MECHANISM_GROUP_KEYS,
    REGIME_BIN_DEFINITIONS,
    analyzer_features,
    build_mechanism_structure,
    build_oracle_caches,
    build_oracle_gap_summary,
    build_oracle_trial_table,
    build_readout_sensitivity,
    phase_aligned_features,
)
from .io import dump_json, ensure_dir, load_json
from .readout import (
    RULE_CONTROL_NEGATIVE_PREWINDOW,
    RULE_ENERGY_LOSS_WINNER,
    RULE_LEGACY_DOMINANCE_SHIFT,
    RULE_LEGACY_DOMINANT_POST,
)

GROUP_KEYS = ["rule", "window_fraction", "gamma_plus", "gamma_minus", "anisotropy_ratio"]
GROUP_WITH_ROLE_KEYS = ["rule", "rule_role", "window_fraction", "gamma_plus", "gamma_minus", "anisotropy_ratio"]
PAIR_KEYS = GROUP_KEYS + ["angle_a_deg", "angle_b_deg"]
SINGLE_KEYS = ["window_fraction", "gamma_plus", "gamma_minus", "anisotropy_ratio", "angle_deg"]
MECHANISM_KEYS = ["window_fraction", "gamma_plus", "gamma_minus", "anisotropy_ratio"]

RULE_DISPLAY_NAMES = {
    RULE_ENERGY_LOSS_WINNER: "extracted_energy_winner",
    "residual_template_classifier": "residual_template_classifier",
    "confidence_weighted_agreement": "confidence_weighted_agreement",
    RULE_LEGACY_DOMINANT_POST: "dominant_post",
    RULE_LEGACY_DOMINANCE_SHIFT: "dominance_shift",
    RULE_CONTROL_NEGATIVE_PREWINDOW: "dominant_pre",
}


@dataclass(slots=True)
class BaseArtifact:
    artifact_dir: Path
    summary: dict[str, Any]
    single_summary: pd.DataFrame
    single_ratio_summary: pd.DataFrame
    single_trials: pd.DataFrame
    single_manifest: pd.DataFrame
    single_states: dict[str, np.ndarray]
    sequential_trial_metrics: pd.DataFrame
    sequential_rule_summary: pd.DataFrame
    sequential_correlation_summary: pd.DataFrame
    sequential_drift_summary: pd.DataFrame
    sequential_chsh_summary: pd.DataFrame
    sequential_residual_agreement: pd.DataFrame
    sequential_gated_summary: pd.DataFrame
    aligned_support_by_confidence: pd.DataFrame
    legacy_rule_controls: pd.DataFrame
    sequential_manifest: pd.DataFrame
    sequential_states: dict[str, np.ndarray]


def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def load_npz_dict(path: Path) -> dict[str, np.ndarray]:
    if not path.exists():
        return {}
    with np.load(path, allow_pickle=False) as payload:
        return {name: payload[name] for name in payload.files}


def write_table(frame: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    ensure_dir(csv_path.parent)
    frame.to_csv(csv_path, index=False)
    dump_json(json_path, frame.to_dict(orient="records"))


def render_disambiguation_markdown() -> str:
    lines = ["# Mechanism-vs-Readout Disambiguation", ""]
    for name, formula in DISAMBIGUATION_METRIC_DEFINITIONS.items():
        lines.extend([f"## `{name}`", "", f"- Definition: {formula}", ""])
    lines.extend(["# Classification Bins", ""])
    for name, description in REGIME_BIN_DEFINITIONS.items():
        lines.extend([f"## `{name}`", "", f"- Interpretation: {description}", ""])
    return "\n".join(lines).strip() + "\n"


def _with_rule_display(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "rule" not in frame.columns:
        return frame
    working = frame.copy()
    insert_at = working.columns.get_loc("rule") + 1
    display_names = working["rule"].map(RULE_DISPLAY_NAMES).fillna(working["rule"])
    if "rule_display_name" in working.columns:
        working["rule_display_name"] = display_names
    else:
        working.insert(insert_at, "rule_display_name", display_names)
    return working


def load_base_artifact(artifact_dir: Path) -> BaseArtifact:
    artifact_dir = artifact_dir.resolve()
    single_dir = artifact_dir / "single"
    sequential_dir = artifact_dir / "sequential"
    return BaseArtifact(
        artifact_dir=artifact_dir,
        summary=load_json(artifact_dir / "summary.json"),
        single_summary=load_csv(single_dir / "summary.csv"),
        single_ratio_summary=load_csv(single_dir / "ratio_summary.csv"),
        single_trials=load_csv(single_dir / "trial_metrics.csv"),
        single_manifest=pd.DataFrame(load_json(single_dir / "run_manifest.json")),
        single_states=load_npz_dict(single_dir / "states.npz"),
        sequential_trial_metrics=load_csv(sequential_dir / "trial_metrics.csv"),
        sequential_rule_summary=load_csv(sequential_dir / "rule_summary.csv"),
        sequential_correlation_summary=load_csv(sequential_dir / "correlation_summary.csv"),
        sequential_drift_summary=load_csv(sequential_dir / "drift_summary.csv"),
        sequential_chsh_summary=load_csv(sequential_dir / "chsh_summary.csv"),
        sequential_residual_agreement=load_csv(sequential_dir / "sequential_residual_agreement.csv"),
        sequential_gated_summary=load_csv(sequential_dir / "sequential_gated_summary.csv"),
        aligned_support_by_confidence=load_csv(sequential_dir / "aligned_support_by_confidence.csv"),
        legacy_rule_controls=load_csv(sequential_dir / "legacy_rule_controls.csv"),
        sequential_manifest=pd.DataFrame(load_json(sequential_dir / "run_manifest.json")),
        sequential_states=load_npz_dict(sequential_dir / "states.npz"),
    )


def extract_gate_thresholds(base: BaseArtifact) -> dict[str, float]:
    thresholds = {
        name: float(definition["default"])
        for name, definition in GATE_DEFINITIONS.items()
    }
    preset = base.summary.get("preset", {})
    preset_thresholds = preset.get("sequential_gate_thresholds")
    if isinstance(preset_thresholds, dict):
        for name, value in preset_thresholds.items():
            thresholds[name] = float(value)
        return thresholds
    if not base.sequential_manifest.empty and "gate_thresholds" in base.sequential_manifest.columns:
        value = base.sequential_manifest.iloc[0]["gate_thresholds"]
        if isinstance(value, dict):
            for name, item in value.items():
                thresholds[name] = float(item)
    return thresholds


def build_single_full(base: BaseArtifact) -> pd.DataFrame:
    if base.single_summary.empty:
        return pd.DataFrame()
    return base.single_summary.sort_values(SINGLE_KEYS).reset_index(drop=True)


def build_sequential_full(base: BaseArtifact) -> pd.DataFrame:
    if base.sequential_rule_summary.empty:
        return pd.DataFrame()

    frame = base.sequential_rule_summary.copy().rename(
        columns={
            "angle_a_deg": "phiA",
            "angle_b_deg": "phiB",
            "correlation": "E_phiA_phiB",
        }
    )

    if not base.sequential_gated_summary.empty:
        gated = base.sequential_gated_summary.copy().rename(
            columns={
                "residual_agreement_rate": "group_residual_agreement_rate",
                "residual_ambiguity_rate": "group_residual_ambiguity_rate",
                "mean_confidence_margin": "group_mean_confidence_margin",
                "mean_projectivity_compatibility": "group_mean_projectivity_compatibility",
                "mean_branch_stability_score": "group_mean_branch_stability_score",
                "aligned_same_sign_mass": "group_aligned_same_sign_mass",
                "aligned_anti_mass": "group_aligned_anti_mass",
                "aligned_same_sign_mass_high_confidence": "group_aligned_same_sign_mass_high_confidence",
                "aligned_anti_mass_high_confidence": "group_aligned_anti_mass_high_confidence",
                "high_confidence_trial_count": "group_high_confidence_trial_count",
                "low_confidence_trial_count": "group_low_confidence_trial_count",
            }
        )
        gated_columns = [
            "rule",
            "rule_role",
            "window_fraction",
            "gamma_plus",
            "gamma_minus",
            "anisotropy_ratio",
            "alice_marginal_drift",
            "bob_marginal_drift",
            "group_aligned_same_sign_mass",
            "group_aligned_anti_mass",
            "group_aligned_same_sign_mass_high_confidence",
            "group_aligned_anti_mass_high_confidence",
            "group_high_confidence_trial_count",
            "group_low_confidence_trial_count",
            "group_residual_agreement_rate",
            "group_residual_ambiguity_rate",
            "group_mean_confidence_margin",
            "group_mean_projectivity_compatibility",
            "group_mean_branch_stability_score",
            "no_signaling_flag",
            "overfit_flag",
            "drift_gate_pass",
            "aligned_support_gate_pass",
            "overfit_gate_pass",
            "residual_coherence_gate_pass",
            "projectivity_gate_pass",
            "gates_passed",
            "all_gates_pass",
            "CHSH_raw",
            "CHSH_gated",
            "headline_eligible",
        ]
        frame = frame.merge(
            gated[gated_columns],
            on=["rule", "rule_role", "window_fraction", "gamma_plus", "gamma_minus", "anisotropy_ratio"],
            how="left",
        )

    return _with_rule_display(
        frame.sort_values(["rule", "window_fraction", "gamma_plus", "gamma_minus", "anisotropy_ratio", "phiA", "phiB"]).reset_index(drop=True)
    )


def build_top_sequential_chsh_audit(gated_summary: pd.DataFrame) -> pd.DataFrame:
    if gated_summary.empty:
        return pd.DataFrame()

    def blockers(row: pd.Series) -> str:
        reasons: list[str] = []
        if str(row["rule"]) != RULE_ENERGY_LOSS_WINNER:
            reasons.append("non_headline_rule")
        if not bool(row["drift_gate_pass"]):
            reasons.append("drift")
        if not bool(row["aligned_support_gate_pass"]):
            reasons.append("aligned_support")
        if not bool(row["residual_coherence_gate_pass"]):
            reasons.append("residual_coherence")
        if not bool(row["projectivity_gate_pass"]):
            reasons.append("projectivity")
        if not bool(row["overfit_gate_pass"]):
            reasons.append("overfit")
        return ",".join(reasons) if reasons else "none"

    def audit_note(row: pd.Series) -> str:
        if bool(row["headline_eligible"]):
            return "passes hard gates"
        if str(row["rule"]) == RULE_CONTROL_NEGATIVE_PREWINDOW:
            return "negative-control CHSH only"
        if not bool(row["drift_gate_pass"]):
            return "high raw CHSH, but drift gate fails"
        if not bool(row["residual_coherence_gate_pass"]):
            return "high raw CHSH, but residual coherence fails"
        if not bool(row["aligned_support_gate_pass"]):
            return "high raw CHSH, but aligned support fails"
        if not bool(row["projectivity_gate_pass"]):
            return "high raw CHSH, but projectivity compatibility fails"
        if not bool(row["overfit_gate_pass"]):
            return "high raw CHSH, but overfit gate fails"
        return "high raw CHSH, but rule is not headline-eligible"

    frame = gated_summary.copy()
    frame["gate_blockers"] = frame.apply(blockers, axis=1)
    frame["audit_note"] = frame.apply(audit_note, axis=1)
    selected = frame.sort_values(
        ["CHSH_raw", "gates_passed", "residual_agreement_rate"],
        ascending=[False, False, False],
    ).head(12)
    return _with_rule_display(
        selected[
            [
                "rule",
                "rule_role",
                "window_fraction",
                "gamma_plus",
                "gamma_minus",
                "anisotropy_ratio",
                "alice_marginal_drift",
                "bob_marginal_drift",
                "group_aligned_same_sign_mass" if "group_aligned_same_sign_mass" in selected.columns else "aligned_same_sign_mass",
                "group_aligned_anti_mass" if "group_aligned_anti_mass" in selected.columns else "aligned_anti_mass",
                "residual_agreement_rate",
                "residual_ambiguity_rate",
                "mean_confidence_margin",
                "mean_projectivity_compatibility",
                "CHSH_raw",
                "CHSH_gated",
                "gates_passed",
                "headline_eligible",
                "no_signaling_flag",
                "overfit_flag",
                "gate_blockers",
                "audit_note",
            ]
        ]
        .rename(
            columns={
                "group_aligned_same_sign_mass": "aligned_same_sign_mass",
                "group_aligned_anti_mass": "aligned_anti_mass",
            }
        )
        .reset_index(drop=True)
    )


def build_rule_comparison(gated_summary: pd.DataFrame) -> pd.DataFrame:
    if gated_summary.empty:
        return pd.DataFrame()
    frame = (
        gated_summary.assign(
            max_marginal_drift=lambda df: df[["alice_marginal_drift", "bob_marginal_drift"]].max(axis=1),
        )
        .groupby(["rule", "rule_role"], as_index=False)
        .agg(
            mean_CHSH_raw=("CHSH_raw", "mean"),
            max_CHSH_raw=("CHSH_raw", "max"),
            mean_max_marginal_drift=("max_marginal_drift", "mean"),
            mean_aligned_same_sign_mass=("aligned_same_sign_mass", "mean"),
            mean_residual_agreement_rate=("residual_agreement_rate", "mean"),
            mean_residual_ambiguity_rate=("residual_ambiguity_rate", "mean"),
            mean_projectivity_compatibility=("mean_projectivity_compatibility", "mean"),
            all_gates_pass_fraction=("all_gates_pass", "mean"),
            headline_eligible_fraction=("headline_eligible", "mean"),
            no_signaling_fraction=("no_signaling_flag", "mean"),
            overfit_fraction=("overfit_flag", "mean"),
        )
        .sort_values(["rule_role", "mean_CHSH_raw"], ascending=[True, False])
        .reset_index(drop=True)
    )
    return _with_rule_display(frame)


def build_headline_eligible_summary(gated_summary: pd.DataFrame) -> pd.DataFrame:
    if gated_summary.empty:
        return pd.DataFrame()
    return _with_rule_display(
        gated_summary[gated_summary["headline_eligible"]]
        .sort_values(["CHSH_gated", "residual_agreement_rate"], ascending=[False, False])
        .reset_index(drop=True)
    )


def build_plot_dataset_manifest_entry(plot_name: str, image_path: Path, dataset_path: Path) -> dict[str, str]:
    return {
        "name": plot_name,
        "image_path": str(image_path),
        "dataset_path": str(dataset_path),
    }


def _primary_window_slice(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "window_fraction" not in frame.columns:
        return frame.copy()
    mask = np.isclose(frame["window_fraction"], PRIMARY_WINDOW_FRACTION)
    return frame[mask].copy() if mask.any() else frame.copy()


def _placeholder_plot(path: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.text(0.5, 0.5, "No data available", ha="center", va="center")
    ax.set_axis_off()
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_residual_metric_vs_anisotropy(
    frame: pd.DataFrame,
    *,
    metric: str,
    title: str,
    ylabel: str,
    out_path: Path,
) -> None:
    if frame.empty:
        _placeholder_plot(out_path, title)
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    for rule, group in frame.groupby("rule"):
        ax.plot(group["anisotropy_ratio"], group[metric], marker="o", label=RULE_DISPLAY_NAMES.get(rule, rule))
    ax.set_title(title)
    ax.set_xlabel("Anisotropy ratio gamma_plus / gamma_minus")
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.2)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_aligned_support_by_confidence(frame: pd.DataFrame, out_path: Path) -> None:
    if frame.empty:
        _placeholder_plot(out_path, "Aligned Support By Confidence")
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharex=True)
    axes[0].plot(frame["anisotropy_ratio"], frame["aligned_same_sign_mass"], marker="o", label="same-sign all")
    axes[0].plot(
        frame["anisotropy_ratio"],
        frame["aligned_same_sign_mass_high_confidence"],
        marker="s",
        linestyle="--",
        label="same-sign high confidence",
    )
    axes[0].set_ylabel("Mass")
    axes[0].set_title("Aligned Same-Sign")
    axes[1].plot(frame["anisotropy_ratio"], frame["aligned_anti_mass"], marker="o", label="anti all")
    axes[1].plot(
        frame["anisotropy_ratio"],
        frame["aligned_anti_mass_high_confidence"],
        marker="s",
        linestyle="--",
        label="anti high confidence",
    )
    axes[1].set_title("Aligned Anti-Sign")
    for axis in axes:
        axis.set_xlabel("Anisotropy ratio gamma_plus / gamma_minus")
        axis.grid(alpha=0.2)
        axis.legend(fontsize=8)
    fig.suptitle("Aligned Support By Confidence")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_gated_chsh(frame: pd.DataFrame, out_path: Path) -> None:
    if frame.empty:
        _placeholder_plot(out_path, "Gated CHSH vs Anisotropy")
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    for rule, group in frame.groupby("rule"):
        label = RULE_DISPLAY_NAMES.get(rule, rule)
        axes[0].plot(group["anisotropy_ratio"], group["CHSH_raw"], marker="o", label=label)
        axes[1].plot(group["anisotropy_ratio"], group["CHSH_gated"], marker="o", label=label)
    for axis, title in zip(axes, ["Raw CHSH", "Gated CHSH"], strict=True):
        axis.axhline(2.0, color="tab:red", linestyle="--", linewidth=1)
        axis.set_xlabel("Anisotropy ratio gamma_plus / gamma_minus")
        axis.set_title(title)
        axis.grid(alpha=0.2)
    axes[0].set_ylabel("CHSH")
    axes[1].legend(fontsize=8)
    fig.suptitle("Gated CHSH vs Anisotropy")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_drift_by_rule(frame: pd.DataFrame, threshold: float, out_path: Path) -> None:
    if frame.empty:
        _placeholder_plot(out_path, "Drift vs Anisotropy By Rule")
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    for rule, group in frame.groupby("rule"):
        max_drift = group[["alice_marginal_drift", "bob_marginal_drift"]].max(axis=1)
        ax.plot(group["anisotropy_ratio"], max_drift, marker="o", label=RULE_DISPLAY_NAMES.get(rule, rule))
    ax.axhline(threshold, color="tab:red", linestyle="--", linewidth=1, label="drift gate")
    ax.set_title("Drift vs Anisotropy By Rule")
    ax.set_xlabel("Anisotropy ratio gamma_plus / gamma_minus")
    ax.set_ylabel("Max marginal drift")
    ax.grid(alpha=0.2)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_headline_eligible_regimes(frame: pd.DataFrame, out_path: Path) -> None:
    if frame.empty:
        _placeholder_plot(out_path, "Headline-Eligible Regimes")
        return
    working = frame.copy()
    working["headline_score"] = working["headline_eligible"].astype(float)
    pivot = working.pivot_table(
        index="window_fraction",
        columns="anisotropy_ratio",
        values="headline_score",
        aggfunc="max",
        fill_value=0.0,
    )
    fig, ax = plt.subplots(figsize=(8, 4.5))
    image = ax.imshow(pivot.to_numpy(), aspect="auto", cmap="Greens", vmin=0.0, vmax=1.0)
    ax.set_xticks(range(len(pivot.columns)), labels=[f"{value:.3g}" for value in pivot.columns])
    ax.set_yticks(range(len(pivot.index)), labels=[f"{value:.3g}" for value in pivot.index])
    ax.set_xlabel("Anisotropy ratio gamma_plus / gamma_minus")
    ax.set_ylabel("Window fraction")
    ax.set_title("Headline-Eligible Regimes")
    fig.colorbar(image, ax=ax, label="headline_eligible")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_residual_confidence_histograms(frame: pd.DataFrame, out_path: Path) -> None:
    if frame.empty:
        _placeholder_plot(out_path, "Residual Confidence Histograms")
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    high = frame[frame["pair_high_confidence_residual"] > 0.5]["mean_confidence_margin"]
    low = frame[frame["pair_low_confidence_residual"] > 0.5]["mean_confidence_margin"]
    axes[0].hist(high, bins=20, alpha=0.7, label="high confidence")
    axes[0].hist(low, bins=20, alpha=0.7, label="low confidence")
    axes[0].set_title("Pair Mean Confidence Margin")
    combined_stage = pd.DataFrame(
        {
            "alice_confidence_margin": frame["alice_confidence_margin"],
            "bob_confidence_margin": frame["bob_confidence_margin"],
        }
    )
    axes[1].hist(combined_stage["alice_confidence_margin"], bins=20, alpha=0.7, label="Alice")
    axes[1].hist(combined_stage["bob_confidence_margin"], bins=20, alpha=0.7, label="Bob")
    axes[1].set_title("Stage Confidence Margins")
    for axis in axes:
        axis.set_xlabel("Confidence margin")
        axis.set_ylabel("Trial count")
        axis.grid(alpha=0.2)
        axis.legend(fontsize=8)
    fig.suptitle("Residual Confidence Histograms")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_rule_comparison(frame: pd.DataFrame, out_path: Path) -> None:
    if frame.empty:
        _placeholder_plot(out_path, "Legacy vs Redesigned Rule Comparison")
        return
    labels = frame["rule_display_name"].tolist() if "rule_display_name" in frame.columns else frame["rule"].tolist()
    x = np.arange(len(frame))
    width = 0.38
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    axes[0].bar(x - width / 2, frame["mean_CHSH_raw"], width=width, label="mean CHSH raw")
    axes[0].bar(x + width / 2, frame["mean_max_marginal_drift"], width=width, label="mean max drift")
    axes[0].set_title("Rule-Level CHSH vs Drift")
    axes[1].bar(x - width / 2, frame["mean_residual_agreement_rate"], width=width, label="agreement")
    axes[1].bar(x + width / 2, frame["headline_eligible_fraction"], width=width, label="headline eligible")
    axes[1].set_title("Rule-Level Coherence vs Eligibility")
    for axis in axes:
        axis.set_xticks(x, labels, rotation=25, ha="right")
        axis.grid(alpha=0.2, axis="y")
        axis.legend(fontsize=8)
    fig.suptitle("Legacy vs Redesigned Rule Comparison")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_mechanism_metric_vs_anisotropy(
    frame: pd.DataFrame,
    *,
    metric: str,
    title: str,
    ylabel: str,
    out_path: Path,
) -> None:
    if frame.empty:
        _placeholder_plot(out_path, title)
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    for window_fraction, group in frame.groupby("window_fraction"):
        ax.plot(group["anisotropy_ratio"], group[metric], marker="o", label=f"T={window_fraction:.3g}")
    ax.set_title(title)
    ax.set_xlabel("Anisotropy ratio gamma_plus / gamma_minus")
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.2)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_confidence_efficiency_curve(frame: pd.DataFrame, out_path: Path) -> None:
    if frame.empty:
        _placeholder_plot(out_path, "Occupancy vs Confidence Threshold")
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharex=True)
    axes[0].plot(frame["margin_threshold"], frame["retained_fraction"], marker="o", label="retained fraction")
    axes[0].plot(frame["margin_threshold"], frame["branch_recoverability"], marker="s", label="branch recoverability")
    axes[0].set_title("Coverage vs Threshold")
    axes[1].plot(frame["margin_threshold"], frame["confidence_efficiency"], marker="o", label="confidence efficiency")
    axes[1].set_title("Efficiency vs Threshold")
    for axis in axes:
        axis.set_xlabel("Residual margin threshold")
        axis.grid(alpha=0.2)
        axis.legend(fontsize=8)
    axes[0].set_ylabel("Score")
    fig.suptitle("Occupancy vs Confidence Threshold")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_practical_vs_oracle(
    frame: pd.DataFrame,
    *,
    practical_col: str,
    oracle_col: str,
    title: str,
    ylabel: str,
    out_path: Path,
) -> None:
    if frame.empty:
        _placeholder_plot(out_path, title)
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    for window_fraction, group in frame.groupby("window_fraction"):
        ax.plot(group["anisotropy_ratio"], group[practical_col], marker="o", label=f"practical T={window_fraction:.3g}")
        ax.plot(group["anisotropy_ratio"], group[oracle_col], marker="s", linestyle="--", label=f"oracle T={window_fraction:.3g}")
    ax.set_title(title)
    ax.set_xlabel("Anisotropy ratio gamma_plus / gamma_minus")
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.2)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_mechanism_vs_readout_phase_map(frame: pd.DataFrame, out_path: Path) -> None:
    if frame.empty:
        _placeholder_plot(out_path, "Mechanism vs Readout Phase Map")
        return
    colors = {
        "mechanism_limited": "tab:red",
        "readout_limited": "tab:orange",
        "mixed_failure": "tab:gray",
        "bridge_candidate": "tab:green",
    }
    fig, ax = plt.subplots(figsize=(8, 5))
    for label, group in frame.groupby("classification_bin"):
        ax.scatter(
            group["mechanism_strength_score"],
            group["oracle_gap"],
            s=50,
            alpha=0.8,
            label=label,
            color=colors.get(label),
        )
    ax.set_title("Mechanism vs Readout Phase Map")
    ax.set_xlabel("Mechanism strength score")
    ax.set_ylabel("Oracle gap")
    ax.grid(alpha=0.2)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_state_clouds_with_oracle_clusters(frame: pd.DataFrame, out_path: Path) -> None:
    if frame.empty:
        _placeholder_plot(out_path, "State Clouds With Oracle Clusters")
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    colors = frame["oracle_label"].map({-1: "tab:blue", 0: "tab:gray", 1: "tab:orange"}).tolist()
    axes[0].scatter(frame["source_x"], frame["source_y"], c=colors, alpha=0.75, s=20)
    axes[0].set_title("Source Basis")
    axes[1].scatter(frame["analyzer_x"], frame["analyzer_y"], c=colors, alpha=0.75, s=20)
    axes[1].set_title("Alice Analyzer Basis")
    for axis in axes:
        axis.grid(alpha=0.2)
    axes[0].set_xlabel("Re(c0)")
    axes[0].set_ylabel("Re/Im residual coordinate")
    axes[1].set_xlabel("|c+|^2")
    axes[1].set_ylabel("|c-|^2")
    fig.suptitle("State Clouds With Oracle Clusters")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def write_plot_with_dataset(
    dataset: pd.DataFrame,
    plot_name: str,
    plot_dir: Path,
    plot_manifest: list[dict[str, str]],
    plot_fn,
) -> None:
    image_path = plot_dir / f"{plot_name}.png"
    dataset_path = plot_dir / f"{plot_name}.csv"
    ensure_dir(plot_dir)
    dataset.to_csv(dataset_path, index=False)
    plot_fn(dataset, image_path)
    plot_manifest.append(build_plot_dataset_manifest_entry(plot_name, image_path, dataset_path))


def build_best_practical_vs_oracle_frame(readout_sensitivity: pd.DataFrame) -> pd.DataFrame:
    if readout_sensitivity.empty:
        return pd.DataFrame()
    practical = readout_sensitivity[readout_sensitivity["family_category"] == "practical"].copy()
    if practical.empty:
        return pd.DataFrame()
    best_idx = practical.groupby(MECHANISM_KEYS)["confidence_efficiency"].idxmax()
    best = practical.loc[best_idx].rename(
        columns={
            "readout_family": "best_practical_rule",
            "aligned_same_sign_mass": "best_practical_aligned_same_sign_mass",
            "max_marginal_drift": "best_practical_max_marginal_drift",
        }
    )
    return best.sort_values(MECHANISM_KEYS).reset_index(drop=True)


def select_disambiguation_case(regime_classification: pd.DataFrame, case_name: str) -> pd.Series | None:
    if regime_classification.empty:
        return None
    if case_name == "mechanism_limited":
        frame = regime_classification[regime_classification["classification_bin"] == "mechanism_limited"].copy()
        if frame.empty:
            return None
        return frame.sort_values(
            ["mechanism_strength_score", "oracle_gap"],
            ascending=[True, True],
        ).iloc[0]
    if case_name == "readout_limited":
        frame = regime_classification[regime_classification["classification_bin"] == "readout_limited"].copy()
        if frame.empty:
            return None
        return frame.sort_values(
            ["oracle_gap", "mechanism_strength_score"],
            ascending=[False, False],
        ).iloc[0]
    if case_name == "mixed_failure":
        frame = regime_classification[regime_classification["classification_bin"] == "mixed_failure"].copy()
        if frame.empty:
            return None
        return frame.sort_values(
            ["oracle_gap", "mechanism_strength_score"],
            ascending=[False, False],
        ).iloc[0]
    if case_name == "bridge_candidate":
        frame = regime_classification[regime_classification["classification_bin"] == "bridge_candidate"].copy()
        if frame.empty:
            return None
        return frame.sort_values(
            ["best_practical_confidence_efficiency", "oracle_gap"],
            ascending=[False, True],
        ).iloc[0]
    raise ValueError(f"Unknown disambiguation case: {case_name}")


def export_single_raw_case(
    output_dir: Path,
    case_name: str,
    row: pd.Series,
    base: BaseArtifact,
) -> dict[str, Any]:
    case_dir = ensure_dir(output_dir / case_name)
    match = base.single_manifest[
        np.isclose(base.single_manifest["angle_deg"], float(row["angle_deg"]))
        & np.isclose(base.single_manifest["gamma_plus"], float(row["gamma_plus"]))
        & np.isclose(base.single_manifest["gamma_minus"], float(row["gamma_minus"]))
        & np.isclose(base.single_manifest["window_fraction"], float(row["window_fraction"]))
    ]
    if match.empty:
        raise ValueError(f"Could not resolve single raw case for {case_name}")
    combo_id = int(match.sort_values("combo_id").iloc[0]["combo_id"])
    trial_subset = (
        base.single_trials[base.single_trials["combo_id"] == combo_id]
        .sort_values("sample_index")
        .reset_index(drop=True)
    )
    np.savez_compressed(
        case_dir / "raw_arrays.npz",
        combo_id=np.array([combo_id], dtype=int),
        combo_key=np.array([match.iloc[0]["combo_key"]], dtype=str),
        initial_states=base.single_states.get("initial_states", np.empty((0, 0, 2)))[combo_id : combo_id + 1],
        post_states=base.single_states.get("post_states", np.empty((0, 0, 2)))[combo_id : combo_id + 1],
    )
    trial_subset.to_csv(case_dir / "trial_metrics.csv", index=False)
    dump_json(
        case_dir / "metadata.json",
        {
            "case_name": case_name,
            "combo_id": combo_id,
            "window_fraction": float(row["window_fraction"]),
            "gamma_plus": float(row["gamma_plus"]),
            "gamma_minus": float(row["gamma_minus"]),
            "anisotropy_ratio": float(row["anisotropy_ratio"]),
            "angle_deg": float(row["angle_deg"]),
            "projectivity_score": float(row["projectivity_score"]),
        },
    )
    return {
        "case_name": case_name,
        "path": str(case_dir),
        "metadata_path": str(case_dir / "metadata.json"),
    }


def export_regime_raw_case(
    output_dir: Path,
    case_name: str,
    row: pd.Series,
    base: BaseArtifact,
    readout_sensitivity: pd.DataFrame,
    mechanism_structure: pd.DataFrame,
) -> dict[str, Any]:
    case_dir = ensure_dir(output_dir / case_name)
    trial_mask = np.ones(len(base.sequential_trial_metrics), dtype=bool)
    combo_mask = np.ones(len(base.sequential_manifest), dtype=bool)
    for key in MECHANISM_KEYS:
        trial_mask &= np.isclose(base.sequential_trial_metrics[key], float(row[key]))
        combo_mask &= np.isclose(base.sequential_manifest[key], float(row[key]))
    trial_subset = (
        base.sequential_trial_metrics[trial_mask]
        .sort_values(["combo_id", "sample_index"])
        .reset_index(drop=True)
    )
    combo_subset = base.sequential_manifest[combo_mask].sort_values("combo_id").reset_index(drop=True)
    sensitivity_subset = (
        readout_sensitivity[
            np.logical_and.reduce(
                [np.isclose(readout_sensitivity[key], float(row[key])) for key in MECHANISM_KEYS]
            )
        ]
        .sort_values(["family_category", "readout_family"])
        .reset_index(drop=True)
    )
    structure_subset = mechanism_structure[
        np.logical_and.reduce(
            [np.isclose(mechanism_structure[key], float(row[key])) for key in MECHANISM_KEYS]
        )
    ].reset_index(drop=True)
    combo_ids = combo_subset["combo_id"].astype(int).to_numpy() if not combo_subset.empty else np.array([], dtype=int)
    np.savez_compressed(
        case_dir / "raw_arrays.npz",
        combo_ids=combo_ids,
        combo_keys=np.asarray(combo_subset.get("combo_key", pd.Series(dtype=str)).to_numpy(), dtype=str),
        initial_states=base.sequential_states.get("initial_states", np.empty((0, 0, 2)))[combo_ids] if len(combo_ids) else np.empty((0, 0, 2)),
        post_alice_states=base.sequential_states.get("post_alice_states", np.empty((0, 0, 2)))[combo_ids] if len(combo_ids) else np.empty((0, 0, 2)),
        post_bob_states=base.sequential_states.get("post_bob_states", np.empty((0, 0, 2)))[combo_ids] if len(combo_ids) else np.empty((0, 0, 2)),
    )
    trial_subset.to_csv(case_dir / "trial_metrics.csv", index=False)
    combo_subset.to_csv(case_dir / "combo_manifest.csv", index=False)
    sensitivity_subset.to_csv(case_dir / "readout_sensitivity.csv", index=False)
    structure_subset.to_csv(case_dir / "mechanism_structure.csv", index=False)
    dump_json(
        case_dir / "metadata.json",
        {
            "case_name": case_name,
            "classification_bin": str(row["classification_bin"]),
            "classification_justification": str(row["classification_justification"]),
            "window_fraction": float(row["window_fraction"]),
            "gamma_plus": float(row["gamma_plus"]),
            "gamma_minus": float(row["gamma_minus"]),
            "anisotropy_ratio": float(row["anisotropy_ratio"]),
            "mechanism_strength_score": float(row["mechanism_strength_score"]),
            "oracle_gap": float(row["oracle_gap"]),
        },
    )
    return {
        "case_name": case_name,
        "path": str(case_dir),
        "metadata_path": str(case_dir / "metadata.json"),
    }


def select_case_row(base: BaseArtifact, case_name: str) -> pd.Series | None:
    gated = base.sequential_gated_summary.copy()
    agreement = base.sequential_residual_agreement.copy()
    thresholds = extract_gate_thresholds(base)
    if gated.empty and agreement.empty:
        return None

    if case_name == "best_gated_regime":
        eligible = gated[gated["headline_eligible"]].copy()
        if eligible.empty:
            return None
        return eligible.sort_values(["CHSH_gated", "residual_agreement_rate"], ascending=[False, False]).iloc[0]

    if case_name == "lowest_drift_regime":
        if gated.empty:
            return None
        working = gated.copy()
        working["max_marginal_drift"] = working[["alice_marginal_drift", "bob_marginal_drift"]].max(axis=1)
        return working.sort_values(
            ["max_marginal_drift", "overfit_flag", "residual_ambiguity_rate", "mean_projectivity_compatibility"],
            ascending=[True, True, True, False],
        ).iloc[0]

    if case_name == "highest_residual_agreement_regime":
        if agreement.empty:
            return None
        working = agreement.copy()
        if not gated.empty:
            working = working.merge(
                gated[
                    [
                        "rule",
                        "window_fraction",
                        "gamma_plus",
                        "gamma_minus",
                        "anisotropy_ratio",
                        "CHSH_raw",
                        "headline_eligible",
                    ]
                ],
                on=GROUP_KEYS,
                how="left",
            )
        return working.sort_values(
            ["residual_agreement_rate", "mean_confidence_margin", "CHSH_raw"],
            ascending=[False, False, False],
        ).iloc[0]

    if case_name == "top_negative_control_chsh_regime":
        if gated.empty:
            return None
        control = gated[gated["rule"] == RULE_CONTROL_NEGATIVE_PREWINDOW].copy()
        if control.empty:
            return None
        return control.sort_values("CHSH_raw", ascending=False).iloc[0]

    if case_name == "projective_but_support_fail_regime":
        if gated.empty:
            return None
        working = gated[
            (gated["mean_projectivity_compatibility"] >= thresholds["min_projectivity_compatibility"])
            & (~gated["aligned_support_gate_pass"])
        ].copy()
        if working.empty:
            return None
        return working.sort_values(
            ["mean_projectivity_compatibility", "aligned_same_sign_mass", "CHSH_raw"],
            ascending=[False, True, False],
        ).iloc[0]

    raise ValueError(f"Unknown case selection: {case_name}")


def export_sequential_raw_case(
    output_dir: Path,
    case_name: str,
    row: pd.Series,
    base: BaseArtifact,
) -> dict[str, Any]:
    ensure_dir(output_dir)
    case_dir = ensure_dir(output_dir / case_name)

    mask = np.ones(len(base.sequential_trial_metrics), dtype=bool)
    combo_mask = np.ones(len(base.sequential_manifest), dtype=bool)
    for key in GROUP_KEYS[1:]:
        mask &= np.isclose(base.sequential_trial_metrics[key], float(row[key]))
        combo_mask &= np.isclose(base.sequential_manifest[key], float(row[key]))

    trial_subset = base.sequential_trial_metrics[mask].sort_values(["combo_id", "sample_index"]).reset_index(drop=True)
    manifest_subset = base.sequential_manifest[combo_mask].sort_values("combo_id").reset_index(drop=True)
    if not trial_subset.empty:
        trial_subset["selected_rule"] = row["rule"]
        trial_subset["selected_rule_display_name"] = RULE_DISPLAY_NAMES.get(str(row["rule"]), str(row["rule"]))

    gate_row = base.sequential_gated_summary.copy()
    if not gate_row.empty:
        gate_mask = np.ones(len(gate_row), dtype=bool)
        for key in GROUP_KEYS:
            gate_mask &= np.isclose(gate_row[key], float(row[key])) if key != "rule" else gate_row[key].eq(row[key])
        gate_matches = gate_row[gate_mask]
    else:
        gate_matches = pd.DataFrame()

    gate_labels = gate_matches.iloc[0].to_dict() if not gate_matches.empty else {}
    if not trial_subset.empty:
        for column in [
            "drift_gate_pass",
            "aligned_support_gate_pass",
            "overfit_gate_pass",
            "residual_coherence_gate_pass",
            "projectivity_gate_pass",
            "all_gates_pass",
            "headline_eligible",
        ]:
            trial_subset[column] = gate_labels.get(column)

    combo_ids = manifest_subset["combo_id"].astype(int).to_numpy() if not manifest_subset.empty else np.array([], dtype=int)
    raw_payload = {
        "combo_ids": combo_ids,
        "combo_keys": np.asarray(manifest_subset.get("combo_key", pd.Series(dtype=str)).to_numpy(), dtype=str),
        "angle_a_deg": manifest_subset.get("angle_a_deg", pd.Series(dtype=float)).to_numpy(dtype=float),
        "angle_b_deg": manifest_subset.get("angle_b_deg", pd.Series(dtype=float)).to_numpy(dtype=float),
    }
    for name in ("initial_states", "post_alice_states", "post_bob_states"):
        states = base.sequential_states.get(name)
        raw_payload[name] = states[combo_ids] if states is not None and len(combo_ids) else np.empty((0, 0, 2))

    metadata = {
        "case_name": case_name,
        "rule": row["rule"],
        "rule_display_name": RULE_DISPLAY_NAMES.get(str(row["rule"]), str(row["rule"])),
        "window_fraction": float(row["window_fraction"]),
        "gamma_plus": float(row["gamma_plus"]),
        "gamma_minus": float(row["gamma_minus"]),
        "anisotropy_ratio": float(row["anisotropy_ratio"]),
        "trial_count": int(len(trial_subset)),
        "combo_count": int(len(manifest_subset)),
        "gate_labels": gate_labels,
    }

    trial_subset.to_csv(case_dir / "trial_metrics.csv", index=False)
    manifest_subset.to_csv(case_dir / "combo_manifest.csv", index=False)
    np.savez_compressed(case_dir / "raw_arrays.npz", **raw_payload)
    dump_json(case_dir / "metadata.json", metadata)
    return {
        "case_name": case_name,
        "path": str(case_dir),
        "metadata_path": str(case_dir / "metadata.json"),
    }


def build_direct_answers(
    mechanism_structure: pd.DataFrame,
    readout_sensitivity: pd.DataFrame,
    oracle_gap_summary: pd.DataFrame,
    regime_classification: pd.DataFrame,
) -> list[str]:
    answers: list[str] = []
    if regime_classification.empty:
        return [
            "1. The disambiguation study did not have enough sequential data to classify the failure mode.",
            "2. Mechanism structure metrics were not available.",
            "3. Oracle-vs-practical comparisons were not available.",
            "4. Readout-only rescue could not be evaluated.",
            "5. No project recommendation could be made from the available artifacts.",
        ]

    counts = regime_classification["classification_bin"].value_counts()
    dominant_bin = str(counts.idxmax())
    answers.append(
        "1. The current sequential failures are primarily "
        + dominant_bin.replace("_", "-")
        + f", based on the most frequent regime classification (`{dominant_bin}` appears {int(counts.iloc[0])} times)."
    )

    if not mechanism_structure.empty:
        strongest = mechanism_structure.sort_values(
            ["usable_branch_fraction", "residual_separability_score", "residual_stability_score"],
            ascending=[False, False, False],
        ).iloc[0]
        answers.append(
            "2. The mechanism does generate residual branches, but only up to "
            f"usable_branch_fraction={strongest['usable_branch_fraction']:.3f}, "
            f"separability={strongest['residual_separability_score']:.3f}, "
            f"stability={strongest['residual_stability_score']:.3f} in its strongest regime."
        )
    else:
        answers.append("2. The mechanism structure table was empty.")

    if not oracle_gap_summary.empty:
        best_gap = oracle_gap_summary.sort_values("oracle_gap", ascending=False).iloc[0]
        answers.append(
            "3. The oracle detector "
            + ("does" if best_gap["oracle_gap"] > 0.2 else "does not")
            + " recover materially better behavior than the best practical readout in the strongest gap regime: "
            f"oracle_gap={best_gap['oracle_gap']:.3f}, best_practical_rule={best_gap['best_practical_rule']}."
        )
    else:
        answers.append("3. Oracle-gap analysis was not available.")

    readout_limited = regime_classification[regime_classification["classification_bin"] == "readout_limited"]
    if readout_limited.empty:
        answers.append("4. There is no strong evidence that improving readout alone would rescue the sequential bridge across the tested regimes.")
    else:
        best_rescue = readout_limited.sort_values("oracle_gap", ascending=False).iloc[0]
        answers.append(
            "4. Improving readout alone might rescue a narrow subset of regimes, but only where oracle improvements are substantial: "
            f"oracle_gap={best_rescue['oracle_gap']:.3f}, mechanism_strength={best_rescue['mechanism_strength_score']:.3f}."
        )

    bridge_candidates = regime_classification[regime_classification["classification_bin"] == "bridge_candidate"]
    if bridge_candidates.empty:
        answers.append(
            "5. The evidence favors pivoting toward explicit joint-selector or global-constraint mechanisms rather than continuing to refine the current projective-depletion bridge in isolation."
        )
    else:
        best_candidate = bridge_candidates.sort_values("best_practical_confidence_efficiency", ascending=False).iloc[0]
        answers.append(
            "5. There is at least one bridge-candidate regime, so continued work on projective modal depletion remains arguable: "
            f"best practical confidence efficiency={best_candidate['best_practical_confidence_efficiency']:.3f}."
        )

    return answers


def build_readme(
    base: BaseArtifact,
    mechanism_structure: pd.DataFrame,
    readout_sensitivity: pd.DataFrame,
    oracle_gap_summary: pd.DataFrame,
    regime_classification: pd.DataFrame,
    raw_case_manifest: list[dict[str, Any]],
) -> str:
    thresholds = extract_gate_thresholds(base)
    answers = build_direct_answers(mechanism_structure, readout_sensitivity, oracle_gap_summary, regime_classification)

    lines = [
        "# Verification Audit",
        "",
        f"Source artifact: `{base.artifact_dir}`",
        "",
        "## Mechanism-vs-Readout Disambiguation",
        "",
        "- Layer A analyzes post-Alice residual-state structure directly, without using binary outcomes as the primary signal.",
        "- Layer B compares practical readouts against an oracle separability benchmark to isolate readout brittleness from mechanism weakness.",
        "- The oracle detector is diagnostic only. It is used as an upper bound on what the existing residual-state structure could support, not as a physical final readout.",
        "- The key question is whether the mechanism fails to produce usable branches, the practical readouts fail to recover them, or both.",
        "",
        "## Existing Sequential Gate Thresholds",
        "",
    ]
    for name, value in thresholds.items():
        lines.append(f"- `{name}` = {value}")
    lines.extend(
        [
            "",
            "## Final Answers",
            "",
        ]
    )
    lines.extend(answers)
    lines.extend(
        [
            "",
            "## Raw Cases",
            "",
        ]
    )
    if raw_case_manifest:
        for item in raw_case_manifest:
            lines.append(f"- `{item['case_name']}`: `{item['path']}`")
    else:
        lines.append("- No representative sequential raw cases were available.")
    return "\n".join(lines).strip() + "\n"


def build_verification_audit(artifact_dir: Path, output_dir: Path) -> dict[str, Any]:
    base = load_base_artifact(artifact_dir)
    output_dir = output_dir.resolve()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    ensure_dir(output_dir)

    tables_dir = ensure_dir(output_dir / "tables")
    definitions_dir = ensure_dir(output_dir / "definitions")
    plots_dir = ensure_dir(output_dir / "plots")
    raw_cases_dir = ensure_dir(output_dir / "raw_cases")

    single_full = build_single_full(base)
    sequential_full = build_sequential_full(base)
    residual_agreement = _with_rule_display(base.sequential_residual_agreement.sort_values(GROUP_KEYS).reset_index(drop=True))
    gated_summary = _with_rule_display(base.sequential_gated_summary.sort_values(GROUP_KEYS).reset_index(drop=True))
    aligned_support = _with_rule_display(base.aligned_support_by_confidence.sort_values(GROUP_KEYS).reset_index(drop=True))
    legacy_controls = _with_rule_display(base.legacy_rule_controls.sort_values(GROUP_KEYS).reset_index(drop=True))
    top_chsh_audit = build_top_sequential_chsh_audit(base.sequential_gated_summary)
    rule_comparison = build_rule_comparison(base.sequential_gated_summary)
    headline_eligible = build_headline_eligible_summary(base.sequential_gated_summary)
    alice_oracle_cache, bob_oracle_cache = build_oracle_caches(base.sequential_manifest, base.sequential_states)
    oracle_trials = build_oracle_trial_table(base.sequential_manifest, alice_oracle_cache, bob_oracle_cache)
    mechanism_structure = build_mechanism_structure(base.sequential_manifest, alice_oracle_cache)
    readout_sensitivity, confidence_efficiency_curve = build_readout_sensitivity(
        base.sequential_trial_metrics,
        oracle_trials,
    )
    oracle_gap_summary, regime_classification = build_oracle_gap_summary(
        mechanism_structure,
        readout_sensitivity,
    )
    best_practical_vs_oracle = build_best_practical_vs_oracle_frame(readout_sensitivity)

    write_table(single_full, tables_dir / "single_full.csv", tables_dir / "single_full.json")
    write_table(sequential_full, tables_dir / "sequential_full.csv", tables_dir / "sequential_full.json")
    write_table(residual_agreement, tables_dir / "sequential_residual_agreement.csv", tables_dir / "sequential_residual_agreement.json")
    write_table(gated_summary, tables_dir / "sequential_gated_summary.csv", tables_dir / "sequential_gated_summary.json")
    write_table(aligned_support, tables_dir / "aligned_support_by_confidence.csv", tables_dir / "aligned_support_by_confidence.json")
    write_table(legacy_controls, tables_dir / "legacy_rule_controls.csv", tables_dir / "legacy_rule_controls.json")
    write_table(top_chsh_audit, tables_dir / "top_sequential_chsh_audit.csv", tables_dir / "top_sequential_chsh_audit.json")
    write_table(rule_comparison, tables_dir / "rule_comparison.csv", tables_dir / "rule_comparison.json")
    write_table(headline_eligible, tables_dir / "headline_eligible_summary.csv", tables_dir / "headline_eligible_summary.json")
    write_table(mechanism_structure, tables_dir / "mechanism_structure.csv", tables_dir / "mechanism_structure.json")
    write_table(readout_sensitivity, tables_dir / "readout_sensitivity.csv", tables_dir / "readout_sensitivity.json")
    write_table(confidence_efficiency_curve, tables_dir / "confidence_efficiency_curve.csv", tables_dir / "confidence_efficiency_curve.json")
    write_table(oracle_gap_summary, tables_dir / "oracle_gap_summary.csv", tables_dir / "oracle_gap_summary.json")
    write_table(regime_classification, tables_dir / "regime_classification.csv", tables_dir / "regime_classification.json")
    write_table(best_practical_vs_oracle, tables_dir / "best_practical_vs_oracle.csv", tables_dir / "best_practical_vs_oracle.json")

    dump_json(definitions_dir / "readout_rules.json", READOUT_RULE_DEFINITIONS)
    dump_json(
        definitions_dir / "metrics.json",
        {
            "metrics": METRIC_DEFINITIONS,
            "gates": GATE_DEFINITIONS,
            "failure_modes": FAILURE_MODE_DEFINITIONS,
        },
    )
    dump_json(definitions_dir / "gate_thresholds.json", extract_gate_thresholds(base))
    dump_json(definitions_dir / "disambiguation_metrics.json", DISAMBIGUATION_METRIC_DEFINITIONS)
    dump_json(definitions_dir / "regime_bins.json", REGIME_BIN_DEFINITIONS)
    (definitions_dir / "readout_rules.md").write_text(render_readout_rules_markdown(), encoding="utf-8")
    (definitions_dir / "metrics.md").write_text(render_metrics_markdown(), encoding="utf-8")
    (definitions_dir / "disambiguation.md").write_text(render_disambiguation_markdown(), encoding="utf-8")

    plot_manifest: list[dict[str, str]] = []
    agreement_plot_frame = _primary_window_slice(base.sequential_residual_agreement)
    write_plot_with_dataset(
        _with_rule_display(agreement_plot_frame.sort_values(["rule", "anisotropy_ratio"])),
        "residual-agreement-vs-anisotropy",
        plots_dir,
        plot_manifest,
        lambda df, path: plot_residual_metric_vs_anisotropy(
            df,
            metric="residual_agreement_rate",
            title="Residual Agreement vs Anisotropy",
            ylabel="Residual agreement rate",
            out_path=path,
        ),
    )
    write_plot_with_dataset(
        _with_rule_display(agreement_plot_frame.sort_values(["rule", "anisotropy_ratio"])),
        "residual-ambiguity-vs-anisotropy",
        plots_dir,
        plot_manifest,
        lambda df, path: plot_residual_metric_vs_anisotropy(
            df,
            metric="residual_ambiguity_rate",
            title="Residual Ambiguity vs Anisotropy",
            ylabel="Residual ambiguity rate",
            out_path=path,
        ),
    )

    aligned_plot_frame = _primary_window_slice(
        base.aligned_support_by_confidence[
            base.aligned_support_by_confidence["rule"].eq(RULE_ENERGY_LOSS_WINNER)
        ]
        if not base.aligned_support_by_confidence.empty
        and base.aligned_support_by_confidence["rule"].eq(RULE_ENERGY_LOSS_WINNER).any()
        else base.aligned_support_by_confidence
    ).sort_values(["rule", "anisotropy_ratio"])
    write_plot_with_dataset(
        _with_rule_display(aligned_plot_frame),
        "aligned-support-by-confidence",
        plots_dir,
        plot_manifest,
        plot_aligned_support_by_confidence,
    )

    gated_plot_frame = _primary_window_slice(base.sequential_gated_summary).sort_values(["rule", "anisotropy_ratio"])
    write_plot_with_dataset(
        _with_rule_display(gated_plot_frame),
        "gated-chsh-vs-anisotropy",
        plots_dir,
        plot_manifest,
        plot_gated_chsh,
    )
    write_plot_with_dataset(
        _with_rule_display(gated_plot_frame),
        "drift-vs-anisotropy-by-rule",
        plots_dir,
        plot_manifest,
        lambda df, path: plot_drift_by_rule(df, extract_gate_thresholds(base)["max_bob_drift"], path),
    )

    headline_plot_frame = base.sequential_gated_summary[
        base.sequential_gated_summary["rule"].eq(RULE_ENERGY_LOSS_WINNER)
    ].copy() if not base.sequential_gated_summary.empty else pd.DataFrame()
    write_plot_with_dataset(
        _with_rule_display(headline_plot_frame.sort_values(["window_fraction", "anisotropy_ratio"])),
        "headline-eligible-regimes",
        plots_dir,
        plot_manifest,
        plot_headline_eligible_regimes,
    )

    confidence_plot_frame = base.sequential_trial_metrics[
        [
            "alice_confidence_margin",
            "bob_confidence_margin",
            "mean_confidence_margin",
            "pair_high_confidence_residual",
            "pair_low_confidence_residual",
        ]
    ].copy() if not base.sequential_trial_metrics.empty else pd.DataFrame()
    write_plot_with_dataset(
        confidence_plot_frame,
        "residual-confidence-histograms",
        plots_dir,
        plot_manifest,
        plot_residual_confidence_histograms,
    )
    write_plot_with_dataset(
        rule_comparison,
        "legacy-vs-redesigned-rule-comparison",
        plots_dir,
        plot_manifest,
        plot_rule_comparison,
    )

    write_plot_with_dataset(
        mechanism_structure.sort_values(MECHANISM_KEYS),
        "residual_separability_vs_anisotropy",
        plots_dir,
        plot_manifest,
        lambda df, path: plot_mechanism_metric_vs_anisotropy(
            df,
            metric="residual_separability_score",
            title="Residual Separability vs Anisotropy",
            ylabel="Residual separability score",
            out_path=path,
        ),
    )
    write_plot_with_dataset(
        mechanism_structure.sort_values(MECHANISM_KEYS),
        "residual_stability_vs_anisotropy",
        plots_dir,
        plot_manifest,
        lambda df, path: plot_mechanism_metric_vs_anisotropy(
            df,
            metric="residual_stability_score",
            title="Residual Stability vs Anisotropy",
            ylabel="Residual stability score",
            out_path=path,
        ),
    )

    if not oracle_gap_summary.empty and not confidence_efficiency_curve.empty:
        target = oracle_gap_summary.sort_values("oracle_gap", ascending=False).iloc[0]
        confidence_plot_selection = confidence_efficiency_curve[
            np.logical_and.reduce(
                [np.isclose(confidence_efficiency_curve[key], float(target[key])) for key in MECHANISM_KEYS]
            )
        ].sort_values("margin_threshold")
    else:
        confidence_plot_selection = (
            confidence_efficiency_curve.groupby("margin_threshold", as_index=False)
            .agg(
                retained_fraction=("retained_fraction", "mean"),
                branch_recoverability=("branch_recoverability", "mean"),
                confidence_efficiency=("confidence_efficiency", "mean"),
            )
            if not confidence_efficiency_curve.empty
            else pd.DataFrame()
        )
    write_plot_with_dataset(
        confidence_plot_selection,
        "occupancy_vs_confidence_threshold",
        plots_dir,
        plot_manifest,
        plot_confidence_efficiency_curve,
    )

    write_plot_with_dataset(
        oracle_gap_summary.sort_values(MECHANISM_KEYS),
        "oracle_gap_vs_anisotropy",
        plots_dir,
        plot_manifest,
        lambda df, path: plot_mechanism_metric_vs_anisotropy(
            df,
            metric="oracle_gap",
            title="Oracle Gap vs Anisotropy",
            ylabel="Oracle gap",
            out_path=path,
        ),
    )
    write_plot_with_dataset(
        best_practical_vs_oracle,
        "support_recoverability_practical_vs_oracle",
        plots_dir,
        plot_manifest,
        lambda df, path: plot_practical_vs_oracle(
            df,
            practical_col="best_practical_aligned_same_sign_mass",
            oracle_col="oracle_aligned_same_sign_mass",
            title="Support Recoverability: Practical vs Oracle",
            ylabel="Aligned same-sign mass",
            out_path=path,
        ),
    )
    write_plot_with_dataset(
        best_practical_vs_oracle,
        "drift_recoverability_practical_vs_oracle",
        plots_dir,
        plot_manifest,
        lambda df, path: plot_practical_vs_oracle(
            df,
            practical_col="best_practical_max_marginal_drift",
            oracle_col="oracle_max_marginal_drift",
            title="Drift Recoverability: Practical vs Oracle",
            ylabel="Max marginal drift",
            out_path=path,
        ),
    )
    write_plot_with_dataset(
        regime_classification,
        "mechanism_vs_readout_phase_map",
        plots_dir,
        plot_manifest,
        plot_mechanism_vs_readout_phase_map,
    )

    if not regime_classification.empty and not base.sequential_manifest.empty:
        representative = select_disambiguation_case(regime_classification, "readout_limited")
        if representative is None:
            representative = select_disambiguation_case(regime_classification, "mechanism_limited")
        if representative is None:
            representative = regime_classification.iloc[0]
        combo_match = (
            base.sequential_manifest[
                np.logical_and.reduce(
                    [np.isclose(base.sequential_manifest[key], float(representative[key])) for key in MECHANISM_KEYS]
                )
            ]
            .sort_values(["angle_a_deg", "combo_id"])
            .drop_duplicates("angle_a_deg")
        )
        if not combo_match.empty:
            combo_id = int(
                combo_match.assign(angle_distance=(combo_match["angle_a_deg"] - 45.0).abs())
                .sort_values(["angle_distance", "combo_id"])
                .iloc[0]["combo_id"]
            )
            post_alice_states = base.sequential_states.get("post_alice_states", np.empty((0, 0, 2)))[combo_id]
            source_features = phase_aligned_features(post_alice_states)
            analyzer_feature_block = analyzer_features(post_alice_states, float(combo_match[combo_match["combo_id"] == combo_id].iloc[0]["angle_a_deg"]))
            cloud_dataset = pd.DataFrame(
                {
                    "source_x": source_features[:, 0],
                    "source_y": source_features[:, 1],
                    "analyzer_x": analyzer_feature_block[:, 0],
                    "analyzer_y": analyzer_feature_block[:, 1],
                    "oracle_label": alice_oracle_cache[combo_id].outcomes,
                }
            )
        else:
            cloud_dataset = pd.DataFrame()
    else:
        cloud_dataset = pd.DataFrame()
    write_plot_with_dataset(
        cloud_dataset,
        "state_clouds_with_oracle_clusters",
        plots_dir,
        plot_manifest,
        plot_state_clouds_with_oracle_clusters,
    )
    dump_json(plots_dir / "manifest.json", plot_manifest)

    raw_case_manifest: list[dict[str, Any]] = []
    for case_name in ["mechanism_limited", "readout_limited", "mixed_failure", "bridge_candidate"]:
        row = select_disambiguation_case(regime_classification, case_name)
        if row is None:
            continue
        raw_case_manifest.append(
            export_regime_raw_case(
                raw_cases_dir,
                case_name,
                row,
                base,
                readout_sensitivity,
                mechanism_structure,
            )
        )
    if not single_full.empty:
        raw_case_manifest.append(
            export_single_raw_case(
                raw_cases_dir,
                "best_single_analyzer_case",
                single_full.sort_values("projectivity_score", ascending=False).iloc[0],
                base,
            )
        )
    dump_json(raw_cases_dir / "manifest.json", raw_case_manifest)

    readme = build_readme(
        base,
        mechanism_structure,
        readout_sensitivity,
        oracle_gap_summary,
        regime_classification,
        raw_case_manifest,
    )
    (output_dir / "README.md").write_text(readme, encoding="utf-8")

    manifest = {
        "audit_dir": str(output_dir),
        "source_artifact_dir": str(base.artifact_dir),
        "table_rows": {
            "single_full": int(len(single_full)),
            "sequential_full": int(len(sequential_full)),
            "sequential_residual_agreement": int(len(residual_agreement)),
            "sequential_gated_summary": int(len(gated_summary)),
            "aligned_support_by_confidence": int(len(aligned_support)),
            "legacy_rule_controls": int(len(legacy_controls)),
            "top_sequential_chsh_audit": int(len(top_chsh_audit)),
            "headline_eligible_summary": int(len(headline_eligible)),
            "mechanism_structure": int(len(mechanism_structure)),
            "readout_sensitivity": int(len(readout_sensitivity)),
            "oracle_gap_summary": int(len(oracle_gap_summary)),
            "regime_classification": int(len(regime_classification)),
        },
        "plot_count": len(plot_manifest),
        "raw_case_count": len(raw_case_manifest),
    }
    dump_json(output_dir / "manifest.json", manifest)
    return manifest
