# preferred_chain_codesign

Co-design the explicit front-end netlist and closure/drain path into an integrated hardware-style candidate while preserving the frozen detector/latch boundary

## Objective

Build the first **integrated front-end + closure/drain hardware-style candidate** by combining:

1. the explicit component-level preferred front-end netlist, and
2. the preferred post-click closure/drain topology
   (**common inhibit rail + winner-gated shunt drain**)

into one co-designed chain.

This ticket must answer:

1. Can the explicit front-end netlist and closure/drain path be integrated without breaking the already validated **pre-click** behavior?
2. Can the integrated netlist preserve **post-click exclusivity**, **winner-dominant drain**, and **whole-trial energy accounting**?
3. Does the integrated hardware-style chain still preserve:

   * four-branch winner-law fidelity,
   * correlator fidelity,
   * CHSH fidelity?

This is the next step toward an actual integrated hardware/netlist candidate.

---

## Background

The following pieces are now individually or sequentially validated:

### Explicit front-end netlist candidate

* explicit component-level R/L/C front-end
* source branches
* tank storage elements
* load/readout elements
* inter-branch couplers
* preserved frozen downstream-chain behavior

### Frozen detector boundary

* export mode: `piecewise_envelope:linear:20.0ms`
* gain: `4.0x`
* exposure: `5.0s`

### Frozen detector

* family: `shot_trigger`
* validated operating-point parameters

### Frozen latch

* first-arrival arbiter semantics
* already validated transparency

### Preferred closure/drain candidate

* common inhibit rail + winner-gated shunt drain
* tuned winner-dominance pass
* completion pass
* reduced consistency pass

The next question is no longer whether these blocks work separately. It is whether the **front-end and closure/drain can coexist as one integrated physical chain** without hidden incompatibilities.

---

## Frozen items for this ticket

Do **not** change these unless a hard integration failure forces it:

### Frozen detector boundary

* export mode: `piecewise_envelope:linear:20.0ms`
* gain: `4.0x`
* exposure: `5.0s`

### Frozen detector

* `shot_trigger`
* current validated parameter set

### Frozen latch

* first-arrival arbiter
* current frozen timing assumptions

### Frozen high-level semantics

* front-end computes branch structure
* detector generates first clicks
* latch declares winner
* closure/drain activates only after winner capture

This ticket is about **co-designing the front-end and closure/drain hardware-style realization**, not revisiting measurement semantics.

---

## Scope

Included:

* integrated front-end + closure/drain netlist candidate
* explicit coupling/interface between front-end residual energy and closure/drain path
* pre-click transparency validation in the integrated netlist
* post-click exclusivity validation in the integrated netlist
* whole-trial energy accounting across the integrated netlist
* comparison against the current separated preferred-chain baseline

Excluded:

* detector redesign
* latch redesign
* boundary redesign
* transistor-level detector implementation
* transistor-level latch implementation
* final production schematic/layout
* fabrication constraints beyond basic physical plausibility

---

## Design intent

Move from:

[
\text{explicit front-end netlist}
;+;
\text{separate closure/drain candidate}
]

to:

[
\text{co-designed front-end + closure/drain integrated netlist}
]

while preserving the already validated downstream detector/latch semantics.

The key new question is whether the closure/drain path can be integrated into the front-end network **without leaking backward into the pre-click dynamics**.

---

## Candidate co-design directions

Choose one primary direction and document why.

### Option A — Shared front-end netlist with gated post-click shunt branch

Integrate the winner-gated drain and common inhibit rail directly into the explicit front-end netlist as an attached post-click network.

Preferred first pass.

### Option B — Front-end netlist with shared inhibit bus and branch-local drain devices

Use one common inhibit node distributed across the front-end branches, with winner-specific drain elements co-located near the output branches.

Also acceptable.

### Option C — Hybrid co-design

Keep the explicit front-end netlist intact, but represent closure/drain as a physically attached subnetwork with explicit ports and coupling elements.

Acceptable if it is the cleanest bridge.

---

## Functional requirements

### FR1 — Integrated front-end + closure/drain netlist

The implementation must produce one explicit netlist candidate containing:

* front-end resonant/shared components
* branch ports and loads
* closure/drain components
* common inhibit structure
* winner drain structure

### FR2 — Pre-click transparency

Before `winner_valid=True`, the integrated closure/drain network must not materially degrade the validated pre-click front-end → detector → latch behavior.

### FR3 — Post-click exclusivity

After winner capture:

* the winner drain path must dominate post-click energy flow
* loser paths must be strongly suppressed
* remaining shared energy must decay monotonically

### FR4 — Whole-trial energy accounting

The integrated netlist must expose enough observables to account for:

* pre-click branch energies
* post-click winner drain energy
* loser residual energy
* shared leakage / residual energy
* total energy balance

### FR5 — Frozen downstream compatibility

The integrated netlist must still export detector-facing envelopes consumable by the frozen detector boundary without changing detector/latch semantics.

### FR6 — Preserve preferred-chain behavior

The integrated chain must preserve acceptable:

* winner-law fidelity
* correlator fidelity
* CHSH fidelity
* completion behavior

---

## Inputs / outputs

### Inputs

* shared preparation parameters
* analyzer settings ((a,b))
* benchmark angle sets
* frozen detector params
* frozen latch params
* frozen closure/drain tuning parameters
* frozen detector-boundary settings

### Outputs

* integrated netlist or netlist-equivalent component table
* front-end branch observables
* closure/drain observables
* detector-facing envelope exports
* empirical winner frequencies
* correlator
* CHSH
* whole-trial energy-accounting summaries

---

## Deliverables

### Code / model deliverables

* [ ] integrated front-end + closure/drain netlist candidate
* [ ] front-end/closure coupling module
* [ ] detector-boundary export module
* [ ] integration driver
* [ ] metrics/plots/report builder
* [ ] tests

### Artifact deliverables

* [ ] `artifacts/preferred_chain_codesign/netlist/`
* [ ] `artifacts/preferred_chain_codesign/pre_click/`
* [ ] `artifacts/preferred_chain_codesign/post_click/`
* [ ] `artifacts/preferred_chain_codesign/full_chain/`
* [ ] `artifacts/preferred_chain_codesign/energy_accounting/`
* [ ] `artifacts/preferred_chain_codesign/summary_report.md`
* [ ] `artifacts/preferred_chain_codesign/summary_metrics.json`
* [ ] `artifacts/preferred_chain_codesign/summary_metrics.csv`
* [ ] `artifacts/preferred_chain_codesign/design_note.md`
* [ ] `artifacts/preferred_chain_codesign/candidate_comparison.csv`

### Required design note

* [ ] `design_note.md`

This note must include:

* chosen co-design architecture
* how the closure/drain attaches to the front-end netlist
* where the common inhibit rail lives physically
* where the winner drain path attaches
* what remains frozen
* what remains abstract
* why this is a deeper physical step than the current separated-chain baseline

---

## Required plots

* [ ] integrated netlist topology diagram
* [ ] pre-click transparency comparison vs current baseline
* [ ] winner drain energy fraction
* [ ] loser residual energy fraction
* [ ] remaining shared energy vs time
* [ ] exact vs empirical four-branch winner frequencies
* [ ] correlator exact vs empirical
* [ ] CHSH exact vs empirical
* [ ] whole-trial energy flow summary
* [ ] comparison vs current preferred-chain baseline

---

## Quantitative acceptance criteria

### A. Pre-click transparency

* [ ] winner-frequency RMS shift vs current preferred-chain baseline remains small
* [ ] no material branch bias introduced by the integrated closure/drain network

### B. Winner-law fidelity

* [ ] RMS four-branch winner-law error < 0.03
* [ ] max four-branch winner-law error < 0.05

### C. Correlator fidelity

* [ ] correlator RMS error < 0.05

### D. CHSH fidelity

* [ ] CHSH absolute error < 0.1

### E. Post-click exclusivity

* [ ] winner-drain dominance remains true
* [ ] loser residual fraction remains small
* [ ] monotonic shared-energy decay remains true

### F. Completion

* [ ] completion rate remains high
* [ ] completion remains well-defined and reproducible

### G. Energy accounting

* [ ] whole-trial energy accounting remains finite, coherent, and balanced

### H. Architectural refinement

* [ ] front-end and closure/drain are now explicitly co-designed rather than merely chained
* [ ] no fallback to a disguised separated-block abstraction

---

## Benchmark cases

### Shared-state benchmark

Use the same shared preparation target as the current preferred-chain baseline.

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

1. compute exact reduced-model target weights
2. run integrated front-end + closure/drain netlist
3. export detector-facing envelopes
4. run frozen detector
5. run frozen latch
6. evaluate post-click exclusivity
7. compute winner statistics
8. compute correlator and CHSH
9. summarize whole-trial energy accounting

---

## Experimental / simulation plan

### Task 1 — Choose co-design architecture

Select Option A, B, or C and document why.

**Output**

* `design_note.md`

### Task 2 — Implement integrated netlist candidate

Build the integrated front-end + closure/drain netlist and expose:

* front-end branch observables
* common inhibit signal
* winner drain observables
* loser suppression observables

**Output**

* netlist artifacts
* integrated diagnostics

### Task 3 — Revalidate pre-click behavior

Compare pre-click metrics against the current preferred-chain baseline.

**Output**

* pre-click comparison CSV
* transparency plot

### Task 4 — Validate post-click exclusivity

Measure:

* winner drain fraction
* loser residual fraction
* terminal loser suppression
* completion rate/time
* monotonic shared energy

**Output**

* post-click summary CSV
* post-click plots

### Task 5 — Validate full-chain behavior

Measure:

* winner-law fidelity
* correlator
* CHSH
* decisive fraction

**Output**

* full-chain summary CSV/JSON
* winner/correlator/CHSH plots

### Task 6 — Validate whole-trial energy accounting

Summarize:

* pre-click branch energies
* winner drain energy
* loser residual energy
* shared leakage energy
* balance error

**Output**

* energy-accounting CSV
* energy flow plots

### Task 7 — Compare to current preferred-chain baseline

Compare:

* current preferred chain
* co-designed integrated chain

Metrics:

* winner-law RMS/max
* correlator RMS
* CHSH error
* winner drain dominance
* transparency shift
* energy accounting
* realism gain

**Output**

* `candidate_comparison.csv`
* comparison section in summary report

---

## Tests

Add tests for:

### T1

Integrated netlist remains finite and well-posed.

### T2

Detector-facing export remains compatible with the frozen boundary.

### T3

Pre-click transparency remains within tolerance.

### T4

Winner drain dominance remains true.

### T5

Winner-law, correlator, and CHSH remain within acceptance.

### T6

Whole-trial energy accounting remains balanced.

### T7

Implementation is not reducible to the prior separated-block chain in disguise.

---

## Explicit failure conditions

Reject or iterate if any of the following occur:

* [ ] integrated closure/drain perturbs pre-click behavior materially
* [ ] winner-law fidelity degrades beyond acceptance
* [ ] correlator or CHSH degrades materially
* [ ] post-click winner dominance is lost
* [ ] energy accounting breaks or becomes opaque
* [ ] the supposed co-design is still effectively just a stitched-together baseline chain

---

## Decision gate after this ticket

Proceed only if:

1. the integrated front-end + closure/drain co-design remains quantitatively accurate,
2. the frozen detector/latch boundary remains valid,
3. the full-chain pre-click and post-click roles remain cleanly separated,
4. the co-designed architecture is meaningfully more hardware-like than the current preferred-chain baseline.

If these pass, the next ticket should be either:

* **push selected subblocks toward transistor/device-level realization**, or
* **begin turning the integrated co-designed chain into a more explicit hardware/netlist candidate suitable for deeper circuit study**.

If they fail, iterate on the co-design before deeper physicalization.

---

## Suggested labels

`research`
`front-end`
`closure`
`drain`
`codesign`
`netlist`
`integration`
`high-priority`

---

## Summary

**Co-design the explicit front-end netlist and closure/drain path into a more integrated preferred physical-chain hardware candidate while preserving the frozen detector/latch boundary**
