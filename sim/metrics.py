from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .config import EPSILON
from .readout import ALL_READOUT_RULES
from .state import abs2

CHSH_ANGLE_SET = (
    (0.0, 22.5),
    (0.0, 67.5),
    (45.0, 22.5),
    (45.0, 67.5),
)


@dataclass(slots=True)
class ProjectivitySummary:
    projectivity_score: float
    complementary_quality_mean: float
    purity_mean: float
    dominance_mean: float
    clusterability: float
    total_norm_before_mean: float
    total_norm_after_mean: float
    mean_branch_loss: float
    closure_error_mean: float

    def to_dict(self) -> dict[str, float]:
        return {
            "projectivity_score": self.projectivity_score,
            "complementary_quality_mean": self.complementary_quality_mean,
            "purity_mean": self.purity_mean,
            "dominance_mean": self.dominance_mean,
            "clusterability": self.clusterability,
            "total_norm_before_mean": self.total_norm_before_mean,
            "total_norm_after_mean": self.total_norm_after_mean,
            "mean_branch_loss": self.mean_branch_loss,
            "closure_error_mean": self.closure_error_mean,
        }


def branch_weights(coords: np.ndarray) -> np.ndarray:
    power = abs2(coords)
    totals = np.sum(power, axis=-1, keepdims=True)
    return power / np.maximum(totals, EPSILON)


def dominance_ratio(coords: np.ndarray) -> np.ndarray:
    weights = branch_weights(coords)
    return (weights[..., 0] - weights[..., 1]).astype(np.float64)


def residual_branch_quality(post_coords: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    weights = branch_weights(post_coords)
    quality_plus = weights[..., 0]
    quality_minus = weights[..., 1]
    purity = np.maximum(quality_plus, quality_minus)
    return quality_plus, quality_minus, purity


def complementary_residual_quality(
    pre_coords: np.ndarray,
    post_coords: np.ndarray,
    branch_loss: np.ndarray | None = None,
) -> np.ndarray:
    if branch_loss is None:
        branch_loss = np.clip(abs2(pre_coords) - abs2(post_coords), 0.0, None)
    weights = branch_weights(post_coords)
    extracted_branch = np.argmax(branch_loss, axis=1)
    complementary_branch = 1 - extracted_branch
    return weights[np.arange(weights.shape[0]), complementary_branch]


def clusterability_score(post_coords: np.ndarray, threshold: float = 0.9) -> float:
    _, _, purity = residual_branch_quality(post_coords)
    return float(np.mean(purity >= threshold))


def state_manifold_closure(states: np.ndarray) -> dict[str, float]:
    array = np.asarray(states)
    nonfinite_fraction = float(np.mean(~np.isfinite(array).all(axis=-1)))
    if array.shape[-1] != 2:
        closure_error = 1.0
    else:
        closure_error = 0.0
    return {
        "closure_error_mean": closure_error,
        "nonfinite_fraction": nonfinite_fraction,
    }


def summarize_projectivity(
    pre_coords: np.ndarray,
    post_coords: np.ndarray,
    branch_loss: np.ndarray,
    states_after: np.ndarray,
) -> ProjectivitySummary:
    quality_plus, quality_minus, purity = residual_branch_quality(post_coords)
    complementary_quality = complementary_residual_quality(
        pre_coords,
        post_coords,
        branch_loss=branch_loss,
    )
    pre_norm = np.sum(abs2(pre_coords), axis=1)
    post_norm = np.sum(abs2(post_coords), axis=1)
    closure = state_manifold_closure(states_after)

    return ProjectivitySummary(
        projectivity_score=float(np.mean(complementary_quality)),
        complementary_quality_mean=float(np.mean(complementary_quality)),
        purity_mean=float(np.mean(purity)),
        dominance_mean=float(np.mean(np.abs(dominance_ratio(post_coords)))),
        clusterability=clusterability_score(post_coords),
        total_norm_before_mean=float(np.mean(pre_norm)),
        total_norm_after_mean=float(np.mean(post_norm)),
        mean_branch_loss=float(np.mean(np.sum(branch_loss, axis=1))),
        closure_error_mean=float(closure["closure_error_mean"]),
    )


def summarize_single_trials(trials: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    group_cols = ["window_fraction", "gamma_plus", "gamma_minus", "anisotropy_ratio", "angle_deg"]
    summary = (
        trials.groupby(group_cols, as_index=False)
        .agg(
            projectivity_score=("complementary_residual_quality", "mean"),
            residual_branch_quality=("residual_purity", "mean"),
            dominance_mean=("abs_dominance_post", "mean"),
            clusterability=("residual_is_pure", "mean"),
            total_norm_before=("total_norm_before", "mean"),
            total_norm_after=("total_norm_after", "mean"),
            branch_loss_mean=("total_branch_loss", "mean"),
            quality_to_plus=("quality_to_plus", "mean"),
            quality_to_minus=("quality_to_minus", "mean"),
        )
        .sort_values(group_cols)
        .reset_index(drop=True)
    )

    ratio_summary = (
        summary.groupby(["window_fraction", "anisotropy_ratio"], as_index=False)
        .agg(
            projectivity_score=("projectivity_score", "mean"),
            residual_branch_quality=("residual_branch_quality", "mean"),
            dominance_mean=("dominance_mean", "mean"),
            clusterability=("clusterability", "mean"),
            branch_loss_mean=("branch_loss_mean", "mean"),
        )
        .sort_values(["window_fraction", "anisotropy_ratio"])
        .reset_index(drop=True)
    )

    return summary, ratio_summary


def summarize_sequential_trials(
    trials: pd.DataFrame,
    *,
    rules: tuple[str, ...] = ALL_READOUT_RULES,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rule_frames: list[pd.DataFrame] = []
    drift_rows: list[dict[str, Any]] = []
    correlation_rows: list[dict[str, Any]] = []

    for rule in rules:
        alice_col = f"alice_outcome_{rule}"
        bob_col = f"bob_outcome_{rule}"
        working = trials[
            [
                "window_fraction",
                "gamma_plus",
                "gamma_minus",
                "anisotropy_ratio",
                "angle_a_deg",
                "angle_b_deg",
                alice_col,
                bob_col,
            ]
        ].copy()
        working["rule"] = rule
        working["corr"] = working[alice_col] * working[bob_col]
        working["same_sign"] = (working[alice_col] == working[bob_col]).astype(float)
        working["anti_sign"] = (working[alice_col] != working[bob_col]).astype(float)

        combo_summary = (
            working.groupby(
                [
                    "rule",
                    "window_fraction",
                    "gamma_plus",
                    "gamma_minus",
                    "anisotropy_ratio",
                    "angle_a_deg",
                    "angle_b_deg",
                ],
                as_index=False,
            )
            .agg(
                alice_marginal=(alice_col, "mean"),
                bob_marginal=(bob_col, "mean"),
                same_sign_mass=("same_sign", "mean"),
                anti_sign_mass=("anti_sign", "mean"),
                correlation=("corr", "mean"),
            )
            .sort_values(
                [
                    "window_fraction",
                    "anisotropy_ratio",
                    "angle_a_deg",
                    "angle_b_deg",
                ]
            )
            .reset_index(drop=True)
        )
        rule_frames.append(combo_summary)
        correlation_rows.extend(combo_summary.to_dict(orient="records"))

        alice_drift = (
            combo_summary.groupby(["rule", "window_fraction", "anisotropy_ratio", "angle_a_deg"])
            .agg(alice_drift=("alice_marginal", lambda s: float(s.max() - s.min())))
            .reset_index()
        )
        bob_drift = (
            combo_summary.groupby(["rule", "window_fraction", "anisotropy_ratio", "angle_b_deg"])
            .agg(bob_drift=("bob_marginal", lambda s: float(s.max() - s.min())))
            .reset_index()
        )
        merged_drift = (
            alice_drift.groupby(["rule", "window_fraction", "anisotropy_ratio"], as_index=False)
            .agg(alice_drift_max=("alice_drift", "max"))
            .merge(
                bob_drift.groupby(["rule", "window_fraction", "anisotropy_ratio"], as_index=False)
                .agg(bob_drift_max=("bob_drift", "max")),
                on=["rule", "window_fraction", "anisotropy_ratio"],
                how="outer",
            )
        )
        drift_rows.extend(merged_drift.to_dict(orient="records"))

    rule_summary = pd.concat(rule_frames, ignore_index=True) if rule_frames else pd.DataFrame()
    if drift_rows:
        drift_summary = pd.DataFrame(drift_rows).drop_duplicates().sort_values(
            ["rule", "window_fraction", "anisotropy_ratio"]
        )
    else:
        drift_summary = pd.DataFrame()
    if correlation_rows:
        correlation_df = pd.DataFrame(correlation_rows).drop_duplicates().sort_values(
            ["rule", "window_fraction", "anisotropy_ratio", "angle_a_deg", "angle_b_deg"]
        )
    else:
        correlation_df = pd.DataFrame()

    return rule_summary, drift_summary, correlation_df


def compute_chsh(rule_summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if rule_summary.empty:
        return pd.DataFrame(rows)

    for (rule, window_fraction, anisotropy_ratio), group in rule_summary.groupby(
        ["rule", "window_fraction", "anisotropy_ratio"]
    ):
        lookup = {
            (float(row.angle_a_deg), float(row.angle_b_deg)): float(row.correlation)
            for row in group.itertuples()
        }
        if any(pair not in lookup for pair in CHSH_ANGLE_SET):
            continue
        e_ab = lookup[(0.0, 22.5)]
        e_abp = lookup[(0.0, 67.5)]
        e_apb = lookup[(45.0, 22.5)]
        e_apbp = lookup[(45.0, 67.5)]
        chsh_value = abs(e_ab - e_abp + e_apb + e_apbp)
        rows.append(
            {
                "rule": rule,
                "window_fraction": window_fraction,
                "anisotropy_ratio": anisotropy_ratio,
                "chsh": chsh_value,
            }
        )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["rule", "window_fraction", "anisotropy_ratio"])
