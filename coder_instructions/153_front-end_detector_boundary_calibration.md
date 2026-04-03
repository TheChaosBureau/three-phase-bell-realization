## Front-End Detector Boundary Calibration

Calibrate the physical-front-end → detector boundary to the recovered operating regime and re-run handoff validation

## Objective

Freeze and validate a **calibrated boundary contract** between the first physical/SPICE front-end candidate and the frozen detector+latch abstraction.

The boundary-diagnosis ticket classified the current issue as a **regime mismatch**, not a front-end failure and not a detector-theory failure. This ticket must turn that diagnosis into a stable calibrated operating point for the handoff.

This ticket must answer:

1. Can the physical front-end be coupled to the frozen detector abstraction using a fixed calibrated gain/exposure regime?
2. Does that calibrated regime preserve winner-law fidelity across the benchmark cases without per-case retuning?
3. Is the recovered regime broad enough to treat as a stable engineering operating window rather than a fragile coincidence?

---

## Background

The boundary diagnosis found:

* classification: `regime mismatch`
* recommended next ticket: calibrate the physical-front-end → detector boundary and re-run handoff validation

Recovered best physical configuration:

* gain: **4.00×**
* exposure: **5.000 s**
* winner-law RMS error: **0.000000**
* winner-law max error: **0.000000**
* decisive fraction: **0.083333**
* mean expected click count: **0.038111**

This strongly suggests the physical front-end topology is acceptable and that the dominant issue is simply the detector-boundary operating regime.

The current export mode from ticket 151 remains fixed for this ticket:

* `piecewise:linear:20.0ms`

The detector family and latch abstraction also remain frozen.

---

## Scope

Included:

* calibration of detector-boundary gain
* calibration of exposure / trial window
* re-validation of handoff with calibrated settings
* local robustness sweeps around calibrated point
* frozen calibration note for future SPICE/hardware work

Excluded:

* front-end topology redesign
* detector-family redesign
* latch redesign
* export mode redesign
* four-branch physical expansion
* physical detector/latch/drain hardware

---

## Functional requirements

### FR1 — Freeze one calibrated handoff regime

Select one detector-boundary operating point defined by:

* trace gain scaling (g)
* detector exposure / trial window (T)
* any detector-side sampling parameters required by the frozen abstraction

The regime must be documented as the default physical-front-end → detector boundary contract.

### FR2 — Preserve benchmark winner law

Using the calibrated regime, re-run the benchmark two-branch handoff validation and verify that winner frequencies track the exact target weights.

### FR3 — Demonstrate local robustness

Show that small perturbations around the calibrated regime do not immediately destroy the handoff.

At minimum, sweep:

* gain around the calibrated value
* exposure around the calibrated value

### FR4 — Freeze the boundary note

Write a short note that records:

* selected export mode
* selected gain and exposure
* exact detector parameter set
* exact latch assumptions
* semantics of the boundary signals
* intended use in future SPICE/hardware phases

---

## Inputs / outputs

### Inputs

* existing physical front-end candidate outputs
* export mode fixed to `piecewise:linear:20.0ms`
* frozen detector parameter set
* frozen latch abstraction
* benchmark two-branch cases
* boundary-diagnosis results

### Outputs

* calibrated handoff parameter set
* benchmark winner-law validation under calibrated settings
* robustness sweeps around calibrated point
* frozen calibration note
* summary report and metrics

---

## Deliverables

### Code deliverables

* [ ] calibrated handoff driver
* [ ] gain/exposure local sweep driver
* [ ] recalibrated handoff validation runner
* [ ] summary report builder
* [ ] frozen calibration note writer

### Artifact deliverables

* [ ] `artifacts/physical_front_end_boundary_calibration/calibrated_run/`
* [ ] `artifacts/physical_front_end_boundary_calibration/local_gain_sweep/`
* [ ] `artifacts/physical_front_end_boundary_calibration/local_exposure_sweep/`
* [ ] `artifacts/physical_front_end_boundary_calibration/frozen_boundary_note.md`
* [ ] `artifacts/physical_front_end_boundary_calibration/summary_report.md`
* [ ] `artifacts/physical_front_end_boundary_calibration/summary_metrics.json`
* [ ] `artifacts/physical_front_end_boundary_calibration/summary_metrics.csv`

### Required plots

* [ ] winner-law error vs gain near calibrated point
* [ ] winner-law error vs exposure near calibrated point
* [ ] decisive fraction vs gain
* [ ] decisive fraction vs exposure
* [ ] calibrated exact vs empirical winner-frequency plot

---

## Quantitative acceptance criteria

### A. Calibrated handoff validation

Using the selected calibrated point:

* [ ] RMS winner-law error < 0.03
* [ ] max winner-law error < 0.05

Stretch target:

* [ ] RMS winner-law error < 0.02

### B. Stability around calibrated point

Under local perturbations of gain and exposure:

* [ ] no catastrophic collapse in decisive fraction
* [ ] no abrupt branch bias
* [ ] winner-law error remains acceptably bounded over a documented neighborhood

This does not require perfect flatness, but it must show the calibrated regime is not a single-point artifact.

### C. Boundary-note completeness

The frozen boundary note must include:

* [ ] selected export mode
* [ ] selected gain
* [ ] selected exposure
* [ ] exact detector params
* [ ] exact latch timing assumptions
* [ ] meaning of `winner_index` / `winner_valid`
* [ ] explicit statement that reset/re-arm remain external trial-boundary operations

---

## Benchmark cases

Use the same benchmark two-branch cases already used in:

* physical front-end candidate validation
* handoff refinement
* boundary diagnosis

For each case:

1. compute exact target weights
2. run physical front-end candidate
3. apply fixed calibrated gain/exposure
4. run detector+latch handoff
5. compare empirical winner frequencies to exact weights

No per-case tuning is allowed.

---

## Experimental / simulation plan

### Task 1 — Freeze candidate calibrated point

Start from the best physical configuration found in boundary diagnosis:

* gain = **4.00×**
* exposure = **5.000 s**

Re-run the benchmark set and confirm the recovered performance persists.

**Output**

* calibrated run summary CSV
* exact vs empirical winner-frequency plot

---

### Task 2 — Local gain sweep

Sweep gain around the calibrated point, for example:

* 3.0×
* 3.5×
* 4.0×
* 4.5×
* 5.0×

Record:

* RMS winner-law error
* max winner-law error
* decisive fraction
* branch bias summary

**Output**

* local gain sweep CSV
* gain sensitivity plot

---

### Task 3 — Local exposure sweep

Sweep exposure around the calibrated point, for example:

* 3.0 s
* 4.0 s
* 5.0 s
* 6.0 s
* 7.0 s

Record:

* RMS winner-law error
* max winner-law error
* decisive fraction

**Output**

* local exposure sweep CSV
* exposure sensitivity plot

---

### Task 4 — Freeze boundary contract

Write `frozen_boundary_note.md` documenting the calibrated boundary.

This note must include:

#### Selected export mode

* `piecewise:linear:20.0ms`

#### Selected gain/exposure

* chosen calibrated values from this ticket

#### Detector reference

* frozen detector family
* exact detector parameter set

#### Latch reference

* input delay
* tie window
* settle time
* priority semantics

#### Output semantics

* `winner_index`
* `winner_valid`

#### Reset semantics

* reset/re-arm are external trial-boundary operations

---

### Task 5 — Recommendation for next phase

At the end of the report, recommend one of:

#### Outcome A — proceed

Boundary is now calibrated and stable enough to support the next phase.

#### Outcome B — proceed cautiously

Boundary works but requires narrow operating tolerances; document them explicitly.

#### Outcome C — do not proceed

Recovered regime is too fragile; revisit abstraction before scaling.

---

## Tests

Add tests for:

### T1

Calibrated point reproduces acceptable winner-law error.

### T2

Local gain sweep executes and reports monotone/consistent metrics.

### T3

Local exposure sweep executes and reports consistent metrics.

### T4

Frozen boundary note is generated and contains required fields.

---

## Explicit failure conditions

Do not proceed to the next phase if any of the following occur:

* [ ] the recovered calibrated point cannot be reproduced
* [ ] benchmark winner-law fidelity only works with per-case tuning
* [ ] local perturbations collapse decisive fraction or introduce strong branch bias
* [ ] no stable calibrated neighborhood can be identified
* [ ] the boundary note cannot be written as a single consistent contract

---

## Decision gate after this ticket

Proceed to the next phase only if:

1. one fixed calibrated regime works across the benchmark set,
2. the regime is locally stable enough to document,
3. the physical-front-end → detector boundary can now be frozen as an engineering contract.

If these pass, the next ticket should be:

**Extend the calibrated physical/SPICE front-end candidate toward either a four-branch physical candidate or a more explicit resonant front-end realization, while keeping the frozen detector+latch boundary fixed.**

If they fail, revisit detector-boundary abstraction assumptions before scaling.

---

## Suggested labels

`research`
`front-end`
`detector`
`calibration`
`boundary`
`high-priority`

---

## Summary

**Calibrate and freeze the physical-front-end → detector boundary operating regime before further SPICE/front-end scaling**
