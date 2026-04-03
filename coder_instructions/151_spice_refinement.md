## SPICE Refinement

Refine physical front-end export/handoff so time-domain branch-power traces preserve detector winner-law fidelity

## Objective

Improve the boundary between the **physical/SPICE-style front-end candidate** and the frozen **detector+latch abstraction** so that the validated winner law is preserved end-to-end.

The current physical front-end candidate already reproduces the target branch energy fractions well, but the detector+latch handoff degrades winner-law fidelity beyond acceptance. This ticket is specifically to determine whether the failure comes from:

* the exported **time-domain branch-power representation**, or
* a mismatch between the front-end time structure and the detector abstraction.

This ticket must answer:

1. Can the physical front-end export a detector-facing time-domain signal that preserves the target winner law?
2. Which export/handoff mode is best:

   * direct sampled branch-power trace,
   * piecewise envelope approximation,
   * fitted exponential envelope?
3. Does the common-envelope assumption
   [
   P_k(t)\approx \Gamma(t),w_k
   ]
   actually hold in the physical front-end candidate at the time-domain level, or only after time integration?

---

## Background

The first physical/SPICE front-end candidate passed the **front-end-only** test:

* two-branch RMS energy-fraction error: **0.003008**
* max energy-fraction error: **0.004175**

but failed the **integrated winner-law** gate:

* integrated RMS winner-law error: **0.050038**
* integrated max winner-law error: **0.083333**

The current design note says the front-end exports actual load power traces and then compresses them into detector-facing exponential envelopes. That compression is the primary suspect.

So the problem is now understood as a **handoff/export problem**, not a front-end-weight problem.

---

## Scope

Included:

* refine branch-power export from physical front-end candidate
* compare multiple export/handoff modes
* quantify time-domain common-envelope fidelity
* re-run detector+latch integration for each export mode
* identify the best export contract for future SPICE work

Excluded:

* redesign of the physical front-end topology itself
* redesign of detector model
* redesign of latch
* physical detector hardware
* physical latch hardware
* physical drain/closure hardware
* four-branch physical candidate expansion (unless explicitly useful after two-branch fix)

---

## Functional requirements

### FR1 — Preserve physical front-end outputs

Do **not** change the front-end topology in this ticket. The existing physical front-end candidate remains the source of:

* branch voltage traces
* branch current traces
* branch power traces
* branch absorbed energies

### FR2 — Compare export modes

Implement and compare at least these three export modes:

#### Mode A — direct power-trace export

Pass the actual sampled branch-power trace (P_k(t)) directly into the detector adapter.

#### Mode B — piecewise envelope export

Approximate the branch-power trace using a piecewise-constant or piecewise-linear envelope with configurable resolution.

#### Mode C — fitted exponential export

Retain the current exponential compression/fitting method as a baseline.

### FR3 — Quantify common-envelope fidelity

For each benchmark case, compute
[
\Gamma_k(t)=\frac{P_k(t)}{w_k}
]
for all branches with nonzero (w_k), and measure how closely (\Gamma_k(t)) agrees across branches.

This is needed to determine whether the detector abstraction is being asked to consume something it was never designed for.

### FR4 — Re-run detector+latch integration

For each export mode, run the existing detector+latch chain and measure:

* two-branch winner-law error
* max winner-law error
* consistency relative to exact target weights

### FR5 — Choose and freeze best export contract

Select the export mode that best preserves winner-law fidelity and document it as the revised physical-front-end → detector interface.

---

## Inputs / outputs

### Inputs

* existing physical front-end candidate outputs
* exact target branch weights (w_i)
* frozen detector parameter set
* frozen latch abstraction
* benchmark states/analyzer settings

### Outputs

* export-mode comparison metrics
* revised detector-facing branch-envelope contract
* updated summary report
* recommendation for the next phase

---

## Deliverables

### Code deliverables

* [ ] direct trace export path
* [ ] piecewise envelope export path
* [ ] exponential export baseline path
* [ ] common-envelope fidelity metrics
* [ ] comparison driver
* [ ] updated integration summary report

### Artifact deliverables

* [ ] `artifacts/physical_front_end_handoff/direct_trace/`
* [ ] `artifacts/physical_front_end_handoff/piecewise_envelope/`
* [ ] `artifacts/physical_front_end_handoff/exponential_fit/`
* [ ] `artifacts/physical_front_end_handoff/comparison/`
* [ ] `summary_report.md`
* [ ] `summary_metrics.json`
* [ ] `summary_metrics.csv`

### Required design note

* [ ] `handoff_design_note.md`

This note must state:

* what each export mode means physically
* what detector-facing assumptions it preserves or violates
* which mode is adopted and why

---

## Required plots

* [ ] branch power traces (P_1(t),P_2(t)) for benchmark cases
* [ ] normalized (\Gamma_k(t)=P_k(t)/w_k) overlay plot
* [ ] exact vs exported envelope comparison
* [ ] winner-law error by export mode
* [ ] residual/error summary plot

---

## Quantitative acceptance criteria

### Front-end-only behavior

The current physical front-end candidate already passes front-end-only metrics. Preserve that performance:

* [ ] RMS energy-fraction error remains < 0.01
* [ ] max energy-fraction error remains < 0.02

### Handoff improvement target

The main target of this ticket is to reduce integrated winner-law error relative to the current baseline:

Current baseline:

* RMS winner-law error: **0.050038**
* max winner-law error: **0.083333**

Require the selected export mode to achieve:

* [ ] RMS winner-law error < 0.03
* [ ] max winner-law error < 0.05

Stretch target:

* [ ] RMS winner-law error < 0.02

### Common-envelope fidelity

For the chosen export mode, the branch-normalized envelopes should be sufficiently similar that detector bias is not dominated by time-structure mismatch.

Track and report:

* RMS difference between (\Gamma_1(t)) and (\Gamma_2(t))
* max difference
* case-by-case summary

No hard threshold required initially, but this metric must be reported and used to explain outcome fidelity.

---

## Benchmark cases

Use the same two-branch benchmark cases already used in the physical front-end candidate report:

### Case 1

Pole-state / rotated-analyzer benchmark

### Case 2

Equatorial-state / rotated-analyzer benchmark

### Case 3

At least one intermediate state/analyzer benchmark

For each case:

1. compute exact (w_1,w_2)
2. run physical front-end candidate
3. export branch-power signal in each mode
4. run detector+latch integration
5. compare final winner frequencies to exact weights

---

## Experimental / simulation plan

### Task 1 — Preserve and expose raw branch-power traces

Ensure the current front-end candidate exports raw sampled branch powers cleanly.

**Output**

* raw trace files
* branch trace plot

---

### Task 2 — Implement export mode A: direct trace

Feed the detector adapter the actual sampled branch-power trace directly.

**Output**

* direct-trace integration metrics
* direct-trace winner-frequency plots

---

### Task 3 — Implement export mode B: piecewise envelope

Implement configurable piecewise approximation of the raw power trace.

Parameters to expose:

* bin width
* piecewise mode (constant or linear)

**Output**

* piecewise integration metrics
* sensitivity to envelope resolution

---

### Task 4 — Keep export mode C: fitted exponential baseline

Retain the current exponential-fit export for direct comparison.

**Output**

* exponential baseline metrics

---

### Task 5 — Compute common-envelope fidelity

For each case and export mode:

* compute (\Gamma_k(t)=P_k(t)/w_k)
* compare branch-normalized envelopes
* summarize mismatch

**Output**

* common-envelope fidelity plots
* case summary table

---

### Task 6 — Compare and select best handoff mode

For all modes, compare:

* RMS winner-law error
* max winner-law error
* export complexity
* physical interpretability
* consistency with detector assumptions

**Output**

* comparison CSV
* recommended export mode
* revised handoff note

---

## Tests

Add tests for:

### T1

Raw trace export is valid and finite.

### T2

Piecewise export preserves total branch energy within tolerance.

### T3

Direct/piecewise/exponential export paths are consumable by the detector adapter.

### T4

Winner-law error is computed consistently across export modes.

### T5

Selected export mode improves on the current baseline.

---

## Explicit failure conditions

Reject the current handoff model and iterate again if:

* [ ] all export modes still produce RMS winner-law error (\ge 0.03)
* [ ] direct trace export still fails despite accurate front-end branch fractions
* [ ] common-envelope fidelity is poor enough to indicate the detector abstraction itself is incompatible with the physical front-end time structure
* [ ] the export requires hidden renormalization or undocumented correction factors

---

## Decision gate after this ticket

Proceed to the next phase only if:

1. one export/handoff mode restores acceptable winner-law fidelity,
2. the revised detector-facing interface is documented and stable,
3. the front-end → detector boundary is no longer the dominant source of error.

If these pass, the next ticket should be:

**Freeze the physical front-end export contract, then extend the physical/SPICE candidate toward the four-branch shared-state case or toward a more explicit resonant front-end realization.**

If they fail, revisit the detector abstraction assumptions before scaling up.

---

## Suggested labels

`research`
`front-end`
`integration`
`handoff`
`spice`
`high-priority`

---

## Summary

**Refine physical front-end export so time-domain branch-power traces preserve detector winner-law fidelity**
