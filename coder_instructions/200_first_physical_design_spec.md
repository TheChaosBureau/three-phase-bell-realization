# First Physical Design

Design the first physical closure/drain implementation candidate for the preferred “common-mode inhibit + winner drain” interpretation

## Objective

Turn the validated reduced post-click closure/drain specification into the **first physical/SPICE-style closure/drain implementation candidate**.

This ticket must answer:

1. What concrete circuit topology can realize the preferred interpretation:

   * **common-mode inhibit + winner drain**?
2. Can that topology preserve the already validated requirement that closure acts **only after** winner capture?
3. Can it physically suppress loser branches and route the dominant share of remaining stored/shared energy into the winner drain path?
4. Can it do so without materially disturbing the pre-click front-end → detector → latch behavior?

This is the first move from reduced closure semantics into physical implementation.

---

## Background

The current reduced closure/drain work identified a preferred interpretation:

* preferred candidate: **common-mode inhibit + winner drain**
* closure variable: (Z(t))
* pre-click transparency shift: **0.000000**
* mean winner drain fraction: **0.860623**
* mean loser residual fraction: **0.002693**
* completion rate: **0.995000**
* monotonic shared energy: **True**

So the role of closure is now clear:

* it does **not** generate branch weights,
* it does **not** decide the winner,
* it activates only after `winner_valid=True`,
* it suppresses losers and opens a winner-associated drain path.

The front-end, detector, latch, and frozen boundary are already established and should remain unchanged for this ticket.

---

## Scope

Included:

* first physical/SPICE-style closure/drain candidate
* candidate circuit topology for common-mode inhibit + winner drain
* reduced-to-circuit mapping of (Z(t)), loser suppression, and winner drain
* interface from latch outputs to closure/drain block
* validation against reduced closure semantics
* pre-click transparency check
* post-click exclusivity / drain dominance check

Excluded:

* redesign of resonant front-end
* redesign of detector family
* redesign of latch logic
* final production hardware
* full nonlinear/shared-core hardware co-design
* reset hardware beyond a defined interface contract (unless trivial)

---

## Design intent

Move from the reduced semantics:

* closure variable (Z(t))
* loser suppression
* winner-only drain enable
* monotonic shared energy decay

to a first physical/SPICE-style implementation candidate with explicit circuit meaning.

The preferred interpretation should be realized as something like:

1. **winner capture from latch**
2. **shared/common inhibit signal rises**
3. **loser branch paths are strongly attenuated or clamped**
4. **winner-associated drain path is enabled or strengthened**
5. **shared stored energy decays through the winner**
6. **trial-complete condition becomes detectable**

---

## Preferred interpretation to implement

### Preferred closure interpretation

**Common-mode inhibit + winner drain**

### Intended physical meaning

* a shared/common inhibit control line is asserted after winner capture
* that inhibit line suppresses all branches globally except the selected winner path
* a winner-gated drain element is enabled, providing a dominant discharge route for the remaining stored energy
* no closure path is allowed to feed back into the pre-click race

This interpretation must remain the default candidate unless a blocker appears.

---

## Functional requirements

### FR1 — Post-click only activation

The closure/drain block must remain inactive until:

* `winner_valid=True`
* and a specific `winner_index` is present

There must be no pre-click closure activity that modifies the already validated front-end/detector race.

### FR2 — Common-mode inhibit

The implementation must contain an explicit shared/common control signal corresponding to the reduced closure variable (Z(t)).

This signal must:

* rise only after winner capture
* affect all branches
* strongly suppress non-winning branches

### FR3 — Winner-only drain enable

The implementation must contain an explicit winner-associated drain path that is enabled only for the selected winner.

### FR4 — Loser suppression

Non-winning branches must be suppressed sufficiently that post-click loser energy remains negligible relative to the winner drain share.

### FR5 — Trial completion semantics

The implementation must define how “trial complete” is detected, for example by:

* shared energy below threshold
* drain current below threshold
* fixed completion interval after closure activation

### FR6 — Reset interface

The implementation must define how reset/re-arm would be applied after trial completion, but the full reset hardware may remain outside scope if needed.

---

## Candidate implementation directions

Choose one primary candidate and optionally one fallback.

### Option A — Common inhibit rail + winner-gated shunt drain

* common inhibit line disables/clamps all branch output paths
* winner selection gates one drain shunt or controlled sink
* simplest conceptual mapping to reduced semantics

Preferred first pass.

### Option B — Shared bias collapse + winner-only discharge path

* latch event collapses a shared bias that suppresses losers
* winner line simultaneously opens the dominant discharge path

Acceptable.

### Option C — Common-mode clamp + winner-coupled recombination drain

* common-mode clamp reduces all residual branch activity
* winner branch couples into a dedicated recombination or dump path

Also acceptable if more natural for the existing front-end.

---

## Inputs / outputs

### Inputs

* `winner_index`
* `winner_valid`
* latch outputs or equivalent winner-select lines
* optional branch energies/powers
* optional shared-core energy estimate

### Outputs

* common inhibit signal (Z(t)) or explicit circuit analog
* winner drain enable
* loser suppress controls
* optional drain current / drain energy observables
* `trial_complete`

---

## Deliverables

### Code / model deliverables

* [ ] first physical/SPICE-style closure/drain implementation candidate
* [ ] reduced-to-circuit mapping module
* [ ] integration adapter from latch outputs to closure/drain block
* [ ] metrics/plots/report builder
* [ ] tests

### Artifact deliverables

* [ ] `artifacts/physical_closure_drain_candidate/candidate_design.md`
* [ ] `artifacts/physical_closure_drain_candidate/reduced_mapping/`
* [ ] `artifacts/physical_closure_drain_candidate/integration/`
* [ ] `artifacts/physical_closure_drain_candidate/spice_facing/`
* [ ] `artifacts/physical_closure_drain_candidate/summary_report.md`
* [ ] `artifacts/physical_closure_drain_candidate/summary_metrics.json`
* [ ] `artifacts/physical_closure_drain_candidate/summary_metrics.csv`

### Required design note

* [ ] `candidate_design.md`

This note must include:

* chosen topology
* what carries the common-mode inhibit signal
* what suppresses losers
* what enables the winner drain
* how trial completion is detected
* how reset is expected to work
* what remains abstract

---

## Required plots

* [ ] closure/control signal (Z(t)) or analog vs time
* [ ] winner drain current/power vs time
* [ ] loser suppression traces
* [ ] remaining shared energy vs time
* [ ] post-click energy partition summary
* [ ] comparison to reduced closure semantics

---

## Quantitative acceptance criteria

### A. Pre-click transparency

With the closure/drain candidate attached but inactive pre-click:

* [ ] no measurable degradation of the already validated pre-click winner-law behavior beyond a small documented tolerance

### B. Post-click exclusivity

After winner capture:

* [ ] winner drain receives the dominant share of post-click energy
* [ ] mean loser residual fraction remains small
* [ ] loser branch activity decays rapidly after closure activation

### C. Trial completion

* [ ] remaining shared energy decreases monotonically after closure activation
* [ ] completion rate is high and well-defined
* [ ] trial-complete criterion is reproducible

### D. Reduced-model consistency

The physical/SPICE-style candidate should qualitatively reproduce the reduced closure result:

* strong winner drain dominance
* negligible loser residuals
* post-click-only activation
* no hidden pre-click feedback

---

## Benchmark integration tasks

### Task 1 — Map reduced semantics into first physical closure candidate

Choose a topology and define:

* what is (Z(t)) in circuit terms
* what is the loser suppression path
* what is the winner drain path

**Output**

* `candidate_design.md`

### Task 2 — Integrate closure candidate downstream of current chain

Attach the closure/drain candidate to:

* resonant four-branch front-end
* frozen detector
* frozen latch

**Output**

* integration summary artifacts

### Task 3 — Verify pre-click transparency

Re-run pre-click benchmark statistics with closure/drain attached but gated off until winner capture.

**Output**

* transparency summary
* comparison to prior pre-click baseline

### Task 4 — Verify post-click exclusivity and drain dominance

Measure:

* winner drain share
* loser residual share
* shared energy decay
* completion behavior

**Output**

* post-click energy partition summary
* shared-energy decay plots

### Task 5 — Compare against reduced closure interpretation

Compare the physical candidate against the reduced preferred interpretation:

* common-mode inhibit + winner drain

**Output**

* comparison note and metrics

---

## Tests

Add tests for:

### T1

Closure/drain block remains inactive before `winner_valid`.

### T2

Winner capture activates exactly one winner drain path.

### T3

Loser suppression occurs after closure activation.

### T4

Remaining shared energy decreases monotonically after closure activation.

### T5

Winner drain dominates post-click energy share.

### T6

Trial-complete signal is generated consistently.

---

## Explicit failure conditions

Reject or iterate on the candidate if any of the following occur:

* [ ] pre-click race is materially disturbed
* [ ] no explicit common-mode inhibit signal can be identified
* [ ] winner drain does not dominate post-click energy flow
* [ ] loser branches continue to absorb significant post-click energy
* [ ] trial completion is ambiguous or inconsistent
* [ ] the topology cannot be mapped clearly to the preferred reduced interpretation

---

## Decision gate after this ticket

Proceed only if:

1. a plausible physical/SPICE-style closure/drain candidate is defined,
2. it preserves pre-click transparency,
3. it reproduces the desired post-click exclusivity semantics,
4. it maps cleanly to the preferred reduced interpretation.

If these pass, the next ticket should be either:

* **co-design the resonant front-end and physical closure/drain path into a more explicit integrated hardware candidate**, or
* **move toward an explicit LC/coupled-port realization including the closure path**, depending on where the main remaining abstraction sits.

If they fail, revise the closure/drain implementation candidate before moving further toward hardware integration.

---

## Suggested labels

`research`
`closure`
`drain`
`post-click`
`spice`
`integration`
`high-priority`

---

## Summary

**Design the first physical/SPICE-style common-mode inhibit + winner drain closure/drain candidate for the four-branch measurement chain**
