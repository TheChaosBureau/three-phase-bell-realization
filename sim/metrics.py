from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .config import BRANCHES


def target_joint_weights(delta: float) -> dict[str, float]:
    sin2 = math.sin(delta) ** 2
    cos2 = math.cos(delta) ** 2
    return {
        "pp": 0.5 * sin2,
        "pm": 0.5 * cos2,
        "mp": 0.5 * cos2,
        "mm": 0.5 * sin2,
    }


def empirical_joint_probs(df_pair: pd.DataFrame) -> dict[str, float]:
    decisive = df_pair[df_pair["winner"] != "none"]
    total = len(decisive)
    if total == 0:
        return {branch: 0.0 for branch in BRANCHES}
    return {
        branch: float((decisive["winner"] == branch).sum() / total)
        for branch in BRANCHES
    }


def correlator_from_probs(probs: dict[str, float]) -> float:
    return probs["pp"] + probs["mm"] - probs["pm"] - probs["mp"]


def winner_law_errors(
    probs: dict[str, float],
    target: dict[str, float],
) -> tuple[float, float]:
    diffs = np.array([probs[branch] - target[branch] for branch in BRANCHES], dtype=float)
    return float(np.sqrt(np.mean(diffs**2))), float(np.max(np.abs(diffs)))


def compute_chsh(
    angle_summary: pd.DataFrame,
    settings: tuple[float, float, float, float],
) -> dict[str, float]:
    a, a_prime, b, b_prime = settings

    def _lookup(angle_a: float, angle_b: float) -> tuple[float, float]:
        mask = np.isclose(angle_summary["angle_a"], angle_a) & np.isclose(angle_summary["angle_b"], angle_b)
        if not mask.any():
            return float("nan"), -math.cos(2.0 * (angle_a - angle_b))
        row = angle_summary.loc[mask].iloc[0]
        return float(row["correlator_empirical"]), float(row["correlator_target"])

    e_ab, e_ab_target = _lookup(a, b)
    e_ab_prime, e_ab_prime_target = _lookup(a, b_prime)
    e_a_prime_b, e_a_prime_b_target = _lookup(a_prime, b)
    e_a_prime_b_prime, e_a_prime_b_prime_target = _lookup(a_prime, b_prime)

    s_empirical = e_ab + e_ab_prime + e_a_prime_b - e_a_prime_b_prime
    s_target_signed = e_ab_target + e_ab_prime_target + e_a_prime_b_target - e_a_prime_b_prime_target
    s_target = abs(s_target_signed)
    return {
        "a": a,
        "a_prime": a_prime,
        "b": b,
        "b_prime": b_prime,
        "E_ab": e_ab,
        "E_ab_prime": e_ab_prime,
        "E_a_prime_b": e_a_prime_b,
        "E_a_prime_b_prime": e_a_prime_b_prime,
        "S_empirical": s_empirical,
        "S_target": s_target,
        "S_abs_error": float(abs(abs(s_empirical) - s_target)) if math.isfinite(s_empirical) else float("nan"),
    }
