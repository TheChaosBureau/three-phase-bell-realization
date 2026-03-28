from __future__ import annotations

import numpy as np

from .state import abs2

RULE_DOMINANT_PRE = "dominant_pre"
RULE_DOMINANT_POST = "dominant_post"
RULE_DOMINANCE_SHIFT = "dominance_shift"
RULE_EXTRACTED_ENERGY = "extracted_energy"
RULE_RESIDUAL_CLASSIFIER = "residual_classifier"
ALL_READOUT_RULES = (
    RULE_DOMINANT_PRE,
    RULE_DOMINANT_POST,
    RULE_DOMINANCE_SHIFT,
    RULE_EXTRACTED_ENERGY,
    RULE_RESIDUAL_CLASSIFIER,
)


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


def extracted_energy_outcome(pre_coords: np.ndarray, post_coords: np.ndarray) -> np.ndarray:
    extracted = branch_extracted_energy(pre_coords, post_coords)
    return _signed_outcome(extracted[..., 0] - extracted[..., 1])


def residual_classifier_outcome(post_coords: np.ndarray) -> np.ndarray:
    post_weights = abs2(post_coords)
    return _signed_outcome(post_weights[..., 0] - post_weights[..., 1])


def compute_all_outcomes(pre_coords: np.ndarray, post_coords: np.ndarray) -> dict[str, np.ndarray]:
    return {
        RULE_DOMINANT_PRE: dominant_component_outcome(pre_coords, post_coords, mode="pre"),
        RULE_DOMINANT_POST: dominant_component_outcome(pre_coords, post_coords, mode="post"),
        RULE_DOMINANCE_SHIFT: dominant_component_outcome(pre_coords, post_coords, mode="shift"),
        RULE_EXTRACTED_ENERGY: extracted_energy_outcome(pre_coords, post_coords),
        RULE_RESIDUAL_CLASSIFIER: residual_classifier_outcome(post_coords),
    }
