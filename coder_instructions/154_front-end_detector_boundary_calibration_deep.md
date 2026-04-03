## Calibration Spec

Re-run physical-front-end → detector boundary calibration at high statistics to verify reproducibility of the recovered regime

## Objective

Determine whether the previously recovered physical-front-end → detector operating regime

* export mode: `piecewise:linear:20.0ms`
* gain: `4.0x`
* exposure: `5.0s`

is **actually reproducible** when evaluated at sufficient statistics.

The current “do not proceed” result is not yet trustworthy because it was verified with a very small trial count (`PHYSICAL_FRONT_END_BOUNDARY_CAL_TRIALS=6`) and very low decisive fraction. This ticket must resolve whether the calibration failure is:

1. a genuine instability of the recovered regime, or
2. a low-statistics artifact.

This ticket is a **corrective validation pass**, not a redesign.

---

## Background

Boundary diagnosis previously identified a best physical configuration at:

* gain = **4.00×**
* exposure = **5.000 s**
* winner-law RMS error = **0.000000**
* decisive fraction = **0.083333**

However, the subsequent frozen-boundary calibration, run at low statistics, reported:

* RMS winner-law error = **0.086603**
* max winner-law error = **0.150000**
* mean decisive fraction = **0.055556**

Because the decisive fraction is small and the calibration report was verified at very low trial count, the discrepancy must be resolved before treating the boundary contract as invalid.

---

## Scope

Included:

* high-statistics rerun of the frozen calibrated regime only
* no parameter redesign
* no front-end redesign
* no detector/latch redesign
* no export-mode redesign
* reproducibility check against the previously recovered regime
* uncertainty / confidence summary for winner-law metrics

Excluded:

* four-branch physical expansion
* new gain/exposure search
* new boundary diagnosis logic
* new abstraction assumptions
* topology changes

---

## Functional requirements

### FR1 — Hold the frozen contract fixed

The rerun must use the exact same frozen boundary contract:

* export mode: `piecewise:linear:20.0ms`
* gain: `4.0x`
* exposure: `5.0s`

No per-case retuning is allowed.

### FR2 — Increase statistics substantially

Run enough trials that the decisive-event sample is large enough to meaningfully estimate winner-law fidelity.

At minimum:

* [ ] ( \ge 500 ) trials per benchmark case

Preferred:

* [ ] enough total trials that decisive-event count per benchmark case is comfortably ( \ge 100 )

If decisive fraction remains very low, increase total trials accordingly.

### FR3 — Report decisive-event counts explicitly

For each benchmark case, report:

* total trials
* decisive trials
* decisive fraction
* empirical winner frequencies
* winner-law RMS error
* confidence or uncertainty summary

### FR4 — Compare directly to earlier diagnosis

The report must include a direct side-by-side comparison between:

* previous best-diagnosis regime result
* new high-statistics rerun result

### FR5 — Make a reproducibility decision

At the end, classify the outcome as one of:

#### Outcome A — reproducible

The recovered regime remains good under high-statistics rerun.

#### Outcome B — not reproducible

The earlier best-regime result was a low-statistics fluke.

#### Outcome C — inconclusive

Decisive-event counts remain too low to support a stable conclusion; further operating-point adjustment or trial scaling is needed.

---

## Inputs / outputs

### Inputs

* existing physical front-end candidate
* frozen export mode
* frozen detector params
* frozen latch params
* benchmark two-branch cases
* the previously identified best gain/exposure regime

### Outputs

* high-statistics calibrated-run CSV
* reproducibility comparison table
* decisive-count summary
* uncertainty-aware summary report

---

## Deliverables

### Code deliverables

* [ ] high-statistics rerun driver
* [ ] decisive-count summary module
* [ ] comparison-to-prior-diagnosis report builder

### Artifact deliverables

* [ ] `artifacts/physical_front_end_boundary_repro_check/high_stat_run/`
* [ ] `artifacts/physical_front_end_boundary_repro_check/comparison/`
* [ ] `artifacts/physical_front_end_boundary_repro_check/summary_report.md`
* [ ] `artifacts/physical_front_end_boundary_repro_check/summary_metrics.json`
* [ ] `artifacts/physical_front_end_boundary_repro_check/summary_metrics.csv`

### Required plots

* [ ] calibrated winner-frequency plot with larger trial count
* [ ] decisive-count / decisive-fraction plot by benchmark case
* [ ] comparison plot: earlier best-regime vs high-stat rerun
* [ ] error bars or confidence-interval plot for winner-law error if practical

---

## Quantitative acceptance criteria

### Reproducibility target

Using the frozen calibrated regime:

* [ ] RMS winner-law error < 0.03
* [ ] max winner-law error < 0.05

Stretch target:

* [ ] RMS winner-law error < 0.02

### Minimum evidence target

For each benchmark case:

* [ ] decisive-event count reported explicitly
* [ ] decisive-event count high enough that the reported winner-law error is interpretable

### Decision rule

Proceed only if:

* the recovered regime remains within the acceptable winner-law envelope at high statistics,
* or the report clearly shows that the earlier result was not reproducible.

No ambiguous conclusion should remain.

---

## Benchmark cases

Use the exact same benchmark set as the frozen boundary calibration.

For each case:

1. compute exact target weights
2. run the physical front-end candidate
3. apply frozen gain/exposure
4. run detector+latch handoff
5. compute winner statistics using the larger trial count
6. compare with exact target weights

No case-specific parameter adjustment is allowed.

---

## Experimental / simulation plan

### Task 1 — High-statistics rerun at frozen settings

Run the calibrated boundary contract with substantially higher trial count.

Suggested starting point:

* ( \ge 500 ) trials per benchmark case

Increase further if decisive-event counts remain too small.

**Output**

* `high_stat_run.csv`
* updated winner-frequency plot

---

### Task 2 — Decisive-count summary

For each benchmark case, compute:

* total trial count
* decisive event count
* decisive fraction
* undecided / no-click count

**Output**

* decisive-count summary CSV
* decisive-fraction plot

---

### Task 3 — Compare against previous best regime result

Build a comparison table showing:

* prior diagnosis result
* current rerun result
* differences in RMS error
* differences in decisive fraction

**Output**

* comparison CSV
* comparison plot

---

### Task 4 — Reproducibility classification

At the end of the report, explicitly classify:

* reproducible
* not reproducible
* inconclusive

and justify that classification from the data.

---

## Tests

Add tests for:

### T1

Frozen contract is enforced exactly (no parameter drift).

### T2

Trial-count increase is actually applied and reported.

### T3

Decisive-event counts are included in outputs.

### T4

Summary report classifies reproducibility deterministically.

---

## Explicit failure conditions

This ticket fails only if it still cannot answer whether the recovered regime is reproducible.

Examples:

* [ ] frozen settings were not actually held fixed
* [ ] trial counts remain too small to interpret decisive outcomes
* [ ] decisive-event counts are not reported
* [ ] summary still makes a “do not proceed” claim without adequate statistical support

---

## Decision gate after this ticket

### If Outcome A — reproducible

Resume the original roadmap:

* freeze the boundary contract
* proceed to the next front-end physical scaling step

### If Outcome B — not reproducible

Then the current “do not proceed” stands, and the next ticket should be:

* revisit detector-boundary abstraction assumptions before scaling

### If Outcome C — inconclusive

Open a narrow follow-up:

* increase statistics further or adjust only total exposure budget, not the architecture

---

## Suggested labels

`research`
`front-end`
`boundary`
`calibration`
`reproducibility`
`high-priority`

---

## Summary

**Verify at high statistics whether the recovered physical-front-end → detector operating regime is truly reproducible**
