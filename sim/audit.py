from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .definitions import (
    FAILURE_MODE_DEFINITIONS,
    METRIC_DEFINITIONS,
    OVERFIT_CHSH_THRESHOLD,
    PRIMARY_WINDOW_FRACTION,
    READOUT_RULE_DEFINITIONS,
    SIGNALING_THRESHOLD,
    render_metrics_markdown,
    render_readout_rules_markdown,
)
from .io import dump_json, ensure_dir, load_json
from .state import abs2, to_analyzer_basis

CHSH_TERM_LABELS = {
    (0.0, 22.5): "E_ab",
    (0.0, 67.5): "E_abp",
    (45.0, 22.5): "E_apb",
    (45.0, 67.5): "E_apbp",
}
GROUP_KEYS = ["rule", "window_fraction", "gamma_plus", "gamma_minus", "anisotropy_ratio"]
PAIR_KEYS = GROUP_KEYS + ["phiA", "phiB"]
SEQUENTIAL_BASE_KEYS = ["window_fraction", "gamma_plus", "gamma_minus", "anisotropy_ratio"]
SINGLE_KEYS = ["window_fraction", "gamma_plus", "gamma_minus", "anisotropy_ratio", "angle_deg"]


@dataclass(slots=True)
class BaseArtifact:
    artifact_dir: Path
    summary: dict[str, Any]
    single_summary: pd.DataFrame
    single_trials: pd.DataFrame
    single_manifest: pd.DataFrame
    single_states: dict[str, np.ndarray]
    sequential_rule_summary: pd.DataFrame
    sequential_trial_metrics: pd.DataFrame
    sequential_correlation_summary: pd.DataFrame
    sequential_drift_summary: pd.DataFrame
    sequential_chsh_summary: pd.DataFrame
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


def load_base_artifact(artifact_dir: Path) -> BaseArtifact:
    artifact_dir = artifact_dir.resolve()
    single_dir = artifact_dir / "single"
    sequential_dir = artifact_dir / "sequential"
    return BaseArtifact(
        artifact_dir=artifact_dir,
        summary=load_json(artifact_dir / "summary.json"),
        single_summary=load_csv(single_dir / "summary.csv"),
        single_trials=load_csv(single_dir / "trial_metrics.csv"),
        single_manifest=pd.DataFrame(load_json(single_dir / "run_manifest.json")),
        single_states=load_npz_dict(single_dir / "states.npz"),
        sequential_rule_summary=load_csv(sequential_dir / "rule_summary.csv"),
        sequential_trial_metrics=load_csv(sequential_dir / "trial_metrics.csv"),
        sequential_correlation_summary=load_csv(sequential_dir / "correlation_summary.csv"),
        sequential_drift_summary=load_csv(sequential_dir / "drift_summary.csv"),
        sequential_chsh_summary=load_csv(sequential_dir / "chsh_summary.csv"),
        sequential_manifest=pd.DataFrame(load_json(sequential_dir / "run_manifest.json")),
        sequential_states=load_npz_dict(sequential_dir / "states.npz"),
    )


def build_single_full(base: BaseArtifact) -> pd.DataFrame:
    if base.single_summary.empty:
        return pd.DataFrame()
    frame = base.single_summary.copy()
    return frame.sort_values(SINGLE_KEYS).reset_index(drop=True)


def build_pair_projectivity(base: BaseArtifact) -> tuple[pd.DataFrame, pd.DataFrame]:
    trials = base.sequential_trial_metrics.copy()
    if trials.empty:
        return pd.DataFrame(), pd.DataFrame()

    trials["sequential_projectivity_compatibility_trial"] = 0.5 * (
        trials["alice_complementary_residual_quality"]
        + trials["bob_complementary_residual_quality"]
    )
    pair_summary = (
        trials.groupby(
            ["window_fraction", "gamma_plus", "gamma_minus", "anisotropy_ratio", "angle_a_deg", "angle_b_deg"],
            as_index=False,
        )
        .agg(
            alice_projectivity_score=("alice_complementary_residual_quality", "mean"),
            bob_projectivity_score=("bob_complementary_residual_quality", "mean"),
            sequential_projectivity_compatibility=("sequential_projectivity_compatibility_trial", "mean"),
            alice_residual_purity=("alice_residual_purity", "mean"),
            bob_residual_purity=("bob_residual_purity", "mean"),
        )
        .rename(columns={"angle_a_deg": "phiA", "angle_b_deg": "phiB"})
        .sort_values(["window_fraction", "anisotropy_ratio", "phiA", "phiB"])
        .reset_index(drop=True)
    )
    group_summary = (
        pair_summary.groupby(SEQUENTIAL_BASE_KEYS, as_index=False)
        .agg(
            sequential_projectivity_group_mean=("sequential_projectivity_compatibility", "mean"),
            mean_alice_projectivity_score=("alice_projectivity_score", "mean"),
            mean_bob_projectivity_score=("bob_projectivity_score", "mean"),
        )
        .sort_values(["window_fraction", "anisotropy_ratio"])
        .reset_index(drop=True)
    )
    return pair_summary, group_summary


def build_group_reference_table(base: BaseArtifact) -> pd.DataFrame:
    if base.sequential_rule_summary.empty:
        return pd.DataFrame(columns=GROUP_KEYS)
    return (
        base.sequential_rule_summary[GROUP_KEYS]
        .drop_duplicates()
        .sort_values(GROUP_KEYS)
        .reset_index(drop=True)
    )


def build_drift_table(base: BaseArtifact, group_reference: pd.DataFrame) -> pd.DataFrame:
    if base.sequential_drift_summary.empty:
        return pd.DataFrame(columns=GROUP_KEYS + ["alice_marginal_drift", "bob_marginal_drift"])
    drift = base.sequential_drift_summary.rename(
        columns={
            "alice_drift_max": "alice_marginal_drift",
            "bob_drift_max": "bob_marginal_drift",
        }
    )
    merge_cols = ["rule", "window_fraction", "anisotropy_ratio"]
    merged = drift.merge(
        group_reference.drop_duplicates(merge_cols),
        on=merge_cols,
        how="left",
    )
    return merged[GROUP_KEYS + ["alice_marginal_drift", "bob_marginal_drift"]]


def build_aligned_metrics(base: BaseArtifact) -> pd.DataFrame:
    frame = base.sequential_rule_summary.copy()
    if frame.empty:
        return pd.DataFrame(columns=GROUP_KEYS + ["aligned_same_sign_mass", "aligned_anti_mass"])
    aligned = frame[np.isclose(frame["angle_a_deg"], frame["angle_b_deg"])]
    if aligned.empty:
        return pd.DataFrame(columns=GROUP_KEYS + ["aligned_same_sign_mass", "aligned_anti_mass"])
    return (
        aligned.groupby(GROUP_KEYS, as_index=False)
        .agg(
            aligned_same_sign_mass=("same_sign_mass", "mean"),
            aligned_anti_mass=("anti_sign_mass", "mean"),
        )
        .sort_values(GROUP_KEYS)
        .reset_index(drop=True)
    )


def build_chsh_terms(base: BaseArtifact, group_reference: pd.DataFrame) -> pd.DataFrame:
    frame = base.sequential_correlation_summary.copy()
    if frame.empty:
        return pd.DataFrame(columns=GROUP_KEYS + ["E_ab", "E_abp", "E_apb", "E_apbp", "CHSH"])

    canonical = frame[
        frame.apply(
            lambda row: (float(row["angle_a_deg"]), float(row["angle_b_deg"])) in CHSH_TERM_LABELS,
            axis=1,
        )
    ].copy()
    canonical["term"] = canonical.apply(
        lambda row: CHSH_TERM_LABELS[(float(row["angle_a_deg"]), float(row["angle_b_deg"]))],
        axis=1,
    )
    terms = (
        canonical.pivot_table(
            index=GROUP_KEYS,
            columns="term",
            values="correlation",
            aggfunc="first",
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )

    if not base.sequential_chsh_summary.empty:
        chsh = base.sequential_chsh_summary.rename(columns={"chsh": "CHSH"})
        chsh = chsh.merge(
            group_reference.drop_duplicates(["rule", "window_fraction", "anisotropy_ratio"]),
            on=["rule", "window_fraction", "anisotropy_ratio"],
            how="left",
        )
        chsh = chsh[GROUP_KEYS + ["CHSH"]]
        terms = terms.merge(chsh, on=GROUP_KEYS, how="left")
    else:
        terms["CHSH"] = np.nan

    return terms.sort_values(GROUP_KEYS).reset_index(drop=True)


def build_group_summary(base: BaseArtifact) -> tuple[pd.DataFrame, pd.DataFrame]:
    group_reference = build_group_reference_table(base)
    pair_projectivity, pair_projectivity_group = build_pair_projectivity(base)
    drift = build_drift_table(base, group_reference)
    aligned = build_aligned_metrics(base)
    chsh_terms = build_chsh_terms(base, group_reference)

    group_summary = group_reference.merge(drift, on=GROUP_KEYS, how="left")
    group_summary = group_summary.merge(aligned, on=GROUP_KEYS, how="left")
    group_summary = group_summary.merge(
        pair_projectivity_group,
        on=SEQUENTIAL_BASE_KEYS,
        how="left",
    )
    group_summary = group_summary.merge(chsh_terms, on=GROUP_KEYS, how="left")
    group_summary["no_signaling_flag"] = (
        group_summary["alice_marginal_drift"].fillna(np.inf) <= SIGNALING_THRESHOLD
    ) & (
        group_summary["bob_marginal_drift"].fillna(np.inf) <= SIGNALING_THRESHOLD
    )
    group_summary["signaling_flag"] = ~group_summary["no_signaling_flag"]
    group_summary["max_marginal_drift"] = group_summary[
        ["alice_marginal_drift", "bob_marginal_drift"]
    ].max(axis=1)
    group_summary["overfit_flag"] = (
        (group_summary["CHSH"].fillna(-np.inf) > OVERFIT_CHSH_THRESHOLD)
        & (
            (group_summary["alice_marginal_drift"].fillna(0.0) > SIGNALING_THRESHOLD)
            | (group_summary["bob_marginal_drift"].fillna(0.0) > SIGNALING_THRESHOLD)
        )
    )
    return (
        group_summary.sort_values(GROUP_KEYS).reset_index(drop=True),
        pair_projectivity,
    )


def build_sequential_full(base: BaseArtifact) -> tuple[pd.DataFrame, pd.DataFrame]:
    if base.sequential_rule_summary.empty:
        return pd.DataFrame(), pd.DataFrame()

    group_summary, pair_projectivity = build_group_summary(base)
    frame = base.sequential_rule_summary.copy().rename(
        columns={
            "angle_a_deg": "phiA",
            "angle_b_deg": "phiB",
            "correlation": "E_phiA_phiB",
        }
    )
    frame = frame.merge(
        pair_projectivity,
        on=SEQUENTIAL_BASE_KEYS + ["phiA", "phiB"],
        how="left",
    )
    frame = frame.merge(
        group_summary[
            GROUP_KEYS
            + [
                "alice_marginal_drift",
                "bob_marginal_drift",
                "aligned_same_sign_mass",
                "aligned_anti_mass",
                "E_ab",
                "E_abp",
                "E_apb",
                "E_apbp",
                "CHSH",
                "no_signaling_flag",
                "signaling_flag",
                "overfit_flag",
                "sequential_projectivity_group_mean",
            ]
        ],
        on=GROUP_KEYS,
        how="left",
    )
    frame["f5_overfit_readout_flag"] = frame["overfit_flag"]
    frame = frame[
        [
            "rule",
            "anisotropy_ratio",
            "gamma_plus",
            "gamma_minus",
            "window_fraction",
            "phiA",
            "phiB",
            "E_phiA_phiB",
            "E_ab",
            "E_abp",
            "E_apb",
            "E_apbp",
            "CHSH",
            "alice_marginal_drift",
            "bob_marginal_drift",
            "aligned_same_sign_mass",
            "aligned_anti_mass",
            "same_sign_mass",
            "anti_sign_mass",
            "alice_marginal",
            "bob_marginal",
            "no_signaling_flag",
            "signaling_flag",
            "overfit_flag",
            "f5_overfit_readout_flag",
            "sequential_projectivity_compatibility",
            "sequential_projectivity_group_mean",
            "alice_projectivity_score",
            "bob_projectivity_score",
            "alice_residual_purity",
            "bob_residual_purity",
        ]
    ]
    return (
        frame.sort_values(PAIR_KEYS).reset_index(drop=True),
        group_summary,
    )


def classify_top_row(row: pd.Series) -> str:
    if bool(row.get("signaling_flag", False)):
        return "likely signaling"
    if bool(row.get("overfit_flag", False)):
        return "likely readout artifact"
    if (
        float(row.get("aligned_same_sign_mass", 1.0)) <= 0.1
        and float(row.get("sequential_projectivity_group_mean", 0.0)) >= 0.8
        and float(row.get("CHSH", 0.0)) >= 1.5
    ):
        return "likely meaningful"
    return "likely readout artifact"


def build_top_chsh_audit(group_summary: pd.DataFrame) -> pd.DataFrame:
    if group_summary.empty:
        return pd.DataFrame()
    frame = group_summary.sort_values("CHSH", ascending=False).head(10).copy()
    frame["audit_note"] = frame.apply(classify_top_row, axis=1)
    return frame[
        [
            "rule",
            "anisotropy_ratio",
            "gamma_plus",
            "gamma_minus",
            "window_fraction",
            "CHSH",
            "alice_marginal_drift",
            "bob_marginal_drift",
            "aligned_same_sign_mass",
            "aligned_anti_mass",
            "sequential_projectivity_group_mean",
            "signaling_flag",
            "overfit_flag",
            "audit_note",
        ]
    ].reset_index(drop=True)


def build_rule_comparison(group_summary: pd.DataFrame) -> pd.DataFrame:
    if group_summary.empty:
        return pd.DataFrame()
    frame = (
        group_summary.groupby("rule", as_index=False)
        .agg(
            average_chsh=("CHSH", "mean"),
            average_alice_marginal_drift=("alice_marginal_drift", "mean"),
            average_bob_marginal_drift=("bob_marginal_drift", "mean"),
            average_max_marginal_drift=("max_marginal_drift", "mean"),
            average_aligned_same_sign_mass=("aligned_same_sign_mass", "mean"),
            average_projectivity_compatibility=("sequential_projectivity_group_mean", "mean"),
            f5_overfit_readout_rows=("overfit_flag", "sum"),
            no_signaling_fraction=("no_signaling_flag", "mean"),
        )
        .sort_values("average_chsh", ascending=False)
        .reset_index(drop=True)
    )
    return frame


def build_trust_ranking(group_summary: pd.DataFrame) -> pd.DataFrame:
    if group_summary.empty:
        return pd.DataFrame()
    frame = group_summary.copy()
    frame["no_signal_score"] = np.clip(
        1.0 - frame["max_marginal_drift"].fillna(SIGNALING_THRESHOLD) / SIGNALING_THRESHOLD,
        0.0,
        1.0,
    )
    frame["aligned_score"] = np.clip(1.0 - frame["aligned_same_sign_mass"].fillna(1.0), 0.0, 1.0)
    frame["projectivity_score_component"] = np.clip(
        frame["sequential_projectivity_group_mean"].fillna(0.0),
        0.0,
        1.0,
    )
    frame["chsh_score_component"] = np.clip(frame["CHSH"].fillna(0.0) / 2.0, 0.0, 1.0)
    frame["trust_score"] = (
        0.35 * frame["no_signal_score"]
        + 0.25 * frame["aligned_score"]
        + 0.25 * frame["projectivity_score_component"]
        + 0.15 * frame["chsh_score_component"]
        - 0.25 * frame["overfit_flag"].astype(float)
    )
    frame["trust_label"] = np.where(
        (~frame["overfit_flag"]) & frame["no_signaling_flag"] & (frame["trust_score"] >= 0.75),
        "credible",
        np.where(frame["trust_score"] >= 0.5, "caution", "not_trustworthy"),
    )
    return frame[
        [
            "rule",
            "anisotropy_ratio",
            "gamma_plus",
            "gamma_minus",
            "window_fraction",
            "CHSH",
            "alice_marginal_drift",
            "bob_marginal_drift",
            "aligned_same_sign_mass",
            "aligned_anti_mass",
            "sequential_projectivity_group_mean",
            "no_signaling_flag",
            "overfit_flag",
            "trust_score",
            "trust_label",
        ]
    ].sort_values("trust_score", ascending=False).reset_index(drop=True)


def select_single_case(single_full: pd.DataFrame, *, case_name: str) -> pd.Series | None:
    if single_full.empty:
        return None
    if case_name == "best_single_projectivity":
        return single_full.sort_values("projectivity_score", ascending=False).iloc[0]
    if case_name == "isotropic_baseline":
        baseline = single_full[np.isclose(single_full["anisotropy_ratio"], 1.0)].copy()
        if baseline.empty:
            return single_full.iloc[0]
        baseline["window_distance"] = (baseline["window_fraction"] - PRIMARY_WINDOW_FRACTION).abs()
        baseline["angle_distance"] = (baseline["angle_deg"] - 45.0).abs()
        return baseline.sort_values(
            ["window_distance", "angle_distance", "projectivity_score"],
            ascending=[True, True, False],
        ).iloc[0]
    raise ValueError(f"Unknown single-case selection: {case_name}")


def select_sequential_case(group_summary: pd.DataFrame, *, case_name: str) -> pd.Series | None:
    if group_summary.empty:
        return None
    if case_name == "top_sequential_chsh":
        return group_summary.sort_values("CHSH", ascending=False).iloc[0]
    if case_name == "lowest_drift_sequential":
        frame = group_summary.copy()
        frame = frame.sort_values(
            ["max_marginal_drift", "overfit_flag", "sequential_projectivity_group_mean", "CHSH"],
            ascending=[True, True, False, False],
        )
        return frame.iloc[0]
    if case_name == "flagged_overfit_readout":
        flagged = group_summary[group_summary["overfit_flag"]].copy()
        if flagged.empty:
            return group_summary.sort_values("CHSH", ascending=False).iloc[0]
        return flagged.sort_values("CHSH", ascending=False).iloc[0]
    raise ValueError(f"Unknown sequential-case selection: {case_name}")


def export_single_raw_case(
    output_dir: Path,
    case_name: str,
    row: pd.Series,
    base: BaseArtifact,
) -> dict[str, Any]:
    manifest = base.single_manifest.copy()
    match = manifest[
        np.isclose(manifest["angle_deg"], row["angle_deg"])
        & np.isclose(manifest["gamma_plus"], row["gamma_plus"])
        & np.isclose(manifest["gamma_minus"], row["gamma_minus"])
        & np.isclose(manifest["window_fraction"], row["window_fraction"])
    ]
    if match.empty:
        raise ValueError(f"Could not resolve single raw case for {case_name}")
    combo = match.sort_values("combo_id").iloc[0]
    combo_id = int(combo["combo_id"])

    trial_subset = (
        base.single_trials[base.single_trials["combo_id"] == combo_id]
        .sort_values("sample_index")
        .reset_index(drop=True)
    )
    pre_coords = (
        trial_subset["c_plus_pre_real"].to_numpy() + 1j * trial_subset["c_plus_pre_imag"].to_numpy(),
        trial_subset["c_minus_pre_real"].to_numpy() + 1j * trial_subset["c_minus_pre_imag"].to_numpy(),
    )
    post_coords = (
        trial_subset["c_plus_post_real"].to_numpy() + 1j * trial_subset["c_plus_post_imag"].to_numpy(),
        trial_subset["c_minus_post_real"].to_numpy() + 1j * trial_subset["c_minus_post_imag"].to_numpy(),
    )
    case_dir = ensure_dir(output_dir / case_name)
    np.savez_compressed(
        case_dir / "raw_arrays.npz",
        combo_id=np.array(combo_id),
        angle_deg=np.array(float(row["angle_deg"])),
        initial_states=base.single_states["initial_states"][combo_id],
        post_states=base.single_states["post_states"][combo_id],
        analyzer_pre_coords=np.column_stack(pre_coords),
        analyzer_post_coords=np.column_stack(post_coords),
        extracted_energies=trial_subset[["branch_loss_plus", "branch_loss_minus"]].to_numpy(),
        residual_branch_sign=trial_subset["residual_branch_sign"].to_numpy(),
        extracted_branch_sign=trial_subset["extracted_branch_sign"].to_numpy(),
    )
    metadata = {
        "case_name": case_name,
        "case_type": "single",
        "selection_row": row.to_dict(),
        "combo_id": combo_id,
    }
    dump_json(case_dir / "metadata.json", metadata)
    return metadata


def pivot_outcomes(
    trial_subset: pd.DataFrame,
    combo_ids: list[int],
    column: str,
) -> np.ndarray:
    pivot = trial_subset.pivot(index="combo_id", columns="sample_index", values=column)
    pivot = pivot.reindex(combo_ids)
    return pivot.to_numpy()


def export_sequential_raw_case(
    output_dir: Path,
    case_name: str,
    row: pd.Series,
    base: BaseArtifact,
) -> dict[str, Any]:
    manifest = base.sequential_manifest.copy()
    subset = manifest[
        np.isclose(manifest["window_fraction"], row["window_fraction"])
        & np.isclose(manifest["gamma_plus"], row["gamma_plus"])
        & np.isclose(manifest["gamma_minus"], row["gamma_minus"])
    ].sort_values(["angle_a_deg", "angle_b_deg", "combo_id"])
    if subset.empty:
        raise ValueError(f"Could not resolve sequential raw case for {case_name}")

    combo_ids = subset["combo_id"].astype(int).tolist()
    idx = np.array(combo_ids, dtype=int)
    initial_states = base.sequential_states["initial_states"][idx]
    post_alice_states = base.sequential_states["post_alice_states"][idx]
    post_bob_states = base.sequential_states["post_bob_states"][idx]
    angle_a_deg = subset["angle_a_deg"].to_numpy(dtype=float)
    angle_b_deg = subset["angle_b_deg"].to_numpy(dtype=float)

    alice_pre_coords = []
    alice_post_coords = []
    bob_pre_coords = []
    bob_post_coords = []
    alice_extracted = []
    bob_extracted = []
    for pair_index, (phi_a_deg, phi_b_deg) in enumerate(zip(angle_a_deg, angle_b_deg, strict=True)):
        phi_a = np.deg2rad(phi_a_deg)
        phi_b = np.deg2rad(phi_b_deg)
        a_pre = to_analyzer_basis(initial_states[pair_index], phi_a)
        a_post = to_analyzer_basis(post_alice_states[pair_index], phi_a)
        b_pre = to_analyzer_basis(post_alice_states[pair_index], phi_b)
        b_post = to_analyzer_basis(post_bob_states[pair_index], phi_b)
        alice_pre_coords.append(a_pre)
        alice_post_coords.append(a_post)
        bob_pre_coords.append(b_pre)
        bob_post_coords.append(b_post)
        alice_extracted.append(np.clip(abs2(a_pre) - abs2(a_post), 0.0, None))
        bob_extracted.append(np.clip(abs2(b_pre) - abs2(b_post), 0.0, None))

    rule = str(row["rule"])
    trial_subset = (
        base.sequential_trial_metrics[base.sequential_trial_metrics["combo_id"].isin(combo_ids)]
        .sort_values(["combo_id", "sample_index"])
        .reset_index(drop=True)
    )
    case_dir = ensure_dir(output_dir / case_name)
    np.savez_compressed(
        case_dir / "raw_arrays.npz",
        combo_ids=np.array(combo_ids, dtype=int),
        pair_labels=np.array([f"{a:.1f}_{b:.1f}" for a, b in zip(angle_a_deg, angle_b_deg, strict=True)], dtype=str),
        angle_a_deg=angle_a_deg,
        angle_b_deg=angle_b_deg,
        rule=np.array(rule),
        initial_states=initial_states,
        post_alice_states=post_alice_states,
        post_bob_states=post_bob_states,
        alice_pre_coords=np.stack(alice_pre_coords),
        alice_post_coords=np.stack(alice_post_coords),
        bob_pre_coords=np.stack(bob_pre_coords),
        bob_post_coords=np.stack(bob_post_coords),
        alice_extracted_energies=np.stack(alice_extracted),
        bob_extracted_energies=np.stack(bob_extracted),
        alice_outcomes=pivot_outcomes(trial_subset, combo_ids, f"alice_outcome_{rule}"),
        bob_outcomes=pivot_outcomes(trial_subset, combo_ids, f"bob_outcome_{rule}"),
    )
    metadata = {
        "case_name": case_name,
        "case_type": "sequential",
        "selection_row": row.to_dict(),
        "combo_ids": combo_ids,
    }
    dump_json(case_dir / "metadata.json", metadata)
    return metadata


def choose_plot_dataset_single_branch(single_full: pd.DataFrame) -> pd.DataFrame:
    if single_full.empty:
        return pd.DataFrame()
    primary = single_full[np.isclose(single_full["window_fraction"], PRIMARY_WINDOW_FRACTION)].copy()
    if primary.empty:
        primary = single_full.copy()
    ratio = primary["anisotropy_ratio"].max()
    return primary[np.isclose(primary["anisotropy_ratio"], ratio)].sort_values("angle_deg")


def choose_plot_dataset_state_cloud(single_trials: pd.DataFrame, limit: int = 400) -> pd.DataFrame:
    if single_trials.empty:
        return pd.DataFrame()
    primary = single_trials[np.isclose(single_trials["window_fraction"], PRIMARY_WINDOW_FRACTION)].copy()
    if primary.empty:
        primary = single_trials.copy()
    ratio = primary["anisotropy_ratio"].max()
    primary = primary[np.isclose(primary["anisotropy_ratio"], ratio)]
    if primary.empty:
        return pd.DataFrame()
    angle = 45.0 if np.isclose(primary["angle_deg"], 45.0).any() else float(primary["angle_deg"].iloc[0])
    return primary[np.isclose(primary["angle_deg"], angle)].head(limit).reset_index(drop=True)


def choose_plot_dataset_marginal(rule_summary: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if rule_summary.empty:
        return pd.DataFrame(), pd.DataFrame()
    primary = rule_summary[
        (rule_summary["rule"] == "residual_classifier")
        & np.isclose(rule_summary["window_fraction"], PRIMARY_WINDOW_FRACTION)
    ].copy()
    if primary.empty:
        primary = rule_summary[rule_summary["rule"] == "residual_classifier"].copy()
    if primary.empty:
        primary = rule_summary.copy()
    if primary.empty:
        return pd.DataFrame(), pd.DataFrame()
    ratio = primary["anisotropy_ratio"].max()
    primary = primary[np.isclose(primary["anisotropy_ratio"], ratio)]
    alice_slice = primary[np.isclose(primary["phiA"], primary["phiA"].min())].copy()
    bob_slice = primary[np.isclose(primary["phiB"], primary["phiB"].min())].copy()
    return alice_slice, bob_slice


def choose_plot_dataset_correlation(rule_summary: pd.DataFrame) -> pd.DataFrame:
    if rule_summary.empty:
        return pd.DataFrame()
    primary = rule_summary[
        (rule_summary["rule"] == "residual_classifier")
        & np.isclose(rule_summary["window_fraction"], PRIMARY_WINDOW_FRACTION)
    ].copy()
    if primary.empty:
        primary = rule_summary[rule_summary["rule"] == "residual_classifier"].copy()
    if primary.empty:
        return pd.DataFrame()
    ratio = primary["anisotropy_ratio"].max()
    primary = primary[np.isclose(primary["anisotropy_ratio"], ratio)].copy()
    primary["delta_deg"] = primary["phiB"] - primary["phiA"]
    return (
        primary.groupby("delta_deg", as_index=False)
        .agg(correlation=("E_phiA_phiB", "mean"))
        .sort_values("delta_deg")
        .reset_index(drop=True)
    )


def choose_plot_dataset_aligned(group_summary: pd.DataFrame) -> pd.DataFrame:
    if group_summary.empty:
        return pd.DataFrame()
    return (
        group_summary[group_summary["rule"] == "residual_classifier"][
            ["window_fraction", "anisotropy_ratio", "aligned_same_sign_mass", "aligned_anti_mass"]
        ]
        .sort_values(["window_fraction", "anisotropy_ratio"])
        .reset_index(drop=True)
    )


def export_plot_artifacts(
    audit_dir: Path,
    base: BaseArtifact,
    single_full: pd.DataFrame,
    sequential_full: pd.DataFrame,
    group_summary: pd.DataFrame,
) -> list[dict[str, Any]]:
    plot_names = [
        "projectivity-vs-anisotropy.png",
        "residual-quality-vs-anisotropy.png",
        "state-clouds-before-after.png",
        "marginal-drift-vs-remote-angle.png",
        "correlation-vs-delta.png",
        "chsh-vs-anisotropy.png",
        "aligned-same-sign-mass-vs-anisotropy.png",
        "single-branch-response-vs-angle.png",
    ]
    plots_dir = ensure_dir(audit_dir / "plots")
    data_dir = ensure_dir(plots_dir / "data")
    manifest: list[dict[str, Any]] = []
    source_plot_dir = base.artifact_dir / "plots"
    single_ratio = (
        single_full.groupby(["window_fraction", "anisotropy_ratio"], as_index=False)
        .agg(
            projectivity_score=("projectivity_score", "mean"),
            residual_branch_quality=("residual_branch_quality", "mean"),
        )
        if not single_full.empty
        else pd.DataFrame()
    )

    dataset_map: dict[str, pd.DataFrame] = {
        "projectivity-vs-anisotropy.png": single_ratio[
            ["window_fraction", "anisotropy_ratio", "projectivity_score"]
        ].sort_values(["window_fraction", "anisotropy_ratio"])
        if not single_ratio.empty
        else pd.DataFrame(),
        "residual-quality-vs-anisotropy.png": single_ratio[
            ["window_fraction", "anisotropy_ratio", "residual_branch_quality"]
        ].sort_values(["window_fraction", "anisotropy_ratio"])
        if not single_ratio.empty
        else pd.DataFrame(),
        "state-clouds-before-after.png": choose_plot_dataset_state_cloud(base.single_trials),
        "marginal-drift-vs-remote-angle.png": pd.concat(
            choose_plot_dataset_marginal(sequential_full),
            ignore_index=True,
        )
        if not sequential_full.empty
        else pd.DataFrame(),
        "correlation-vs-delta.png": choose_plot_dataset_correlation(sequential_full),
        "chsh-vs-anisotropy.png": group_summary[
            ["rule", "window_fraction", "anisotropy_ratio", "CHSH"]
        ].drop_duplicates().sort_values(["rule", "window_fraction", "anisotropy_ratio"])
        if not group_summary.empty
        else pd.DataFrame(),
        "aligned-same-sign-mass-vs-anisotropy.png": choose_plot_dataset_aligned(group_summary),
        "single-branch-response-vs-angle.png": choose_plot_dataset_single_branch(single_full),
    }

    for plot_name in plot_names:
        source_path = source_plot_dir / plot_name
        dest_path = plots_dir / plot_name
        if source_path.exists():
            shutil.copy2(source_path, dest_path)
        dataset = dataset_map.get(plot_name, pd.DataFrame())
        dataset_file = data_dir / f"{plot_name.removesuffix('.png')}.csv"
        if not dataset.empty:
            dataset.to_csv(dataset_file, index=False)
        manifest.append(
            {
                "plot_file": str(dest_path.relative_to(audit_dir)),
                "source_plot": str(source_path),
                "dataset_file": str(dataset_file.relative_to(audit_dir)) if dataset_file.exists() else None,
                "dataset_rows": int(len(dataset)) if not dataset.empty else 0,
            }
        )
    dump_json(plots_dir / "manifest.json", manifest)
    return manifest


def build_direct_answers(
    top_chsh_audit: pd.DataFrame,
    rule_comparison: pd.DataFrame,
    trust_ranking: pd.DataFrame,
    single_full: pd.DataFrame,
) -> dict[str, str]:
    answers: dict[str, str] = {}

    if not top_chsh_audit.empty:
        top = top_chsh_audit.iloc[0]
        answers["q1"] = (
            "The strongest sequential CHSH rows are mainly signaling-driven under the current audit thresholds."
            if bool(top["signaling_flag"])
            else "The strongest sequential CHSH row survives the current signaling checks."
        )
        answers["q4"] = (
            "There is at least one low-drift sequential regime with a nontrivial trust score."
            if not trust_ranking.empty and str(trust_ranking.iloc[0]["trust_label"]) == "credible"
            else "No sequential regime currently clears the conservative trust screen as both low-drift and sphere-like."
        )
    else:
        answers["q1"] = "No sequential CHSH audit rows were available."
        answers["q4"] = "No sequential trust ranking was available."

    if not rule_comparison.empty:
        riskiest = rule_comparison.sort_values(
            ["f5_overfit_readout_rows", "average_max_marginal_drift"],
            ascending=[False, False],
        ).iloc[0]
        safest = rule_comparison.sort_values(
            ["f5_overfit_readout_rows", "average_max_marginal_drift"],
            ascending=[True, True],
        ).iloc[0]
        answers["q2"] = (
            f"The riskiest rule is {riskiest['rule']} under the current audit summary, while {safest['rule']} is the least drift-prone."
        )
    else:
        answers["q2"] = "Rule-risk comparison was not available."

    if not single_full.empty:
        best_single = single_full.sort_values("projectivity_score", ascending=False).iloc[0]
        answers["q3"] = (
            f"The strongest single-analyzer projectivity score is {best_single['projectivity_score']:.3f} at "
            f"ratio={best_single['anisotropy_ratio']:.3f}, window={best_single['window_fraction']:.3f}, angle={best_single['angle_deg']:.1f}."
        )
    else:
        answers["q3"] = "Single-analyzer projectivity rows were not available."

    if not top_chsh_audit.empty and not trust_ranking.empty:
        top_chsh = float(top_chsh_audit.iloc[0]["CHSH"])
        top_trust = float(trust_ranking.iloc[0]["trust_score"])
        answers["q5"] = (
            f"The earlier summary likely overstated the bridge readiness of the best CHSH rows: the top CHSH is {top_chsh:.3f}, but the top conservative trust score is only {top_trust:.3f}."
        )
    else:
        answers["q5"] = "Bridge-readiness could not be reassessed from the available audit tables."

    return answers


def write_readme(
    audit_dir: Path,
    source_artifact: BaseArtifact,
    direct_answers: dict[str, str],
    raw_case_manifest: list[dict[str, Any]],
    plot_manifest: list[dict[str, Any]],
) -> None:
    lines = [
        "# Verification Audit",
        "",
        "This folder is a transparency/audit expansion of an existing anisotropic-damping simulation run.",
        "",
        f"- Source artifact: `{source_artifact.artifact_dir}`",
        "- Simulation model changes: none",
        "- Audit purpose: expose the full tables, exact rule/metric definitions, representative raw arrays, and conservative sequential diagnostics.",
        "",
        "## Row Semantics",
        "",
        "- `tables/single_full.*` is one row per `(window_fraction, gamma_plus, gamma_minus, anisotropy_ratio, angle_deg)` summary row.",
        "- `tables/sequential_full.*` is one row per `(rule, window_fraction, gamma_plus, gamma_minus, anisotropy_ratio, phiA, phiB)` angle-pair row.",
        "- The canonical CHSH terms `E_ab`, `E_abp`, `E_apb`, `E_apbp`, and `CHSH` repeat across every angle-pair row that shares the same `(rule, window_fraction, anisotropy_ratio)` group.",
        "- `alice_marginal_drift`, `bob_marginal_drift`, `aligned_same_sign_mass`, `aligned_anti_mass`, `no_signaling_flag`, and `overfit_flag` are group-level diagnostics repeated onto the angle-pair rows for audit convenience.",
        "",
        "## Direct Answers",
        "",
    ]
    for key, value in direct_answers.items():
        lines.append(f"- `{key}`: {value}")

    lines.extend(
        [
            "",
            "## Raw Case Selection",
            "",
        ]
    )
    for item in raw_case_manifest:
        lines.append(
            f"- `{item['case_name']}`: type={item['case_type']}"
        )

    lines.extend(
        [
            "",
            "## Plot Manifest",
            "",
            f"- Plot entries: {len(plot_manifest)}",
            "- See `plots/manifest.json` for the source image path and the exported plotted dataset backing each PNG.",
            "",
        ]
    )
    (audit_dir / "README.md").write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def build_verification_audit(
    artifact_dir: Path,
    output_dir: Path,
) -> dict[str, Any]:
    base = load_base_artifact(artifact_dir)
    output_dir = output_dir.resolve()
    ensure_dir(output_dir)
    tables_dir = ensure_dir(output_dir / "tables")
    raw_dir = ensure_dir(output_dir / "raw_cases")
    definitions_dir = ensure_dir(output_dir / "definitions")

    single_full = build_single_full(base)
    sequential_full, group_summary = build_sequential_full(base)
    top_chsh_audit = build_top_chsh_audit(group_summary)
    rule_comparison = build_rule_comparison(group_summary)
    trust_ranking = build_trust_ranking(group_summary)

    write_table(single_full, tables_dir / "single_full.csv", tables_dir / "single_full.json")
    write_table(
        sequential_full,
        tables_dir / "sequential_full.csv",
        tables_dir / "sequential_full.json",
    )
    write_table(
        group_summary,
        tables_dir / "sequential_groups.csv",
        tables_dir / "sequential_groups.json",
    )
    write_table(
        rule_comparison,
        tables_dir / "rule_comparison.csv",
        tables_dir / "rule_comparison.json",
    )
    write_table(
        top_chsh_audit,
        tables_dir / "top_chsh_audit.csv",
        tables_dir / "top_chsh_audit.json",
    )
    write_table(
        trust_ranking,
        tables_dir / "trust_ranking.csv",
        tables_dir / "trust_ranking.json",
    )

    (definitions_dir / "readout_rules.md").write_text(
        render_readout_rules_markdown(),
        encoding="utf-8",
    )
    (definitions_dir / "metrics.md").write_text(
        render_metrics_markdown(),
        encoding="utf-8",
    )
    dump_json(definitions_dir / "readout_rules.json", READOUT_RULE_DEFINITIONS)
    dump_json(
        definitions_dir / "metrics.json",
        {
            "metrics": METRIC_DEFINITIONS,
            "failure_modes": FAILURE_MODE_DEFINITIONS,
        },
    )

    raw_case_manifest: list[dict[str, Any]] = []
    single_best = select_single_case(single_full, case_name="best_single_projectivity")
    isotropic = select_single_case(single_full, case_name="isotropic_baseline")
    if single_best is not None:
        raw_case_manifest.append(export_single_raw_case(raw_dir, "best_single_projectivity", single_best, base))
    if isotropic is not None:
        raw_case_manifest.append(export_single_raw_case(raw_dir, "isotropic_baseline", isotropic, base))

    top_seq = select_sequential_case(group_summary, case_name="top_sequential_chsh")
    low_drift = select_sequential_case(group_summary, case_name="lowest_drift_sequential")
    overfit = select_sequential_case(group_summary, case_name="flagged_overfit_readout")
    if top_seq is not None:
        raw_case_manifest.append(export_sequential_raw_case(raw_dir, "top_sequential_chsh", top_seq, base))
    if low_drift is not None:
        raw_case_manifest.append(export_sequential_raw_case(raw_dir, "lowest_drift_sequential", low_drift, base))
    if overfit is not None:
        raw_case_manifest.append(export_sequential_raw_case(raw_dir, "flagged_overfit_readout", overfit, base))
    dump_json(raw_dir / "manifest.json", raw_case_manifest)

    plot_manifest = export_plot_artifacts(output_dir, base, single_full, sequential_full, group_summary)
    direct_answers = build_direct_answers(top_chsh_audit, rule_comparison, trust_ranking, single_full)
    write_readme(output_dir, base, direct_answers, raw_case_manifest, plot_manifest)

    manifest = {
        "source_artifact_dir": str(base.artifact_dir),
        "audit_dir": str(output_dir),
        "tables": {
            "single_full_rows": int(len(single_full)),
            "sequential_full_rows": int(len(sequential_full)),
            "sequential_group_rows": int(len(group_summary)),
            "top_chsh_rows": int(len(top_chsh_audit)),
            "trust_ranking_rows": int(len(trust_ranking)),
        },
        "raw_cases": raw_case_manifest,
        "plots": plot_manifest,
        "direct_answers": direct_answers,
    }
    dump_json(output_dir / "manifest.json", manifest)
    return manifest
