# Simulation Brief

**Project:** Sequential Readout / Update Layer Redesign
**Objective:** Replace the current sequential outcome layer with a **post-update, residual-centered, physically interpretable readout architecture** and audit whether any sequential regime remains credible after hard gating on drift, aligned support, and readout coherence.

---

## 1. Purpose

The current anisotropic-damping simulator produced a promising **single-analyzer projective depletion** result, but the audit showed that the strongest sequential CHSH rows are mainly signaling-driven and/or readout artifacts.

The next task is **not** to optimize CHSH.

The next task is to redesign the **sequential readout/update layer** so that:

* outcomes are derived from **post-update depletion structure**, not pre-window information,
* the residual state is treated as the central object,
* readout coherence is measurable,
* and no sequential regime is considered credible unless it passes strict non-CHSH gates first.

This redesign is intended to determine whether the current mechanism can support a trustworthy sequential bridge at all.

---

## 2. Scope

This task modifies the **sequential layer only**.

Do **not** replace the current single-analyzer anisotropic-damping dynamics.

Do **not** change the source state representation or damping operator unless necessary for compatibility.

Do **not** add Bell-target fitting, collapse rules, or hard-coded joint probabilities.

The scope is:

1. keep the current anisotropic-damping source/update model,
2. redesign how sequential outcomes are assigned,
3. add residual-centered diagnostics,
4. apply hard acceptance gates before CHSH is interpreted,
5. produce new audit tables and plots.

---

## 3. Core question

Can the current anisotropic-damping dynamics, combined with a **physically meaningful post-update readout**, produce sequential pair statistics that are:

* low-drift,
* low same-sign at aligned analyzers,
* coherent across residual-state and energy-based readouts,
* and only then potentially nonclassical-looking?

---

## 4. Current diagnosis motivating this redesign

The previous audit concluded:

* the strongest single-analyzer projectivity result is promising,
* but the strongest sequential CHSH rows are mainly signaling-driven,
* `dominant_pre` is the riskiest rule,
* no sequential regime currently clears the conservative trust screen as both low-drift and sphere-like.

This redesign is intended to eliminate pre-window leakage and test whether any credible sequential structure remains.

---

## 5. Required architectural changes

## 5.1 Remove `dominant_pre` from headline use

`dominant_pre` must be retained only as a **negative control**.

It may still be computed and logged, but it must not appear in:

* best-result tables,
* top-CHSH summaries,
* trust-ranking headlines.

It should be explicitly labeled:

* `control_negative_prewindow`

## 5.2 Make the residual state the primitive sequential object

The sequential pipeline must be organized explicitly as:

1. initial source state (\psi_0)
2. Alice update (\psi_0 \rightarrow \psi_A)
3. Alice readout from post-update quantities
4. residual-state confidence assessment
5. Bob update (\psi_A \rightarrow \psi_B)
6. Bob readout from post-update quantities

The code should make these stages explicit.

## 5.3 Separate update and readout

Refactor so that:

* **update layer** computes state evolution
* **readout layer** assigns discrete outcomes from the evolved state
* **diagnostic layer** compares different readout rules and confidence scores

No readout rule should directly use pre-window quantities as its primary decision variable.

---

## 6. Sequential update model

Assume the existing anisotropic-damping model remains:

[
\psi_A = e^{-D_{\phi_A}T_w}\psi_0
]
[
\psi_B = e^{-D_{\phi_B}T_w}\psi_A
]

The redesign should use the post-Alice and post-Bob states as the basis for outcome assignment and diagnostics.

The simulator may continue to compute branch-basis quantities before and after each update for analysis, but outcome rules must be centered on post-update and/or extracted-energy logic.

---

## 7. Required readout rules

Implement exactly these readout rules for sequential mode.

## Rule R1 — Extracted-energy winner

Primary rule.

For analyzer A, define branch energy losses during the update:

[
E^{\text{loss}}*{A,+} = |c*{A,+}^{\text{pre}}|^2 - |c_{A,+}^{\text{post}}|^2
]
[
E^{\text{loss}}*{A,-} = |c*{A,-}^{\text{pre}}|^2 - |c_{A,-}^{\text{post}}|^2
]

Then assign:
[
A=+1 \text{ if } E^{\text{loss}}*{A,+} > E^{\text{loss}}*{A,-}
]
[
A=-1 \text{ otherwise}
]

Apply the same structure for Bob.

This is the primary headline readout rule.

## Rule R2 — Residual-template classifier

Secondary diagnostic rule.

For analyzer A, compare the post-update state (\psi_A) against ideal analyzer-basis residual templates and assign:

* (A=+1) if (\psi_A) is closer to the (+)-branch residual
* (A=-1) if (\psi_A) is closer to the (-)-branch residual

The exact template definition must be documented.

This rule must be treated as diagnostic and potentially overfit-prone.

## Rule R3 — Confidence-weighted agreement rule

Diagnostic only.

Assign an outcome only when R1 and R2 agree. Otherwise label the trial as:

* `ambiguous_residual`

This rule is not for headline CHSH. It is for measuring coherence between energy-based and residual-based readout.

---

## 8. Required removed/deprioritized rules

The following rules should be removed from headline analysis:

* `dominant_pre` → keep as negative control only
* `dominant_post` → optional legacy comparison only
* `dominance_shift` → optional comparison only
* any rule whose main decision variable is pre-window branch dominance

If these remain in the code, they must be labeled as:

* `legacy_rule`
* `negative_control`
  or equivalent.

---

## 9. New diagnostics to implement

## D1 — Residual agreement rate

For each parameter group, compute the fraction of trials where:

* R1 and R2 produce the same outcome

This is a primary coherence diagnostic.

## D2 — Residual ambiguity rate

Compute the fraction of trials where:

* R1 and R2 disagree, or
* the residual-template classifier has confidence below threshold

This quantifies whether the mechanism is truly discrete or mostly analog/ambiguous.

## D3 — Branch confidence margin

For each analyzer stage, compute a confidence margin such as:
[
\Delta_E = \frac{|E^{\text{loss}}*{+} - E^{\text{loss}}*{-}|}{E^{\text{loss}}*{+} + E^{\text{loss}}*{-} + \epsilon}
]

and/or an analogous residual-template margin.

## D4 — Residual-state confidence gate

Each trial must be labeled:

* `high_confidence_residual`
* `low_confidence_residual`

based on projectivity/purity/confidence thresholds.

Do not silently discard low-confidence trials.

## D5 — Conditional aligned support

At aligned analyzers, compute:

* same-sign mass over all trials
* same-sign mass over high-confidence trials only
* anti-sign mass over all trials
* anti-sign mass over high-confidence trials only

This is essential for testing whether residual confidence is actually related to sphere-like support structure.

## D6 — Sequential branch-stability score

Quantify whether Bob’s outcome is stable under small perturbations to Alice’s post-state.

A local perturbation test is acceptable.

---

## 10. Hard acceptance gates

No sequential regime may be called promising unless it passes all gates below.

## G1 — Drift gate

Alice and Bob marginal drifts must both be below configured thresholds.

Thresholds must be explicit in config.

## G2 — Aligned support gate

Aligned same-sign mass must be below threshold.

Threshold must be explicit.

## G3 — Overfit gate

Any regime flagged as readout-overfit is automatically excluded from headline use.

## G4 — Residual coherence gate

Residual agreement rate must exceed threshold and residual ambiguity rate must be below threshold.

## G5 — Projectivity compatibility gate

Sequential projectivity compatibility must exceed threshold.

Only after G1–G5 are passed may CHSH be used as a serious ranking criterion.

---

## 11. CHSH policy

CHSH is now a **late-stage secondary metric**.

The simulator must:

1. compute CHSH only after the hard gates are evaluated,
2. report gated and ungated CHSH separately,
3. never rank regimes by CHSH alone.

Required outputs:

* `CHSH_raw`
* `CHSH_gated`
* `gates_passed`
* `headline_eligible`

---

## 12. Required outputs

## 12.1 Tables

Produce at minimum:

### `sequential_residual_agreement.csv`

One row per parameter group with:

* rule
* anisotropy_ratio
* gamma_plus
* gamma_minus
* window_fraction
* residual_agreement_rate
* residual_ambiguity_rate
* mean_confidence_margin
* mean_projectivity_compatibility

### `sequential_gated_summary.csv`

One row per parameter group with:

* rule
* anisotropy_ratio
* gamma_plus
* gamma_minus
* window_fraction
* alice_marginal_drift
* bob_marginal_drift
* aligned_same_sign_mass
* aligned_anti_mass
* no_signaling_flag
* overfit_flag
* drift_gate_pass
* aligned_support_gate_pass
* overfit_gate_pass
* residual_coherence_gate_pass
* projectivity_gate_pass
* all_gates_pass
* CHSH_raw
* CHSH_gated
* headline_eligible

### `aligned_support_by_confidence.csv`

For each relevant group:

* same-sign mass (all trials)
* same-sign mass (high-confidence only)
* anti-sign mass (all trials)
* anti-sign mass (high-confidence only)
* number of high-confidence trials
* number of low-confidence trials

### `legacy_rule_controls.csv`

Summary table for deprecated/negative-control rules:

* `dominant_pre`
* `dominant_post`
* `dominance_shift`
  with the same group diagnostics, but clearly labeled control-only.

## 12.2 Raw representative cases

Provide raw-case bundles for:

1. best gated regime, if any
2. lowest-drift regime
3. highest residual-agreement regime
4. top negative-control CHSH regime
5. one regime where projectivity is good but aligned support fails

Each bundle must include per-trial states, branch energies, outcomes, confidence labels, and gate labels.

---

## 13. Required plots

Generate at minimum:

1. `residual-agreement-vs-anisotropy.png`
2. `residual-ambiguity-vs-anisotropy.png`
3. `aligned-support-by-confidence.png`
4. `gated-chsh-vs-anisotropy.png`
5. `drift-vs-anisotropy-by-rule.png`
6. `headline-eligible-regimes.png`
7. `residual-confidence-histograms.png`
8. `legacy-vs-redesigned-rule-comparison.png`

Save the plotted datasets as CSV as well.

---

## 14. README requirements

Add a new README section explaining:

* why `dominant_pre` is now negative-control only
* what the new primary sequential rule is
* what the residual agreement rate means
* what qualifies as a headline-eligible sequential regime
* why CHSH is now secondary to drift/support/coherence gates

---

## 15. Configuration requirements

Add explicit config thresholds for:

* `max_alice_drift`
* `max_bob_drift`
* `max_aligned_same_sign_mass`
* `min_residual_agreement_rate`
* `max_residual_ambiguity_rate`
* `min_projectivity_compatibility`
* `confidence_margin_threshold`

All thresholds must be documented in both:

* machine-readable config
* README summary

---

## 16. Explicit non-goals

Do **not**:

* tune thresholds to maximize CHSH
* reintroduce pre-window readout as a headline method
* hide low-confidence trials
* post-select away bad regimes silently
* alter the source/update dynamics to make the redesign “look better”
* add any rule that directly references both settings unless that dependence comes only through the evolved state

This task is about making the sequential layer more physically trustworthy, not about improving headline violation numbers.

---

## 17. Final questions the coder must answer

The redesigned outputs must answer:

1. Does any post-update readout rule produce a credible sequential regime after hard gating?
2. Do energy-based and residual-based readouts actually agree in promising regimes?
3. Are aligned same-sign outcomes suppressed when residual confidence is high?
4. Does low drift survive once overfit-prone rules are removed from headline use?
5. After this redesign, is there still any evidence of a sphere-like sequential bridge?

---

## 18. One-sentence summary

Redesign the sequential readout layer so outcomes are derived from post-update depletion structure rather than pre-window branch dominance, then gate all sequential claims on drift, aligned support, residual coherence, and projectivity before interpreting CHSH.