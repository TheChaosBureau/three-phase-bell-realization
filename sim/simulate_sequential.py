from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .config import EPSILON, SequentialRunConfig
from .damping import evolve_with_diagnostics
from .metrics import (
    complementary_residual_quality,
    compute_chsh,
    residual_branch_quality,
    summarize_sequential_trials,
)
from .readout import (
    ALL_READOUT_RULES,
    RULE_ENERGY_LOSS_WINNER,
    compute_stage_readout,
    rule_role,
)
from .state import abs2, from_analyzer_basis, sample_source_states


@dataclass(slots=True)
class SequentialBatchResult:
    trial_metrics: pd.DataFrame
    rule_summary: pd.DataFrame
    drift_summary: pd.DataFrame
    correlation_summary: pd.DataFrame
    chsh_summary: pd.DataFrame
    residual_agreement_summary: pd.DataFrame
    gated_summary: pd.DataFrame
    aligned_support_by_confidence: pd.DataFrame
    legacy_rule_controls: pd.DataFrame
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


def _compute_bob_branch_stability(
    post_alice_states: np.ndarray,
    phi_b_rad: float,
    config: SequentialRunConfig,
    reference_outcomes: np.ndarray,
    *,
    perturbation_scale: float = 1e-3,
) -> np.ndarray:
    basis_direction = np.array([[1.0, -1.0]], dtype=np.complex128) / np.sqrt(2.0)
    state_norms = np.linalg.norm(post_alice_states, axis=1, keepdims=True)
    scaled_direction = basis_direction * np.maximum(state_norms, EPSILON) * perturbation_scale
    lab_delta = from_analyzer_basis(scaled_direction, phi_b_rad)

    stability_checks: list[np.ndarray] = []
    for sign in (1.0, -1.0):
        perturbed_input = post_alice_states + sign * lab_delta
        perturbed_diag = evolve_with_diagnostics(perturbed_input, phi_b_rad, config.damping)
        perturbed_stage = compute_stage_readout(
            perturbed_diag["coords_before"],
            perturbed_diag["coords_after"],
            residual_branch_quality(perturbed_diag["coords_after"])[2],
            config.gate_thresholds,
        )
        stability_checks.append(
            perturbed_stage.outcomes[RULE_ENERGY_LOSS_WINNER] == reference_outcomes
        )

    return np.mean(np.stack(stability_checks), axis=0).astype(np.float64)


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
            alice_stage = compute_stage_readout(
                alice_pre,
                alice_post,
                alice_purity,
                config.gate_thresholds,
            )

            for angle_b_deg in config.bob_angles_deg:
                phi_b_rad = np.deg2rad(angle_b_deg)
                bob_diag = evolve_with_diagnostics(
                    post_alice_states,
                    phi_b_rad,
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
                bob_stage = compute_stage_readout(
                    bob_pre,
                    bob_post,
                    bob_purity,
                    config.gate_thresholds,
                )
                bob_branch_stability = _compute_bob_branch_stability(
                    post_alice_states,
                    phi_b_rad,
                    config,
                    bob_stage.outcomes[RULE_ENERGY_LOSS_WINNER],
                )
                pair_readout_agreement = alice_stage.readout_agreement & bob_stage.readout_agreement
                pair_residual_ambiguity = alice_stage.residual_ambiguous | bob_stage.residual_ambiguous
                mean_projectivity_compatibility = 0.5 * (alice_complementary + bob_complementary)
                pair_high_confidence = (
                    alice_stage.high_confidence_residual
                    & bob_stage.high_confidence_residual
                    & (mean_projectivity_compatibility >= config.gate_thresholds.min_projectivity_compatibility)
                )
                pair_low_confidence = ~pair_high_confidence
                mean_confidence_margin = 0.5 * (
                    alice_stage.confidence_margin + bob_stage.confidence_margin
                )

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
                        "gate_thresholds": {
                            "max_alice_drift": config.gate_thresholds.max_alice_drift,
                            "max_bob_drift": config.gate_thresholds.max_bob_drift,
                            "max_aligned_same_sign_mass": config.gate_thresholds.max_aligned_same_sign_mass,
                            "min_residual_agreement_rate": config.gate_thresholds.min_residual_agreement_rate,
                            "max_residual_ambiguity_rate": config.gate_thresholds.max_residual_ambiguity_rate,
                            "min_projectivity_compatibility": config.gate_thresholds.min_projectivity_compatibility,
                            "confidence_margin_threshold": config.gate_thresholds.confidence_margin_threshold,
                        },
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
                        "alice_energy_margin": alice_stage.energy_margin,
                        "alice_residual_margin": alice_stage.residual_margin,
                        "alice_confidence_margin": alice_stage.confidence_margin,
                        "alice_residual_template_plus_score": alice_stage.residual_template_plus_score,
                        "alice_residual_template_minus_score": alice_stage.residual_template_minus_score,
                        "alice_residual_template_distance_gap": alice_stage.residual_template_distance_gap,
                        "alice_readout_agreement": alice_stage.readout_agreement.astype(float),
                        "alice_residual_ambiguous": alice_stage.residual_ambiguous.astype(float),
                        "alice_high_confidence_residual": alice_stage.high_confidence_residual.astype(float),
                        "alice_low_confidence_residual": alice_stage.low_confidence_residual.astype(float),
                        "bob_energy_margin": bob_stage.energy_margin,
                        "bob_residual_margin": bob_stage.residual_margin,
                        "bob_confidence_margin": bob_stage.confidence_margin,
                        "bob_residual_template_plus_score": bob_stage.residual_template_plus_score,
                        "bob_residual_template_minus_score": bob_stage.residual_template_minus_score,
                        "bob_residual_template_distance_gap": bob_stage.residual_template_distance_gap,
                        "bob_readout_agreement": bob_stage.readout_agreement.astype(float),
                        "bob_residual_ambiguous": bob_stage.residual_ambiguous.astype(float),
                        "bob_high_confidence_residual": bob_stage.high_confidence_residual.astype(float),
                        "bob_low_confidence_residual": bob_stage.low_confidence_residual.astype(float),
                        "pair_readout_agreement": pair_readout_agreement.astype(float),
                        "pair_residual_ambiguity": pair_residual_ambiguity.astype(float),
                        "pair_high_confidence_residual": pair_high_confidence.astype(float),
                        "pair_low_confidence_residual": pair_low_confidence.astype(float),
                        "mean_confidence_margin": mean_confidence_margin,
                        "mean_projectivity_compatibility": mean_projectivity_compatibility,
                        "bob_branch_stability_score": bob_branch_stability,
                    }
                )
                for rule in ALL_READOUT_RULES:
                    outcomes = alice_stage.outcomes[rule]
                    frame[f"alice_outcome_{rule}"] = outcomes
                    frame[f"alice_valid_{rule}"] = alice_stage.valid[rule].astype(float)
                    frame[f"rule_role_{rule}"] = rule_role(rule)
                for rule in ALL_READOUT_RULES:
                    outcomes = bob_stage.outcomes[rule]
                    frame[f"bob_outcome_{rule}"] = outcomes
                    frame[f"bob_valid_{rule}"] = bob_stage.valid[rule].astype(float)

                trial_frames.append(frame)
                combo_id += 1

    trials = pd.concat(trial_frames, ignore_index=True) if trial_frames else pd.DataFrame()
    (
        rule_summary,
        drift_summary,
        correlation_summary,
        residual_agreement_summary,
        gated_summary,
        aligned_support_by_confidence,
        legacy_rule_controls,
    ) = (
        summarize_sequential_trials(trials, gate_thresholds=configs[0].gate_thresholds)
        if (not trials.empty and configs)
        else (pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    )
    chsh_summary = compute_chsh(correlation_summary) if not correlation_summary.empty else pd.DataFrame()

    return SequentialBatchResult(
        trial_metrics=trials,
        rule_summary=rule_summary,
        drift_summary=drift_summary,
        correlation_summary=correlation_summary,
        chsh_summary=chsh_summary,
        residual_agreement_summary=residual_agreement_summary,
        gated_summary=gated_summary,
        aligned_support_by_confidence=aligned_support_by_confidence,
        legacy_rule_controls=legacy_rule_controls,
        initial_states=np.stack(initial_state_blocks) if initial_state_blocks else np.empty((0, 0, 2)),
        post_alice_states=np.stack(post_alice_blocks) if post_alice_blocks else np.empty((0, 0, 2)),
        post_bob_states=np.stack(post_bob_blocks) if post_bob_blocks else np.empty((0, 0, 2)),
        combo_keys=combo_keys,
        run_manifest=run_manifest,
    )
