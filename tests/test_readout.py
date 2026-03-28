from __future__ import annotations

import numpy as np

from sim.readout import (
    RULE_DOMINANCE_SHIFT,
    RULE_DOMINANT_POST,
    RULE_DOMINANT_PRE,
    RULE_EXTRACTED_ENERGY,
    RULE_RESIDUAL_CLASSIFIER,
    branch_extracted_energy,
    compute_all_outcomes,
)


def test_branch_extracted_energy_matches_norm_loss() -> None:
    pre = np.array([[2.0 + 0.0j, 1.0 + 0.0j]])
    post = np.array([[1.0 + 0.0j, 0.5 + 0.0j]])
    extracted = branch_extracted_energy(pre, post)

    assert np.isclose(extracted.sum(), (np.abs(pre) ** 2).sum() - (np.abs(post) ** 2).sum())


def test_compute_all_outcomes_returns_expected_rule_set() -> None:
    pre = np.array([[2.0 + 0.0j, 1.0 + 0.0j], [0.5 + 0.0j, 2.0 + 0.0j]])
    post = np.array([[0.2 + 0.0j, 1.4 + 0.0j], [1.4 + 0.0j, 0.2 + 0.0j]])
    outcomes = compute_all_outcomes(pre, post)

    assert set(outcomes) == {
        RULE_DOMINANT_PRE,
        RULE_DOMINANT_POST,
        RULE_DOMINANCE_SHIFT,
        RULE_EXTRACTED_ENERGY,
        RULE_RESIDUAL_CLASSIFIER,
    }
    assert np.array_equal(outcomes[RULE_RESIDUAL_CLASSIFIER], np.array([-1, 1], dtype=np.int8))
