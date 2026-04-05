## Integration

Integrate the tuned closure/drain candidate with the resonant four-branch front-end as the preferred physical chain

## Objective

Assemble and validate the first full **preferred physical-chain candidate** by integrating:

1. resonant four-branch front-end
2. frozen detector-boundary export contract
3. frozen detector family
4. frozen winner latch
5. tuned physical closure/drain candidate

This ticket must answer:

1. Does the full preferred chain preserve the already validated **pre-click** behavior?
2. After winner capture, does the tuned closure/drain block preserve **post-click exclusivity** and **winner-dominant energy drain** in the integrated system?
3. Does the fully integrated chain still preserve:

   * four-branch winner-law fidelity,
   * correlator fidelity,
   * CHSH fidelity,
   * completion behavior,
   * coherent energy accounting across the whole trial?

This is the first end-to-end integration of the **preferred physical chain**, not just separate validated blocks.

---

## Background

The following components are now individually validated:

### Resonant four-branch front-end

* explicit modal resonator realization
* analyzer/readout coupling
* high-fidelity branch energy fractions
* compatible with the frozen boundary

### Frozen detector boundary

* export mode: `piecewise_envelope:linear:20.0ms`
* gain: `4.0x`
* exposure: `5.0s`

### Detector

* frozen detector family: `shot_trigger`
* validated rare-event operating regime

### Winner latch

* validated first-arrival exclusivity
* pre-click transparency preserved

### Closure/drain

Preferred tuned candidate:

* topology: **common inhibit rail + winner-gated shunt drain**
* winner drain dominance pass: **True**
* winner path activation pass: **True**
* completion pass: **True**
* reduced consistency pass: **True**

So the next engineering step is to connect these into one full chain and confirm that the integrated behavior remains good.

---

## Scope

Included:

* end-to-end integration of the full preferred chain
* pre-click and post-click validation in one flow
* integrated energy accounting
* correlator and CHSH validation through the full chain
* completion and drain-dominance validation in the integrated setting
* report and artifacts

Excluded:

* detector redesign
* latch redesign
* closure redesign
* boundary redesign
* new front-end redesign
* transistor-level implementation
* full explicit LC/tank hardware realization beyond the existing resonant candidate

---

## Preferred chain to integrate

The chain is:

[
\text{resonant shared front-end}
\to
\text{frozen detector-boundary export}
\to
\text{frozen detector}
\to
\text{frozen winner latch}
\to
\text{tuned closure/drain}
]

### Frozen pieces

Keep fixed:

* resonant front-end candidate
* export mode: `piecewise_envelope:linear:20.0ms`
* gain: `4.0x`
* exposure: `5.0s`
* detector params
* latch timing assumptions
* tuned closure/drain parameters

No retuning in this ticket unless a clear integration bug is found.

---

## Functional requirements

### FR1 — Full-chain pre-click transparency

Before `winner_valid=True`, the integrated presence of the closure/drain block must not materially degrade the already validated front-end → detector → latch pre-click behavior.

### FR2 — Full-chain winner-law fidelity

Across benchmark angle cases, the integrated chain must still produce empirical four-branch winner frequencies close to the exact target branch weights.

### FR3 — Full-chain correlator fidelity

Using empirical four-branch winner frequencies from the full chain, compute:
[
E = p_{++}-p_{+-}-p_{-+}+p_{--}
]
and compare to the target correlator.

### FR4 — Full-chain CHSH fidelity

For benchmark CHSH settings, compute the empirical CHSH value from the fully integrated chain and compare against target.

### FR5 — Post-click exclusivity

After winner capture:

* loser branches must be suppressed,
* the winner drain must capture the dominant post-click energy share,
* residual shared energy must decay monotonically,
* completion must be well-defined.

### FR6 — Whole-trial energy accounting

The integrated chain must expose and summarize at least:

* pre-click branch energies,
* post-click winner drain energy,
* loser residual energy,
* remaining shared energy,
* total energy bookkeeping summary

---

## Inputs / outputs

### Inputs

* shared-state preparation parameters
* analyzer settings (a,b)
* benchmark angle sets
* frozen detector params
* frozen latch params
* tuned closure/drain params
* frozen export boundary settings

### Outputs

* exact branch weights
* empirical winner frequencies
* correlator
* CHSH
* winner drain fraction
* loser residual fraction
* completion metrics
* whole-trial energy accounting summaries

---

## Deliverables

### Code deliverables

* [ ] full preferred-chain integration driver
* [ ] whole-trial energy-accounting module
* [ ] integrated metrics module
* [ ] integrated plots module
* [ ] summary report builder
* [ ] tests

### Artifact deliverables

* [ ] `artifacts/preferred_physical_chain/full_chain/`
* [ ] `artifacts/preferred_physical_chain/pre_click/`
* [ ] `artifacts/preferred_physical_chain/post_click/`
* [ ] `artifacts/preferred_physical_chain/energy_accounting/`
* [ ] `artifacts/preferred_physical_chain/summary_report.md`
* [ ] `artifacts/preferred_physical_chain/summary_metrics.json`
* [ ] `artifacts/preferred_physical_chain/summary_metrics.csv`
* [ ] `artifacts/preferred_physical_chain/chain_design_note.md`

### Required design note

* [ ] `chain_design_note.md`

This note must include:

* the exact blocks being integrated
* what remains frozen
* what is measured pre-click vs post-click
* the intended meaning of “full preferred physical chain”
* what remains abstract and what is now integrated

---

## Required plots

* [ ] exact vs empirical four-branch winner frequencies
* [ ] correlator exact vs empirical
* [ ] CHSH exact vs empirical
* [ ] winner drain energy fraction
* [ ] loser residual energy fraction
* [ ] remaining shared energy vs time
* [ ] whole-trial energy flow summary
* [ ] pre-click transparency comparison to prior baseline

---

## Quantitative acceptance criteria

### A. Winner-law fidelity

Across benchmark cases:

* [ ] RMS four-branch winner-law error < 0.03
* [ ] max four-branch winner-law error < 0.05

### B. Correlator fidelity

* [ ] correlator RMS error < 0.05

### C. CHSH fidelity

* [ ] CHSH absolute error < 0.1

### D. Pre-click transparency

* [ ] no material degradation relative to the prior resonant-front-end + detector + latch baseline

### E. Post-click exclusivity

* [ ] winner drain dominance remains true
* [ ] loser residual fraction remains small
* [ ] monotonic shared-energy decay remains true

### F. Completion

* [ ] completion rate remains high
* [ ] trial completion remains well-defined and reproducible

---

## Benchmark cases

### Shared-state benchmark

Use the same singlet-like shared preparation as prior four-branch front-end tickets.

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

1. compute exact reduced-model weights
2. run resonant front-end
3. export detector-facing envelopes
4. run detector
5. run latch
6. run closure/drain
7. compute winner statistics
8. compute correlator/CHSH
9. summarize energy accounting

---

## Experimental / simulation plan

### Task 1 — Assemble the full preferred chain

Connect:

* resonant four-branch front-end
* frozen detector boundary export
* frozen detector
* frozen latch
* tuned closure/drain candidate

**Output**

* `chain_design_note.md`
* integration block diagram

### Task 2 — Revalidate pre-click behavior

Run benchmark cases with the closure/drain attached but only activated post-click.

Measure:

* winner-law transparency shift
* any branch bias change
* any change in decisive fraction

**Output**

* pre-click comparison CSV
* transparency plot

### Task 3 — Validate full-chain post-click behavior

Measure:

* winner drain fraction
* loser residual fraction
* terminal loser suppression
* completion rate
* completion time
* monotonic shared-energy decay

**Output**

* post-click summary CSV
* energy-partition plots

### Task 4 — Validate whole-chain winner law

Measure:

* exact vs empirical four-branch winner frequencies
* RMS/max error

**Output**

* winner-frequency plots
* summary CSV

### Task 5 — Validate correlator and CHSH

From the full-chain winner frequencies, compute:

* correlator
* CHSH

**Output**

* correlator plot
* CHSH plot
* summary metrics

### Task 6 — Whole-trial energy accounting

Summarize:

* front-end branch energies
* winner drain energy
* loser residual energy
* remaining shared energy
* total tracked energy fractions

**Output**

* energy accounting CSV
* energy flow plot

---

## Tests

Add tests for:

### T1

Full chain runs end-to-end on benchmark cases.

### T2

Pre-click transparency remains within tolerance.

### T3

Winner drain dominance remains true in the integrated chain.

### T4

Remaining shared energy decays monotonically after winner capture.

### T5

Winner-law, correlator, and CHSH metrics remain within acceptance.

### T6

Whole-trial energy accounting produces finite and consistent outputs.

---

## Explicit failure conditions

Reject or iterate on the full preferred chain if any of the following occur:

* [ ] pre-click winner-law fidelity degrades materially
* [ ] closure/drain no longer dominates in the integrated setting
* [ ] loser residual energy grows materially
* [ ] completion becomes unstable or ambiguous
* [ ] correlator or CHSH degrades beyond tolerance
* [ ] energy accounting becomes inconsistent or uninformative

---

## Decision gate after this ticket

Proceed only if:

1. the full preferred physical chain works end-to-end,
2. pre-click and post-click roles remain cleanly separated,
3. winner-law, correlator, and CHSH remain acceptable,
4. energy flow through the whole trial is physically interpretable.

If these pass, the next ticket should be either:

* **move one step deeper toward explicit LC/coupled-port implementation of the preferred chain**, or
* **begin co-designing the front-end and closure/drain blocks into a more explicit physical netlist candidate**.

If they fail, iterate on chain integration before deeper physicalization.

---

## Suggested labels

`research`
`integration`
`front-end`
`detector`
`latch`
`closure`
`drain`
`high-priority`

---

## Summary

**Integrate the resonant four-branch front-end, frozen detector/latch boundary, and tuned closure/drain candidate into the preferred physical chain**
