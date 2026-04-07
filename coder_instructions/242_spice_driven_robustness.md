## spice_driven_robustness

Run a modest SPICE-driven robustness / non-ideality sweep on the preferred chain and quantify operating margins

## Objective

Use the current **SPICE-driven preferred-chain baseline** as the upstream artifact and run a targeted robustness / non-ideality program to determine whether the chain is structurally credible or overly fragile.

This ticket must answer:

1. Does the **SPICE-driven preferred chain** remain quantitatively strong under modest perturbations?
2. Which perturbations are the most dangerous:

   * front-end component tolerances,
   * coupling mismatch,
   * load mismatch,
   * leakage/parasitic variation,
   * frozen detector-boundary variation,
   * closure/drain strength variation?
3. Can the project define a small but honest **safe operating window** for the SPICE-driven chain?

This is the key remaining milestone toward **Stop Level C**.

---

## Background

The current SPICE-driven preferred chain already passes:

* actual ngspice-generated shared front-end traces
* frozen detector boundary
* frozen `shot_trigger` detector
* frozen first-arrival latch
* preferred closure/drain semantics

Current SPICE-driven chain metrics:

* winner-law RMS error: **0.015062**
* winner-law max error: **0.036789**
* correlator RMS error: **0.015408**
* CHSH absolute error: **0.045424**
* mean decisive fraction: **0.996944**
* pre-click transparency RMS shift: **0.002479**
* winner-drain dominance rate: **0.999860**
* energy-accounting pass: **True**

So the chain is now good enough to stop asking “does it work?” and start asking:

> does it still work under modest physical perturbations?

---

## Frozen baseline for this ticket

Do **not** change these except as explicitly varied by the sweep definitions:

### Frozen upstream artifact

* actual ngspice-generated shared front-end traces

### Frozen detector boundary nominal settings

* export mode: `piecewise_envelope:linear:20.0ms`
* gain: `4.0x`
* exposure: `5.0s`

### Frozen detector

* family: `shot_trigger`
* current validated parameter set

### Frozen latch

* first-arrival arbiter
* current timing assumptions

### Frozen closure/drain semantics

* common inhibit rail + winner-gated shunt/resonant drain
* current tuned preferred parameters

All robustness runs must compare back to this baseline.

---

## Scope

Included:

* SPICE-driven robustness sweeps
* modest non-ideality injection
* sensitivity ranking across perturbation classes
* operating-window summary
* comparison to the frozen SPICE-driven baseline

Excluded:

* redesign of the front-end
* detector redesign
* latch redesign
* closure/drain redesign
* new semantics
* full Monte Carlo over every parameter at once
* fabrication/layout concerns

---

## Perturbation classes to sweep

Run at least the following classes.

### Class A — Front-end component tolerances

Apply modest variation to explicit front-end netlist elements, such as:

* R tolerances
* L tolerances
* C tolerances

Suggested levels:

* ±1%
* ±2%
* ±5%

### Class B — Coupling mismatch

Perturb inter-branch / shared-core coupling terms or mutual/coupled-port equivalents.

Suggested levels:

* ±1%
* ±2%
* ±5%

### Class C — Load mismatch

Perturb branch load values / readout loading asymmetrically.

Suggested levels:

* ±1%
* ±2%
* ±5%

### Class D — Leakage / parasitic variation

Perturb shared-leak / parasitic-style terms that affect residual energy flow.

Suggested levels:

* small, moderate, documented values appropriate to the current model

### Class E — Detector-boundary variation

Perturb the frozen boundary modestly:

* gain around `4.0x`
* exposure around `5.0s`

Suggested local sweep:

* gain: `3.5x, 4.0x, 4.5x`
* exposure: `4.0s, 5.0s, 6.0s`

### Class F — Closure/drain strength variation

Perturb the tuned closure/drain parameters modestly:

* inhibit rise / control time constant
* winner drain strength
* loser clamp strength

Only modest local perturbations; do not re-optimize.

---

## Functional requirements

### FR1 — SPICE-driven baseline remains the source

All robustness runs must start from actual SPICE-generated front-end traces or actual SPICE runs under perturbed front-end values.

### FR2 — Metrics are computed uniformly

For each perturbation configuration, compute:

* winner-law RMS error
* winner-law max error
* correlator RMS error
* CHSH absolute error
* decisive fraction
* pre-click transparency shift
* winner-drain dominance rate
* mean loser residual fraction
* completion rate
* energy-accounting balance error

### FR3 — Class-by-class isolation

Perturbation classes should first be studied one at a time before any combined perturbation sampling.

### FR4 — Safe operating window summary

At the end, summarize a modest operating window in which the SPICE-driven chain remains acceptably accurate.

### FR5 — Sensitivity ranking

Rank perturbation classes by how damaging they are to the preferred-chain metrics.

---

## Inputs / outputs

### Inputs

* actual SPICE front-end netlist / trace generation path
* frozen downstream stack
* perturbation class definitions
* benchmark angle cases
* CHSH benchmark set

### Outputs

* per-class sweep results
* sensitivity ranking
* safe operating window summary
* updated comparison to frozen SPICE-driven baseline

---

## Deliverables

### Code / analysis deliverables

* [ ] robustness sweep driver
* [ ] perturbation injectors for each class
* [ ] metrics aggregator
* [ ] sensitivity ranking module
* [ ] summary report builder
* [ ] tests

### Artifact deliverables

* [ ] `artifacts/spice_driven_robustness/front_end_tolerances/`
* [ ] `artifacts/spice_driven_robustness/coupling_mismatch/`
* [ ] `artifacts/spice_driven_robustness/load_mismatch/`
* [ ] `artifacts/spice_driven_robustness/leakage_variation/`
* [ ] `artifacts/spice_driven_robustness/boundary_variation/`
* [ ] `artifacts/spice_driven_robustness/closure_variation/`
* [ ] `artifacts/spice_driven_robustness/summary_report.md`
* [ ] `artifacts/spice_driven_robustness/summary_metrics.json`
* [ ] `artifacts/spice_driven_robustness/summary_metrics.csv`
* [ ] `artifacts/spice_driven_robustness/sensitivity_ranking.csv`
* [ ] `artifacts/spice_driven_robustness/design_note.md`

### Required design note

* [ ] `design_note.md`

This note must include:

* what perturbation classes were used
* what levels were used
* what was held frozen
* which metrics moved the most
* the recommended safe operating window
* what this implies for Stop Level C

---

## Required plots

* [ ] winner-law RMS error vs perturbation level for each class
* [ ] correlator RMS error vs perturbation level
* [ ] CHSH absolute error vs perturbation level
* [ ] decisive fraction vs perturbation level
* [ ] pre-click transparency shift vs perturbation level
* [ ] winner-drain dominance vs perturbation level
* [ ] energy-balance error vs perturbation level
* [ ] sensitivity ranking bar chart
* [ ] safe operating window summary plot

---

## Quantitative acceptance criteria

### A. No catastrophic fragility

Under modest perturbations (roughly ±1–2% in key front-end classes and local detector-boundary/closure perturbations), the chain should remain in the acceptable regime:

* [ ] winner-law RMS error < 0.03
* [ ] max winner-law error < 0.05
* [ ] correlator RMS error < 0.05
* [ ] CHSH absolute error < 0.1

### B. Pre-click stability

* [ ] pre-click transparency shifts remain small under modest perturbations

### C. Post-click stability

* [ ] winner-drain dominance remains true under modest perturbations
* [ ] loser residual fraction remains small
* [ ] completion remains high and well-defined

### D. Energy-accounting stability

* [ ] energy-accounting pass remains true
* [ ] balance errors remain small and documented

### E. Interpretability

* [ ] the report identifies which perturbation class is most dangerous
* [ ] the report identifies at least one documented safe operating window

---

## Benchmark cases

### Shared-state benchmark

Use the current SPICE-driven preferred-chain benchmark preparation.

### Angle benchmarks

At minimum:

* [ ] (a=0^\circ,\ b=0^\circ)
* [ ] (a=45^\circ,\ b=22.5^\circ)
* [ ] (a=0^\circ,\ b=45^\circ)

### CHSH benchmark

Use:
[
a_0=0^\circ,\quad a_1=45^\circ,\quad b_0=22.5^\circ,\quad b_1=-22.5^\circ
]

Run all perturbation classes against this fixed benchmark set.

---

## Experimental / simulation plan

### Task 1 — Freeze the SPICE-driven baseline

Record the current nominal SPICE-driven preferred-chain metrics as the comparison anchor.

**Output**

* baseline metrics file
* baseline comparison note

### Task 2 — Run class-by-class perturbation sweeps

Run each perturbation class independently over the prescribed levels.

**Output**

* per-class CSVs
* per-class plots

### Task 3 — Aggregate and rank sensitivities

Compare metric degradation across perturbation classes.

**Output**

* `sensitivity_ranking.csv`
* ranking plot

### Task 4 — Summarize safe operating window

Identify a modest perturbation window where the chain remains acceptable.

**Output**

* safe-window table
* summary note

### Task 5 — Stop Level C recommendation

At the end, classify the result as one of:

#### Outcome A — Stop Level C achieved

The SPICE-driven chain is accurate and modestly robust.

#### Outcome B — nearly achieved

The SPICE-driven chain works, but one or two perturbation classes remain too fragile.

#### Outcome C — not yet

The SPICE-driven chain is too sensitive to support a strong Stop Level C claim.

**Output**

* conclusion section in `summary_report.md`

---

## Tests

Add tests for:

### T1

Each perturbation class runs and records metrics.

### T2

Metrics remain finite and comparable across sweeps.

### T3

Sensitivity ranking is produced deterministically.

### T4

Safe operating window summary is generated.

### T5

Report clearly distinguishes baseline vs perturbed SPICE-driven runs.

---

## Explicit failure conditions

Reject or iterate if any of the following occur:

* [ ] modest perturbations cause immediate collapse of winner-law / correlator / CHSH behavior
* [ ] pre-click transparency becomes fragile under small perturbations
* [ ] winner-drain dominance fails under modest perturbations
* [ ] energy accounting becomes unstable
* [ ] the report cannot identify any reasonable safe operating window

---

## Decision gate after this ticket

Proceed only if:

1. the SPICE-driven preferred chain remains strong under modest perturbations,
2. a safe operating window can be stated honestly,
3. the resulting package is strong enough to support Stop Level C.

If these pass, the next step should be:

* freeze the SPICE-driven preferred chain as the final Stop Level C baseline, and optionally
* choose whether to continue toward deeper device-level realization or stop.

If they fail, iterate on the most sensitive perturbation class before claiming Stop Level C.

---

## Suggested labels

`research`
`spice`
`robustness`
`non-ideality`
`integration`
`milestone`
`high-priority`

---

## Summary

**Run a modest robustness / non-ideality sweep on the SPICE-driven preferred chain and define a safe operating window for Stop Level C**
