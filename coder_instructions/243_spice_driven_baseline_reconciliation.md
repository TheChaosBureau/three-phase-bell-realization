## Title

Reconcile the SPICE-driven robustness baseline against the previously validated SPICE-driven preferred-chain baseline before robustness adjudication

## Objective

Before drawing any conclusion from the SPICE-driven robustness sweep, reconcile the **nominal robustness baseline** with the **previously validated SPICE-driven preferred-chain baseline**.

This ticket must answer:

1. Why does the robustness report’s nominal baseline differ materially from the earlier SPICE-driven preferred-chain result?
2. Are the same:

   * benchmark cases,
   * trial counts,
   * seeds,
   * SPICE trace preprocessing rules,
   * detector-boundary settings,
   * detector parameters,
   * latch parameters,
   * closure/drain parameters,
   * and metric aggregation logic
     actually being used?
3. Can the earlier passing SPICE-driven baseline be reproduced **inside the robustness harness**?

This ticket is diagnostic and corrective. It is **not** a new robustness sweep.

---

## Background

The earlier SPICE-driven preferred-chain result passed with approximately:

* winner-law RMS error: **0.015062**
* correlator RMS error: **0.015408**
* CHSH absolute error: **0.045424**
* mean decisive fraction: **0.996944**
* winner-drain dominance rate: **0.999860**
* energy-accounting pass: **True**

However, the nominal “baseline” reported inside the robustness sweep is materially worse:

* winner-law RMS error: **0.032399**
* correlator RMS error: **0.042699**
* CHSH absolute error: **0.206599**

Because the robustness baseline is already outside the acceptance region, the robustness result cannot yet be treated as a valid final judgment on Stop Level C. The first task is to determine whether the discrepancy arises from:

* baseline drift,
* harness misconfiguration,
* changed preprocessing,
* changed aggregation,
* changed randomization,
* or a genuine instability in the SPICE-driven chain.

---

## Scope

Included:

* side-by-side baseline comparison
* reconciliation of harness configuration with the prior validated SPICE-driven baseline
* reproduction of the earlier passing SPICE-driven result inside the robustness harness
* identification of the exact source of baseline drift

Excluded:

* new robustness sweep across perturbation classes
* detector redesign
* latch redesign
* closure/drain redesign
* front-end redesign
* new SPICE netlist work
* acceptance-threshold changes unless explicitly justified after reconciliation

---

## Frozen reference points for this ticket

### Reference baseline A — validated SPICE-driven preferred-chain result

Use the earlier passing SPICE-driven preferred-chain run as the reference target.

### Reference baseline B — nominal robustness baseline

Use the current robustness nominal baseline as the comparison target.

These two baselines must be reconciled.

### Frozen semantics

Do not change:

* detector boundary nominal settings
* detector family and nominal parameters
* latch semantics
* closure/drain semantics
* benchmark definition
  unless the ticket explicitly identifies a configuration mismatch.

---

## Functional requirements

### FR1 — Full baseline comparison table

Produce a complete side-by-side comparison of the earlier passing SPICE-driven baseline and the robustness nominal baseline, including:

* benchmark cases used
* number of trials
* seeds / RNG behavior
* SPICE netlist version / front-end artifact version
* trace ingestion path
* trace preprocessing / carrier averaging rules
* detector-boundary export settings
* detector parameters
* latch parameters
* closure/drain parameters
* metric aggregation logic

### FR2 — Reproduction inside robustness harness

Run the robustness harness with settings explicitly matched to the earlier passing SPICE-driven baseline and test whether the earlier result can be reproduced within reasonable statistical tolerance.

### FR3 — Root-cause classification

Classify the discrepancy as one of:

* **configuration mismatch**
* **preprocessing mismatch**
* **aggregation mismatch**
* **random/statistical mismatch**
* **true chain instability**
* **other documented cause**

### FR4 — Recommendation for robustness rerun

At the end, state clearly whether the robustness sweep should be:

* re-run unchanged after baseline fix,
* re-run with corrected nominal settings,
* or replaced by a smaller reconciliation-first sweep.

---

## Inputs / outputs

### Inputs

* earlier passing SPICE-driven preferred-chain artifact set
* robustness nominal baseline artifact set
* current robustness harness configuration
* benchmark definitions
* frozen detector/latch/closure settings

### Outputs

* baseline comparison table
* reproduced-or-not reproduction result
* root-cause classification
* corrective recommendation for the robustness phase

---

## Deliverables

### Code / analysis deliverables

* [ ] baseline comparison script
* [ ] robustness-harness reproduction runner
* [ ] root-cause classification helper
* [ ] reconciliation report builder
* [ ] tests

### Artifact deliverables

* [ ] `artifacts/spice_driven_baseline_reconciliation/comparison/`
* [ ] `artifacts/spice_driven_baseline_reconciliation/reproduction/`
* [ ] `artifacts/spice_driven_baseline_reconciliation/summary_report.md`
* [ ] `artifacts/spice_driven_baseline_reconciliation/summary_metrics.json`
* [ ] `artifacts/spice_driven_baseline_reconciliation/summary_metrics.csv`
* [ ] `artifacts/spice_driven_baseline_reconciliation/reconciliation_note.md`

### Required design / reconciliation note

* [ ] `reconciliation_note.md`

This note must include:

* what two baselines were compared
* what settings were identical
* what settings differed
* whether the earlier SPICE-driven baseline could be reproduced inside the robustness harness
* what exact issue caused the drift
* what should be done next

---

## Required plots

* [ ] side-by-side metric comparison plot for the two baselines
* [ ] reproduction run vs earlier SPICE-driven baseline
* [ ] metric-difference breakdown plot
* [ ] configuration-difference summary plot or table if helpful

---

## Quantitative acceptance criteria

### A. Comparison completeness

* [ ] all major baseline settings are compared explicitly
* [ ] no major configuration dimension is left implicit

### B. Reproduction attempt

* [ ] the robustness harness is run with settings matched as closely as possible to the earlier passing SPICE-driven baseline
* [ ] the result is compared numerically to the earlier passing baseline

### C. Root-cause clarity

* [ ] the ticket ends with a specific root-cause classification, not a vague statement

### D. Actionability

* [ ] the ticket states clearly how the robustness sweep should be corrected before further adjudication

This is a diagnostic ticket, so success means clarity and actionability, not necessarily that the two baselines match perfectly.

---

## Experimental / analysis plan

### Task 1 — Extract baseline A and baseline B configurations

Extract all relevant settings and metadata from:

* earlier passing SPICE-driven preferred-chain run
* robustness nominal baseline run

**Output**

* comparison table / CSV

### Task 2 — Compare preprocessing and export pipeline

Audit:

* SPICE trace ingestion
* carrier averaging
* power alignment
* boundary export
* trial aggregation
* metric computation

**Output**

* preprocessing comparison section in report

### Task 3 — Reproduce earlier baseline inside robustness harness

Configure the robustness harness to match the earlier passing SPICE-driven settings as closely as possible and rerun the nominal baseline.

**Output**

* reproduction metrics
* comparison to earlier passing baseline

### Task 4 — Identify root cause

Determine whether the mismatch is caused by:

* configuration drift
* preprocessing drift
* aggregation drift
* low-statistics mismatch
* or genuine instability

**Output**

* root-cause section in report

### Task 5 — Recommend next action

Conclude with one of:

#### Outcome A — baseline reconciled

Earlier passing baseline is reproducible inside the robustness harness. Robustness can now be rerun meaningfully.

#### Outcome B — baseline mismatch found and corrected

A specific mismatch was found; robustness should be rerun with corrected nominal settings.

#### Outcome C — true instability discovered

The discrepancy persists even after reconciliation; robustness concern is real and should be treated as a chain issue.

---

## Tests

Add tests for:

### T1

Baseline comparison artifacts are generated.

### T2

Reproduction run uses explicitly matched settings.

### T3

Summary report includes root-cause classification.

### T4

Reconciliation report includes a concrete recommended next action.

---

## Explicit failure conditions

This ticket fails only if it still cannot explain the discrepancy.

Examples of unacceptable outcomes:

* [ ] no explicit side-by-side baseline comparison is produced
* [ ] no reproduction run is attempted
* [ ] no root-cause classification is given
* [ ] the report still recommends robustness adjudication without reconciling the nominal baseline

---

## Decision gate after this ticket

Proceed to robustness adjudication only if:

1. the earlier passing SPICE-driven baseline is reproduced or its mismatch is explicitly explained,
2. the robustness nominal point is corrected or validated,
3. the project has a trustworthy SPICE-driven baseline from which robustness can be judged.

If these conditions pass, the next ticket should be:

**Re-run the SPICE-driven robustness / non-ideality sweep from the reconciled nominal baseline and define a safe operating window for Stop Level C.**

If they do not pass, treat the baseline discrepancy itself as the main blocker before any Stop Level C claim.

---

## Suggested labels

`research`
`spice`
`robustness`
`baseline`
`reconciliation`
`diagnostics`
`high-priority`

---

## Summary

**Reconcile the SPICE-driven robustness baseline with the previously validated SPICE-driven preferred-chain baseline before making any Stop Level C robustness judgment**
