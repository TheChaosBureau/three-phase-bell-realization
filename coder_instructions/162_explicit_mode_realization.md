# Explicit mode realization

Move the refined four-branch physical/SPICE front-end toward an explicit resonant/shared-mode realization while preserving the frozen detector/latch boundary

## Objective

Replace the current **reduced 4-state linear shared core** with a more explicit **resonant/shared-mode front-end realization**.

This ticket must answer:

1. Can the internal shared core be realized as a more explicitly resonant/shared-mode linear system rather than a reduced abstract state block?
2. Can that more physical front-end still preserve:

   * four-branch energy-fraction fidelity,
   * winner-law fidelity through the frozen detector+latch boundary,
   * correlator fidelity,
   * CHSH fidelity?
3. Does the new realization provide a credible bridge toward an eventual shared resonant hardware/netlist implementation?

---

## Background

The current refined four-branch candidate already passes all gates:

* RMS four-branch energy-fraction error: **0.002656**
* max four-branch energy-fraction error: **0.004978**
* RMS four-branch winner-law error: **0.009738**
* max four-branch winner-law error: **0.021342**
* correlator RMS error: **0.020687**
* CHSH absolute error: **0.016017**
* mean decisive fraction: **0.935917**

It also improves architectural realism by replacing direct exact-weight assignment with:

* an explicit internal shared 4-state core,
* analyzer-dependent joint output map,
* finite-output branch loads.

So the next abstraction to reduce is the **shared core itself**.

The frozen boundary remains unchanged:

* export mode: `piecewise_envelope:linear:20.0ms`
* gain: `4.0x`
* exposure: `5.0s`

Detector family, latch semantics, and calibrated boundary are fixed.

---

## Scope

Included:

* more explicit resonant/shared-mode front-end realization
* internal shared-mode dynamics or equivalent resonant multiport realization
* four-branch branch-power export
* integration into the frozen detector+latch boundary
* exact-vs-realized branch-fraction comparison
* correlator and CHSH validation
* comparison against the prior refined 4-state candidate

Excluded:

* detector redesign
* latch redesign
* boundary redesign
* post-click drain/closure hardware
* nonlinear closure physics
* final full hardware build

---

## Design intent

Move from:

[
\text{reduced 4-state shared core}
\to
\text{analyzer map}
\to
\text{branch outputs}
]

toward something closer to:

[
\text{explicit resonant/shared-mode realization}
\to
\text{analyzer/readout coupling}
\to
\text{branch outputs}
]

The new front-end must still be linear and SPICE-compatible, but its internal structure should now look more like a shared-mode physical core and less like a generic reduced state-space block.

---

## Candidate implementation directions

Choose one and document why.

### Option A — Explicit modal resonator realization

Implement a linear shared-mode core with identifiable modal structure:

* mode matrix / coupling matrix
* modal preparation near the singlet-like mode
* analyzer/readout acting on that modal state
* branch outputs derived from the resulting physical ports

Preferred first pass.

### Option B — Multiport coupled linear network

Implement a shared multiport network with:

* internal coupled nodes or ports
* explicit analyzer/readout couplers
* branch outputs arising from the coupled network response

Also acceptable.

### Option C — Early LC/coupled-port resonant surrogate

Implement a first-pass resonant network using explicit R/L/C or equivalent coupled-port elements, provided it remains tractable.

Optional but attractive if not too costly.

---

## Functional requirements

### FR1 — Explicit shared-mode or resonant internal structure

The front-end must contain a clearly identifiable internal shared-mode or resonant structure, not just a generic 4-state reduced block.

### FR2 — Four measurable output branches

The front-end must still export four measurable branches:

* `++`
* `+-`
* `-+`
* `--`

Each branch must provide:

* voltage
* current
* instantaneous power
* integrated absorbed energy

### FR3 — Analyzer dependence through physical/shared structure

Analyzer settings ((a,b)) must affect branch outputs through the internal shared core and readout structure, not via direct branch-weight assignment.

### FR4 — Four-branch energy-fraction fidelity

Normalized branch fractions
[
f_k=\frac{E_k}{\sum_j E_j}
]
must remain close to the exact reduced-model target weights (w_k).

### FR5 — Frozen detector boundary compatibility

The detector-facing exports must remain compatible with the frozen boundary:

* export mode: `piecewise_envelope:linear:20.0ms`
* gain: `4.0x`
* exposure: `5.0s`

### FR6 — End-to-end integrated fidelity

Through the frozen detector+latch chain, the front-end must preserve:

* four-branch winner-law fidelity
* correlator fidelity
* CHSH fidelity

---

## Inputs / outputs

### Inputs

* shared prepared state / preparation parameters
* analyzer settings (a,b)
* benchmark angle sets
* frozen detector params
* frozen latch params
* frozen boundary settings

### Outputs

* internal modal/shared-core diagnostics
* branch voltages
* branch currents
* branch powers
* branch energies
* normalized branch fractions
* detector-facing exported envelopes
* integrated winner frequencies
* correlator
* CHSH

---

## Deliverables

### Code deliverables

* [ ] resonant/shared-mode four-branch front-end candidate
* [ ] internal mode/shared-core diagnostics
* [ ] export interface
* [ ] detector+latch integration adapter
* [ ] metrics/plots/report builder
* [ ] tests

### Artifact deliverables

* [ ] `artifacts/physical_front_end_four_branch_resonant/shared_core/`
* [ ] `artifacts/physical_front_end_four_branch_resonant/four_branch/`
* [ ] `artifacts/physical_front_end_four_branch_resonant/integration/`
* [ ] `artifacts/physical_front_end_four_branch_resonant/spice_facing/`
* [ ] `artifacts/physical_front_end_four_branch_resonant/summary_report.md`
* [ ] `artifacts/physical_front_end_four_branch_resonant/summary_metrics.json`
* [ ] `artifacts/physical_front_end_four_branch_resonant/summary_metrics.csv`
* [ ] `artifacts/physical_front_end_four_branch_resonant/front_end_candidate_design.md`
* [ ] `artifacts/physical_front_end_four_branch_resonant/candidate_comparison.csv`

### Required design note

* [ ] `front_end_candidate_design.md`

This note must state:

* chosen resonant/shared-mode architecture
* how it improves physical interpretability relative to the refined 4-state candidate
* how preparation is represented
* how analyzer dependence is represented
* what remains abstract
* what is gained physically

---

## Required plots

* [ ] internal shared-mode / modal diagnostics
* [ ] exact vs realized four-branch energy fractions
* [ ] four branch power traces
* [ ] exact vs empirical four-branch winner frequencies
* [ ] correlator exact vs empirical
* [ ] CHSH exact vs empirical
* [ ] comparison vs prior refined candidate

---

## Quantitative acceptance criteria

### Front-end alone

Across benchmark cases:

* [ ] RMS four-branch energy-fraction error < 0.03
* [ ] max four-branch energy-fraction error < 0.05

### Integrated chain

With frozen boundary:

* [ ] RMS four-branch winner-law error < 0.03
* [ ] max four-branch winner-law error < 0.05

### Correlator

* [ ] correlator RMS error < 0.05

### CHSH

* [ ] CHSH absolute error < 0.1

### Architectural refinement criterion

* [ ] internal structure is recognizably more resonant/shared-mode than the prior refined 4-state core
* [ ] branch outputs are not produced by direct exact-weight assignment
* [ ] the design note clearly explains the realism gain

---

## Benchmark cases

### Shared-state benchmark

Use the same singlet-like shared state or equivalent shared-mode preparation target.

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

For each case:

1. compute exact reduced-model (w_k)
2. run resonant/shared-mode front-end
3. compute realized branch fractions
4. export detector-facing envelopes
5. run frozen detector+latch chain
6. compute empirical winner frequencies
7. compute correlator and CHSH

---

## Experimental / simulation plan

### Task 1 — Choose resonant/shared-mode architecture

Select Option A, B, or C and document why.

**Output**

* `front_end_candidate_design.md`

### Task 2 — Implement internal shared-mode core

Implement the front-end with enough internal diagnostics to show branch outputs arise from a shared resonant/mode structure.

**Output**

* internal mode/state summaries
* shared-core diagnostic artifacts

### Task 3 — Validate four-branch energy fractions

Compare realized branch fractions to exact (w_k).

**Output**

* fraction comparison CSV/plots
* RMS/max error summary

### Task 4 — Export detector-facing envelopes

Export branch envelopes under the frozen calibrated boundary.

**Output**

* `spice_facing_interface.md`
* example exported envelope files

### Task 5 — Integrated detector+latch validation

Run the resonant/shared-mode front-end through the frozen detector+latch chain.

**Output**

* integration summary CSV
* winner-frequency plot
* correlator plot
* CHSH plot

### Task 6 — Compare to prior refined candidate

Compare against the prior explicit 4-state shared-core candidate on:

* front-end fraction error
* winner-law error
* correlator error
* CHSH error
* architectural realism gain

**Output**

* `candidate_comparison.csv`
* comparison section in summary report

---

## Tests

Add tests for:

### T1

Four-branch fractions sum to 1 within tolerance.

### T2

Resonant/shared-mode candidate remains close to exact target weights.

### T3

Detector-facing export remains compatible with frozen boundary.

### T4

Integrated winner-law metrics remain within acceptance.

### T5

Correlator and CHSH metrics remain within tolerance.

### T6

The implementation is not reducible to trivial direct exact-weight assignment.

---

## Explicit failure conditions

Reject or iterate if any of the following occur:

* [ ] energy-fraction fidelity degrades beyond acceptance
* [ ] integrated winner-law fidelity degrades beyond acceptance
* [ ] correlator or CHSH materially degrades
* [ ] the supposed resonant/shared-mode core is still effectively a disguised exact-weight mapper
* [ ] detector-boundary compatibility breaks under the frozen contract

---

## Decision gate after this ticket

Proceed only if:

1. the resonant/shared-mode candidate remains quantitatively accurate,
2. the frozen detector/latch boundary remains valid,
3. the architecture is meaningfully more physical than the prior refined candidate.

If these pass, the next ticket should be either:

* **begin specifying the physical post-click closure/drain path**, or
* **move one step deeper toward an explicit resonant LC/coupled-port implementation**, depending on which boundary is then most constraining.

If they fail, iterate on the shared-core realization before moving on.

---

## Suggested labels

`research`
`front-end`
`four-branch`
`shared-core`
`resonant`
`spice`
`integration`
`high-priority`

---

## Summary

**Refine the four-branch front-end into a more explicit resonant/shared-mode realization while preserving the frozen calibrated detector/latch boundary**