## Common Inhibit Tuning

Tune the common inhibit rail + winner-gated shunt drain candidate to achieve winner-drain dominance

## Objective

Iterate on the first physical closure/drain implementation candidate so that the preferred topology

* **common inhibit rail**
* **winner-gated shunt drain**

achieves **winner-drain dominance** while preserving:

* pre-click transparency
* post-click loser suppression
* monotonic shared-energy decay
* reproducible trial completion

This ticket is **not** a topology change ticket. It is a **parameter/tuning ticket** for the preferred closure interpretation.

The central question is:

> Can the existing common inhibit + winner-drain topology be tuned so that the winner drain captures a sufficiently dominant share of post-click energy without disturbing the already validated pre-click chain?

---

## Background

The first physical closure/drain candidate established:

### Passed

* pre-click transparency shift: **0.000000**
* transparency pass: **True**
* completion rate: **0.994167**
* mean completion time: **2.607534 s**
* monotonic shared energy: **True**
* reduced-consistency pass: **True**

### Failed

* mean winner drain fraction: **0.847713**
* mean loser residual fraction: **0.003998**
* winner drain dominance pass: **False**

This suggests the topology is conceptually correct but not yet quantitatively strong enough:

* common-mode inhibit is behaving correctly,
* winner-only drain activation exists,
* loser suppression is substantial,
* but the winner drain does not yet dominate post-click energy strongly enough.

So the next step is to **tune the candidate**, not replace it.

---

## Scope

Included:

* tuning of the existing common inhibit + winner drain candidate
* parameter sweeps of inhibit, clamp, and drain strengths/timing
* post-click exclusivity optimization
* reduced-model comparison
* updated closure/drain summary report

Excluded:

* topology replacement
* front-end redesign
* detector redesign
* latch redesign
* transistor-level implementation
* final hardware co-design
* reset system redesign

---

## Design intent

Keep the preferred interpretation fixed:

> **common-mode inhibit + winner drain**

and improve its quantitative behavior by adjusting:

* how fast the inhibit rail rises,
* how strongly losers are clamped,
* how strongly and how quickly the winner drain turns on,
* how completion is defined if needed.

The intended result is:

* more post-click energy routed into the winner drain,
* less residual non-winner energy,
* no loss of pre-click transparency.

---

## Functional requirements

### FR1 — Preserve pre-click transparency

The closure/drain block must remain inactive before `winner_valid=True`.

Pre-click winner-law transparency must remain essentially unchanged relative to the current validated detector+latch baseline.

### FR2 — Improve winner-drain dominance

The tuned candidate must increase the winner drain share of post-click energy relative to the first candidate.

### FR3 — Preserve loser suppression

Loser suppression must remain strong and should improve if possible.

### FR4 — Preserve monotonic energy decay

Remaining shared energy after winner capture must continue to decay monotonically.

### FR5 — Preserve trial completion

Completion rate and completion semantics must remain stable and well-defined.

### FR6 — Stay within current interpretation

The implementation must remain recognizably the same preferred topology:

* one common inhibit rail
* one winner-gated drain path
* loser suppression via the common inhibit action and branch clamp path

No hidden topology change or interpretation switch is allowed in this ticket.

---

## Parameters to tune

At minimum, expose and sweep:

### P1 — Inhibit rail rise parameters

* inhibit rise rate / time constant
* inhibit saturation level
* optional inhibit onset delay relative to `winner_valid`

### P2 — Loser clamp strength

* loser clamp conductance scale
* loser clamp time constant or rise profile
* final loser residual conductance floor

### P3 — Winner drain strength

* winner drain conductance scale
* winner drain turn-on time constant
* winner drain saturation level

### P4 — Optional completion threshold

If needed, adjust:

* trial-complete threshold
* drain-current cutoff threshold
* shared-energy completion fraction

Only if this affects meaningful trial completion semantics; it should not be used to hide weak drain performance.

---

## Inputs / outputs

### Inputs

* `winner_valid`
* `winner_index` / one-hot `SEL_WIN[k]`
* current resonant front-end residual energy observables
* current branch observables
* tuned closure/drain parameters

### Outputs

* `V_inhibit(t)` or equivalent common inhibit signal
* loser clamp conductance traces
* winner drain conductance traces
* winner drain current/power
* remaining shared energy
* `trial_complete`

---

## Deliverables

### Code deliverables

* [ ] parameterized closure/drain tuning module
* [ ] sweep driver for inhibit/clamp/drain parameters
* [ ] metrics/plots/report builder
* [ ] updated tests

### Artifact deliverables

* [ ] `artifacts/physical_closure_drain_tuning/parameter_sweeps/`
* [ ] `artifacts/physical_closure_drain_tuning/best_candidate/`
* [ ] `artifacts/physical_closure_drain_tuning/summary_report.md`
* [ ] `artifacts/physical_closure_drain_tuning/summary_metrics.json`
* [ ] `artifacts/physical_closure_drain_tuning/summary_metrics.csv`
* [ ] `artifacts/physical_closure_drain_tuning/tuned_candidate_design_note.md`

### Required design note

* [ ] `tuned_candidate_design_note.md`

This note must include:

* what parameters were tuned
* what changed relative to the first candidate
* what the best tuned configuration is
* why it remains the same preferred topology
* what still remains abstract

---

## Required plots

* [ ] winner drain fraction vs winner drain strength
* [ ] winner drain fraction vs loser clamp strength
* [ ] winner drain fraction vs inhibit rise rate
* [ ] loser residual fraction vs tuned parameters
* [ ] terminal loser suppression vs tuned parameters
* [ ] completion rate/time vs tuned parameters
* [ ] pre-click transparency shift vs tuned parameters
* [ ] best tuned candidate post-click energy partition plot

---

## Quantitative acceptance criteria

### A. Pre-click transparency

* [ ] winner-law RMS transparency shift remains negligible and documented
* [ ] no measurable pre-click distortion beyond a small tolerance

### B. Winner-drain dominance

Tune until the candidate satisfies a stronger winner-dominance condition.

At minimum require:

* [ ] mean winner drain fraction increased relative to **0.847713**
* [ ] mean loser residual fraction remains small
* [ ] winner drain dominance pass = **True**

If an explicit threshold is needed, document it in the report.

### C. Loser suppression

* [ ] terminal loser suppression remains high and preferably improves over the first candidate

### D. Trial completion

* [ ] completion rate remains high
* [ ] shared energy remains monotonic after closure activation
* [ ] completion remains well-defined

### E. Reduced-model consistency

* [ ] tuned candidate remains consistent with the preferred reduced closure interpretation:

  * common-mode inhibit
  * winner-only drain
  * post-click-only activation

---

## Benchmark integration tasks

### Task 1 — Build parameter sweep harness

Expose at least the key parameters:

* inhibit rise
* loser clamp strength
* winner drain strength

Run sweeps over the current closure/drain integration flow.

**Output**

* parameter sweep CSVs
* parameter response plots

---

### Task 2 — Identify best tuned configuration

Find the best candidate that improves winner drain dominance while preserving transparency and completion behavior.

**Output**

* `best_candidate/` artifact set
* tuned parameter table

---

### Task 3 — Compare against first candidate

For the best tuned candidate, compare directly to the first closure/drain candidate on:

* winner drain fraction
* loser residual fraction
* terminal loser suppression
* completion rate
* completion time
* pre-click transparency shift

**Output**

* comparison CSV
* comparison section in summary report

---

### Task 4 — Reduced-consistency check

Confirm that the tuned candidate still matches the intended reduced interpretation and has not drifted into a different mechanism.

**Output**

* reduced-consistency summary
* note in design document

---

## Tests

Add tests for:

### T1

Closure remains inactive before `winner_valid`.

### T2

Winner drain fraction improves under stronger drain / clamp settings in a controlled monotone sanity case.

### T3

Loser suppression remains strong after tuning.

### T4

Shared energy remains monotonic after closure activation.

### T5

Best tuned candidate improves on the first candidate.

---

## Explicit failure conditions

Reject the tuned candidate if any of the following occur:

* [ ] winner-drain dominance still fails after reasonable tuning sweeps
* [ ] tuning improves winner drain share only by breaking pre-click transparency
* [ ] loser suppression degrades materially
* [ ] completion behavior becomes unstable or ambiguous
* [ ] the implementation effectively changes interpretation instead of tuning the chosen topology

---

## Decision gate after this ticket

Proceed only if:

1. winner drain dominance now passes,
2. pre-click transparency remains intact,
3. loser suppression and completion remain good,
4. the candidate still cleanly represents the preferred “common inhibit + winner drain” interpretation.

If these pass, the next ticket should be either:

* **integrate the tuned physical closure/drain candidate with the resonant front-end as the preferred physical chain**, or
* **move one step deeper toward a more explicit circuit/netlist realization of the closure/drain path**.

If they fail, then consider revisiting the closure topology itself.

---

## Suggested labels

`research`
`closure`
`drain`
`post-click`
`tuning`
`integration`
`high-priority`

---

## Summary

**Tune the common inhibit rail + winner-gated shunt drain closure candidate to achieve winner-drain dominance while preserving pre-click transparency**
