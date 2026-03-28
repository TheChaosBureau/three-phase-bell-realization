from __future__ import annotations

import numpy as np

from sim.config import DampingConfig
from sim.disambiguation import summarize_oracle_stage


def test_oracle_stage_detects_clean_two_branch_structure() -> None:
    initial_states = np.array(
        [
            [1.0 + 0.0j, 0.0 + 0.0j],
            [0.9 + 0.0j, 0.1 + 0.0j],
            [0.0 + 0.0j, 1.0 + 0.0j],
            [0.1 + 0.0j, 0.9 + 0.0j],
        ],
        dtype=np.complex128,
    )
    summary = summarize_oracle_stage(
        combo_id=0,
        angle_deg=0.0,
        initial_states=initial_states,
        post_states=initial_states,
        damping=DampingConfig(gamma_plus=4.0, gamma_minus=1.0, window_fraction=0.25),
    )

    assert summary.separability_score > 0.5
    assert summary.strong_plus_fraction > 0.0
    assert summary.strong_minus_fraction > 0.0
    assert summary.ambiguity_fraction < 0.5
