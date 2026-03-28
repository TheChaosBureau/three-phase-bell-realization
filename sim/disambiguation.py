from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .config import DampingConfig, EPSILON
from .damping import evolve_with_diagnostics
from .readout import (
    RULE_CONFIDENCE_WEIGHTED_AGREEMENT,
    RULE_ENERGY_LOSS_WINNER,
    RULE_RESIDUAL_TEMPLATE_CLASSIFIER,
)
from .state import abs2, normalize_states, to_analyzer_basis

GROUP_KEYS = ["window_fraction", "gamma_plus", "gamma_minus", "anisotropy_ratio"]
FAMILY_KEYS = GROUP_KEYS + ["readout_family"]
MARGIN_THRESHOLD_SWEEP = (0.1, 0.2, 0.3, 0.4, 0.5)
ORACLE_MARGIN_THRESHOLD = 0.15

REGIME_BIN_DEFINITIONS = {
    "mechanism_limited": "Weak structural separability or weak oracle recovery; no practical readout rescue.",
    "readout_limited": "Strong branch structure with substantial oracle improvement over practical readouts.",
    "mixed_failure": "Moderate structure and some oracle improvement, but still not enough for a credible bridge.",
    "bridge_candidate": "Strong structure, practical readouts close to oracle, and low drift/support burden.",
}

DISAMBIGUATION_METRIC_DEFINITIONS = {
    "residual_separability_score": "Mean cluster-assignment margin `(d_other - d_own) / (d_other + d_own + eps)` from a deterministic two-cluster fit on post-Alice residual-state features.",
    "residual_stability_score": "Mean label-retention rate under phase, noise, angle, and anisotropy perturbation probes, restricted to originally non-ambiguous oracle labels.",
    "usable_branch_fraction": "Sum of the strong plus-branch and strong minus-branch occupancy fractions under the oracle cluster detector.",
    "manifold_closure_error": "Residual variance outside the leading two singular directions of the post-Alice residual-state feature cloud.",
    "branch_continuity_score": "Mean fraction of nearest neighbors in initial-state feature space that remain on the same non-ambiguous oracle branch.",
    "branch_recoverability": "Mean agreement of a practical readout with the oracle branch labels across Alice and Bob stages, restricted to jointly valid oracle comparisons.",
    "confidence_efficiency": "Retained pair fraction multiplied by branch recoverability for a practical or oracle readout family.",
    "support_recoverability": "Aligned same-sign mass of a practical family minus the oracle aligned same-sign mass for the same parameter group.",
    "drift_recoverability": "Maximum marginal drift of a practical family minus the oracle maximum marginal drift for the same parameter group.",
    "oracle_gap": "Oracle confidence efficiency minus the best practical confidence efficiency within the same parameter group.",
}


@dataclass(slots=True)
class OracleStageSummary:
    combo_id: int
    angle_deg: float
    outcomes: np.ndarray
    raw_signs: np.ndarray
    margins: np.ndarray
    separability_score: float
    stability_score: float
    strong_plus_fraction: float
    strong_minus_fraction: float
    ambiguity_fraction: float
    manifold_closure_error: float
    branch_continuity_score: float
    mean_oracle_margin: float
    centers: np.ndarray
    label_map: dict[int, int]


def phase_aligned_features(states: np.ndarray) -> np.ndarray:
    normalized = normalize_states(states)
    anchor = np.where(np.abs(normalized[:, 0]) > EPSILON, normalized[:, 0], normalized[:, 1])
    phases = np.exp(-1j * np.angle(anchor))
    aligned = normalized * phases[:, None]
    return np.column_stack(
        [
            aligned[:, 0].real,
            aligned[:, 1].real,
            aligned[:, 1].imag,
        ]
    )


def analyzer_features(states: np.ndarray, phi_deg: float) -> np.ndarray:
    coords = to_analyzer_basis(states, np.deg2rad(phi_deg))
    normalized = normalize_states(coords)
    powers = abs2(normalized)
    anchor = np.where(np.abs(normalized[:, 0]) > EPSILON, normalized[:, 0], normalized[:, 1])
    phases = np.exp(-1j * np.angle(anchor))
    aligned = normalized * phases[:, None]
    return np.column_stack(
        [
            powers[:, 0],
            powers[:, 1],
            aligned[:, 1].real,
            aligned[:, 1].imag,
            powers[:, 0] - powers[:, 1],
        ]
    )


def combined_features(states: np.ndarray, phi_deg: float) -> np.ndarray:
    return np.concatenate([phase_aligned_features(states), analyzer_features(states, phi_deg)], axis=1)


def two_cluster_kmeans(features: np.ndarray, max_iter: int = 20) -> tuple[np.ndarray, np.ndarray]:
    centered = features - np.mean(features, axis=0, keepdims=True)
    _, _, vh = np.linalg.svd(centered, full_matrices=False)
    direction = vh[0]
    projection = centered @ direction
    left = features[np.argmin(projection)]
    right = features[np.argmax(projection)]
    centers = np.stack([left, right]).astype(np.float64)

    labels = np.zeros(len(features), dtype=np.int8)
    for _ in range(max_iter):
        distances = np.linalg.norm(features[:, None, :] - centers[None, :, :], axis=2)
        next_labels = np.argmin(distances, axis=1).astype(np.int8)
        if np.array_equal(labels, next_labels):
            break
        labels = next_labels
        for cluster_id in (0, 1):
            members = features[labels == cluster_id]
            if len(members):
                centers[cluster_id] = np.mean(members, axis=0)
    return labels, centers


def oracle_assignment_from_features(
    features: np.ndarray,
    centers: np.ndarray,
    label_map: dict[int, int],
    *,
    margin_threshold: float = ORACLE_MARGIN_THRESHOLD,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    distances = np.linalg.norm(features[:, None, :] - centers[None, :, :], axis=2)
    cluster_ids = np.argmin(distances, axis=1).astype(np.int8)
    own = distances[np.arange(len(features)), cluster_ids]
    other = distances[np.arange(len(features)), 1 - cluster_ids]
    margins = (other - own) / np.maximum(other + own, EPSILON)
    raw_signs = np.array([label_map[int(cluster_id)] for cluster_id in cluster_ids], dtype=np.int8)
    outcomes = np.where(margins >= margin_threshold, raw_signs, 0).astype(np.int8)
    return outcomes, raw_signs, margins.astype(np.float64)


def separability_score_from_assignment(features: np.ndarray, centers: np.ndarray) -> float:
    distances = np.linalg.norm(features[:, None, :] - centers[None, :, :], axis=2)
    own = np.min(distances, axis=1)
    other = np.max(distances, axis=1)
    margins = (other - own) / np.maximum(other + own, EPSILON)
    return float(np.mean(np.clip(margins, 0.0, 1.0)))


def manifold_closure_error(features: np.ndarray) -> float:
    centered = features - np.mean(features, axis=0, keepdims=True)
    singular_values = np.linalg.svd(centered, compute_uv=False)
    if len(singular_values) <= 2:
        return 0.0
    total = float(np.sum(singular_values**2))
    if total <= EPSILON:
        return 0.0
    residual = float(np.sum(singular_values[2:] ** 2))
    return residual / total


def branch_continuity_score(initial_states: np.ndarray, oracle_outcomes: np.ndarray, k_neighbors: int = 5) -> float:
    valid = oracle_outcomes != 0
    if np.count_nonzero(valid) <= 2:
        return 0.0
    features = phase_aligned_features(initial_states[valid])
    labels = oracle_outcomes[valid]
    distances = np.linalg.norm(features[:, None, :] - features[None, :, :], axis=2)
    np.fill_diagonal(distances, np.inf)
    neighbor_count = min(k_neighbors, len(features) - 1)
    neighbors = np.argpartition(distances, kth=neighbor_count - 1, axis=1)[:, :neighbor_count]
    same_label = labels[neighbors] == labels[:, None]
    return float(np.mean(same_label))


def stability_score(
    initial_states: np.ndarray,
    angle_deg: float,
    damping: DampingConfig,
    centers: np.ndarray,
    label_map: dict[int, int],
    reference_outcomes: np.ndarray,
) -> float:
    strong_mask = reference_outcomes != 0
    if not np.any(strong_mask):
        return 0.0

    rng = np.random.default_rng(0)
    probes: list[tuple[np.ndarray, float, DampingConfig]] = []

    phase_shifted = initial_states.copy()
    phase_shifted[:, 1] *= np.exp(0.1j)
    probes.append((phase_shifted, angle_deg, damping))

    noise = 0.01 * (rng.normal(size=initial_states.shape) + 1j * rng.normal(size=initial_states.shape))
    noisy = normalize_states(initial_states + noise)
    probes.append((noisy, angle_deg, damping))

    probes.append((initial_states, angle_deg + 1.0, damping))

    perturbed_damping = DampingConfig(
        gamma_plus=damping.gamma_plus * 1.05,
        gamma_minus=damping.gamma_minus,
        window_fraction=damping.window_fraction,
        base_period=damping.base_period,
    )
    probes.append((initial_states, angle_deg, perturbed_damping))

    scores: list[float] = []
    for probe_states, probe_angle_deg, probe_damping in probes:
        post_states = evolve_with_diagnostics(probe_states, np.deg2rad(probe_angle_deg), probe_damping)["states_after"]
        probe_features = combined_features(post_states, probe_angle_deg)
        probe_outcomes, _, _ = oracle_assignment_from_features(probe_features, centers, label_map)
        scores.append(float(np.mean(probe_outcomes[strong_mask] == reference_outcomes[strong_mask])))
    return float(np.mean(scores))


def cluster_label_map(analyzer_feature_values: np.ndarray, cluster_ids: np.ndarray) -> dict[int, int]:
    cluster_means = {}
    for cluster_id in (0, 1):
        members = analyzer_feature_values[cluster_ids == cluster_id]
        cluster_means[cluster_id] = float(np.mean(members)) if len(members) else 0.0
    ordered = sorted(cluster_means, key=cluster_means.get)
    return {ordered[0]: -1, ordered[1]: 1}


def summarize_oracle_stage(
    combo_id: int,
    angle_deg: float,
    initial_states: np.ndarray,
    post_states: np.ndarray,
    damping: DampingConfig,
) -> OracleStageSummary:
    features = combined_features(post_states, angle_deg)
    cluster_ids, centers = two_cluster_kmeans(features)
    analyzer_dominance = analyzer_features(post_states, angle_deg)[:, -1]
    label_map = cluster_label_map(analyzer_dominance, cluster_ids)
    outcomes, raw_signs, margins = oracle_assignment_from_features(features, centers, label_map)
    separability = separability_score_from_assignment(features, centers)
    closure_error = manifold_closure_error(features)
    continuity = branch_continuity_score(initial_states, outcomes)
    stability = stability_score(initial_states, angle_deg, damping, centers, label_map, outcomes)

    return OracleStageSummary(
        combo_id=combo_id,
        angle_deg=angle_deg,
        outcomes=outcomes,
        raw_signs=raw_signs,
        margins=margins,
        separability_score=separability,
        stability_score=stability,
        strong_plus_fraction=float(np.mean(outcomes == 1)),
        strong_minus_fraction=float(np.mean(outcomes == -1)),
        ambiguity_fraction=float(np.mean(outcomes == 0)),
        manifold_closure_error=closure_error,
        branch_continuity_score=continuity,
        mean_oracle_margin=float(np.mean(margins)),
        centers=centers,
        label_map=label_map,
    )


def build_oracle_caches(
    manifest: pd.DataFrame,
    states: dict[str, np.ndarray],
) -> tuple[dict[int, OracleStageSummary], dict[int, OracleStageSummary]]:
    alice_cache: dict[int, OracleStageSummary] = {}
    bob_cache: dict[int, OracleStageSummary] = {}

    initial_blocks = states.get("initial_states")
    alice_blocks = states.get("post_alice_states")
    bob_blocks = states.get("post_bob_states")
    if initial_blocks is None or alice_blocks is None or bob_blocks is None:
        return alice_cache, bob_cache

    for row in manifest.sort_values("combo_id").itertuples():
        combo_id = int(row.combo_id)
        damping = DampingConfig(
            gamma_plus=float(row.gamma_plus),
            gamma_minus=float(row.gamma_minus),
            window_fraction=float(row.window_fraction),
        )
        initial_states = initial_blocks[combo_id]
        alice_cache[combo_id] = summarize_oracle_stage(
            combo_id,
            float(row.angle_a_deg),
            initial_states,
            alice_blocks[combo_id],
            damping,
        )
        bob_cache[combo_id] = summarize_oracle_stage(
            combo_id,
            float(row.angle_b_deg),
            initial_states,
            bob_blocks[combo_id],
            damping,
        )
    return alice_cache, bob_cache


def build_oracle_trial_table(
    manifest: pd.DataFrame,
    alice_cache: dict[int, OracleStageSummary],
    bob_cache: dict[int, OracleStageSummary],
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for row in manifest.sort_values("combo_id").itertuples():
        combo_id = int(row.combo_id)
        alice = alice_cache.get(combo_id)
        bob = bob_cache.get(combo_id)
        if alice is None or bob is None:
            continue
        sample_count = len(alice.outcomes)
        frames.append(
            pd.DataFrame(
                {
                    "combo_id": combo_id,
                    "sample_index": np.arange(sample_count),
                    "oracle_alice_outcome": alice.outcomes,
                    "oracle_alice_margin": alice.margins,
                    "oracle_bob_outcome": bob.outcomes,
                    "oracle_bob_margin": bob.margins,
                }
            )
        )
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def build_mechanism_structure(
    manifest: pd.DataFrame,
    alice_cache: dict[int, OracleStageSummary],
) -> pd.DataFrame:
    if manifest.empty or not alice_cache:
        return pd.DataFrame()

    unique_alice = (
        manifest.sort_values("combo_id")
        .drop_duplicates(GROUP_KEYS + ["angle_a_deg"])
        .reset_index(drop=True)
    )

    rows: list[dict[str, Any]] = []
    for group_key, group in unique_alice.groupby(GROUP_KEYS):
        group_rows = []
        for combo_id in group["combo_id"].astype(int):
            summary = alice_cache[combo_id]
            group_rows.append(
                {
                    "residual_separability_score": summary.separability_score,
                    "residual_stability_score": summary.stability_score,
                    "strong_branch_plus_fraction": summary.strong_plus_fraction,
                    "strong_branch_minus_fraction": summary.strong_minus_fraction,
                    "ambiguity_fraction": summary.ambiguity_fraction,
                    "manifold_closure_error": summary.manifold_closure_error,
                    "branch_continuity_score": summary.branch_continuity_score,
                    "mean_oracle_margin": summary.mean_oracle_margin,
                }
            )
        metrics = pd.DataFrame(group_rows)
        usable_branch_fraction = float(
            metrics["strong_branch_plus_fraction"].mean() + metrics["strong_branch_minus_fraction"].mean()
        )
        mechanism_strength = float(
            np.mean(
                [
                    metrics["residual_separability_score"].mean(),
                    metrics["residual_stability_score"].mean(),
                    usable_branch_fraction,
                    metrics["branch_continuity_score"].mean(),
                    1.0 - metrics["manifold_closure_error"].mean(),
                ]
            )
        )
        oracle_branch_quality = float(
            metrics["residual_separability_score"].mean()
            * metrics["residual_stability_score"].mean()
            * max(usable_branch_fraction, 0.0)
        )
        row = dict(zip(GROUP_KEYS, group_key, strict=True))
        row.update(
            {
                "residual_separability_score": float(metrics["residual_separability_score"].mean()),
                "residual_stability_score": float(metrics["residual_stability_score"].mean()),
                "strong_branch_plus_fraction": float(metrics["strong_branch_plus_fraction"].mean()),
                "strong_branch_minus_fraction": float(metrics["strong_branch_minus_fraction"].mean()),
                "ambiguity_fraction": float(metrics["ambiguity_fraction"].mean()),
                "usable_branch_fraction": usable_branch_fraction,
                "manifold_closure_error": float(metrics["manifold_closure_error"].mean()),
                "branch_continuity_score": float(metrics["branch_continuity_score"].mean()),
                "mean_oracle_margin": float(metrics["mean_oracle_margin"].mean()),
                "mechanism_strength_score": mechanism_strength,
                "oracle_branch_quality": oracle_branch_quality,
                "angle_count": int(len(group_rows)),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows).sort_values(GROUP_KEYS).reset_index(drop=True)


def drift_from_pair_summary(summary: pd.DataFrame) -> float:
    if summary.empty:
        return float("nan")
    alice = (
        summary.groupby("angle_a_deg", as_index=False)
        .agg(alice_drift=("alice_marginal", lambda values: float(values.max() - values.min())))
    )
    bob = (
        summary.groupby("angle_b_deg", as_index=False)
        .agg(bob_drift=("bob_marginal", lambda values: float(values.max() - values.min())))
    )
    alice_max = float(alice["alice_drift"].max()) if not alice.empty else float("nan")
    bob_max = float(bob["bob_drift"].max()) if not bob.empty else float("nan")
    return float(np.nanmax([alice_max, bob_max]))


def summarize_readout_family(
    frame: pd.DataFrame,
    *,
    readout_family: str,
    family_category: str,
    margin_threshold: float | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for group_key, group in frame.groupby(GROUP_KEYS):
        pair_rows = []
        for (angle_a_deg, angle_b_deg), pair in group.groupby(["angle_a_deg", "angle_b_deg"]):
            valid = pair["pair_valid"].astype(bool)
            if np.any(valid):
                alice_values = pair.loc[valid, "alice_outcome"].to_numpy(dtype=float)
                bob_values = pair.loc[valid, "bob_outcome"].to_numpy(dtype=float)
                same_sign = float(np.mean(alice_values == bob_values))
                anti_sign = float(np.mean(alice_values != bob_values))
                correlation = float(np.mean(alice_values * bob_values))
                alice_marginal = float(np.mean(alice_values))
                bob_marginal = float(np.mean(bob_values))
            else:
                same_sign = np.nan
                anti_sign = np.nan
                correlation = np.nan
                alice_marginal = np.nan
                bob_marginal = np.nan
            pair_rows.append(
                {
                    "angle_a_deg": float(angle_a_deg),
                    "angle_b_deg": float(angle_b_deg),
                    "aligned_pair": bool(np.isclose(angle_a_deg, angle_b_deg)),
                    "same_sign_mass": same_sign,
                    "anti_sign_mass": anti_sign,
                    "correlation": correlation,
                    "alice_marginal": alice_marginal,
                    "bob_marginal": bob_marginal,
                }
            )
        pair_summary = pd.DataFrame(pair_rows)
        aligned = pair_summary[pair_summary["aligned_pair"]]
        stage_recoverability = np.array(
            [
                group["alice_recoverability"].mean(),
                group["bob_recoverability"].mean(),
            ],
            dtype=np.float64,
        )
        recoverability = float(np.nanmean(stage_recoverability)) if np.isfinite(stage_recoverability).any() else 0.0
        retained_fraction = float(group["pair_valid"].mean())
        row = dict(zip(GROUP_KEYS, group_key, strict=True))
        row.update(
            {
                "readout_family": readout_family,
                "family_category": family_category,
                "margin_threshold": margin_threshold,
                "branch_recoverability": recoverability,
                "ambiguity_rate": float(1.0 - retained_fraction),
                "retained_fraction": retained_fraction,
                "confidence_efficiency": recoverability * retained_fraction,
                "aligned_same_sign_mass": float(aligned["same_sign_mass"].mean()) if not aligned.empty else np.nan,
                "aligned_anti_mass": float(aligned["anti_sign_mass"].mean()) if not aligned.empty else np.nan,
                "max_marginal_drift": drift_from_pair_summary(pair_summary),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def build_readout_sensitivity(
    trials: pd.DataFrame,
    oracle_trials: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if trials.empty or oracle_trials.empty:
        return pd.DataFrame(), pd.DataFrame()

    merged = trials.merge(oracle_trials, on=["combo_id", "sample_index"], how="left")
    merged["oracle_alice_valid"] = merged["oracle_alice_outcome"] != 0
    merged["oracle_bob_valid"] = merged["oracle_bob_outcome"] != 0

    family_frames: list[pd.DataFrame] = []

    def add_family(
        readout_family: str,
        family_category: str,
        alice_outcome: np.ndarray,
        bob_outcome: np.ndarray,
        alice_valid: np.ndarray,
        bob_valid: np.ndarray,
        *,
        margin_threshold: float | None = None,
    ) -> None:
        working = merged[
            GROUP_KEYS + ["angle_a_deg", "angle_b_deg", "aligned_pair"]
        ].copy()
        working["alice_outcome"] = alice_outcome
        working["bob_outcome"] = bob_outcome
        working["alice_valid"] = alice_valid.astype(bool)
        working["bob_valid"] = bob_valid.astype(bool)
        working["pair_valid"] = working["alice_valid"] & working["bob_valid"]
        working["alice_recoverability"] = np.where(
            working["alice_valid"] & merged["oracle_alice_valid"],
            (working["alice_outcome"] == merged["oracle_alice_outcome"]).astype(float),
            np.nan,
        )
        working["bob_recoverability"] = np.where(
            working["bob_valid"] & merged["oracle_bob_valid"],
            (working["bob_outcome"] == merged["oracle_bob_outcome"]).astype(float),
            np.nan,
        )
        family_frames.append(
            summarize_readout_family(
                working,
                readout_family=readout_family,
                family_category=family_category,
                margin_threshold=margin_threshold,
            )
        )

    add_family(
        RULE_ENERGY_LOSS_WINNER,
        "practical",
        merged[f"alice_outcome_{RULE_ENERGY_LOSS_WINNER}"].to_numpy(dtype=np.int8),
        merged[f"bob_outcome_{RULE_ENERGY_LOSS_WINNER}"].to_numpy(dtype=np.int8),
        merged[f"alice_valid_{RULE_ENERGY_LOSS_WINNER}"].to_numpy(dtype=bool),
        merged[f"bob_valid_{RULE_ENERGY_LOSS_WINNER}"].to_numpy(dtype=bool),
    )
    add_family(
        RULE_RESIDUAL_TEMPLATE_CLASSIFIER,
        "practical",
        merged[f"alice_outcome_{RULE_RESIDUAL_TEMPLATE_CLASSIFIER}"].to_numpy(dtype=np.int8),
        merged[f"bob_outcome_{RULE_RESIDUAL_TEMPLATE_CLASSIFIER}"].to_numpy(dtype=np.int8),
        merged[f"alice_valid_{RULE_RESIDUAL_TEMPLATE_CLASSIFIER}"].to_numpy(dtype=bool),
        merged[f"bob_valid_{RULE_RESIDUAL_TEMPLATE_CLASSIFIER}"].to_numpy(dtype=bool),
    )
    add_family(
        RULE_CONFIDENCE_WEIGHTED_AGREEMENT,
        "practical",
        merged[f"alice_outcome_{RULE_CONFIDENCE_WEIGHTED_AGREEMENT}"].to_numpy(dtype=np.int8),
        merged[f"bob_outcome_{RULE_CONFIDENCE_WEIGHTED_AGREEMENT}"].to_numpy(dtype=np.int8),
        merged[f"alice_valid_{RULE_CONFIDENCE_WEIGHTED_AGREEMENT}"].to_numpy(dtype=bool),
        merged[f"bob_valid_{RULE_CONFIDENCE_WEIGHTED_AGREEMENT}"].to_numpy(dtype=bool),
    )

    threshold_frames: list[pd.DataFrame] = []
    for threshold in MARGIN_THRESHOLD_SWEEP:
        alice_valid = merged["alice_residual_margin"].to_numpy(dtype=float) >= threshold
        bob_valid = merged["bob_residual_margin"].to_numpy(dtype=float) >= threshold
        family_name = f"margin_thresholded_residual@{threshold:.2f}"
        add_family(
            family_name,
            "practical",
            merged[f"alice_outcome_{RULE_RESIDUAL_TEMPLATE_CLASSIFIER}"].to_numpy(dtype=np.int8),
            merged[f"bob_outcome_{RULE_RESIDUAL_TEMPLATE_CLASSIFIER}"].to_numpy(dtype=np.int8),
            alice_valid,
            bob_valid,
            margin_threshold=threshold,
        )
        threshold_frames.append(
            pd.DataFrame(
                {
                    "margin_threshold": [threshold],
                }
            )
        )

    add_family(
        "oracle_separability_benchmark",
        "oracle",
        merged["oracle_alice_outcome"].to_numpy(dtype=np.int8),
        merged["oracle_bob_outcome"].to_numpy(dtype=np.int8),
        merged["oracle_alice_valid"].to_numpy(dtype=bool),
        merged["oracle_bob_valid"].to_numpy(dtype=bool),
    )

    summary = pd.concat(family_frames, ignore_index=True).sort_values(FAMILY_KEYS).reset_index(drop=True)
    oracle_reference = summary[summary["readout_family"] == "oracle_separability_benchmark"][
        GROUP_KEYS + ["aligned_same_sign_mass", "max_marginal_drift", "confidence_efficiency"]
    ].rename(
        columns={
            "aligned_same_sign_mass": "oracle_aligned_same_sign_mass",
            "max_marginal_drift": "oracle_max_marginal_drift",
            "confidence_efficiency": "oracle_confidence_efficiency",
        }
    )
    summary = summary.merge(oracle_reference, on=GROUP_KEYS, how="left")
    summary["support_recoverability"] = (
        summary["aligned_same_sign_mass"] - summary["oracle_aligned_same_sign_mass"]
    )
    summary["drift_recoverability"] = summary["max_marginal_drift"] - summary["oracle_max_marginal_drift"]

    confidence_curve = summary[summary["readout_family"].str.startswith("margin_thresholded_residual@")][
        GROUP_KEYS
        + [
            "margin_threshold",
            "retained_fraction",
            "branch_recoverability",
            "confidence_efficiency",
        ]
    ].reset_index(drop=True)
    return summary, confidence_curve


def classify_regime(row: pd.Series) -> tuple[str, str]:
    if (
        row["mechanism_strength_score"] >= 0.75
        and row["best_practical_confidence_efficiency"] >= row["oracle_confidence_efficiency"] - 0.1
        and row["best_practical_max_marginal_drift"] <= 0.05
        and row["best_practical_aligned_same_sign_mass"] <= 0.25
    ):
        return ("bridge_candidate", "Strong structure with practical readout close to oracle under low drift/support burden.")
    if (
        row["mechanism_strength_score"] < 0.55
        or row["oracle_branch_quality"] < 0.5
    ) and row["oracle_gap"] < 0.15:
        return ("mechanism_limited", "Structural branch quality is weak and oracle rescue is small.")
    if (
        row["mechanism_strength_score"] >= 0.7
        and row["oracle_gap"] >= 0.2
        and (
            row["oracle_support_gain"] >= 0.05
            or row["oracle_drift_gain"] >= 0.02
        )
    ):
        return ("readout_limited", "Structural branch quality is present and oracle recovery materially outperforms practical readouts.")
    return ("mixed_failure", "Moderate structure or moderate oracle improvement, but not enough for a credible bridge.")


def build_oracle_gap_summary(
    mechanism_structure: pd.DataFrame,
    readout_sensitivity: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if mechanism_structure.empty or readout_sensitivity.empty:
        return pd.DataFrame(), pd.DataFrame()

    practical = readout_sensitivity[readout_sensitivity["family_category"] == "practical"].copy()
    oracle = readout_sensitivity[
        readout_sensitivity["readout_family"] == "oracle_separability_benchmark"
    ].copy()
    if practical.empty or oracle.empty:
        return pd.DataFrame(), pd.DataFrame()

    best_idx = practical.groupby(GROUP_KEYS)["confidence_efficiency"].idxmax()
    best_practical = practical.loc[best_idx].reset_index(drop=True).rename(
        columns={
            "readout_family": "best_practical_rule",
            "confidence_efficiency": "best_practical_confidence_efficiency",
            "aligned_same_sign_mass": "best_practical_aligned_same_sign_mass",
            "max_marginal_drift": "best_practical_max_marginal_drift",
            "branch_recoverability": "best_practical_branch_recoverability",
            "ambiguity_rate": "best_practical_ambiguity_rate",
        }
    )
    oracle = oracle.rename(
        columns={
            "branch_recoverability": "oracle_branch_recoverability",
            "ambiguity_rate": "oracle_ambiguity_rate",
        }
    )
    frame = mechanism_structure.merge(best_practical, on=GROUP_KEYS, how="left").merge(
        oracle[
            GROUP_KEYS
            + [
                "oracle_branch_recoverability",
                "oracle_ambiguity_rate",
            ]
        ],
        on=GROUP_KEYS,
        how="left",
    )
    frame["oracle_gap"] = frame["oracle_confidence_efficiency"] - frame["best_practical_confidence_efficiency"]
    frame["oracle_support_gain"] = (
        frame["best_practical_aligned_same_sign_mass"] - frame["oracle_aligned_same_sign_mass"]
    )
    frame["oracle_drift_gain"] = (
        frame["best_practical_max_marginal_drift"] - frame["oracle_max_marginal_drift"]
    )

    labels = frame.apply(classify_regime, axis=1, result_type="expand")
    frame["classification_bin"] = labels[0]
    frame["classification_justification"] = labels[1]

    oracle_gap_summary = frame[
        GROUP_KEYS
        + [
            "oracle_gap",
            "best_practical_rule",
            "best_practical_confidence_efficiency",
            "oracle_confidence_efficiency",
            "classification_bin",
            "classification_justification",
        ]
    ].sort_values(GROUP_KEYS).reset_index(drop=True)

    regime_classification = frame[
        GROUP_KEYS
        + [
            "classification_bin",
            "classification_justification",
            "mechanism_strength_score",
            "oracle_branch_quality",
            "oracle_gap",
            "best_practical_rule",
            "best_practical_confidence_efficiency",
            "oracle_confidence_efficiency",
            "oracle_support_gain",
            "oracle_drift_gain",
        ]
    ].sort_values(GROUP_KEYS).reset_index(drop=True)
    return oracle_gap_summary, regime_classification
