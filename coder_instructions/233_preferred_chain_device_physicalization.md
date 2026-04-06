## preferred_chain_device_physicalization

Deepen device-level physicalization of selected subblocks in the integrated preferred-chain netlist while preserving frozen measurement semantics

## Objective

Take the current **integrated preferred-chain co-design netlist** and replace selected idealized or reduced subblocks with more explicit **device-/component-level realizations**, while keeping the already validated measurement semantics frozen.

This ticket must answer:

1. Which subblocks can be made more device-realistic now without destabilizing the chain?
2. Can those deeper device-level realizations preserve:

   * pre-click transparency,
   * winner-law fidelity,
   * correlator fidelity,
   * CHSH fidelity,
   * post-click exclusivity,
   * coherent whole-trial energy accounting?
3. Which abstractions remain unavoidable after this step, and which have now been reduced meaningfully?

This is a **physicalization ticket**, not a semantics ticket.

---

## Background

The current integrated co-designed preferred chain already passes end-to-end:

* explicit front-end R/L/C netlist
* attached common-inhibit rail
* winner-gated drain branch
* shared-leak subnetwork
* frozen detector boundary
* frozen detector
* frozen latch

Current integrated chain metrics:

* winner-law RMS error: **0.014691**
* winner-law max error: **0.036434**
* correlator RMS error: **0.009446**
* CHSH absolute error: **0.003501**
* mean decisive fraction: **0.996944**
* winner-drain dominance rate: **0.999721**
* completion rate: **0.995556**
* pre-click transparency RMS/max shift: **0 / 0**

The architecture is therefore strong enough to stop rearranging top-level blocks and start reducing abstraction inside specific subblocks.

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

* first-arrival arbiter
* current frozen timing assumptions

### Frozen role split

* front-end computes branch structure
* detector generates first clicks
* latch declares winner
* closure/drain activates only post-click

### Frozen closure interpretation

* common inhibit rail + winner-gated shunt/resonant drain

This ticket is about making subblocks more explicit physically, not changing the measurement semantics.

---

## Scope

Included:

* deeper device-/component-level physicalization of selected subblocks
* replacement of idealized subblocks with more explicit circuit/device models where practical
* comparison against the current integrated preferred-chain baseline
* preservation of the frozen downstream semantics

Excluded:

* detector-family redesign
* latch-semantic redesign
* export-boundary redesign
* new interpretation of closure/drain
* fabrication/layout work
* claims of final hardware completeness

---

## Candidate subblocks for deeper physicalization

Select at least one primary subblock, optionally two.

### Subblock A — Common inhibit rail realization

Replace the current abstract/common control rise block with a more explicit circuit-style realization, such as:

* RC-driven gate network
* comparator-triggered control node
* gated bias rail collapse model
* transistor-like switch surrogate if tractable

### Subblock B — Winner drain path realization

Replace the current winner-gated drain abstraction with a more explicit device-level or branch-level drain realization, such as:

* switched shunt branch
* gated resonant dump path
* explicit dissipative branch with realistic turn-on behavior
* coupled drain tank with gated coupling

### Subblock C — Coupled-port/front-end coupler realization

Replace some idealized front-end coupling elements with more explicit component-level realizations, such as:

* explicit mutual inductance / transformer-like coupling
* more explicit passive coupler blocks
* explicit branch-port matching components

### Subblock D — Shared leak / residual path realization

Replace the current shared leak abstraction with a more explicit passive leakage or parasitic-style model.

### Preferred first choice

Start with:

1. **winner drain path realization**
2. **common inhibit rail realization**

Those are likely to yield the biggest physical realism gain with the lowest risk to the pre-click branch structure.

---

## Design intent

Move from an integrated netlist that is already explicit at the block/component-table level toward one where key subblocks have a more believable circuit/device interpretation.

The target is still **not** a production netlist. The target is:

* fewer idealized control abstractions
* more explicit physical meaning of subblocks
* preserved full-chain behavior

---

## Functional requirements

### FR1 — Keep top-level chain fixed

The full chain structure must remain:

[
\text{front-end netlist}
\to
\text{frozen detector boundary}
\to
\text{frozen detector}
\to
\text{frozen latch}
\to
\text{post-click closure/drain}
]

Only selected subblocks may be deepened.

### FR2 — Device-level realization of selected subblocks

Each selected subblock must be replaced by a more explicit physical/device-style realization and documented clearly.

### FR3 — Preserve pre-click transparency

Any deeper physicalization must remain effectively invisible before `winner_valid=True`.

### FR4 — Preserve post-click exclusivity

The physicalized closure/drain subblocks must still:

* suppress losers strongly
* give winner-dominant drain
* preserve monotonic shared-energy decay

### FR5 — Preserve full-chain performance

The deeper physicalized chain must preserve:

* winner-law fidelity
* correlator fidelity
* CHSH fidelity
* decisive fraction
* energy accounting

### FR6 — Explicit realism gain

The design note must explain why the new subblock realization is genuinely more physical than the current baseline.

---

## Inputs / outputs

### Inputs

* integrated preferred-chain baseline netlist
* shared-state preparation parameters
* analyzer settings ((a,b))
* frozen detector params
* frozen latch params
* frozen detector-boundary settings
* benchmark cases

### Outputs

* updated integrated netlist candidate
* subblock-specific diagnostics
* whole-chain metrics
* comparison vs current integrated baseline

---

## Deliverables

### Code / model deliverables

* [ ] physicalized subblock implementations
* [ ] integrated chain update using those implementations
* [ ] diagnostics for selected subblocks
* [ ] metrics/plots/report builder
* [ ] tests

### Artifact deliverables

* [ ] `artifacts/preferred_chain_device_physicalization/subblocks/`
* [ ] `artifacts/preferred_chain_device_physicalization/pre_click/`
* [ ] `artifacts/preferred_chain_device_physicalization/post_click/`
* [ ] `artifacts/preferred_chain_device_physicalization/full_chain/`
* [ ] `artifacts/preferred_chain_device_physicalization/energy_accounting/`
* [ ] `artifacts/preferred_chain_device_physicalization/summary_report.md`
* [ ] `artifacts/preferred_chain_device_physicalization/summary_metrics.json`
* [ ] `artifacts/preferred_chain_device_physicalization/summary_metrics.csv`
* [ ] `artifacts/preferred_chain_device_physicalization/design_note.md`
* [ ] `artifacts/preferred_chain_device_physicalization/candidate_comparison.csv`

### Required design note

* [ ] `design_note.md`

This note must include:

* which subblocks were deepened
* what the old abstraction was
* what the new device-/component-level realization is
* why this is a physical realism gain
* what remains abstract
* what was intentionally left frozen

---

## Required plots

* [ ] selected-subblock internal signals / state plots
* [ ] pre-click transparency comparison vs current baseline
* [ ] winner drain / loser residual energy plots
* [ ] exact vs empirical four-branch winner frequencies
* [ ] correlator exact vs empirical
* [ ] CHSH exact vs empirical
* [ ] whole-trial energy flow summary
* [ ] comparison vs current integrated preferred-chain baseline

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

* [ ] pre-click transparency shift remains negligible relative to the current integrated preferred-chain baseline

### E. Post-click exclusivity

* [ ] winner-drain dominance remains true
* [ ] loser residual fraction remains small
* [ ] monotonic shared-energy decay remains true

### F. Energy accounting

* [ ] energy-accounting pass remains true
* [ ] total energy balance remains coherent

### G. Architectural realism gain

* [ ] the selected subblocks are genuinely more explicit physically
* [ ] the report makes the realism gain legible
* [ ] no disguised rollback to earlier abstractions

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

1. run the updated integrated chain
2. export detector-facing envelopes
3. run frozen detector
4. run frozen latch
5. evaluate post-click exclusivity
6. compute winner-law metrics
7. compute correlator and CHSH
8. summarize energy accounting

---

## Experimental / simulation plan

### Task 1 — Select subblocks to deepen

Choose which subblocks will be physicalized first and document the rationale.

**Output**

* `design_note.md`

### Task 2 — Implement deeper device-level subblocks

Replace the selected abstractions with more explicit circuit/device-level realizations.

**Output**

* subblock artifacts and diagnostics

### Task 3 — Revalidate pre-click behavior

Measure pre-click transparency shift against the current integrated preferred-chain baseline.

**Output**

* pre-click comparison CSV
* transparency plots

### Task 4 — Revalidate post-click behavior

Measure:

* winner drain fraction
* loser residual fraction
* completion behavior
* monotonic shared-energy decay

**Output**

* post-click summary CSV
* exclusivity plots

### Task 5 — Revalidate full-chain behavior

Measure:

* winner-law fidelity
* correlator
* CHSH
* decisive fraction

**Output**

* full-chain summary CSV/JSON
* winner/correlator/CHSH plots

### Task 6 — Revalidate whole-trial energy accounting

Summarize:

* pre-click energy
* winner drain energy
* loser residual energy
* shared leakage
* total balance

**Output**

* energy-accounting CSV
* energy flow plots

### Task 7 — Compare to current integrated preferred-chain baseline

Compare:

* current integrated preferred chain
* deeper device-level candidate

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

Physicalized subblocks remain finite and well-posed.

### T2

Detector-facing export remains compatible with the frozen boundary.

### T3

Pre-click transparency remains within tolerance.

### T4

Winner drain dominance remains true.

### T5

Winner-law, correlator, and CHSH remain within acceptance.

### T6

Energy accounting remains balanced.

### T7

The selected subblocks are not simply the old abstraction under a new name.

---

## Explicit failure conditions

Reject or iterate if any of the following occur:

* [ ] selected subblocks do not materially improve physical explicitness
* [ ] pre-click transparency degrades materially
* [ ] winner-law fidelity degrades beyond acceptance
* [ ] correlator or CHSH degrade materially
* [ ] post-click exclusivity weakens materially
* [ ] energy accounting breaks or becomes opaque

---

## Decision gate after this ticket

Proceed only if:

1. at least one selected subblock is meaningfully more physical,
2. the frozen downstream semantics remain valid,
3. the full chain remains quantitatively strong,
4. the realism gain is worth the added complexity.

If these pass, the next ticket should be either:

* **push another subblock toward device-level realization**, or
* **begin composing a deeper integrated hardware/netlist candidate from the physicalized subblocks**.

If they fail, step back and reassess which subblocks are worth physicalizing next.

---

## Suggested labels

`research`
`device-level`
`physicalization`
`front-end`
`closure`
`drain`
`integration`
`high-priority`

---

## Summary

**Deepen selected subblocks of the integrated preferred-chain netlist toward device-/component-level realization while preserving the frozen detector/latch boundary**
