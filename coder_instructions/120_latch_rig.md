# Design and characterize a common-mode / zero-sequence winner latch for the two-cell detector rig

## Objective

Implement and validate a **winner-take-all common-mode / zero-sequence latch** for the existing two-cell detector rig.

This latch must:

1. capture the **first** detector nucleation pulse,
2. declare exactly one winner,
3. suppress or mask later rival pulses,
4. hold the winner state until reset,
5. avoid materially disturbing the pre-click race law already validated in the two-cell detector experiment.

This is the next step after the detector-cell validation gate and is required before integrating the detector chain with the linear front-end or moving to SPICE.

---

## Background

The current detector rig results support proceeding to the latch phase:

* rare-event operating point exists,
* linear-hazard residual < 5%,
* dark counts are low relative to nominal signal-trigger rate,
* pulse integrity is good,
* two-cell gain mismatch is acceptable,
* two-branch race behavior matches the target first-click law with RMS error (\approx 0.0048).

The existing hardware concept is:

* matched absorber plus near-threshold avalanche/metastable latch detector cell,
* explicit reset path,
* timestamp/winner capture in a two-cell rig.

The missing piece is the **post-click exclusivity layer**:

* one winner only,
* loser masked,
* clean handoff to later energy-drain / closure logic.

This ticket covers that layer only.

---

## Scope

Included:

* latch logic design
* bench implementation in the two-cell rig
* first-arrival winner capture
* loser masking
* reset and holdoff handling
* verification that pre-click race statistics are not materially degraded

Excluded:

* four-branch latch
* physical drain/energy-redirection network
* shared-core / analyzer integration
* SPICE of full apparatus
* pre-click analog feedback into detector cells
* Kuramoto / entrainment mechanisms

---

## Functional requirements

### FR1 — First-arrival winner capture

Given detector output pulses `A_pulse` and `B_pulse`, the latch must:

* capture the first arriving pulse,
* set `winner = A` or `winner = B`,
* ignore later rival pulses until reset.

### FR2 — One-winner exclusivity

The latch must never declare both winners in a single trial.

### FR3 — Hold behavior

After winner capture:

* hold winner state stable until reset,
* expose winner state on output lines suitable for later integration with closure/drain hardware.

### FR4 — Loser suppression / masking

After first capture:

* suppress further rival counting,
* prevent double counting during detector dead time and reset holdoff.

### FR5 — Reset and re-arm

After reset:

* clear winner state,
* re-arm both channels,
* return to a neutral state with no retained winner memory.

### FR6 — Pre-click transparency

Before any click occurs, the latch must be electrically/logically quiet enough that it does **not materially distort** the already validated two-branch race law.

This is the most important system-level requirement.

---

## Inputs / outputs

### Inputs

* `A_pulse`: digital nucleation pulse from detector cell A
* `B_pulse`: digital nucleation pulse from detector cell B
* `reset`: global reset signal
* optional `holdoff_enable` or `trial_gate`

### Outputs

* `winner_A`
* `winner_B`
* `winner_valid`
* optional `mask_A`, `mask_B` to block further detector counting
* optional `winner_line` for later energy-drain/closure integration
* optional timestamped winner event for logging

---

## Design intent

The latch is the circuit realization of the **common-mode / zero-sequence closure** at the logic/event level.

Its role is **post-click only**:

* it does not create the branch weights,
* it does not determine the rare-event hazard law,
* it only enforces exclusivity after a winner has nucleated.

---

## Candidate implementation directions

Choose one practical first implementation, for example:

* SR-latch / cross-coupled set-reset logic fed by pulse shapers
* arbiter / first-edge capture logic
* fast comparator edge capture into a mutually exclusive latch
* FPGA/CPLD or discrete logic prototype if fastest for bench validation

The first implementation may be logic-level rather than fully analog, as long as timing and masking behavior can be characterized.

---

## Deliverables

### Hardware / logic deliverables

* [ ] latch block diagram
* [ ] latch schematic or logic design
* [ ] timing diagram for A-first, B-first, near-simultaneous, and reset sequences
* [ ] interface definition to detector cells
* [ ] interface placeholder for future drain/closure block

### Measurement deliverables

* [ ] first-arrival capture test results
* [ ] exclusivity test results
* [ ] double-count suppression results
* [ ] reset/re-arm results
* [ ] detector-race-with-latch results

### Artifacts

* [ ] `artifacts/latch_rig/latch_block_diagram.md`
* [ ] `artifacts/latch_rig/latch_schematic.md` or equivalent
* [ ] `artifacts/latch_rig/timing_cases.csv`
* [ ] `artifacts/latch_rig/first_arrival_tests.csv`
* [ ] `artifacts/latch_rig/exclusivity_tests.csv`
* [ ] `artifacts/latch_rig/reset_tests.csv`
* [ ] `artifacts/latch_rig/race_with_latch.csv`
* [ ] `artifacts/latch_rig/summary_metrics.json`
* [ ] summary markdown report

---

## Quantitative acceptance criteria

### A. First-arrival capture

For injected synthetic test pulses with known ordering:

* [ ] correct winner selected in >99.9% of clearly ordered cases
* [ ] no double-winner declaration

### B. Near-simultaneous behavior

For pulse arrival differences near the timing-resolution limit:

* [ ] tie-handling behavior is deterministic and documented
* [ ] no metastable undefined output state persists past the design settling time

### C. Exclusivity

* [ ] no second winner after first capture
* [ ] loser pulses after winner capture are ignored or masked

### D. Reset / re-arm

* [ ] reset clears latch reliably
* [ ] system re-arms cleanly
* [ ] no retained winner memory
* [ ] reset holdoff integrates correctly with detector dead time

### E. Pre-click transparency

With the latch attached, repeat the existing two-branch detector race tests and compare to the current baseline.

Acceptance targets:

* [ ] added RMS race error increase < 0.01
* [ ] no branch bias shift > 0.01 in benchmark splits
* [ ] no increase in timeout/undecided fraction beyond small documented tolerance

This is the critical integration gate.

---

## Experimental plan

### Task 1 — Define latch logic and timing requirements

Specify:

* pulse input assumptions
* minimum pulse width
* maximum expected jitter
* setup/hold behavior
* reset timing
* winner hold duration

**Output**

* timing-spec document
* truth table / state diagram

---

### Task 2 — Build synthetic-pulse testbench

Create a bench setup that injects controlled digital pulses into A and B inputs with adjustable time offset (\Delta t).

Test cases:

* A leads B by large margin
* B leads A by large margin
* A/B nearly simultaneous
* repeated pulses after winner set
* reset then retrigger

**Output**

* first-arrival test data
* tie-region characterization

---

### Task 3 — Verify one-winner exclusivity

Using synthetic pulses:

* ensure exactly one winner is declared
* ensure later pulses are masked

**Output**

* exclusivity summary
* edge-case report

---

### Task 4 — Integrate latch into two-cell detector rig

Attach the latch to the existing detector outputs.

Verify:

* pulse interface compatibility
* no missed captures
* no obvious loading or timing corruption

**Output**

* integrated rig block diagram
* detector+latch timing traces

---

### Task 5 — Repeat two-branch race experiment with latch attached

Reuse the benchmark branch splits:

* (0.50/0.50)
* (0.60/0.40)
* (0.70/0.30)
* (0.75/0.25)

Measure:

* winner frequency
* decisive fraction
* race RMS error
* deviation from no-latch baseline

**Output**

* race-with-latch CSV
* winner frequency vs target plot
* comparison-to-baseline plot

---

### Task 6 — Reset/recovery validation

Run repeated click/reset cycles and verify:

* winner state clears reliably
* both branches re-arm
* no state memory persists
* no new race bias appears after repeated runs

**Output**

* reset/recovery timing plot
* repeated-cycle stability summary

---

## Required metrics

### First-arrival metrics

* winner correctness rate
* double-winner count
* tie-region width
* latch settling time

### Integration metrics

* race RMS error
* race max error
* branch bias shift relative to no-latch baseline
* decisive fraction
* missed-winner rate

### Reset metrics

* reset success fraction
* re-arm latency
* post-reset bias drift

---

## Explicit failure conditions

Reject or redesign the latch if any of the following occur:

* [ ] double-winner declarations occur
* [ ] near-simultaneous inputs produce undefined persistent states
* [ ] latch loading materially changes detector pulse quality
* [ ] race RMS error degrades significantly relative to current detector-only baseline
* [ ] systematic bias appears toward A or B unrelated to branch power split
* [ ] reset fails to reliably clear state
* [ ] post-reset behavior drifts or retains winner memory

---

## Decision gate after this ticket

Proceed to the next phase only if:

1. first-arrival winner capture is reliable,
2. exclusivity is robust,
3. reset/re-arm is stable,
4. two-branch race law remains intact with the latch attached.

If these pass, the next ticket should be:

**Integrate the latch-enabled detector chain with the linear front-end and validate branch-weight → winner-law behavior end-to-end, then prepare a SPICE-facing abstraction.**

If these do not pass, revise latch design before any front-end integration.

---

## Suggested labels

`research`
`detector`
`latch`
`hardware`
`measurement`
`high-priority`

---

## Summary

**Build and validate a first-arrival common-mode winner latch for the two-cell detector rig**
