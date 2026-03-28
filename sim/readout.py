from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import EPSILON, SequentialGateConfig
from .state import abs2

RULE_ENERGY_LOSS_WINNER = "energy_loss_winner"
RULE_RESIDUAL_TEMPLATE_CLASSIFIER = "residual_template_classifier"
RULE_CONFIDENCE_WEIGHTED_AGREEMENT = "confidence_weighted_agreement"
RULE_LEGACY_DOMINANT_POST = "legacy_dominant_post"
RULE_LEGACY_DOMINANCE_SHIFT = "legacy_dominance_shift"
RULE_CONTROL_NEGATIVE_PREWINDOW = "control_negative_prewindow"

# Backward-compatible aliases for the previous public rule names.
RULE_DOMINANT_PRE = RULE_CONTROL_NEGATIVE_PREWINDOW
RULE_DOMINANT_POST = RULE_LEGACY_DOMINANT_POST
RULE_DOMINANCE_SHIFT = RULE_LEGACY_DOMINANCE_SHIFT
RULE_EXTRACTED_ENERGY = RULE_ENERGY_LOSS_WINNER
RULE_RESIDUAL_CLASSIFIER = RULE_RESIDUAL_TEMPLATE_CLASSIFIER

HEADLINE_RULES = (RULE_ENERGY_LOSS_WINNER,)
DIAGNOSTIC_RULES = (
    RULE_RESIDUAL_TEMPLATE_CLASSIFIER,
    RULE_CONFIDENCE_WEIGHTED_AGREEMENT,
)
LEGACY_RULES = (
    RULE_LEGACY_DOMINANT_POST,
    RULE_LEGACY_DOMINANCE_SHIFT,
)
NEGATIVE_CONTROL_RULES = (RULE_CONTROL_NEGATIVE_PREWINDOW,)
ALL_READOUT_RULES = HEADLINE_RULES + DIAGNOSTIC_RULES + LEGACY_RULES + NEGATIVE_CONTROL_RULES

RULE_ROLE = {
    RULE_ENERGY_LOSS_WINNER: "headline_primary",
    RULE_RESIDUAL_TEMPLATE_CLASSIFIER: "diagnostic_rule",
    RULE_CONFIDENCE_WEIGHTED_AGREEMENT: "diagnostic_rule",
    RULE_LEGACY_DOMINANT_POST: "legacy_rule",
    RULE_LEGACY_DOMINANCE_SHIFT: "legacy_rule",
    RULE_CONTROL_NEGATIVE_PREWINDOW: "negative_control",
}


@dataclass(slots=True)
class StageReadout:
    outcomes: dict[str, np.ndarray]
    valid: dict[str, np.ndarray]
    energy_margin: np.ndarray
    residual_margin: np.ndarray
    confidence_margin: np.ndarray
    residual_purity: np.ndarray
    residual_template_plus_score: np.ndarray
    residual_template_minus_score: np.ndarray
    residual_template_distance_gap: np.ndarray
    readout_agreement: np.ndarray
    residual_ambiguous: np.ndarray
    high_confidence_residual: np.ndarray
    low_confidence_residual: np.ndarray


def _signed_outcome(delta: np.ndarray) -> np.ndarray:
    return np.where(delta >= 0.0, 1, -1).astype(np.int8)


def branch_extracted_energy(pre_coords: np.ndarray, post_coords: np.ndarray) -> np.ndarray:
    return np.clip(abs2(pre_coords) - abs2(post_coords), 0.0, None)


def dominant_component_outcome(
    pre_coords: np.ndarray,
    post_coords: np.ndarray,
    *,
    mode: str = "post",
) -> np.ndarray:
    pre_weights = abs2(pre_coords)
    post_weights = abs2(post_coords)

    if mode == "pre":
        delta = pre_weights[..., 0] - pre_weights[..., 1]
    elif mode == "post":
        delta = post_weights[..., 0] - post_weights[..., 1]
    elif mode == "shift":
        delta = (post_weights[..., 0] - post_weights[..., 1]) - (
            pre_weights[..., 0] - pre_weights[..., 1]
        )
    else:
        raise ValueError(f"Unsupported dominant-component mode: {mode}")

    return _signed_outcome(delta)


def energy_loss_outcome(pre_coords: np.ndarray, post_coords: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    extracted = branch_extracted_energy(pre_coords, post_coords)
    delta = extracted[..., 0] - extracted[..., 1]
    margin = np.abs(delta) / np.maximum(np.sum(extracted, axis=-1), EPSILON)
    return _signed_outcome(delta), extracted, margin.astype(np.float64)


def residual_template_scores(post_coords: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    norms = np.linalg.norm(post_coords, axis=-1, keepdims=True)
    normalized = post_coords / np.maximum(norms, EPSILON)
    score_plus = np.abs(normalized[..., 0])
    score_minus = np.abs(normalized[..., 1])
    margin = np.abs(score_plus - score_minus) / np.maximum(score_plus + score_minus, EPSILON)
    return (
        score_plus.astype(np.float64),
        score_minus.astype(np.float64),
        _signed_outcome(score_plus - score_minus),
        margin.astype(np.float64),
    )


def residual_classifier_outcome(post_coords: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    return residual_template_scores(post_coords)


def compute_stage_readout(
    pre_coords: np.ndarray,
    post_coords: np.ndarray,
    residual_purity: np.ndarray,
    gate_thresholds: SequentialGateConfig,
    *,
    purity_threshold: float = 0.9,
) -> StageReadout:
    energy_outcome, _, energy_margin = energy_loss_outcome(pre_coords, post_coords)
    residual_plus_score, residual_minus_score, residual_outcome, residual_margin = residual_classifier_outcome(
        post_coords
    )
    confidence_margin = np.minimum(energy_margin, residual_margin)
    readout_agreement = energy_outcome == residual_outcome
    residual_ambiguous = (~readout_agreement) | (residual_margin < gate_thresholds.confidence_margin_threshold)
    high_confidence_residual = (
        ~residual_ambiguous
        & (
        (residual_purity >= purity_threshold)
        & (confidence_margin >= gate_thresholds.confidence_margin_threshold)
        )
    )
    low_confidence_residual = ~high_confidence_residual

    confidence_weighted_outcome = np.where(residual_ambiguous, 0, energy_outcome).astype(np.int8)
    confidence_weighted_valid = ~residual_ambiguous

    outcomes = {
        RULE_ENERGY_LOSS_WINNER: energy_outcome,
        RULE_RESIDUAL_TEMPLATE_CLASSIFIER: residual_outcome,
        RULE_CONFIDENCE_WEIGHTED_AGREEMENT: confidence_weighted_outcome,
        RULE_LEGACY_DOMINANT_POST: dominant_component_outcome(pre_coords, post_coords, mode="post"),
        RULE_LEGACY_DOMINANCE_SHIFT: dominant_component_outcome(pre_coords, post_coords, mode="shift"),
        RULE_CONTROL_NEGATIVE_PREWINDOW: dominant_component_outcome(pre_coords, post_coords, mode="pre"),
    }
    valid = {rule: np.ones(len(post_coords), dtype=bool) for rule in ALL_READOUT_RULES}
    valid[RULE_CONFIDENCE_WEIGHTED_AGREEMENT] = confidence_weighted_valid

    return StageReadout(
        outcomes=outcomes,
        valid=valid,
        energy_margin=energy_margin,
        residual_margin=residual_margin,
        confidence_margin=confidence_margin,
        residual_purity=residual_purity.astype(np.float64),
        residual_template_plus_score=residual_plus_score,
        residual_template_minus_score=residual_minus_score,
        residual_template_distance_gap=np.abs(residual_plus_score - residual_minus_score).astype(np.float64),
        readout_agreement=readout_agreement,
        residual_ambiguous=residual_ambiguous,
        high_confidence_residual=high_confidence_residual,
        low_confidence_residual=low_confidence_residual,
    )


def compute_all_outcomes(
    pre_coords: np.ndarray,
    post_coords: np.ndarray,
    *,
    residual_purity: np.ndarray | None = None,
    gate_thresholds: SequentialGateConfig | None = None,
) -> dict[str, np.ndarray]:
    if residual_purity is None:
        post_power = abs2(post_coords)
        totals = np.maximum(np.sum(post_power, axis=-1), EPSILON)
        residual_purity = np.max(post_power, axis=-1) / totals
    stage = compute_stage_readout(
        pre_coords,
        post_coords,
        residual_purity=np.asarray(residual_purity, dtype=np.float64),
        gate_thresholds=gate_thresholds or SequentialGateConfig(),
    )
    return stage.outcomes


def rule_role(rule: str) -> str:
    return RULE_ROLE[rule]


def is_headline_rule(rule: str) -> bool:
    return rule in HEADLINE_RULES
