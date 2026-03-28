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
    base: BaseArtifact,
    single_full: pd.DataFrame,
    gated_summary: pd.DataFrame,
    residual_agreement_summary: pd.DataFrame,
    aligned_support: pd.DataFrame,
) -> list[str]:
    answers: list[str] = []
    thresholds = extract_gate_thresholds(base)

    headline = gated_summary[gated_summary["headline_eligible"]].copy() if not gated_summary.empty else pd.DataFrame()
    if headline.empty:
        answers.append(
            "1. No post-update rule currently produces a headline-eligible sequential regime after the hard gates."
        )
    else:
        best = headline.sort_values("CHSH_gated", ascending=False).iloc[0]
        answers.append(
            "1. At least one headline primary regime survives the hard gates: "
            f"ratio={best['anisotropy_ratio']:.3g}, window={best['window_fraction']:.3g}, CHSH_gated={best['CHSH_gated']:.3f}."
        )

    promising = headline if not headline.empty else gated_summary[gated_summary["rule"] == RULE_ENERGY_LOSS_WINNER].copy()
    if not promising.empty:
        best_agreement = promising.sort_values(
            ["residual_agreement_rate", "mean_confidence_margin"],
            ascending=[False, False],
        ).iloc[0]
        answers.append(
            "2. Energy-based and residual-template readouts agree best in the strongest surviving or nearest-surviving headline regime at "
            f"agreement={best_agreement['residual_agreement_rate']:.3f}, ambiguity={best_agreement['residual_ambiguity_rate']:.3f}."
        )
    elif not residual_agreement_summary.empty:
        best_agreement = residual_agreement_summary.sort_values(
            ["residual_agreement_rate", "mean_confidence_margin"],
            ascending=[False, False],
        ).iloc[0]
        answers.append(
            "2. Agreement exists, but not in a regime that clears the hard gates: "
            f"best agreement={best_agreement['residual_agreement_rate']:.3f}, ambiguity={best_agreement['residual_ambiguity_rate']:.3f}."
        )
    else:
        answers.append("2. Residual-agreement diagnostics were not available.")

    aligned_headline = aligned_support[aligned_support["rule"] == RULE_ENERGY_LOSS_WINNER].copy() if not aligned_support.empty else pd.DataFrame()
    if not aligned_headline.empty:
        best_support = aligned_headline.sort_values(
            ["aligned_same_sign_mass_high_confidence", "aligned_same_sign_mass"],
            ascending=[True, True],
        ).iloc[0]
        answers.append(
            "3. High-confidence filtering "
            + (
                "does suppress"
                if best_support["aligned_same_sign_mass_high_confidence"] < best_support["aligned_same_sign_mass"]
                else "does not suppress"
            )
            + " aligned same-sign mass in the best headline slice: "
            f"all={best_support['aligned_same_sign_mass']:.3f}, high-confidence={best_support['aligned_same_sign_mass_high_confidence']:.3f}."
        )
    else:
        answers.append("3. Aligned-support-by-confidence data were not available.")

    redesigned = gated_summary[
        ~gated_summary["rule"].isin([RULE_LEGACY_DOMINANT_POST, RULE_LEGACY_DOMINANCE_SHIFT, RULE_CONTROL_NEGATIVE_PREWINDOW])
    ].copy() if not gated_summary.empty else pd.DataFrame()
    low_drift = redesigned[
        (redesigned["alice_marginal_drift"] <= thresholds["max_alice_drift"])
        & (redesigned["bob_marginal_drift"] <= thresholds["max_bob_drift"])
    ] if not redesigned.empty else pd.DataFrame()
    if low_drift.empty:
        answers.append(
            "4. Low drift does not survive robustly once legacy and negative-control rules are removed from headline use."
        )
    else:
        best_low_drift = low_drift.sort_values(
            ["residual_agreement_rate", "mean_projectivity_compatibility"],
            ascending=[False, False],
        ).iloc[0]
        answers.append(
            "4. Low drift survives for some redesigned rules, but those regimes still need the support and coherence gates checked: "
            f"rule={best_low_drift['rule_display_name'] if 'rule_display_name' in best_low_drift else best_low_drift['rule']}, "
            f"alice_drift={best_low_drift['alice_marginal_drift']:.3f}, bob_drift={best_low_drift['bob_marginal_drift']:.3f}."
        )

    if not headline.empty:
        answers.append(
            "5. There is still some sphere-like sequential evidence only in the narrow sense that at least one headline rule clears drift, support, coherence, and projectivity together."
        )
    else:
        best_single = single_full.sort_values("projectivity_score", ascending=False).iloc[0] if not single_full.empty else None
        if best_single is not None:
            answers.append(
                "5. After the redesign there is no credible sphere-like sequential bridge yet; the strongest surviving evidence remains single-analyzer projectivity at "
                f"ratio={best_single['anisotropy_ratio']:.3g}, window={best_single['window_fraction']:.3g}, angle={best_single['angle_deg']:.3g}."
            )
        else:
            answers.append("5. After the redesign there is no credible sphere-like sequential bridge in the available artifacts.")

    return answers


def build_readme(
    base: BaseArtifact,
    single_full: pd.DataFrame,
    gated_summary: pd.DataFrame,
    residual_agreement_summary: pd.DataFrame,
    aligned_support: pd.DataFrame,
    raw_case_manifest: list[dict[str, Any]],
) -> str:
    thresholds = extract_gate_thresholds(base)
    answers = build_direct_answers(base, single_full, gated_summary, residual_agreement_summary, aligned_support)

    lines = [
        "# Verification Audit",
        "",
        f"Source artifact: `{base.artifact_dir}`",
        "",
        "## Sequential Redesign",
        "",
        "- `dominant_pre` is retained only as the negative-control rule `control_negative_prewindow` because it reads pre-window branch dominance instead of post-update depletion structure.",
        "- The new primary sequential rule is `energy_loss_winner`, which assigns outcomes from analyzer-basis branch energy losses during the update.",
        "- `residual_agreement_rate` measures how often the energy-loss winner and residual-template classifier agree across both sequential stages.",
        "- A regime is `headline_eligible` only when it belongs to the primary rule and passes drift, aligned-support, residual-coherence, projectivity, and overfit gates.",
        "- CHSH is secondary because raw pair structure is not considered credible until the non-CHSH gates are already satisfied.",
        "",
        "## Gate Thresholds",
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

    write_table(single_full, tables_dir / "single_full.csv", tables_dir / "single_full.json")
    write_table(sequential_full, tables_dir / "sequential_full.csv", tables_dir / "sequential_full.json")
    write_table(residual_agreement, tables_dir / "sequential_residual_agreement.csv", tables_dir / "sequential_residual_agreement.json")
    write_table(gated_summary, tables_dir / "sequential_gated_summary.csv", tables_dir / "sequential_gated_summary.json")
    write_table(aligned_support, tables_dir / "aligned_support_by_confidence.csv", tables_dir / "aligned_support_by_confidence.json")
    write_table(legacy_controls, tables_dir / "legacy_rule_controls.csv", tables_dir / "legacy_rule_controls.json")
    write_table(top_chsh_audit, tables_dir / "top_sequential_chsh_audit.csv", tables_dir / "top_sequential_chsh_audit.json")
    write_table(rule_comparison, tables_dir / "rule_comparison.csv", tables_dir / "rule_comparison.json")
    write_table(headline_eligible, tables_dir / "headline_eligible_summary.csv", tables_dir / "headline_eligible_summary.json")

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
    (definitions_dir / "readout_rules.md").write_text(render_readout_rules_markdown(), encoding="utf-8")
    (definitions_dir / "metrics.md").write_text(render_metrics_markdown(), encoding="utf-8")

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
    dump_json(plots_dir / "manifest.json", plot_manifest)

    raw_case_manifest: list[dict[str, Any]] = []
    for case_name in [
        "best_gated_regime",
        "lowest_drift_regime",
        "highest_residual_agreement_regime",
        "top_negative_control_chsh_regime",
        "projective_but_support_fail_regime",
    ]:
        row = select_case_row(base, case_name)
        if row is None:
            continue
        raw_case_manifest.append(export_sequential_raw_case(raw_cases_dir, case_name, row, base))
    dump_json(raw_cases_dir / "manifest.json", raw_case_manifest)

    readme = build_readme(base, single_full, gated_summary, residual_agreement, aligned_support, raw_case_manifest)
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
        },
        "plot_count": len(plot_manifest),
        "raw_case_count": len(raw_case_manifest),
    }
    dump_json(output_dir / "manifest.json", manifest)
    return manifest
