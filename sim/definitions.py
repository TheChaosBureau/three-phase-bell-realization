from __future__ import annotations

from textwrap import dedent

PRIMARY_WINDOW_FRACTION = 0.25
PURE_CLUSTER_THRESHOLD = 0.9
SIGNALING_THRESHOLD = 0.05
OVERFIT_CHSH_THRESHOLD = 1.9


READOUT_RULE_DEFINITIONS: dict[str, dict[str, str]] = {
    "dominant_pre": {
        "state_variables": "Analyzer-basis pre-window coordinates `(c_+, c_-)`.",
        "timing": "Pre-window only.",
        "basis": "Analyzer basis.",
        "logic": dedent(
            """
            Compute pre-window branch powers `p_+ = |c_+|^2` and `p_- = |c_-|^2`.
            Return `+1` when `p_+ >= p_-`, else `-1`.
            """
        ).strip(),
        "ties": "Ties go to `+1` because the implementation uses `>=`.",
    },
    "dominant_post": {
        "state_variables": "Analyzer-basis post-window coordinates `(c'_+, c'_-)`.",
        "timing": "Post-window only.",
        "basis": "Analyzer basis.",
        "logic": dedent(
            """
            Compute post-window branch powers `p'_+ = |c'_+|^2` and `p'_- = |c'_-|^2`.
            Return `+1` when `p'_+ >= p'_-`, else `-1`.
            """
        ).strip(),
        "ties": "Ties go to `+1` because the implementation uses `>=`.",
    },
    "dominance_shift": {
        "state_variables": "Analyzer-basis pre-window and post-window coordinates.",
        "timing": "Uses both pre-window and post-window values.",
        "basis": "Analyzer basis.",
        "logic": dedent(
            """
            Compute pre-window dominance `d = |c_+|^2 - |c_-|^2`.
            Compute post-window dominance `d' = |c'_+|^2 - |c'_-|^2`.
            Return `+1` when `(d' - d) >= 0`, else `-1`.
            """
        ).strip(),
        "ties": "Ties go to `+1` because the implementation uses `>=`.",
    },
    "extracted_energy": {
        "state_variables": "Analyzer-basis pre-window and post-window coordinates.",
        "timing": "Uses both pre-window and post-window values.",
        "basis": "Analyzer basis.",
        "logic": dedent(
            """
            Compute extracted branch energies
            `E_+ = max(|c_+|^2 - |c'_+|^2, 0)` and `E_- = max(|c_-|^2 - |c'_-|^2, 0)`.
            Return `+1` when `E_+ >= E_-`, else `-1`.
            """
        ).strip(),
        "ties": "Ties go to `+1` because the implementation uses `>=`.",
    },
    "residual_classifier": {
        "state_variables": "Analyzer-basis post-window coordinates `(c'_+, c'_-)`.",
        "timing": "Post-window only.",
        "basis": "Analyzer basis.",
        "logic": dedent(
            """
            Compute post-window branch powers `p'_+ = |c'_+|^2` and `p'_- = |c'_-|^2`.
            Return `+1` when `p'_+ >= p'_-`, else `-1`.
            This is equivalent to choosing the larger post-window normalized branch weight.
            """
        ).strip(),
        "ties": "Ties go to `+1` because the implementation uses `>=`.",
    },
}


METRIC_DEFINITIONS: dict[str, dict[str, str]] = {
    "projectivity_score": {
        "formula": dedent(
            """
            For each trial, find the extracted branch by `argmax(branch_loss_+, branch_loss_-)`.
            The complementary branch is the opposite branch.
            Compute post-window normalized branch weights
            `w'_+ = |c'_+|^2 / (|c'_+|^2 + |c'_-|^2)` and `w'_- = 1 - w'_+`.
            The per-trial complementary residual quality is the post-window weight on the complementary branch.
            `projectivity_score` is the mean complementary residual quality across trials.
            """
        ).strip(),
        "normalization": "Uses normalized post-window branch weights; values are in `[0, 1]`.",
        "aggregation": "Mean across trials for a fixed `(window_fraction, gamma_plus, gamma_minus, anisotropy_ratio, angle_deg)` row.",
        "interpretation": "Higher is more projective-like because the residual mass lands on the branch opposite the depleted branch.",
    },
    "clusterability": {
        "formula": f"`clusterability = mean(residual_purity >= {PURE_CLUSTER_THRESHOLD})`, where `residual_purity = max(w'_+, w'_-)`.",
        "normalization": f"Binary threshold at `{PURE_CLUSTER_THRESHOLD}` per trial, then averaged to `[0, 1]`.",
        "aggregation": "Mean across trials for the row.",
        "interpretation": "Higher means more trials collapse into a clearly dominant residual branch.",
    },
    "residual_branch_quality": {
        "formula": "`residual_branch_quality = mean(max(w'_+, w'_-))`.",
        "normalization": "Uses normalized post-window branch weights; values are in `[0.5, 1]` for nonzero states.",
        "aggregation": "Mean across trials.",
        "interpretation": "Higher means cleaner branch purity after the damping window.",
    },
    "branch_loss_mean": {
        "formula": "`branch_loss_mean = mean(branch_loss_+ + branch_loss_-)`, with `branch_loss_± = max(|c_±|^2 - |c'_±|^2, 0)`.",
        "normalization": "No additional normalization beyond the source-state normalization.",
        "aggregation": "Mean total extracted energy across trials.",
        "interpretation": "Higher means the analyzer removed more norm/energy during the window.",
    },
    "dominance_mean": {
        "formula": "`dominance_mean = mean(abs(w'_+ - w'_-))`.",
        "normalization": "Uses normalized post-window branch weights; values are in `[0, 1]`.",
        "aggregation": "Mean across trials.",
        "interpretation": "Higher means stronger post-window branch asymmetry.",
    },
    "alice_marginal_drift": {
        "formula": dedent(
            f"""
            For each fixed `(rule, window_fraction, anisotropy_ratio, phiA)`, compute Alice's marginal mean
            across Bob settings. The per-`phiA` drift is `max(alice_marginal) - min(alice_marginal)`.
            `alice_marginal_drift` is the maximum of that quantity over all `phiA` values in the group.
            """
        ).strip(),
        "normalization": "No normalization beyond the `[-1, 1]` outcome scale.",
        "aggregation": "Max over remote-angle spread, then max over local settings.",
        "interpretation": f"Lower is better; values above `{SIGNALING_THRESHOLD}` are treated as a signaling warning.",
    },
    "bob_marginal_drift": {
        "formula": dedent(
            f"""
            For each fixed `(rule, window_fraction, anisotropy_ratio, phiB)`, compute Bob's marginal mean
            across Alice settings. The per-`phiB` drift is `max(bob_marginal) - min(bob_marginal)`.
            `bob_marginal_drift` is the maximum of that quantity over all `phiB` values in the group.
            """
        ).strip(),
        "normalization": "No normalization beyond the `[-1, 1]` outcome scale.",
        "aggregation": "Max over remote-angle spread, then max over local settings.",
        "interpretation": f"Lower is better; values above `{SIGNALING_THRESHOLD}` are treated as a signaling warning.",
    },
    "aligned_same_sign_mass": {
        "formula": "`aligned_same_sign_mass = mean(same_sign_mass)` over aligned pairs where `phiA = phiB`.",
        "normalization": "Each aligned pair contributes a fraction in `[0, 1]`.",
        "aggregation": "Mean over aligned angle rows within a `(rule, window_fraction, anisotropy_ratio)` group.",
        "interpretation": "Lower is more singlet-like; high aligned same-sign leakage is a warning sign.",
    },
    "aligned_anti_mass": {
        "formula": "`aligned_anti_mass = mean(anti_sign_mass)` over aligned pairs where `phiA = phiB`.",
        "normalization": "Each aligned pair contributes a fraction in `[0, 1]`.",
        "aggregation": "Mean over aligned angle rows within a `(rule, window_fraction, anisotropy_ratio)` group.",
        "interpretation": "Higher is more singlet-like because aligned analyzers prefer opposite outcomes.",
    },
    "sequential_projectivity_compatibility": {
        "formula": dedent(
            """
            For each `(phiA, phiB)` pair, compute
            `0.5 * (mean(alice_complementary_residual_quality) + mean(bob_complementary_residual_quality))`.
            """
        ).strip(),
        "normalization": "Uses the same `[0, 1]` complementary-quality scale as the single-analyzer projectivity score.",
        "aggregation": "Mean over trials for a fixed `(window_fraction, anisotropy_ratio, phiA, phiB)` pair.",
        "interpretation": "Higher means the sequential state updates remain compatible with the single-analyzer projective-branch story.",
    },
    "no_signaling_flag": {
        "formula": f"`alice_marginal_drift <= {SIGNALING_THRESHOLD}` and `bob_marginal_drift <= {SIGNALING_THRESHOLD}`.",
        "normalization": "Boolean flag.",
        "aggregation": "Evaluated per `(rule, window_fraction, anisotropy_ratio)` group, then repeated across its rows in the audit table.",
        "interpretation": "True means the current audit thresholds do not indicate signaling.",
    },
    "overfit_flag": {
        "formula": dedent(
            f"""
            `overfit_flag = (CHSH > {OVERFIT_CHSH_THRESHOLD}) and`
            `((alice_marginal_drift > {SIGNALING_THRESHOLD}) or (bob_marginal_drift > {SIGNALING_THRESHOLD}))`.
            """
        ).strip(),
        "normalization": "Boolean flag.",
        "aggregation": "Evaluated per `(rule, window_fraction, anisotropy_ratio)` group, then repeated across its rows in the audit table.",
        "interpretation": "True means the strongest sequential signal in the group is accompanied by explicit marginal drift and should be treated as likely overfit/signaling-driven.",
    },
}


FAILURE_MODE_DEFINITIONS: dict[str, dict[str, str]] = {
    "F1_isotropic_nonprojective": {
        "trigger": "`mean_projectivity_score(ani=1.0) < 0.7`.",
        "interpretation": "The isotropic baseline does not exhibit clean projective residual branching.",
    },
    "F2_generic_deformation": {
        "trigger": "`branch_loss_mean > 0.05` and `residual_branch_quality < 0.7` for at least one single-analyzer row.",
        "interpretation": "The state deforms and loses norm, but not toward a clean residual branch.",
    },
    "F3_signaling_regime": {
        "trigger": f"`alice_marginal_drift > {SIGNALING_THRESHOLD}` or `bob_marginal_drift > {SIGNALING_THRESHOLD}` for at least one sequential group.",
        "interpretation": "Remote settings visibly move local marginals under the current audit threshold.",
    },
    "F4_washout_regime": {
        "trigger": "For `window_fraction >= 0.5`, projectivity drops below `0.8 *` the corresponding `T/4` baseline for the same anisotropy ratio.",
        "interpretation": "Long windows erase useful branch-discriminating structure.",
    },
    "F5_overfit_readout": {
        "trigger": dedent(
            f"""
            A sequential group satisfies `CHSH > {OVERFIT_CHSH_THRESHOLD}` and at least one of:
            `alice_marginal_drift > {SIGNALING_THRESHOLD}`,
            or `bob_marginal_drift > {SIGNALING_THRESHOLD}`.
            """
        ).strip(),
        "interpretation": "The readout appears to amplify attractive pair statistics in a regime that is not trustworthy on state-level diagnostics.",
    },
}


def render_readout_rules_markdown() -> str:
    sections = ["# Readout Rules", ""]
    for name, definition in READOUT_RULE_DEFINITIONS.items():
        sections.extend(
            [
                f"## `{name}`",
                "",
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
    sections = ["# Metrics And Failure Modes", ""]
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
