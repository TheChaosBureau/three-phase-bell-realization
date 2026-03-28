# Follow-up Spec

**Project:** Verification Artifact Expansion for Anisotropic-Damping Modal Simulator
**Purpose:** Provide the audit trail needed to evaluate whether the current simulator is genuinely showing emergent projective behavior, or whether the strongest sequential results are being driven by readout artifacts or hidden signaling.

---

## 1. Goal

The current summary is enough to show that the anisotropic-damping-first direction is promising, but not enough to validate the sequential mechanism.

The next deliverable is **not a new simulator**.
It is a **verification expansion** of the current run outputs so the model can be audited properly.

The key concern is that some sequential CHSH values exceed 3.0, while the run also flags:

* signaling regime,
* overfit readout,
* and caution about calling the best sequential structure “sphere-like” without drift comparison.

We need the underlying tables, rule definitions, and diagnostics to determine whether the sequential results are meaningful or artifacts.

---

## 2. Required deliverables

Please provide all of the following.

### D1. Full sequential results table

Export the **complete per-combination sequential results table** as CSV and JSON.

Each row must include at minimum:

* `rule`
* `anisotropy_ratio`
* `gamma_plus`
* `gamma_minus`
* `window_fraction`
* `phiA`
* `phiB`
* `E_ab`
* `E_abp`
* `E_apb`
* `E_apbp`
* `CHSH`
* `alice_marginal_drift`
* `bob_marginal_drift`
* `aligned_same_sign_mass`
* `aligned_anti_mass`
* any per-row no-signaling flag
* any per-row overfit flag
* any per-row projectivity metric used in sequential mode

If a row aggregates across settings, document exactly how.

### D2. Full single-analyzer results table

Export the **complete per-combination single-analyzer results table** as CSV and JSON.

Each row must include at minimum:

* `angle_deg`
* `anisotropy_ratio`
* `gamma_plus`
* `gamma_minus`
* `window_fraction`
* `branch_loss_mean`
* `dominance_mean`
* `quality_to_plus`
* `quality_to_minus`
* `residual_branch_quality`
* `projectivity_score`
* `clusterability`
* `total_norm_before`
* `total_norm_after`

### D3. Exact definitions of all readout rules

Provide the exact formula or pseudocode for each readout rule:

* `dominant_pre`
* `dominant_post`
* `dominance_shift`
* `extracted_energy`
* `residual_classifier`

For each rule, specify:

1. which state variables it uses,
2. whether it uses pre-window or post-window information,
3. whether it references analyzer-basis or source-basis coordinates,
4. the exact comparison/threshold logic,
5. any tie-breaking or normalization.

### D4. Exact definitions of all metrics

Provide the exact formula or pseudocode for:

* `projectivity_score`
* `clusterability`
* `residual_branch_quality`
* `branch_loss_mean`
* `dominance_mean`
* `alice_marginal_drift`
* `bob_marginal_drift`
* `aligned_same_sign_mass`
* `aligned_anti_mass`
* failure mode triggers F1–F5

For each metric, specify:

1. formula,
2. normalization,
3. aggregation method,
4. interpretation of high/low values.

### D5. Plot artifacts

Provide the plot files already referenced in the summary, plus the underlying plotted data if possible.

Required plots:

* `projectivity_vs_anisotropy`
* `residual_quality_vs_anisotropy`
* `state_clouds_before_after`
* `marginal_drift_vs_remote_angle`
* `correlation_vs_delta`
* `chsh_vs_anisotropy`
* `aligned_same_sign_mass_vs_anisotropy`
* `single_branch_response_vs_angle`

Also provide a small README or manifest that says which dataset each plot was generated from.

### D6. Raw arrays for representative cases

For a small number of representative parameter sets, save raw trial arrays as `.npz` or similar.

Required representatives:

1. best single-analyzer projectivity case
2. isotropic baseline case
3. top sequential CHSH case
4. lowest-drift sequential case
5. one flagged overfit-readout case

Each raw bundle should include, as applicable:

* initial states
* post-Alice states
* post-Bob states
* analyzer-basis coordinates
* extracted energies
* per-trial outcomes

---

## 3. Required diagnostic analysis

Please add the following specific analyses.

### A1. Audit top sequential CHSH rows

For each of the top 10 sequential CHSH rows, provide a diagnostic row/report containing:

* CHSH
* Alice drift
* Bob drift
* aligned same-sign mass
* rule
* anisotropy ratio
* window
* whether the row is flagged signaling
* whether the row is flagged overfit
* a short text note: “likely meaningful”, “likely signaling”, or “likely readout artifact”

### A2. Rule-risk comparison

Provide a summary table comparing the readout rules on:

* average CHSH
* average marginal drift
* average aligned same-sign mass
* average projectivity compatibility
* number of rows flagged by F5_overfit_readout

This is especially important for `dominant_pre`.

### A3. Sequential trustworthiness ranking

Rank parameter/rule combinations by a conservative trust criterion, for example:

* low drift,
* low same-sign leakage at alignment,
* no overfit flag,
* decent projectivity,
* nontrivial CHSH.

The point is to identify the most credible sequential regimes, not just the biggest CHSH.

---

## 4. Key questions this deliverable must answer

The expanded outputs must let us answer these directly:

1. Are the strongest sequential CHSH results real consequences of the damping dynamics, or are they mainly produced by readout design?
2. Which rules are physically meaningful, and which are effectively smuggling the answer in?
3. Is the promising single-analyzer projectivity result genuinely strong under the metric definition used?
4. Is there any sequential regime that is both low-drift and structurally sphere-like?
5. Do the current summaries understate or overstate how close the model is to a plausible bridge mechanism?

---

## 5. Explicit non-goal

Do **not** change the simulation model yet.

At this stage, we are asking for:

* transparency,
* auditability,
* and verification artifacts.

We are **not** yet asking for new mechanism variants or new physics assumptions.

---

## 6. Output organization

Please deliver under a new folder, for example:
`artifacts/sim/verification-audit/`

Suggested structure:

* `tables/`

  * `single_full.csv`
  * `single_full.json`
  * `sequential_full.csv`
  * `sequential_full.json`
  * `rule_comparison.csv`
  * `top_chsh_audit.csv`
* `plots/`
* `raw_cases/`
* `definitions/`

  * `readout_rules.md`
  * `metrics.md`
* `README.md`

---

## 7. One-sentence summary

Provide the full results tables, exact rule/metric definitions, representative raw cases, and targeted audits of the top sequential CHSH rows so we can determine whether the current simulator is showing genuine emergent projective behavior or mostly readout/signaling artifacts.
