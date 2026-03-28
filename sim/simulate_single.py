from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .config import SingleRunConfig
from .damping import evolve_with_diagnostics
from .metrics import (
    complementary_residual_quality,
    dominance_ratio,
    residual_branch_quality,
    summarize_projectivity,
    summarize_single_trials,
)
from .state import abs2, sample_source_states


@dataclass(slots=True)
class SingleBatchResult:
    trial_metrics: pd.DataFrame
    combo_summary: pd.DataFrame
    ratio_summary: pd.DataFrame
    initial_states: np.ndarray
    post_states: np.ndarray
    combo_keys: list[str]
    run_manifest: list[dict[str, Any]]


def _combo_key(config: SingleRunConfig, angle_deg: float) -> str:
    return (
        f"wf_{config.damping.window_fraction:.6f}"
        f"__gp_{config.damping.gamma_plus:.6f}"
        f"__gm_{config.damping.gamma_minus:.6f}"
        f"__angle_{angle_deg:.6f}"
    )


def run_single_batch(configs: list[SingleRunConfig]) -> SingleBatchResult:
    trial_frames: list[pd.DataFrame] = []
    run_manifest: list[dict[str, Any]] = []
    combo_keys: list[str] = []
    initial_state_blocks: list[np.ndarray] = []
    post_state_blocks: list[np.ndarray] = []
    combo_id = 0

    for config in configs:
        source_states = sample_source_states(config.source)
        for angle_deg in config.expanded_angles_deg():
            diagnostics = evolve_with_diagnostics(
                source_states,
                np.deg2rad(angle_deg),
                config.damping,
            )
            pre_coords = diagnostics["coords_before"]
            post_coords = diagnostics["coords_after"]
            post_states = diagnostics["states_after"]
            branch_loss = diagnostics["branch_loss"]

            pre_power = abs2(pre_coords)
            post_power = abs2(post_coords)
            quality_plus, quality_minus, residual_purity = residual_branch_quality(post_coords)
            complementary_quality = complementary_residual_quality(
                pre_coords,
                post_coords,
                branch_loss=branch_loss,
            )
            dominance_pre = dominance_ratio(pre_coords)
            dominance_post = dominance_ratio(post_coords)
            summary = summarize_projectivity(pre_coords, post_coords, branch_loss, post_states)

            key = _combo_key(config, angle_deg)
            combo_keys.append(key)
            initial_state_blocks.append(source_states)
            post_state_blocks.append(post_states)
            run_manifest.append(
                {
                    "combo_id": combo_id,
                    "combo_key": key,
                    "angle_deg": angle_deg,
                    "gamma_plus": config.damping.gamma_plus,
                    "gamma_minus": config.damping.gamma_minus,
                    "anisotropy_ratio": config.damping.anisotropy_ratio,
                    "window_fraction": config.damping.window_fraction,
                    "sample_count": config.source.sample_count,
                    "projectivity": summary.to_dict(),
                }
            )

            frame = pd.DataFrame(
                {
                    "combo_id": combo_id,
                    "combo_key": key,
                    "sample_index": np.arange(config.source.sample_count),
                    "angle_deg": angle_deg,
                    "window_fraction": config.damping.window_fraction,
                    "gamma_plus": config.damping.gamma_plus,
                    "gamma_minus": config.damping.gamma_minus,
                    "anisotropy_ratio": config.damping.anisotropy_ratio,
                    "c_plus_pre_real": pre_coords[:, 0].real,
                    "c_plus_pre_imag": pre_coords[:, 0].imag,
                    "c_minus_pre_real": pre_coords[:, 1].real,
                    "c_minus_pre_imag": pre_coords[:, 1].imag,
                    "c_plus_post_real": post_coords[:, 0].real,
                    "c_plus_post_imag": post_coords[:, 0].imag,
                    "c_minus_post_real": post_coords[:, 1].real,
                    "c_minus_post_imag": post_coords[:, 1].imag,
                    "pre_plus_power": pre_power[:, 0],
                    "pre_minus_power": pre_power[:, 1],
                    "post_plus_power": post_power[:, 0],
                    "post_minus_power": post_power[:, 1],
                    "branch_loss_plus": branch_loss[:, 0],
                    "branch_loss_minus": branch_loss[:, 1],
                    "total_norm_before": np.sum(pre_power, axis=1),
                    "total_norm_after": np.sum(post_power, axis=1),
                    "quality_to_plus": quality_plus,
                    "quality_to_minus": quality_minus,
                    "residual_purity": residual_purity,
                    "residual_is_pure": (residual_purity >= 0.9).astype(float),
                    "dominance_pre": dominance_pre,
                    "dominance_post": dominance_post,
                    "abs_dominance_post": np.abs(dominance_post),
                    "complementary_residual_quality": complementary_quality,
                    "extracted_branch_sign": np.where(branch_loss[:, 0] >= branch_loss[:, 1], 1, -1),
                    "residual_branch_sign": np.where(post_power[:, 0] >= post_power[:, 1], 1, -1),
                    "total_branch_loss": np.sum(branch_loss, axis=1),
                }
            )
            trial_frames.append(frame)
            combo_id += 1

    trials = pd.concat(trial_frames, ignore_index=True) if trial_frames else pd.DataFrame()
    combo_summary, ratio_summary = summarize_single_trials(trials) if not trials.empty else (
        pd.DataFrame(),
        pd.DataFrame(),
    )

    return SingleBatchResult(
        trial_metrics=trials,
        combo_summary=combo_summary,
        ratio_summary=ratio_summary,
        initial_states=np.stack(initial_state_blocks) if initial_state_blocks else np.empty((0, 0, 2)),
        post_states=np.stack(post_state_blocks) if post_state_blocks else np.empty((0, 0, 2)),
        combo_keys=combo_keys,
        run_manifest=run_manifest,
    )
