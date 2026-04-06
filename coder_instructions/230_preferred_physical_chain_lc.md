## Preferred Physical Chain LC

Move the preferred physical chain toward an explicit LC/coupled-port realization while preserving the frozen detector/latch boundary

## Objective

Refine the current **preferred physical chain** into a more explicit **LC/coupled-port realization** without changing the already validated measurement semantics.

This ticket must answer:

1. Can the current resonant shared-state front-end be re-expressed as a more explicit coupled-port / LC-style network?
2. Can the preferred post-click closure/drain path be represented in a more explicit circuit form compatible with that front-end?
3. Does the resulting deeper physical realization still preserve:

   * four-branch winner-law fidelity,
   * correlator fidelity,
   * CHSH fidelity,
   * pre-click transparency,
   * post-click exclusivity,
   * coherent whole-trial energy accounting?

This is the next physicalization step. It is **not** a detector/latch redesign ticket.

---

## Background

The current preferred physical chain is now validated end-to-end:

* resonant shared four-branch front-end
* frozen detector boundary: `piecewise_envelope:linear:20.0ms`, gain `4.0x`, exposure `5.0s`
* frozen detector family: `shot_trigger`
* frozen winner latch: first-arrival arbiter
* tuned post-click closure/drain: common inhibit rail + winner-gated shunt drain

Current full-chain performance:

* winner-law RMS error: **0.013075**
* winner-law max error: **0.038679**
* correlator RMS error: **0.024136**
* CHSH absolute error: **0.042854**
* mean decisive fraction: **0.995694**
* winner-drain dominance rate: **0.999721**
* energy-accounting pass: **True**

So the architecture is now good enough to stop retuning semantics and start reducing abstraction in the physical chain itself.

---

## Scope

Included:

* deeper explicit LC/coupled-port realization of the preferred chain
* more explicit front-end shared resonant structure
* more explicit closure/drain circuit interpretation
* preservation of the frozen detector/latch boundary
* end-to-end validation against the current preferred-chain benchmark

Excluded:

* detector redesign
* latch redesign
* export-boundary redesign
* boundary recalibration
* full transistor-level production implementation
* new measurement semantics
* claims beyond the current shared resonant analog program

---

## Frozen items for this ticket

Do **not** change these unless a hard failure forces it:

### Frozen detector boundary

* export mode: `piecewise_envelope:linear:20.0ms`
* gain: `4.0x`
* exposure: `5.0s`

### Frozen detector

* family: `shot_trigger`
* current validated parameter set

### Frozen latch

* first-arrival arbiter semantics
* tie behavior and reset semantics as already frozen

### Frozen closure interpretation

* common inhibit rail + winner-gated shunt drain

### Frozen architectural role split

* front-end computes branch structure
* detector produces first clicks
* latch declares winner
* closure/drain handles post-click exclusivity and energy completion

---

## Design intent

Move from the current preferred chain, which is already physically intelligible but still partly reduced-order, toward a more explicit circuit-style chain:

[
\text{shared LC/coupled-port front-end}
\to
\text{frozen detector boundary}
\to
\text{frozen detector}
\to
\text{frozen latch}
\to
\text{more explicit closure/drain circuit}
]

The goal is to reduce abstraction in the **front-end and closure/drain realization**, while keeping the measurement semantics fixed.

---

## Candidate implementation directions

Choose one primary direction and document why.

### Option A — Coupled-port shared resonator network

Implement the front-end as an explicit coupled-port linear network with identifiable shared modes and branch readout ports.

Preferred first pass.

### Option B — Explicit LC modal realization

Implement an LC-style shared resonant network with reduced but explicit inductive/capacitive mode structure.

Also acceptable.

### Option C — Hybrid approach

Keep a reduced modal solve internally, but realize the coupling/readout and closure/drain stages in a more explicit port-network form.

Also acceptable if it is the most practical bridge.

---

## Functional requirements

### FR1 — More explicit shared resonant realization

The front-end must be more explicit than the current reduced resonant candidate, with identifiable coupled-port or LC-like internal structure.

### FR2 — Four measurable output branches

The front-end must still export measurable branch:

* voltages
* currents
* instantaneous powers
* absorbed energies

for:

* `++`
* `+-`
* `-+`
* `--`

### FR3 — Explicit closure/drain circuit interpretation

The closure/drain path must be represented in a more explicit circuit-style way than the current reduced conductance-style surrogate, while preserving the same preferred interpretation:

* common inhibit rail
* winner-only drain enable
* loser suppression

### FR4 — Preserve frozen boundary compatibility

The exported detector-facing envelopes must remain compatible with the frozen boundary contract.

### FR5 — Preserve preferred-chain behavior

The deeper LC/coupled-port realization must preserve:

* winner-law fidelity
* correlator fidelity
* CHSH fidelity
* pre-click transparency
* post-click exclusivity
* energy accounting

---

## Inputs / outputs

### Inputs

* shared-state preparation parameters
* analyzer settings ((a,b))
* benchmark angle sets
* frozen detector params
* frozen latch params
* tuned closure/drain params
* frozen boundary settings

### Outputs

* shared-core modal/coupled-port diagnostics
* branch voltages
* branch currents
* branch powers
* branch energies
* detector-facing exported envelopes
* empirical winner frequencies
* correlator
* CHSH
* post-click drain metrics
* whole-trial energy accounting

---

## Deliverables

### Code deliverables

* [ ] deeper LC/coupled-port preferred-chain candidate
* [ ] shared-core diagnostics
* [ ] closure/drain circuit-style diagnostics
* [ ] export interface
* [ ] integration driver
* [ ] metrics/plots/report builder
* [ ] tests

### Artifact deliverables

* [ ] `artifacts/preferred_physical_chain_lc/shared_core/`
* [ ] `artifacts/preferred_physical_chain_lc/front_end/`
* [ ] `artifacts/preferred_physical_chain_lc/post_click/`
* [ ] `artifacts/preferred_physical_chain_lc/full_chain/`
* [ ] `artifacts/preferred_physical_chain_lc/energy_accounting/`
* [ ] `artifacts/preferred_physical_chain_lc/summary_report.md`
* [ ] `artifacts/preferred_physical_chain_lc/summary_metrics.json`
* [ ] `artifacts/preferred_physical_chain_lc/summary_metrics.csv`
* [ ] `artifacts/preferred_physical_chain_lc/design_note.md`
* [ ] `artifacts/preferred_physical_chain_lc/candidate_comparison.csv`

### Required design note

* [ ] `design_note.md`

This note must state:

* chosen LC/coupled-port architecture
* how it improves physical explicitness relative to the current preferred chain
* how preparation is represented
* how analyzer dependence is represented
* how closure/drain is represented
* what remains abstract
* what was kept frozen

---

## Required plots

* [ ] shared-core modal / coupled-port diagnostics
* [ ] exact vs realized four-branch energy fractions
* [ ] exact vs empirical four-branch winner frequencies
* [ ] correlator exact vs empirical
* [ ] CHSH exact vs empirical
* [ ] winner drain / loser residual energy plots
* [ ] whole-trial energy flow summary
* [ ] comparison vs current preferred chain baseline

---

## Quantitative acceptance criteria

### A. Winner-law fidelity

* [ ] RMS four-branch winner-law error < 0.03
* [ ] max four-branch winner-law error < 0.05

### B. Correlator fidelity

* [ ] correlator RMS error < 0.05

### C. CHSH fidelity

* [ ] CHSH absolute error < 0.1

### D. Pre-click transparency

* [ ] no material degradation relative to the current preferred-chain baseline

### E. Post-click exclusivity

* [ ] winner-drain dominance remains true
* [ ] loser residual fraction remains small
* [ ] monotonic shared-energy decay remains true

### F. Energy accounting

* [ ] whole-trial energy accounting remains finite, coherent, and well balanced

### G. Architectural refinement

* [ ] the new chain is meaningfully more explicit in LC/coupled-port terms than the current preferred chain
* [ ] no disguised fallback to direct exact-weight assignment

---

## Benchmark cases

### Shared-state benchmark

Use the same singlet-like shared preparation as the current preferred chain.

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
2. run the deeper LC/coupled-port preferred chain
3. export detector-facing envelopes
4. run frozen detector
5. run frozen latch
6. run preferred closure/drain
7. compute winner statistics
8. compute correlator and CHSH
9. summarize whole-trial energy accounting

---

## Experimental / simulation plan

### Task 1 — Choose LC/coupled-port architecture

Select Option A, B, or C and document why.

**Output**

* `design_note.md`

### Task 2 — Implement deeper front-end shared core

Implement the more explicit shared resonant/coupled-port front-end.

**Output**

* shared-core diagnostics
* front-end summary artifacts

### Task 3 — Implement more explicit closure/drain realization

Represent the preferred closure interpretation in a more explicit circuit-style way while preserving its semantics.

**Output**

* post-click diagnostics
* closure/drain summary artifacts

### Task 4 — Validate full chain

Run the complete preferred chain under the frozen boundary and compute:

* winner-law metrics
* correlator
* CHSH
* post-click exclusivity metrics
* whole-trial energy accounting

**Output**

* full-chain summary CSV/JSON
* summary plots

### Task 5 — Compare against current preferred chain

Compare:

* current preferred chain
* deeper LC/coupled-port candidate

on:

* winner-law RMS/max
* correlator RMS
* CHSH error
* winner drain dominance
* energy accounting
* architectural realism gain

**Output**

* `candidate_comparison.csv`
* comparison section in summary report

---

## Tests

Add tests for:

### T1

Four-branch energy fractions remain finite and normalized.

### T2

Detector-facing export remains compatible with the frozen boundary.

### T3

Integrated winner-law metrics remain within acceptance.

### T4

Correlator and CHSH remain within tolerance.

### T5

Pre-click transparency remains within tolerance.

### T6

Winner drain dominance and energy accounting remain valid.

### T7

Implementation is not reducible to trivial direct exact-weight assignment.

---

## Explicit failure conditions

Reject or iterate if any of the following occur:

* [ ] winner-law fidelity degrades beyond acceptance
* [ ] correlator or CHSH degrades materially
* [ ] pre-click transparency is lost
* [ ] closure/drain no longer dominates post-click energy flow
* [ ] energy accounting breaks or becomes opaque
* [ ] the supposed LC/coupled-port realization is still effectively the same reduced abstraction in disguise

---

## Decision gate after this ticket

Proceed only if:

1. the deeper LC/coupled-port preferred chain remains quantitatively accurate,
2. the frozen detector/latch boundary remains valid,
3. post-click closure/drain semantics remain strong,
4. the architecture is meaningfully more explicit physically than the current preferred chain.

If these pass, the next ticket should be either:

* **co-design the front-end and closure/drain into a more explicit integrated hardware/netlist candidate**, or
* **begin moving specific subblocks toward transistor/device-level implementation**, depending on what remains most abstract.

If they fail, iterate on the LC/coupled-port realization before deeper physicalization.

---

## Suggested labels

`research`
`front-end`
`closure`
`drain`
`lc`
`coupled-port`
`integration`
`high-priority`

---

## Suggested title variant

**Deepen the preferred physical chain into an explicit LC/coupled-port realization while preserving the frozen detector/latch boundary**
