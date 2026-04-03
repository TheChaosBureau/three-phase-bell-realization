## Post-click closure/drain path

Specify the post-click closure/drain path for the resonant four-branch measurement chain

## Objective

Define the first engineering specification for the **post-click closure/drain path** that follows the already validated front-end → detector → latch chain.

This ticket must answer:

1. What physical or circuit-level block takes `winner_index` / `winner_valid` and makes the outcome **energetically exclusive**?
2. How are the non-winning branches suppressed after winner capture?
3. How is the remaining stored/shared energy redirected into the winning branch?
4. How can this be specified in a way that preserves the already validated **pre-click** behavior?

This ticket is a **specification and reduced-model validation ticket**, not a final hardware build ticket.

---

## Background

The pre-click chain is now in good shape:

* explicit shared resonant modal core
* analyzer/readout coupling
* branch power export
* frozen detector boundary
* winner latch
* exclusive winner selection

What remains physically underspecified is the **post-click completion stage**:

* once one branch wins,
* what shared/common mechanism suppresses the others,
* and what drains the remaining stored energy through the winner?

Earlier work already separated these roles conceptually:

* front-end computes branch weights,
* detector determines first nucleation,
* latch determines winner,
* closure/drain should act **after** winner selection, not before.

This ticket formalizes that last block.

---

## Scope

Included:

* post-click closure/drain functional specification
* reduced-model closure/drain block
* interface definition from latch outputs to closure/drain block
* reduced-model validation of loser suppression and winner drain semantics
* candidate circuit interpretations of common-mode / zero-sequence closure

Excluded:

* full physical hardware implementation
* detector redesign
* latch redesign
* front-end redesign
* pre-click feedback into the race
* final full LC/tank closure netlist

---

## Design intent

The closure/drain block is a **post-click only** block.

Its job is not to generate branch weights or decide the winner.

Its job is:

1. detect that `winner_valid=True`
2. identify `winner_index`
3. inhibit all non-winning branches
4. open or strengthen a drain path for the winner
5. force remaining energy to exit through the winner branch or winner-associated drain channel
6. settle the trial into one macroscopic recorded outcome

This is the intended circuit meaning of the common-mode / zero-sequence closure role.

---

## Functional requirements

### FR1 — Post-click only

The closure/drain block must not materially modify pre-click branch competition.

It should be activated only after winner capture:

* by `winner_valid`
* or by an equivalent post-click latch signal

### FR2 — Winner-directed drain

Once branch (k_*) wins, the closure/drain block must create a path such that the remaining stored energy preferentially exits through the winner branch or a winner-associated drain path.

### FR3 — Loser suppression

After winner capture, non-winning branches must be suppressed strongly enough that they do not continue to accumulate meaningful post-click energy.

### FR4 — Shared/common closure variable

The specification must define an explicit shared closure variable or equivalent shared control path, such as:

* common-mode control node
* global inhibit line
* shared bias collapse
* winner-gated shunt path
* zero-sequence-like closure state

This variable must be named and defined explicitly.

### FR5 — Trial completion semantics

The closure/drain block must define when a trial is considered complete, for example:

* shared energy below threshold
* winner drain energy saturated
* fixed post-click settling time elapsed

### FR6 — Reset semantics

The block must define what is required to re-arm the system for the next trial, but full reset hardware implementation is not required in this ticket.

---

## Inputs / outputs

### Inputs

* `winner_index`
* `winner_valid`
* optional branch energies or branch powers
* optional internal shared-core energy estimate
* optional latch timing signals

### Outputs

* winner drain enable
* loser suppress signals
* shared closure state (Z(t)) or equivalent
* optional post-click energy accounting
* trial-complete flag

---

## Required reduced-model block

Implement a reduced closure/drain model that can be attached downstream of the existing resonant four-branch chain.

At minimum, the reduced model must include:

### State variables

* shared closure variable (Z(t))
* remaining stored/shared energy (W(t)) or equivalent
* winner drain state
* loser suppression states

### Minimal behavior

After winner selection at time (t_*):

* (Z(t)) rises from 0 toward 1
* loser branches are attenuated/suppressed as a function of (Z)
* winner drain conductance or drain strength rises as a function of (Z)
* remaining energy (W(t)) decreases monotonically
* trial ends when (W(t)) is sufficiently small

---

## Candidate reduced equations

The ticket does not require these exact equations, but the reduced model should look something like:

### Closure rise

[
\dot Z = \alpha_Z(1-Z), \qquad t>t_*
]

### Winner drain

[
\dot W = -g_{\text{win}},Z,W
]

### Loser suppression

For loser branch (j\neq k_*),
[
\dot L_j = -\beta_L Z L_j
]
or equivalent suppression rule.

The coder may choose a different reduced form, but must document:

* what rises
* what is suppressed
* what drains
* what ends the trial

---

## Deliverables

### Code deliverables

* [ ] reduced closure/drain block
* [ ] integration adapter from latch outputs to closure/drain block
* [ ] post-click energy-accounting module
* [ ] metrics/plots/report builder
* [ ] tests

### Artifact deliverables

* [ ] `artifacts/post_click_closure_spec/reduced_model/`
* [ ] `artifacts/post_click_closure_spec/integration/`
* [ ] `artifacts/post_click_closure_spec/summary_report.md`
* [ ] `artifacts/post_click_closure_spec/summary_metrics.json`
* [ ] `artifacts/post_click_closure_spec/summary_metrics.csv`
* [ ] `artifacts/post_click_closure_spec/closure_design_note.md`

### Required design note

* [ ] `closure_design_note.md`

This note must define:

* the closure variable
* the winner drain path
* loser suppression semantics
* trial completion condition
* reset/re-arm assumptions
* candidate physical interpretations of the closure variable

---

## Required plots

* [ ] closure variable (Z(t)) after winner capture
* [ ] remaining shared energy (W(t)) vs time
* [ ] winner drain energy accumulation
* [ ] loser suppression traces
* [ ] post-click energy partition summary

---

## Quantitative acceptance criteria

### A. Pre-click transparency

When closure/drain is attached but inactive pre-click:

* [ ] no measurable degradation of the already validated pre-click winner-law behavior beyond a small documented tolerance

### B. Post-click exclusivity

After winner capture:

* [ ] loser post-click energy remains negligible relative to winner drain energy
* [ ] winner drain captures the dominant share of remaining stored energy

### C. Trial completion

* [ ] remaining shared energy decays monotonically after winner capture
* [ ] trial-complete condition is well-defined and reproducible

### D. Specification quality

* [ ] closure variable is explicit
* [ ] circuit interpretation candidates are listed
* [ ] no hidden pre-click feedback is introduced

---

## Candidate physical interpretations to compare

The ticket should explicitly consider and compare at least a few possible physical meanings for the closure/drain path, for example:

1. **winner-gated common shunt**
2. **shared bias collapse controlled by winner latch**
3. **common-mode inhibit + winner-only drain enable**
4. **zero-sequence-like closure variable coupled to all branches**
5. **transformer/coupled-port recombination drain activated by winner selection**

The goal is not to finalize hardware, but to identify which interpretation is most plausible.

---

## Benchmark integration tasks

### Task 1 — Attach reduced closure block downstream of current chain

Connect:

* resonant four-branch front-end
* frozen detector
* frozen latch
* reduced closure/drain block

### Task 2 — Verify pre-click transparency

Re-run benchmark pre-click statistics with closure block present but inactive until `winner_valid`.

### Task 3 — Verify post-click exclusivity

After winner capture, measure:

* winner drain energy
* loser residual energy
* shared energy decay

### Task 4 — Compare closure interpretations

Implement or emulate a small set of candidate closure interpretations and compare their behavior qualitatively and quantitatively.

---

## Tests

Add tests for:

### T1

Closure block remains inactive before winner capture.

### T2

Winner capture activates closure/drain exactly once.

### T3

Loser suppression occurs after winner capture.

### T4

Remaining shared energy decreases monotonically after closure activation.

### T5

Winner drain receives the dominant post-click energy share.

---

## Explicit failure conditions

Reject or revise the closure/drain specification if any of the following occur:

* [ ] closure affects pre-click race materially
* [ ] winner drain does not dominate post-click energy flow
* [ ] losers continue to absorb significant post-click energy
* [ ] no explicit closure variable can be defined
* [ ] trial completion remains ambiguous
* [ ] the design note cannot map the reduced block to plausible circuit interpretations

---

## Decision gate after this ticket

Proceed only if:

1. the post-click closure/drain role is explicitly specified,
2. the reduced closure/drain block preserves pre-click behavior,
3. the block gives physically meaningful post-click exclusivity and energy redirection semantics,
4. at least one plausible circuit interpretation emerges as a preferred candidate.

If these pass, the next ticket should be either:

* **design the first physical closure/drain implementation candidate**, or
* **co-design closure/drain with a deeper explicit LC/coupled-port front-end realization**, depending on which is most constraining.

If they fail, revise the closure/drain abstraction before moving to hardware-level closure work.

---

## Suggested labels

`research`
`closure`
`drain`
`post-click`
`integration`
`high-priority`

---

## Summary

**Specify and validate the post-click closure/drain path for the resonant four-branch measurement chain**
