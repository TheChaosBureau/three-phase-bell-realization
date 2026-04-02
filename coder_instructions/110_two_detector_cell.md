## Two-cell detector characterization rig for rare-event linear-hazard validation

## Objective

Implement and characterize a **two-cell detector test rig** to validate the detector-layer hypothesis before any SPICE or shared-core integration.

The rig must answer two questions:

1. Does one detector cell exhibit a usable rare-event operating window with
   [
   \lambda(P)\approx \lambda_{\text{dark}}+\alpha P
   ]
   over a calibrated absorbed-power range?

2. When two matched cells compete, does first-click winner frequency satisfy
   [
   P(\text{cell 1 wins})\approx \frac{P_1}{P_1+P_2},?
   ]

This is the gate for moving on to physical closure/latch design and later SPICE integration.

---

## Background

The linear front-end work already gives exact branch weights / energy fractions. The missing step is the detector layer: discrete one-click outcomes require a detector model beyond linear resonant energy partition.

The reduced simulations support a **shot-trigger / rare-event nucleation** detector family and reject slow accumulator-style mechanisms. This ticket is to test that detector hypothesis experimentally in the smallest viable rig: **two matched detector cells** and a calibrated power-splitting input.

---

## Scope

This ticket covers:

* one candidate detector-cell schematic
* one two-cell benchtop test rig
* single-cell characterization
* two-cell matching characterization
* two-branch first-click race experiment
* plots/tables summarizing detector viability

This ticket does **not** cover:

* four-branch shared-core build
* zero-sequence/common-mode closure implementation
* SPICE model of the full apparatus
* final hardware front-end realization
* entanglement-scale experiments

---

## Deliverables

### Hardware / schematic deliverables

* [ ] detector-cell schematic candidate
* [ ] two-cell test-rig block diagram
* [ ] parts list / BOM
* [ ] biasing and reset scheme
* [ ] calibrated input-drive setup description

### Measurement deliverables

* [ ] dark-count characterization
* [ ] rate-vs-power calibration
* [ ] pulse-shape characterization
* [ ] dead-time / reset characterization
* [ ] branch-to-branch matching characterization
* [ ] two-branch first-click race data

### Artifacts

* [ ] `artifacts/detector_rig/single_cell/`
* [ ] `artifacts/detector_rig/two_cell/`
* [ ] `artifacts/detector_rig/race/`
* [ ] summary markdown report
* [ ] CSV/JSON summaries
* [ ] plots

---

## Functional requirements

### FR1 — Detector cell operating regime

The detector cell must support a **rare-event metastable regime**:

* no self-oscillation
* no deterministic switching at nominal bias
* stochastic clicks at low signal
* clean output pulse per trigger

### FR2 — Linear-hazard calibration

There must exist an operating range such that
[
\lambda(P)\approx \lambda_{\text{dark}}+\alpha P
]
fits measured click-rate data with acceptable residuals.

### FR3 — One pulse per event

A successful nucleation event must produce:

* one clean digital pulse
* no double triggers
* repeatable reset behavior

### FR4 — Two-cell matching

Two nominally identical cells must be matchable closely enough that branch bias is not dominated by detector mismatch.

### FR5 — Race-law fidelity

When two cells are driven simultaneously with calibrated powers (P_1,P_2), the first-click winner frequencies must approximately satisfy
[
P(\text{cell 1 wins})\approx \frac{P_1}{P_1+P_2}.
]

---

## Quantitative acceptance criteria

### Single-cell acceptance

* [ ] identifiable rare-event operating point exists
* [ ] (\lambda(P)) fit residual < 5% over chosen operating window
* [ ] dark count rate (\lambda_{\text{dark}}) is small compared to nominal signal-trigger rate
* [ ] pulse output is clean and one-shot
* [ ] reset/dead time is measurable and stable

### Two-cell matching acceptance

* [ ] gain mismatch (\alpha_i) between cells (\le 2%) after trimming/calibration, or explicitly quantified if not achieved
* [ ] dark-count mismatch is small and reported
* [ ] pulse timing mismatch is characterized

### Two-branch race acceptance

Across benchmark splits:

* [ ] (0.50/0.50)
* [ ] (0.60/0.40)
* [ ] (0.70/0.30)
* [ ] (0.75/0.25)

winner frequencies track
[
\frac{P_1}{P_1+P_2}
]
with RMS error < 0.05 in the first pass, stretch target < 0.02.

---

## Experimental plan

### Task 1 — Select one detector-cell candidate

Pick one candidate detector cell with the intended behavior:

* matched absorber/input
* metastable or avalanche-like internal element
* digital pulse output
* reset input or reset procedure

**Output**

* chosen schematic
* rationale for why this candidate best matches rare-event shot-trigger behavior

---

### Task 2 — Build single-cell characterization fixture

Implement one-cell rig with:

* calibrated absorbed-power injection
* adjustable bias
* click counter / timestamp capture
* pulse capture
* reset control

**Output**

* block diagram
* fixture wiring notes
* acquisition procedure

---

### Task 3 — Find rare-event operating point

At near-zero input power:

* sweep bias
* identify:

  * quiet regime
  * rare-event regime
  * unstable/self-firing regime

Pick one or more operating points for the rest of the tests.

**Output**

* operating-point table
* bias-vs-dark-count plot

---

### Task 4 — Dark-count characterization

At fixed operating point:

* record click counts over long windows
* estimate
  [
  \lambda_{\text{dark}}
  ]
* measure repeatability over time

**Output**

* dark-count summary table
* long-run stability plot

---

### Task 5 — Rate-vs-power calibration

Inject a calibrated sequence of absorbed powers (P_k):

* measure click rate at each point
* fit
  [
  \lambda(P)=\lambda_{\text{dark}}+\alpha P
  ]
* compute residuals

**Output**

* (\lambda(P)) plot
* fit coefficients
* residual plot
* accepted linear operating window

---

### Task 6 — Pulse-shape and one-click integrity

Capture pulse waveforms over many events:

* amplitude
* width
* rise time
* double-pulse rate
* timing jitter

**Output**

* pulse overlay plot
* pulse statistics table

---

### Task 7 — Dead-time / reset characterization

Measure:

* dead time after click
* reset recovery time
* repeatability over repeated trigger/reset cycles

**Output**

* dead-time summary
* recovery plot

---

### Task 8 — Duplicate cell and assess matching

Build a second nominally identical detector cell and repeat key measurements:

* (\lambda_{\text{dark}})
* (\alpha)
* pulse timing
* dead time

**Output**

* two-cell comparison table
* mismatch summary

---

### Task 9 — Two-branch race experiment

Drive both cells simultaneously with calibrated branch powers (P_1,P_2).

Benchmark splits:

* (0.50/0.50)
* (0.60/0.40)
* (0.70/0.30)
* (0.75/0.25)

For each split:

* run many trials
* record first-click winner
* compare empirical winner frequency to target

**Output**

* winner-frequency vs target plot
* RMS race-law error
* raw CSV of race outcomes

---

## Data products

### Required CSV/JSON outputs

* [ ] `single_cell_dark_counts.csv`
* [ ] `single_cell_rate_scan.csv`
* [ ] `single_cell_pulse_stats.csv`
* [ ] `single_cell_dead_time.csv`
* [ ] `two_cell_matching.csv`
* [ ] `two_branch_race.csv`
* [ ] `summary_metrics.json`

### Required plots

* [ ] dark-count vs bias
* [ ] rate-vs-power with fit
* [ ] fit residuals
* [ ] pulse overlays
* [ ] dead-time distribution
* [ ] two-cell matching comparison
* [ ] winner frequency vs (P_1/(P_1+P_2))

---

## Explicit failure conditions

The detector candidate should be rejected or revised if any of these occur:

* [ ] no measurable rare-event regime
* [ ] (\lambda(P)) strongly nonlinear over the intended window
* [ ] strong deterministic threshold behavior instead of rare stochastic triggering
* [ ] dark counts too high relative to nominal signal-trigger rate
* [ ] frequent double pulses / ambiguous outputs
* [ ] strong hysteresis or long-memory effects
* [ ] two-cell mismatch dominates the race outcome
* [ ] two-branch race does not track (P_1/(P_1+P_2))

---

## Decision gate after this ticket

Proceed to the next phase **only if** the following are true:

1. a rare-event linear window exists,
2. two-cell matching is acceptable,
3. two-branch first-click race behavior matches the target law well enough.

If those conditions hold, the next ticket should be:

* design and characterize the **common-mode / zero-sequence latch** and then
* integrate that detector chain with the linear front-end before SPICE.

If those conditions do not hold, the next ticket should be:

* swap detector class and repeat characterization.

---

## Suggested labels

`research`
`detector`
`hardware`
`measurement`
`high-priority`

---

## Summary

**Build and validate a two-cell rare-event detector rig with linear hazard and first-click race behavior**
