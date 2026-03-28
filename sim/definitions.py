from __future__ import annotations

from textwrap import dedent

from .config import SequentialGateConfig
from .readout import (
    RULE_CONFIDENCE_WEIGHTED_AGREEMENT,
    RULE_CONTROL_NEGATIVE_PREWINDOW,
    RULE_ENERGY_LOSS_WINNER,
    RULE_LEGACY_DOMINANCE_SHIFT,
    RULE_LEGACY_DOMINANT_POST,
    RULE_RESIDUAL_TEMPLATE_CLASSIFIER,
)

PRIMARY_WINDOW_FRACTION = 0.25
PURE_CLUSTER_THRESHOLD = 0.9
DEFAULT_GATE_THRESHOLDS = SequentialGateConfig()
SIGNALING_THRESHOLD = DEFAULT_GATE_THRESHOLDS.max_bob_drift
OVERFIT_CHSH_THRESHOLD = 1.9


READOUT_RULE_DEFINITIONS: dict[str, dict[str, str]] = {
    RULE_ENERGY_LOSS_WINNER: {
        "role": "headline_primary",
        "state_variables": "Analyzer-basis pre/post coordinates and branch energy losses during the update.",
        "timing": "Post-update centered; uses the update-induced depletion structure.",
        "basis": "Analyzer basis.",
        "logic": dedent(
            """
            Compute branch energy losses
            `E_loss,+ = max(|c_+^pre|^2 - |c_+^post|^2, 0)` and
            `E_loss,- = max(|c_-^pre|^2 - |c_-^post|^2, 0)`.
            Return `+1` when `E_loss,+ >= E_loss,-`, else `-1`.
            """
        ).strip(),
        "ties": "Ties go to `+1` because the implementation uses `>=`.",
    },
    RULE_RESIDUAL_TEMPLATE_CLASSIFIER: {
        "role": "diagnostic_rule",
        "state_variables": "Post-update analyzer-basis state only.",
        "timing": "Post-update only.",
        "basis": "Analyzer basis.",
        "logic": dedent(
            """
            Normalize the post-update analyzer-basis state `u = psi_post / ||psi_post||`.
            Compare it to the ideal residual templates `e_+ = [1, 0]` and `e_- = [0, 1]`
            through absolute template overlaps `s_+ = |<u, e_+>|` and `s_- = |<u, e_->|`.
            Return `+1` when `s_+ >= s_-`, else `-1`.
            """
        ).strip(),
        "ties": "Ties go to `+1` because the implementation uses `>=`.",
    },
    RULE_CONFIDENCE_WEIGHTED_AGREEMENT: {
        "role": "diagnostic_rule",
        "state_variables": "The headline energy-loss outcome, the residual-template outcome, and the residual-template confidence margin.",
        "timing": "Post-update only for the classifier; combines both redesigned rules after the update.",
        "basis": "Analyzer basis.",
        "logic": dedent(
            f"""
            Let `A_E` be the energy-loss winner outcome and `A_R` be the residual-template outcome.
            Let the residual-template confidence margin be `m_R`.
            Return the shared outcome only when `A_E == A_R` and `m_R >= {DEFAULT_GATE_THRESHOLDS.confidence_margin_threshold}`.
            Otherwise emit the sentinel value `0`, interpreted as `ambiguous_residual`.
            """
        ).strip(),
        "ties": "Ambiguous cases are not forced to `+1`; they are marked as `0` and tracked explicitly.",
    },
    RULE_LEGACY_DOMINANT_POST: {
        "role": "legacy_rule",
        "state_variables": "Post-update analyzer-basis branch powers.",
        "timing": "Post-update only.",
        "basis": "Analyzer basis.",
        "logic": "Return `+1` when `|c_+^post|^2 >= |c_-^post|^2`, else `-1`.",
        "ties": "Ties go to `+1` because the implementation uses `>=`.",
    },
    RULE_LEGACY_DOMINANCE_SHIFT: {
        "role": "legacy_rule",
        "state_variables": "Pre-window and post-window analyzer-basis branch powers.",
        "timing": "Uses both pre-window and post-window values.",
        "basis": "Analyzer basis.",
        "logic": "Return `+1` when the post-minus-pre dominance shift is non-negative, else `-1`.",
        "ties": "Ties go to `+1` because the implementation uses `>=`.",
    },
    RULE_CONTROL_NEGATIVE_PREWINDOW: {
        "role": "negative_control",
        "state_variables": "Pre-window analyzer-basis branch powers only.",
        "timing": "Pre-window only.",
        "basis": "Analyzer basis.",
        "logic": "Return `+1` when `|c_+^pre|^2 >= |c_-^pre|^2`, else `-1`.",
        "ties": "Ties go to `+1` because the implementation uses `>=`.",
    },
}


METRIC_DEFINITIONS: dict[str, dict[str, str]] = {
    "residual_agreement_rate": {
        "formula": "Mean over trials of `(alice_energy_outcome == alice_residual_outcome) and (bob_energy_outcome == bob_residual_outcome)`.",
        "normalization": "Binary per trial, averaged to `[0, 1]`.",
        "aggregation": "Mean within a `(rule, window_fraction, gamma_plus, gamma_minus, anisotropy_ratio)` group.",
        "interpretation": "Higher means the energy-based and residual-template readouts tell the same story more often.",
    },
    "residual_ambiguity_rate": {
        "formula": dedent(
            f"""
            Mean over trials of `(alice_or_bob_disagrees) or (alice_or_bob_residual_margin < {DEFAULT_GATE_THRESHOLDS.confidence_margin_threshold})`.
            """
        ).strip(),
        "normalization": "Binary per trial, averaged to `[0, 1]`.",
        "aggregation": "Mean within a sequential group.",
        "interpretation": "Lower is better; high ambiguity means the mechanism is not producing a clean discrete residual story.",
    },
    "mean_confidence_margin": {
        "formula": "Mean over trials of `0.5 * (alice_confidence_margin + bob_confidence_margin)`, where stage confidence is `min(energy_margin, residual_margin)`.",
        "normalization": "Each stage margin is normalized to `[0, 1]`.",
        "aggregation": "Mean within a sequential group.",
        "interpretation": "Higher means the headline and residual-template rules are separated from their decision boundaries.",
    },
    "mean_projectivity_compatibility": {
        "formula": "Mean over trials of `0.5 * (alice_complementary_residual_quality + bob_complementary_residual_quality)`.",
        "normalization": "Uses the single-analyzer complementary residual quality scale `[0, 1]`.",
        "aggregation": "Mean within a sequential group.",
        "interpretation": "Higher means the sequential stages remain compatible with the single-analyzer projective-depletion story.",
    },
    "alice_marginal_drift": {
        "formula": "For fixed `(rule, phiA)`, compute `max(alice_marginal over phiB) - min(alice_marginal over phiB)`. Then take the max over `phiA` within the group.",
        "normalization": "No extra normalization beyond the `[-1, 1]` outcome scale.",
        "aggregation": "Max over local-setting slices inside a sequential group.",
        "interpretation": "Lower is better; this is one half of the no-signaling gate.",
    },
    "bob_marginal_drift": {
        "formula": "For fixed `(rule, phiB)`, compute `max(bob_marginal over phiA) - min(bob_marginal over phiA)`. Then take the max over `phiB` within the group.",
        "normalization": "No extra normalization beyond the `[-1, 1]` outcome scale.",
        "aggregation": "Max over local-setting slices inside a sequential group.",
        "interpretation": "Lower is better; this is the other half of the no-signaling gate.",
    },
    "aligned_same_sign_mass": {
        "formula": "Mean same-sign mass over aligned analyzer rows `phiA = phiB`.",
        "normalization": "Fraction in `[0, 1]`.",
        "aggregation": "Mean over aligned angle rows in a sequential group.",
        "interpretation": "Lower is better for singlet-like aligned support.",
    },
    "aligned_same_sign_mass_high_confidence": {
        "formula": "Mean same-sign mass over aligned rows, restricting to trials labeled `high_confidence_residual`.",
        "normalization": "Fraction in `[0, 1]` over the high-confidence subset.",
        "aggregation": "Mean over aligned rows after high-confidence masking.",
        "interpretation": "Tests whether confidence is actually related to improved aligned support.",
    },
    "mean_branch_stability_score": {
        "formula": "Mean fraction of small deterministic perturbations to Alice's post-state that preserve Bob's headline energy-loss outcome.",
        "normalization": "Two perturbation checks per trial, averaged to `[0, 1]`.",
        "aggregation": "Mean within a sequential group.",
        "interpretation": "Higher means Bob's readout is locally stable rather than knife-edge sensitive.",
    },
    "CHSH_raw": {
        "formula": "`|E_ab - E_abp + E_apb + E_apbp|` using the canonical four setting pairs.",
        "normalization": "Standard CHSH expression.",
        "aggregation": "One value per `(rule, window_fraction, gamma_plus, gamma_minus, anisotropy_ratio)` group.",
        "interpretation": "Secondary only; not meaningful until the hard gates are checked.",
    },
    "CHSH_gated": {
        "formula": "`CHSH_raw` if and only if all hard gates pass, otherwise `NaN`.",
        "normalization": "Same scale as CHSH.",
        "aggregation": "One value per sequential group.",
        "interpretation": "This is the only CHSH value intended for serious ranking after the redesign.",
    },
    "headline_eligible": {
        "formula": f"`all_gates_pass and rule == {RULE_ENERGY_LOSS_WINNER!r}`.",
        "normalization": "Boolean flag.",
        "aggregation": "Per sequential group.",
        "interpretation": "True means the regime survives the redesign's non-CHSH gates and belongs to the headline primary rule.",
    },
}


GATE_DEFINITIONS: dict[str, dict[str, str]] = {
    "max_alice_drift": {
        "default": str(DEFAULT_GATE_THRESHOLDS.max_alice_drift),
        "meaning": "Maximum allowed Alice marginal drift.",
    },
    "max_bob_drift": {
        "default": str(DEFAULT_GATE_THRESHOLDS.max_bob_drift),
        "meaning": "Maximum allowed Bob marginal drift.",
    },
    "max_aligned_same_sign_mass": {
        "default": str(DEFAULT_GATE_THRESHOLDS.max_aligned_same_sign_mass),
        "meaning": "Maximum allowed aligned same-sign mass before the support gate fails.",
    },
    "min_residual_agreement_rate": {
        "default": str(DEFAULT_GATE_THRESHOLDS.min_residual_agreement_rate),
        "meaning": "Minimum required agreement between energy-loss and residual-template readouts.",
    },
    "max_residual_ambiguity_rate": {
        "default": str(DEFAULT_GATE_THRESHOLDS.max_residual_ambiguity_rate),
        "meaning": "Maximum allowed ambiguity rate.",
    },
    "min_projectivity_compatibility": {
        "default": str(DEFAULT_GATE_THRESHOLDS.min_projectivity_compatibility),
        "meaning": "Minimum allowed sequential projectivity compatibility.",
    },
    "confidence_margin_threshold": {
        "default": str(DEFAULT_GATE_THRESHOLDS.confidence_margin_threshold),
        "meaning": "Minimum stage confidence margin used for ambiguity/high-confidence labeling.",
    },
}


FAILURE_MODE_DEFINITIONS: dict[str, dict[str, str]] = {
    "F1_isotropic_nonprojective": {
        "trigger": "`mean_projectivity_score(ani=1.0) < 0.7`.",
        "interpretation": "The isotropic baseline does not show clean projective depletion.",
    },
    "F2_generic_deformation": {
        "trigger": "`branch_loss_mean > 0.05` and `residual_branch_quality < 0.7`.",
        "interpretation": "The state deforms without selecting a clean residual branch.",
    },
    "F3_signaling_regime": {
        "trigger": f"`alice_marginal_drift > {DEFAULT_GATE_THRESHOLDS.max_alice_drift}` or `bob_marginal_drift > {DEFAULT_GATE_THRESHOLDS.max_bob_drift}`.",
        "interpretation": "A sequential group fails the redesigned drift gate.",
    },
    "F4_washout_regime": {
        "trigger": "For `window_fraction >= 0.5`, projectivity drops below `0.8 *` the matching `T/4` baseline at the same anisotropy ratio.",
        "interpretation": "Long windows erase the useful branch-discriminating structure.",
    },
    "F5_overfit_readout": {
        "trigger": f"`CHSH_raw > {OVERFIT_CHSH_THRESHOLD}` and at least one of the drift, residual-coherence, or projectivity gates fails.",
        "interpretation": "The readout is producing attractive pair statistics in a regime that does not survive the redesigned physical trust gates.",
    },
}


def render_readout_rules_markdown() -> str:
    sections = ["# Readout Rules", ""]
    for name, definition in READOUT_RULE_DEFINITIONS.items():
        sections.extend(
            [
                f"## `{name}`",
                "",
                f"- Role: {definition['role']}",
                f"- State variables: {definition['state_variables']}",
                f"- Timing: {definition['timing']}",
                f"- Basis: {definition['basis']}",
                f"- Logic: {definition['logic']}",
                f"- Tie handling: {definition['ties']}",
                "",
            ]
        )
    return "\n".join(sections).strip() + "\n"


def render_metrics_markdown() -> str:
    sections = ["# Metrics, Gates, And Failure Modes", ""]
    sections.extend(["## Gate Thresholds", ""])
    for name, definition in GATE_DEFINITIONS.items():
        sections.extend(
            [
                f"- `{name}` = {definition['default']}: {definition['meaning']}",
            ]
        )
    sections.append("")

    for name, definition in METRIC_DEFINITIONS.items():
        sections.extend(
            [
                f"## `{name}`",
                "",
                f"- Formula: {definition['formula']}",
                f"- Normalization: {definition['normalization']}",
                f"- Aggregation: {definition['aggregation']}",
                f"- Interpretation: {definition['interpretation']}",
                "",
            ]
        )

    sections.extend(["# Failure Modes", ""])
    for name, definition in FAILURE_MODE_DEFINITIONS.items():
        sections.extend(
            [
                f"## `{name}`",
                "",
                f"- Trigger: {definition['trigger']}",
                f"- Interpretation: {definition['interpretation']}",
                "",
            ]
        )
    return "\n".join(sections).strip() + "\n"
