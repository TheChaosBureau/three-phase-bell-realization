## spice_driven_preferred_chain

Drive the frozen detector/latch/closure stack from actual SPICE-generated front-end traces and validate the first SPICE-driven preferred-chain benchmark

## Objective

Use the **actual ngspice-generated shared front-end traces** as the upstream artifact for the already frozen downstream measurement stack:

1. frozen detector boundary
2. frozen detector family
3. frozen winner latch
4. frozen closure/drain semantics

This ticket must answer:

1. Can actual SPICE-generated front-end traces be consumed cleanly by the frozen downstream stack?
2. Does the full downstream chain still preserve:

   * four-branch winner-law fidelity,
   * correlator fidelity,
   * CHSH fidelity,
   * pre-click transparency,
   * post-click exclusivity,
   * coherent whole-trial energy accounting?
3. Is the first **SPICE-driven preferred-chain benchmark** good enough to serve as the new main baseline for the path to Stop Level C?

This is the first end-to-end milestone where the upstream front-end is no longer SPICE-facing or surrogate, but **actual SPICE output**.

---

## Background

The current actual-SPICE front-end milestone has already passed:

* actual engine: **PySpice + ngspice**
* shared-core front-end: actual **R/L/C/coupling netlist**
* SPICE-vs-current-baseline RMS error: **0.001990**
* exact-vs-SPICE RMS error: **0.002815**
* correlator RMS error: **0.004314**
* CHSH absolute error: **0.001326**
* actual SPICE execution pass: **True**
* probeability pass: **True**

The frozen downstream stack remains:

### Frozen detector boundary

* export mode: `piecewise_envelope:linear:20.0ms`
* gain: `4.0x`
* exposure: `5.0s`

### Frozen detector

* family: `shot_trigger`
* current validated operating-point parameters

### Frozen latch

* first-arrival arbiter semantics
* frozen timing assumptions

### Frozen closure/drain

* preferred interpretation: common inhibit rail + winner-gated shunt/resonant drain
* currently tuned preferred candidate

So the next step is no longer about translating the front-end into SPICE. That is done. The next step is to **feed actual SPICE branch traces into the frozen downstream chain**.

---

## Scope

Included:

* actual SPICE front-end trace ingestion
* detector-boundary export from SPICE traces
* frozen detector/latch/closure execution on SPICE-driven inputs
* first SPICE-driven end-to-end benchmark
* full-chain metrics and energy accounting
* comparison against the current preferred-chain baseline

Excluded:

* front-end redesign
* detector redesign
* latch redesign
* closure/drain redesign
* new semantics
* full downstream SPICE implementation
* robustness / non-ideality sweeps beyond basic sanity checks

---

## Frozen items for this ticket

Do **not** change these unless a hard incompatibility forces it:

### Frozen front-end source

* the actual ngspice front-end artifact from the prior ticket

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

### Frozen closure/drain

* common inhibit rail + winner-gated shunt/resonant drain
* current tuned parameters

This ticket is about proving the end-to-end handoff from real SPICE traces into the frozen downstream chain, not about reopening any of those blocks.

---

## Design intent

Move from:

[
\text{actual SPICE front-end only}
]

to:

[
\text{actual SPICE front-end traces}
\to
\text{frozen detector boundary}
\to
\text{frozen detector}
\to
\text{frozen latch}
\to
\text{frozen closure/drain}
]

This should become the first **SPICE-driven preferred-chain benchmark**.

The central question is:

> does the current preferred chain still work when the front-end is supplied by actual SPICE-generated traces rather than baseline or surrogate front-end traces?

---

## Functional requirements

### FR1 — SPICE trace ingestion

The downstream handoff code must ingest actual SPICE-generated branch traces for:

* voltages
* currents
* powers
* integrated energies or equivalent derived observables

### FR2 — Detector-boundary export from SPICE traces

The SPICE branch traces must be converted into the frozen detector-boundary representation without changing the boundary contract.

At minimum:

* preserve the chosen export mode semantics
* preserve gain/exposure settings
* document exactly how SPICE traces are transformed into detector-facing envelopes

### FR3 — Full downstream-chain execution

The frozen downstream stack must run on the SPICE-driven traces:

* detector
* latch
* closure/drain

### FR4 — Full-chain benchmark metrics

The SPICE-driven chain must report:

* four-branch winner-law error
* correlator error
* CHSH error
* decisive fraction
* pre-click transparency metrics
* post-click exclusivity metrics
* whole-trial energy accounting

### FR5 — Comparison to frozen baseline

The SPICE-driven chain must be compared directly against the current preferred-chain baseline and the current actual-SPICE front-end benchmark.

---

## Inputs / outputs

### Inputs

* actual SPICE front-end waveform outputs
* benchmark angle cases
* frozen detector-boundary settings
* frozen detector params
* frozen latch params
* frozen closure/drain params

### Outputs

* detector-facing SPICE-derived traces
* empirical winner frequencies
* correlator
* CHSH
* decisive fraction
* post-click exclusivity metrics
* energy-accounting summaries
* comparison against baseline

---

## Deliverables

### Code / integration deliverables

* [ ] SPICE-trace ingestion layer
* [ ] SPICE-to-detector-boundary export adapter
* [ ] frozen downstream-chain driver for SPICE traces
* [ ] metrics/plots/report builder
* [ ] tests

### Artifact deliverables

* [ ] `artifacts/spice_driven_preferred_chain/front_end_traces/`
* [ ] `artifacts/spice_driven_preferred_chain/boundary_export/`
* [ ] `artifacts/spice_driven_preferred_chain/full_chain/`
* [ ] `artifacts/spice_driven_preferred_chain/post_click/`
* [ ] `artifacts/spice_driven_preferred_chain/energy_accounting/`
* [ ] `artifacts/spice_driven_preferred_chain/summary_report.md`
* [ ] `artifacts/spice_driven_preferred_chain/summary_metrics.json`
* [ ] `artifacts/spice_driven_preferred_chain/summary_metrics.csv`
* [ ] `artifacts/spice_driven_preferred_chain/design_note.md`
* [ ] `artifacts/spice_driven_preferred_chain/candidate_comparison.csv`

### Required design note

* [ ] `design_note.md`

This note must include:

* which actual SPICE traces are used
* how they are transformed into the frozen detector-boundary representation
* what remains outside SPICE
* what exactly is now SPICE-driven
* what compromises or assumptions are still present

---

## Required plots

* [ ] representative SPICE branch voltage traces
* [ ] representative SPICE branch current traces
* [ ] representative SPICE branch power traces
* [ ] detector-facing exported envelopes derived from SPICE
* [ ] exact vs empirical four-branch winner frequencies
* [ ] correlator exact vs empirical
* [ ] CHSH exact vs empirical
* [ ] post-click winner drain / loser residual plots
* [ ] whole-trial energy flow summary
* [ ] comparison vs current preferred-chain baseline

---

## Quantitative acceptance criteria

### A. Winner-law fidelity

* [ ] RMS four-branch winner-law error < 0.03
* [ ] max four-branch winner-law error < 0.05

### B. Correlator fidelity

* [ ] correlator RMS error < 0.05

### C. CHSH fidelity

* [ ] CHSH absolute error < 0.1

### D. Decisive fraction

* [ ] decisive fraction remains in the acceptable operating regime and is explicitly reported

### E. Pre-click transparency

* [ ] no material degradation of the pre-click behavior relative to the frozen preferred-chain baseline

### F. Post-click exclusivity

* [ ] winner-drain dominance remains true
* [ ] loser residual fraction remains small
* [ ] monotonic shared-energy decay remains true

### G. Energy accounting

* [ ] whole-trial energy accounting remains finite, coherent, and balanced

### H. SPICE alignment

* [ ] the report clearly shows that the benchmark is being driven by **actual SPICE-generated traces**, not a surrogate substitute

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

1. run actual SPICE front-end
2. export SPICE branch traces
3. transform traces into frozen detector-boundary representation
4. run detector
5. run latch
6. run closure/drain
7. compute winner statistics
8. compute correlator and CHSH
9. summarize energy accounting

---

## Experimental / simulation plan

### Task 1 — Ingest actual SPICE traces

Use the actual ngspice-generated front-end outputs as the upstream artifact.

**Output**

* archived SPICE trace files
* trace-ingestion summary

### Task 2 — Export detector-facing envelopes from SPICE traces

Convert the SPICE trace outputs into the frozen boundary representation.

**Output**

* detector-boundary-ready SPICE-derived trace files
* export summary note

### Task 3 — Run the frozen downstream chain

Execute the full downstream stack on SPICE-derived inputs.

**Output**

* full-chain summary CSV/JSON
* winner/correlator/CHSH plots

### Task 4 — Validate post-click behavior

Measure:

* winner drain fraction
* loser residual fraction
* completion rate
* monotonic shared-energy decay

**Output**

* post-click summary CSV
* post-click plots

### Task 5 — Validate whole-trial energy accounting

Summarize:

* pre-click front-end energy
* post-click winner drain energy
* loser residual energy
* shared leakage
* total balance

**Output**

* energy-accounting CSV
* energy flow plots

### Task 6 — Compare against baseline

Compare:

* current preferred-chain baseline
* SPICE-driven preferred-chain result

Metrics:

* winner-law RMS/max
* correlator RMS
* CHSH error
* decisive fraction
* winner drain dominance
* energy accounting
* SPICE-driven realism gain

**Output**

* `candidate_comparison.csv`
* comparison section in summary report

---

## Tests

Add tests for:

### T1

Actual SPICE trace ingestion succeeds.

### T2

Boundary export from SPICE traces is finite and valid.

### T3

Frozen downstream chain runs on SPICE-derived inputs.

### T4

Winner-law, correlator, and CHSH metrics remain within acceptance.

### T5

Post-click exclusivity metrics remain valid.

### T6

Energy accounting remains balanced.

### T7

Report clearly distinguishes SPICE-generated inputs from baseline/surrogate inputs.

---

## Explicit failure conditions

Reject or iterate if any of the following occur:

* [ ] actual SPICE traces cannot be consumed cleanly by the frozen boundary
* [ ] winner-law fidelity degrades beyond acceptance
* [ ] correlator or CHSH degrade materially
* [ ] pre-click transparency is lost
* [ ] post-click winner dominance is lost
* [ ] energy accounting breaks or becomes opaque
* [ ] the report cannot clearly demonstrate that the benchmark is genuinely SPICE-driven

---

## Decision gate after this ticket

Proceed only if:

1. the preferred chain works when driven by actual SPICE-generated front-end traces,
2. the frozen detector/latch/closure semantics remain valid,
3. the first SPICE-driven preferred-chain benchmark is quantitatively strong,
4. the output is good enough to count as the first major Stop Level C milestone.

If these pass, the next ticket should be either:

* **run a modest SPICE-driven robustness / non-ideality sweep on the preferred chain**, or
* **move more of the downstream chain into SPICE-compatible form**, depending on which is more valuable.

If they fail, iterate on the SPICE-to-boundary handoff before pushing further.

---

## Suggested labels

`research`
`spice`
`integration`
`front-end`
`detector-boundary`
`milestone`
`high-priority`

---

## Summary

**Validate the first SPICE-driven preferred-chain benchmark by feeding actual SPICE front-end traces into the frozen detector/latch/closure stack**
