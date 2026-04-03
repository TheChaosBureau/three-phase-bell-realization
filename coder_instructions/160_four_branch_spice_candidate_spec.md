## Four Branch Spice canidate

Build the first four-branch physical/SPICE front-end candidate under the frozen calibrated boundary

## Objective

Design and validate the first **physical/SPICE-style four-branch front-end candidate** that interfaces to the already frozen detector+latch boundary.

This ticket must answer:

1. Can a physical/SPICE-style four-branch front-end produce branch absorbed-power envelopes approximating
   [
   P_k(t)=\Gamma(t),w_k
   ]
   for
   [
   k\in{++, +-, -+, --}?
   ]

2. Do the resulting branch energy fractions match the exact reduced shared-state weights
   [
   w_{++}, w_{+-}, w_{-+}, w_{--}?
   ]

3. With the **frozen calibrated boundary** held fixed, does the end-to-end chain preserve:

   * four-branch winner-law fidelity,
   * correlator fidelity,
   * CHSH fidelity?

This is the first scale-up from the validated two-branch physical front-end candidate to the shared four-branch case.

---

## Background

The project has already established:

* reduced shared 4-mode state model
* exact reduced branch-weight generation
* validated rare-event detector family
* validated winner latch
* validated reduced end-to-end integration
* validated SPICE-facing front-end surrogate
* validated first physical/SPICE-style two-branch front-end candidate
* validated and reproducible frozen calibrated boundary for the physical front-end → detector handoff

The frozen calibrated boundary is:

* export mode: `piecewise:linear:20.0ms`
* gain: `4.0x`
* exposure: `5.0s`

This boundary is now treated as fixed for this ticket.

The next engineering step is therefore to scale the **physical front-end** from the two-branch case to the **four-branch shared-state case**, while keeping the detector/latch boundary unchanged.

---

## Scope

Included:

* first four-branch physical/SPICE-style front-end candidate
* branch voltage/current/power export for four branches
* exact-vs-realized four-branch energy-fraction comparison
* detector+latch handoff using the frozen calibrated boundary
* correlator and CHSH validation
* report and artifacts

Excluded:

* physical detector redesign
* physical latch redesign
* export-mode redesign
* boundary recalibration
* physical drain/closure hardware
* final resonant/shared-core hardware netlist
* post-click closure implementation

---

## Functional requirements

### FR1 — Four-branch front-end realization

Implement a physical/SPICE-style front-end candidate that exports four branches:

* `++`
* `+-`
* `-+`
* `--`

Each branch must have measurable:

* voltage
* current
* instantaneous power
* integrated absorbed energy

### FR2 — Four-branch energy-fraction fidelity

For each benchmark state/analyzer setting, the front-end must produce normalized branch fractions
[
f_k=\frac{E_k}{\sum_j E_j}
]
that approximate the exact reduced-model target weights
[
w_k.
]

### FR3 — Detector-facing export compatibility

The four-branch front-end must export detector-facing branch envelopes consumable by the frozen detector abstraction using the already selected boundary contract.

### FR4 — Frozen calibrated boundary enforcement

The detector+latch boundary must remain fixed at:

* export mode: `piecewise:linear:20.0ms`
* gain: `4.0x`
* exposure: `5.0s`

No per-case retuning.

### FR5 — End-to-end shared-state validation

After handoff into the frozen detector+latch chain, the integrated system must produce:

* empirical four-branch winner frequencies close to exact (w_k)
* empirical correlator close to target
* empirical CHSH close to target

---

## Candidate implementation guidance

Use the mildest four-branch physical/SPICE candidate first.

Preferred first pass:

* SPICE-compatible linear subcircuit with physical ports
* explicit four-branch output ports
* controlled-source / linear-port realization acceptable
* matched branch loads
* explicit measurable branch powers

Do **not** jump straight to a full multi-tank resonant hardware netlist unless it is already straightforward.

The purpose of this ticket is to establish the **four-branch physical front-end boundary**, not the final hardware topology.

---

## Inputs / outputs

### Inputs

* shared reduced state (\Psi_0)
* analyzer settings (a,b)
* benchmark angle sets
* frozen detector params
* frozen latch params
* frozen calibrated boundary settings

### Outputs

* four branch voltage traces
* four branch current traces
* four branch power traces
* four branch integrated energies
* normalized branch fractions
* detector-facing envelope export
* integrated winner frequencies
* empirical correlator
* empirical CHSH

---

## Deliverables

### Code deliverables

* [ ] four-branch physical/SPICE front-end candidate
* [ ] four-branch export interface
* [ ] four-branch detector+latch integration adapter
* [ ] four-branch metrics module
* [ ] four-branch plots module
* [ ] summary report builder
* [ ] tests

### Artifact deliverables

* [ ] `artifacts/physical_front_end_four_branch_candidate/four_branch/`
* [ ] `artifacts/physical_front_end_four_branch_candidate/integration/`
* [ ] `artifacts/physical_front_end_four_branch_candidate/spice_facing/`
* [ ] `artifacts/physical_front_end_four_branch_candidate/summary_report.md`
* [ ] `artifacts/physical_front_end_four_branch_candidate/summary_metrics.json`
* [ ] `artifacts/physical_front_end_four_branch_candidate/summary_metrics.csv`
* [ ] `artifacts/physical_front_end_four_branch_candidate/front_end_candidate_design.md`

### Required design note

* [ ] `front_end_candidate_design.md`

This note must include:

* chosen four-branch topology
* why it was chosen as the first physical/SPICE four-branch candidate
* mapping from topology to branch-power export
* known limitations
* what remains abstract vs physical

---

## Required plots

* [ ] exact vs realized four-branch energy fractions
* [ ] four branch power traces
* [ ] detector-facing exported envelopes
* [ ] exact vs empirical four-branch winner frequencies
* [ ] correlator exact vs empirical
* [ ] CHSH exact vs empirical
* [ ] residual/error summary plot

---

## Quantitative acceptance criteria

### Front-end alone

Across benchmark cases:

* [ ] RMS four-branch energy-fraction error < 0.03
* [ ] max four-branch energy-fraction error < 0.05

### Integrated four-branch chain

With the frozen calibrated boundary:

* [ ] RMS four-branch winner-law error < 0.03
* [ ] max four-branch winner-law error < 0.05

### Correlator

* [ ] correlator RMS error vs target < 0.05

### CHSH

* [ ] CHSH absolute error < 0.1

### Contract discipline

* [ ] no per-case retuning of gain/exposure/export mode
* [ ] detector and latch abstractions remain unchanged

---

## Benchmark cases

### Shared-state benchmark

Use the singlet-like shared state.

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
2. run physical/SPICE front-end candidate
3. compute realized branch fractions
4. export detector-facing branch envelopes
5. run frozen detector+latch chain
6. compute empirical branch winner frequencies
7. compute correlator and CHSH where applicable

---

## Experimental / simulation plan

### Task 1 — Design and document the four-branch candidate

Choose the first four-branch physical/SPICE candidate and document:

* topology
* physical meaning of each branch
* how analyzer dependence is represented
* how branch powers are measured/exported

**Output**

* `front_end_candidate_design.md`

---

### Task 2 — Implement four-branch front-end candidate

Implement the candidate so it exports:

* branch voltages
* branch currents
* branch powers
* branch energies

**Output**

* four-branch summary CSV
* power-trace plots

---

### Task 3 — Validate four-branch energy fractions

For each benchmark case:

* compute exact (w_k)
* compute realized branch fractions (f_k)
* compare errors

**Output**

* exact vs realized fraction plots
* RMS/max error summary

---

### Task 4 — Export detector-facing envelopes

Export branch envelopes using the frozen calibrated boundary contract.

**Output**

* detector-facing envelope files
* interface note under `spice_facing/`

---

### Task 5 — Run integrated detector+latch validation

Feed exported envelopes into the frozen detector+latch chain.

Measure:

* empirical four-branch winner frequencies
* correlator
* CHSH

**Output**

* integration summary CSV
* winner-frequency plot
* correlator plot
* CHSH plot

---

## Tests

Add tests for:

### T1

Four-branch fractions sum to 1 within tolerance.

### T2

Four-branch front-end fractions remain close to exact target weights.

### T3

Detector-facing export is consumable by the frozen detector abstraction.

### T4

Integrated four-branch winner frequencies remain close to exact target weights.

### T5

Correlator and CHSH metrics are computed correctly.

---

## Explicit failure conditions

Reject or iterate on the first four-branch candidate if any of the following occur:

* [ ] four-branch energy fractions deviate too far from exact target weights
* [ ] detector-facing exports are incompatible with the frozen calibrated boundary
* [ ] integrated winner-law error exceeds acceptance
* [ ] correlator or CHSH degrades materially relative to reduced-model expectations
* [ ] the candidate requires undocumented hidden normalization or per-case retuning

---

## Decision gate after this ticket

Proceed to the next phase only if:

1. the four-branch physical/SPICE front-end candidate reproduces branch fractions sufficiently well,
2. the frozen calibrated detector+latch boundary remains valid,
3. correlator and CHSH remain accurate through the full four-branch handoff.

If these pass, the next ticket should be:

**Move from the first four-branch physical/SPICE candidate toward a more explicit resonant/shared-core front-end realization, or begin designing the physical post-click closure/drain path.**

If they fail, iterate on the four-branch physical front-end candidate before touching detector or latch assumptions.

---

## Suggested labels

`research`
`front-end`
`spice`
`four-branch`
`integration`
`high-priority`

---

## Summary

**Build the first four-branch physical/SPICE front-end candidate under the frozen calibrated detector/latch boundary**