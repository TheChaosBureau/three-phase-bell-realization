from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .config import SequentialRunConfig
from .damping import evolve_with_diagnostics
from .metrics import (
    complementary_residual_quality,
    compute_chsh,
    residual_branch_quality,
    summarize_sequential_trials,
)
from .readout import compute_all_outcomes
from .state import abs2, sample_source_states


@dataclass(slots=True)
class SequentialBatchResult:
    trial_metrics: pd.DataFrame
    rule_summary: pd.DataFrame
    drift_summary: pd.DataFrame
    correlation_summary: pd.DataFrame
    chsh_summary: pd.DataFrame
    initial_states: np.ndarray
    post_alice_states: np.ndarray
    post_bob_states: np.ndarray
    combo_keys: list[str]
    run_manifest: list[dict[str, Any]]


def _combo_key(config: SequentialRunConfig, angle_a_deg: float, angle_b_deg: float) -> str:
    return (
        f"wf_{config.damping.window_fraction:.6f}"
        f"__gp_{config.damping.gamma_plus:.6f}"
        f"__gm_{config.damping.gamma_minus:.6f}"
        f"__a_{angle_a_deg:.6f}"
        f"__b_{angle_b_deg:.6f}"
    )


def run_sequential_batch(configs: list[SequentialRunConfig]) -> SequentialBatchResult:
    trial_frames: list[pd.DataFrame] = []
    combo_keys: list[str] = []
    run_manifest: list[dict[str, Any]] = []
    initial_state_blocks: list[np.ndarray] = []
    post_alice_blocks: list[np.ndarray] = []
    post_bob_blocks: list[np.ndarray] = []
    combo_id = 0

    for config in configs:
        source_states = sample_source_states(config.source)
        for angle_a_deg in config.alice_angles_deg:
            alice_diag = evolve_with_diagnostics(
                source_states,
                np.deg2rad(angle_a_deg),
                config.damping,
            )
            alice_pre = alice_diag["coords_before"]
            alice_post = alice_diag["coords_after"]
            post_alice_states = alice_diag["states_after"]
            alice_branch_loss = alice_diag["branch_loss"]
            alice_quality_plus, alice_quality_minus, alice_purity = residual_branch_quality(alice_post)
            alice_complementary = complementary_residual_quality(
                alice_pre,
                alice_post,
                branch_loss=alice_branch_loss,
            )
            alice_outcomes = compute_all_outcomes(alice_pre, alice_post)

            for angle_b_deg in config.bob_angles_deg:
                bob_diag = evolve_with_diagnostics(
                    post_alice_states,
                    np.deg2rad(angle_b_deg),
                    config.damping,
                )
                bob_pre = bob_diag["coords_before"]
                bob_post = bob_diag["coords_after"]
                post_bob_states = bob_diag["states_after"]
                bob_branch_loss = bob_diag["branch_loss"]
                bob_quality_plus, bob_quality_minus, bob_purity = residual_branch_quality(bob_post)
                bob_complementary = complementary_residual_quality(
                    bob_pre,
                    bob_post,
                    branch_loss=bob_branch_loss,
                )
                bob_outcomes = compute_all_outcomes(bob_pre, bob_post)

                key = _combo_key(config, angle_a_deg, angle_b_deg)
                combo_keys.append(key)
                initial_state_blocks.append(source_states)
                post_alice_blocks.append(post_alice_states)
                post_bob_blocks.append(post_bob_states)
                run_manifest.append(
                    {
                        "combo_id": combo_id,
                        "combo_key": key,
                        "angle_a_deg": angle_a_deg,
                        "angle_b_deg": angle_b_deg,
                        "gamma_plus": config.damping.gamma_plus,
                        "gamma_minus": config.damping.gamma_minus,
                        "anisotropy_ratio": config.damping.anisotropy_ratio,
                        "window_fraction": config.damping.window_fraction,
                        "sample_count": config.source.sample_count,
                    }
                )

                alice_pre_power = abs2(alice_pre)
                alice_post_power = abs2(alice_post)
                bob_pre_power = abs2(bob_pre)
                bob_post_power = abs2(bob_post)

                frame = pd.DataFrame(
                    {
                        "combo_id": combo_id,
                        "combo_key": key,
                        "sample_index": np.arange(config.source.sample_count),
                        "angle_a_deg": angle_a_deg,
                        "angle_b_deg": angle_b_deg,
                        "delta_deg": angle_b_deg - angle_a_deg,
                        "aligned_pair": float(angle_a_deg == angle_b_deg),
                        "window_fraction": config.damping.window_fraction,
                        "gamma_plus": config.damping.gamma_plus,
                        "gamma_minus": config.damping.gamma_minus,
                        "anisotropy_ratio": config.damping.anisotropy_ratio,
                        "alice_pre_plus": alice_pre_power[:, 0],
                        "alice_pre_minus": alice_pre_power[:, 1],
                        "alice_post_plus": alice_post_power[:, 0],
                        "alice_post_minus": alice_post_power[:, 1],
                        "alice_branch_loss_plus": alice_branch_loss[:, 0],
                        "alice_branch_loss_minus": alice_branch_loss[:, 1],
                        "alice_residual_purity": alice_purity,
                        "alice_quality_to_plus": alice_quality_plus,
                        "alice_quality_to_minus": alice_quality_minus,
                        "alice_complementary_residual_quality": alice_complementary,
                        "bob_pre_plus": bob_pre_power[:, 0],
                        "bob_pre_minus": bob_pre_power[:, 1],
                        "bob_post_plus": bob_post_power[:, 0],
                        "bob_post_minus": bob_post_power[:, 1],
                        "bob_branch_loss_plus": bob_branch_loss[:, 0],
                        "bob_branch_loss_minus": bob_branch_loss[:, 1],
                        "bob_residual_purity": bob_purity,
                        "bob_quality_to_plus": bob_quality_plus,
                        "bob_quality_to_minus": bob_quality_minus,
                        "bob_complementary_residual_quality": bob_complementary,
                    }
                )
                for rule, outcomes in alice_outcomes.items():
                    frame[f"alice_outcome_{rule}"] = outcomes
                for rule, outcomes in bob_outcomes.items():
                    frame[f"bob_outcome_{rule}"] = outcomes

                trial_frames.append(frame)
                combo_id += 1

    trials = pd.concat(trial_frames, ignore_index=True) if trial_frames else pd.DataFrame()
    rule_summary, drift_summary, correlation_summary = (
        summarize_sequential_trials(trials) if not trials.empty else (pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    )
    chsh_summary = compute_chsh(correlation_summary) if not correlation_summary.empty else pd.DataFrame()

    return SequentialBatchResult(
        trial_metrics=trials,
        rule_summary=rule_summary,
        drift_summary=drift_summary,
        correlation_summary=correlation_summary,
        chsh_summary=chsh_summary,
        initial_states=np.stack(initial_state_blocks) if initial_state_blocks else np.empty((0, 0, 2)),
        post_alice_states=np.stack(post_alice_blocks) if post_alice_blocks else np.empty((0, 0, 2)),
        post_bob_states=np.stack(post_bob_blocks) if post_bob_blocks else np.empty((0, 0, 2)),
        combo_keys=combo_keys,
        run_manifest=run_manifest,
    )
