# preferred_front_end_netlist_candidate

Design the first explicit component-level netlist candidate for the LC/coupled-port preferred front-end while preserving the frozen detector/latch boundary

## Objective

Replace the current **hybrid modal + coupled-port front-end realization** with the first **explicit component-level netlist candidate** for the preferred front-end.

This ticket must answer:

1. Can the preferred LC/coupled-port front-end be expressed as an explicit component-level network with identifiable elements such as:

   * inductors,
   * capacitors,
   * resistors,
   * coupled inductors / transformers,
   * admittance or port-coupling elements?

2. Can that explicit netlist preserve the current validated behavior:

   * four-branch energy-fraction fidelity,
   * winner-law fidelity through the frozen detector/latch boundary,
   * correlator fidelity,
   * CHSH fidelity?

3. Does the explicit netlist make the shared resonant front-end more physically interpretable without forcing redesign of the frozen detector/latch/closure layers?

This is the first move from a circuit-facing preferred chain into a **component-level front-end netlist candidate**.

---

## Background

The current LC/coupled-port preferred chain already passes the required acceptance metrics:

* winner-law RMS error: **0.011256**
* winner-law max error: **0.023181**
* correlator RMS error: **0.015337**
* CHSH absolute error: **0.041058**
* mean decisive fraction: **0.995000**
* winner-drain dominance rate: **1.000000**

The architecture is now:

* hybrid modal preparation
* explicit coupled-port readout
* frozen detector boundary
* frozen detector
* frozen latch
* RC-gated resonant winner drain

The next abstraction to reduce is the **front-end implementation itself**: move from a coupled-port realization with reduced internals to a more explicit component-level netlist.

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
* current frozen timing assumptions

### Frozen post-click semantics

* common inhibit rail + winner-gated shunt drain
* current tuned closure/drain parameters and semantics

### Frozen role split

* front-end computes branch structure
* detector generates first clicks
* latch declares winner
* closure/drain handles post-click completion

This ticket is only about deepening the **front-end realization**.

---

## Scope

Included:

* explicit component-level netlist candidate for the preferred front-end
* explicit L/C/R / coupled-port representation
* mapping from preparation/analyzer/readout into explicit network structure
* branch voltage/current/power export
* handoff to the frozen detector boundary
* comparison against the current LC preferred-chain baseline

Excluded:

* detector redesign
* latch redesign
* closure/drain redesign
* boundary redesign
* transistor-level closure/drain implementation
* final production hardware layout
* fabrication constraints beyond basic physical plausibility

---

## Design intent

Move from:

[
\text{hybrid modal prep + coupled-port solve}
]

to something closer to:

[
\text{explicit component-level shared resonant network}
]

while preserving the validated downstream chain.

The front-end must now have a visible physical decomposition:

* resonant storage elements,
* coupling structure,
* readout/load ports,
* analyzer dependence represented through explicit network terms or couplers.

This ticket should reduce abstraction in the **front-end netlist**, not in the measurement semantics.

---

## Candidate implementation directions

Choose one and document why.

### Option A — Lumped LC + coupled-inductor netlist

Use explicit inductors, capacitors, resistors, and mutual couplings / transformer-like elements to realize the shared resonant core and branch readout.

Preferred if tractable.

### Option B — Multiport admittance netlist with explicit passive elements

Represent the front-end as an explicit passive or near-passive port network with identifiable branch-to-branch couplings and resonant elements.

Also acceptable.

### Option C — Hybrid explicit-port netlist

Use explicit passive component blocks for the shared core and readout/load ports, while retaining a reduced preparation block if necessary.

Acceptable if it is the most practical bridge.

---

## Functional requirements

### FR1 — Explicit component-level front-end

The candidate must be expressible as a component-level netlist with identifiable elements and couplings.

### FR2 — Shared resonant structure

The netlist must contain a recognizable shared resonant structure rather than a direct branch-weight assignment.

### FR3 — Four measurable branch outputs

The front-end must export four measurable branches:

* `++`
* `+-`
* `-+`
* `--`

Each branch must provide:

* voltage
* current
* instantaneous power
* integrated absorbed energy

### FR4 — Analyzer dependence through explicit network structure

Analyzer settings ((a,b)) must enter through explicit network/readout coupling or explicit analyzer-port transformations, not by directly assigning exact weights to output branches.

### FR5 — Frozen detector-boundary compatibility

The front-end must export detector-facing envelopes consumable by the frozen detector boundary:

* `piecewise_envelope:linear:20.0ms`
* gain `4.0x`
* exposure `5.0s`

### FR6 — Preserve preferred-chain behavior

With the frozen downstream chain unchanged, the explicit front-end netlist must preserve:

* winner-law fidelity
* correlator fidelity
* CHSH fidelity
* energy accounting quality

---

## Inputs / outputs

### Inputs

* shared-state preparation parameters
* analyzer settings ((a,b))
* benchmark angle sets
* frozen detector params
* frozen latch params
* frozen closure/drain params
* frozen detector-boundary settings

### Outputs

* explicit netlist or netlist-equivalent component table
* internal front-end diagnostics
* branch voltages
* branch currents
* branch powers
* branch energies
* exported detector-facing envelopes
* empirical winner frequencies through the full frozen chain
* correlator
* CHSH
* energy-accounting summaries

---

## Deliverables

### Code / model deliverables

* [ ] explicit component-level front-end netlist candidate
* [ ] front-end simulation wrapper
* [ ] branch export interface
* [ ] integration adapter to frozen downstream chain
* [ ] metrics/plots/report builder
* [ ] tests

### Artifact deliverables

* [ ] `artifacts/preferred_front_end_netlist_candidate/netlist/`
* [ ] `artifacts/preferred_front_end_netlist_candidate/front_end/`
* [ ] `artifacts/preferred_front_end_netlist_candidate/integration/`
* [ ] `artifacts/preferred_front_end_netlist_candidate/energy_accounting/`
* [ ] `artifacts/preferred_front_end_netlist_candidate/summary_report.md`
* [ ] `artifacts/preferred_front_end_netlist_candidate/summary_metrics.json`
* [ ] `artifacts/preferred_front_end_netlist_candidate/summary_metrics.csv`
* [ ] `artifacts/preferred_front_end_netlist_candidate/design_note.md`
* [ ] `artifacts/preferred_front_end_netlist_candidate/candidate_comparison.csv`

### Required design note

* [ ] `design_note.md`

This note must include:

* chosen netlist architecture
* element classes used
* how shared resonant structure is represented
* how preparation is represented
* how analyzer/readout coupling is represented
* what remains abstract
* why this is more explicit than the current LC preferred chain

---

## Required plots

* [ ] netlist topology diagram or equivalent block depiction
* [ ] internal resonant / modal diagnostics
* [ ] exact vs realized four-branch energy fractions
* [ ] exact vs empirical four-branch winner frequencies
* [ ] correlator exact vs empirical
* [ ] CHSH exact vs empirical
* [ ] whole-trial energy flow summary
* [ ] comparison vs current LC preferred chain baseline

---

## Quantitative acceptance criteria

### A. Front-end branch-fraction fidelity

* [ ] RMS four-branch energy-fraction error < 0.03
* [ ] max four-branch energy-fraction error < 0.05

### B. Full-chain winner-law fidelity

With the frozen downstream chain:

* [ ] RMS four-branch winner-law error < 0.03
* [ ] max four-branch winner-law error < 0.05

### C. Correlator fidelity

* [ ] correlator RMS error < 0.05

### D. CHSH fidelity

* [ ] CHSH absolute error < 0.1

### E. Energy accounting

* [ ] whole-trial energy accounting remains finite, coherent, and balanced

### F. Architectural explicitness

* [ ] front-end is recognizably more explicit in component/netlist terms than the current LC preferred chain
* [ ] no trivial direct exact-weight fallback
* [ ] design note clearly documents the realism gain

---

## Benchmark cases

### Shared-state benchmark

Use the same shared preparation target used in the current preferred chain.

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
2. run the explicit front-end netlist candidate
3. export detector-facing envelopes
4. run frozen detector
5. run frozen latch
6. run frozen closure/drain
7. compute winner statistics
8. compute correlator and CHSH
9. summarize energy accounting

---

## Experimental / simulation plan

### Task 1 — Choose explicit netlist architecture

Select Option A, B, or C and document the choice.

**Output**

* `design_note.md`

### Task 2 — Implement front-end netlist candidate

Build the explicit component-level front-end candidate and expose enough diagnostics to show branch outputs arise from the shared resonant network.

**Output**

* netlist artifacts
* front-end diagnostics
* branch summary artifacts

### Task 3 — Validate front-end branch fractions

Compare realized branch fractions to exact target weights.

**Output**

* fraction comparison CSV/plots
* RMS/max error summary

### Task 4 — Export detector-facing envelopes

Export branch envelopes under the frozen boundary contract.

**Output**

* detector-facing export artifacts
* interface note

### Task 5 — Validate full frozen downstream chain

Run the explicit front-end through:

* frozen detector boundary
* frozen detector
* frozen latch
* frozen closure/drain

Measure:

* winner-law fidelity
* correlator
* CHSH
* energy accounting

**Output**

* full integration summary
* summary plots

### Task 6 — Compare to current LC preferred chain

Compare:

* current LC preferred chain
* explicit component-level netlist candidate

Metrics:

* winner-law RMS/max
* correlator RMS
* CHSH error
* winner-drain dominance
* energy accounting
* realism gain

**Output**

* `candidate_comparison.csv`
* comparison section in summary report

---

## Tests

Add tests for:

### T1

Four-branch energy fractions remain normalized.

### T2

Detector-facing export remains compatible with the frozen boundary.

### T3

Full-chain winner-law metrics remain within acceptance.

### T4

Correlator and CHSH remain within tolerance.

### T5

Energy accounting remains finite and balanced.

### T6

Implementation is not reducible to trivial direct exact-weight assignment.

---

## Explicit failure conditions

Reject or iterate if any of the following occur:

* [ ] winner-law fidelity degrades beyond acceptance
* [ ] correlator or CHSH degrades materially
* [ ] energy accounting breaks or becomes opaque
* [ ] detector-boundary compatibility breaks
* [ ] the supposed explicit netlist is still effectively the same abstraction in disguise

---

## Decision gate after this ticket

Proceed only if:

1. the component-level front-end netlist remains quantitatively accurate,
2. the frozen downstream chain remains valid,
3. the architecture is meaningfully more explicit physically than the current LC preferred chain.

If these pass, the next ticket should be either:

* **co-design the front-end netlist and closure/drain netlist into a more explicit integrated hardware candidate**, or
* **push selected subblocks toward transistor/device-level realization**, depending on which abstraction remains dominant.

If they fail, iterate on the front-end netlist candidate before deeper hardware physicalization.

---

## Suggested labels

`research`
`front-end`
`netlist`
`lc`
`coupled-port`
`integration`
`high-priority`

---

## Suggested title variant

**Design the first explicit component-level netlist candidate for the LC/coupled-port preferred front-end while preserving the frozen detector/latch boundary**
