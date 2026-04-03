## Spice Front End Design

Design the first physical/SPICE front-end implementation candidate and connect it to the frozen detector+latch abstraction

## Objective

Replace the current behavioral front-end surrogate with the **first physically meaningful linear/SPICE front-end candidate**.

This ticket must answer:

1. Can a real linear circuit candidate produce branch absorbed-power envelopes that approximate
   [
   P_k(t)=\Gamma(t),w_k
   ]
   closely enough for the frozen detector+latch abstraction to remain valid?

2. Does the end-to-end chain
   [
   \text{physical/SPICE front-end}
   \to
   \text{abstract detector}
   \to
   \text{abstract latch}
   \to
   \text{exclusive winner}
   ]
   preserve winner-law fidelity well enough to justify moving on?

3. Is the chosen physical/SPICE front-end candidate a good basis for later extension to the full shared-core hardware?

---

## Background

The following phases are already complete at the reduced level:

* exact branch-weight generation from the linear front-end
* validated rare-event detector family
* validated winner latch
* validated end-to-end reduced integration
* validated SPICE-facing front-end surrogate

The current surrogate front-end reproduces the target branch weights exactly, and its handoff into the detector+latch stack remains accurate, with integrated two-branch and four-branch winner-law errors in the acceptable range. The next step is therefore to replace that surrogate with the simplest **physical/SPICE front-end candidate** while keeping the validated detector+latch abstraction fixed.

This ticket is the first move from “reduced wrapper” to “actual linear circuit candidate.”

---

## Scope

Included:

* first physical/SPICE-compatible front-end candidate
* two-branch implementation first
* branch voltage/current and absorbed-power export
* integration with frozen detector+latch abstraction
* comparison against exact reduced front-end weights
* report and artifacts

Optional, if two-branch passes early:

* first four-branch candidate scaffold

Excluded:

* physical detector SPICE model
* physical latch SPICE model
* post-click drain/closure hardware
* final multi-tank hardware netlist
* nonlinear detector physics
* full physical entanglement-scale implementation

---

## Strategy

Start with the **two-branch front-end first**.

Do not begin with the full four-branch shared-state front-end.

The first candidate should be the simplest physically meaningful linear network that can export branch absorbed-power envelopes for the detector abstraction.

If the two-branch candidate fails, do not proceed to four branches.

---

## Candidate implementation options

The coder may choose one of the following, but must document which is used.

### Option A — SPICE linear subcircuit with physical ports

Use SPICE primitives and/or controlled sources to realize:

* state input / preparation port
* analyzer rotation or equivalent coupling
* two output branches with matched loads
* measurable branch voltages/currents

This is the preferred first pass.

### Option B — Minimal resonant LC implementation

Use a simple linear resonant two-mode network that approximates the required front-end behavior with explicit L/C/R components.

This is acceptable if it is tractable and well-documented.

### Option C — State-space/SPICE bridge

Use a physically interpretable state-space realization wrapped as a SPICE-facing block, with explicit branch output ports.

This is acceptable if the branch outputs remain measurable in circuit terms.

---

## Functional requirements

### FR1 — Two-branch branch-power export

The front-end must export two branch absorbed-power envelopes:
[
P_1(t),;P_2(t)
]
such that
[
P_i(t)\approx \Gamma(t),w_i
]
for benchmark input states/analyzer settings.

### FR2 — Measurable circuit outputs

The front-end must provide:

* branch voltage (v_i(t))
* branch current (i_i(t))
* branch power
  [
  p_i(t)=v_i(t)i_i(t)
  ]
* branch absorbed energy
  [
  E_i^{(\infty)}=\int_0^\infty p_i(t),dt
  ]

### FR3 — Energy-fraction fidelity

Normalized absorbed energies
[
f_i=\frac{E_i}{E_1+E_2}
]
must track the exact target weights (w_i).

### FR4 — Detector handoff compatibility

The exported branch power envelopes must be consumable by the existing detector abstraction without changing the detector or latch contracts.

### FR5 — Benchmark integration

When the physical/SPICE front-end is composed with the frozen detector+latch abstraction, winner frequencies must remain close to the exact front-end target law.

---

## Inputs / outputs

### Inputs

* prepared two-mode state or equivalent front-end preparation parameters
* analyzer setting / basis parameter
* simulation parameters
* matched branch loads

### Outputs

* branch voltages
* branch currents
* branch powers
* branch absorbed energies
* normalized branch energy fractions
* detector-facing branch envelope export
* integrated winner frequencies after detector+latch handoff

---

## Deliverables

### Code deliverables

* [ ] first physical/SPICE two-branch front-end implementation
* [ ] branch export adapter
* [ ] integration driver connecting front-end outputs to detector+latch abstraction
* [ ] metrics module
* [ ] plots module
* [ ] tests

### Artifact deliverables

* [ ] `artifacts/physical_front_end_candidate/two_branch/`
* [ ] `artifacts/physical_front_end_candidate/integration/`
* [ ] `artifacts/physical_front_end_candidate/spice_facing/`
* [ ] `summary_report.md`
* [ ] `summary_metrics.json`
* [ ] `summary_metrics.csv`

### Required design note

* [ ] `front_end_candidate_design.md`
  containing:

  * circuit topology chosen
  * why this was chosen as the first physical/SPICE candidate
  * mapping from circuit behavior to branch-envelope export
  * known limitations

---

## Required plots

* [ ] exact vs physical/SPICE branch energy fractions
* [ ] branch power envelopes (P_1(t), P_2(t))
* [ ] detector-facing envelope export comparison
* [ ] winner frequency vs target after detector+latch handoff
* [ ] residual/error summary plot

---

## Quantitative acceptance criteria

### Two-branch front-end alone

Across benchmark cases:

* [ ] RMS energy-fraction error < 0.03
* [ ] max energy-fraction error < 0.05

### Integrated two-branch chain

After handoff into frozen detector+latch abstraction:

* [ ] RMS winner-law error < 0.03
* [ ] max winner-law error < 0.05

### Stability / consistency

* [ ] no pathological numerical instability
* [ ] no negative absorbed-energy artifacts beyond tiny numerical noise
* [ ] exported branch envelopes remain finite and well-defined

---

## Benchmark cases

Use at minimum:

### Case 1

Prepared pole state with rotated analyzer

* reference case already used in the reduced model

### Case 2

Equatorial state with rotated analyzer

* reference phase-sensitive case

### Case 3

At least one additional intermediate state/analyzer pair

* to ensure the candidate is not overfit to one case

For each case:

1. compute exact target weights (w_1,w_2)
2. run physical/SPICE front-end
3. compute (f_1,f_2)
4. compare
5. hand off branch envelopes to detector+latch abstraction
6. compare final winner frequencies to exact weights

---

## Experimental / simulation plan

### Task 1 — Choose and document the first front-end candidate

Select one implementation option (A, B, or C) and document:

* topology
* expected transfer behavior
* how branch outputs will be measured/exported

**Output**

* `front_end_candidate_design.md`

---

### Task 2 — Implement two-branch physical/SPICE front-end candidate

Implement the candidate so that it produces:

* branch voltages
* branch currents
* branch powers
* integrated branch energies

**Output**

* two-branch simulation outputs
* branch-energy summary CSV

---

### Task 3 — Validate front-end energy fractions

For each benchmark case:

* compute exact weights
* compute physical front-end fractions
* compare errors

**Output**

* exact vs realized fraction plots
* RMS/max error summary

---

### Task 4 — Export detector-facing branch envelopes

Convert the physical/SPICE front-end outputs into the same branch-envelope contract already used by the detector abstraction.

**Output**

* `spice_facing_interface.md`
* example exported envelope files

---

### Task 5 — Integrate with frozen detector+latch abstraction

Run the existing detector+latch abstraction on the exported branch envelopes.

Compare:

* exact target weights
* physical front-end fractions
* final winner frequencies

**Output**

* integration summary CSV
* winner-frequency vs target plot
* RMS/max error summary

---

## Tests

Add tests for:

### T1

Branch fractions sum to 1 within tolerance.

### T2

Physical/SPICE front-end fractions remain close to exact target weights.

### T3

Detector-facing envelope export is valid and consumable by the existing detector abstraction.

### T4

Integrated winner frequencies remain close to exact target weights.

---

## Explicit failure conditions

Reject or redesign the front-end candidate if any of the following occur:

* [ ] branch absorbed energies deviate too far from target weights
* [ ] exported envelopes are too distorted for detector+latch handoff
* [ ] integrated winner-law error materially exceeds surrogate baseline
* [ ] front-end requires hidden post-hoc normalization not documented in the design
* [ ] candidate is numerically fragile or physically uninterpretable

---

## Decision gate after this ticket

Proceed to the next phase only if:

1. the first physical/SPICE front-end candidate reproduces two-branch energy fractions sufficiently well,
2. detector+latch handoff still preserves winner-law behavior,
3. the front-end/export boundary is stable and documented.

If these pass, the next ticket should be:

**Extend the physical/SPICE front-end candidate toward the four-branch shared-state case, or design the first explicit resonant front-end implementation candidate.**

If they fail, iterate on the two-branch front-end candidate before scaling up.

---

## Suggested labels

`research`
`front-end`
`spice`
`integration`
`measurement`
`high-priority`

---

## Summary

**Build the first physical/SPICE two-branch front-end candidate and validate end-to-end handoff into the frozen detector+latch abstraction**