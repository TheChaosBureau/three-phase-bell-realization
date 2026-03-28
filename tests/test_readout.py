from __future__ import annotations

import numpy as np

from sim.config import SequentialGateConfig
from sim.readout import (
    ALL_READOUT_RULES,
    RULE_CONFIDENCE_WEIGHTED_AGREEMENT,
    RULE_CONTROL_NEGATIVE_PREWINDOW,
    RULE_ENERGY_LOSS_WINNER,
    RULE_LEGACY_DOMINANCE_SHIFT,
    RULE_LEGACY_DOMINANT_POST,
    RULE_RESIDUAL_TEMPLATE_CLASSIFIER,
    branch_extracted_energy,
    compute_all_outcomes,
    compute_stage_readout,
)


def test_branch_extracted_energy_matches_norm_loss() -> None:
    pre = np.array([[2.0 + 0.0j, 1.0 + 0.0j]])
    post = np.array([[1.0 + 0.0j, 0.5 + 0.0j]])
    extracted = branch_extracted_energy(pre, post)

    assert np.isclose(extracted.sum(), (np.abs(pre) ** 2).sum() - (np.abs(post) ** 2).sum())


def test_compute_stage_readout_tracks_agreement_and_ambiguity() -> None:
    pre = np.array(
        [
            [2.0 + 0.0j, 1.0 + 0.0j],
            [0.5 + 0.0j, 2.0 + 0.0j],
        ]
    )
    post = np.array(
        [
            [1.2 + 0.0j, 0.2 + 0.0j],
            [1.4 + 0.0j, 0.2 + 0.0j],
        ]
    )
    stage = compute_stage_readout(
        pre,
        post,
        residual_purity=np.array([0.95, 0.95]),
        gate_thresholds=SequentialGateConfig(confidence_margin_threshold=0.2),
    )

    assert set(stage.outcomes) == set(ALL_READOUT_RULES)
    assert np.array_equal(stage.outcomes[RULE_ENERGY_LOSS_WINNER], np.array([1, -1], dtype=np.int8))
    assert np.array_equal(stage.outcomes[RULE_RESIDUAL_TEMPLATE_CLASSIFIER], np.array([1, 1], dtype=np.int8))
    assert np.array_equal(
        stage.outcomes[RULE_CONFIDENCE_WEIGHTED_AGREEMENT],
        np.array([1, 0], dtype=np.int8),
    )
    assert np.array_equal(stage.valid[RULE_CONFIDENCE_WEIGHTED_AGREEMENT], np.array([True, False]))
    assert np.array_equal(stage.residual_ambiguous, np.array([False, True]))
    assert np.array_equal(stage.high_confidence_residual, np.array([True, False]))


def test_compute_all_outcomes_returns_redesigned_rule_set() -> None:
    pre = np.array([[2.0 + 0.0j, 1.0 + 0.0j]])
    post = np.array([[1.2 + 0.0j, 0.2 + 0.0j]])
    outcomes = compute_all_outcomes(pre, post)

    assert set(outcomes) == {
        RULE_ENERGY_LOSS_WINNER,
        RULE_RESIDUAL_TEMPLATE_CLASSIFIER,
        RULE_CONFIDENCE_WEIGHTED_AGREEMENT,
        RULE_LEGACY_DOMINANT_POST,
        RULE_LEGACY_DOMINANCE_SHIFT,
        RULE_CONTROL_NEGATIVE_PREWINDOW,
    }
