## Front End Detector Boundary Diagnosis

Diagnose physical-front-end → detector boundary by sweeping detector operating regime on exported branch-power traces

## Objective

Determine whether the failure of the physical-front-end → detector+latch handoff is caused by:

1. a **regime mismatch** at the detector boundary
   (wrong trace amplitude scale, exposure duration, or effective hazard scale),

or

2. a **deeper abstraction mismatch** between the physical front-end time structure and the frozen detector model.

This ticket is diagnostic only. It should not redesign:

* the physical front-end topology,
* the detector family,
* the latch.

Instead, it should answer:

> Can winner-law fidelity be recovered by changing only the detector-boundary operating regime on the already exported physical front-end traces?

---

## Background

The current handoff refinement established:

* front-end-only energy-fraction fidelity remains good,
* common-envelope mismatch is tiny,
* but integrated winner-law fidelity is poor,
* and decisive fraction is extremely low.

Representative results:

* best export mode: `piecewise:linear:20.0ms`
* winner-law RMS error: **0.155456**
* max winner-law error: **0.250000**
* mean decisive fraction: **0.013889**
* common-envelope RMS mismatch: **0.000042**

This strongly suggests the front-end weight geometry is not the problem. The immediate suspicion is that the detector abstraction is being driven in the wrong effective regime:

* too weak,
* too short,
* or otherwise outside the parameter window in which the reduced detector model was validated.

---

## Scope

Included:

* diagnostic sweeps on already exported physical front-end branch-power traces
* detector-boundary gain / scaling sweeps
* trial-duration / exposure sweeps
* expected-click-count diagnostics
* synthetic-envelope sanity comparison
* recommendation on whether the issue is calibration/regime or abstraction mismatch

Excluded:

* physical front-end redesign
* detector model redesign
* latch redesign
* four-branch physical expansion
* SPICE netlist changes
* hidden export corrections beyond explicit documented scaling sweeps

---

## Functional requirements

### FR1 — Detector-boundary power-scale sweep

Apply a scalar gain (g) to the exported branch-power traces before detector consumption:
[
P_k^{(g)}(t)=g,P_k(t)
]

Sweep over at least:

* 0.25×
* 0.5×
* 1×
* 2×
* 4×
* 8×
* 16×

For each (g), re-run detector+latch integration and record:

* decisive fraction
* RMS winner-law error
* max winner-law error

### FR2 — Detector-boundary time-window / exposure sweep

With fixed branch-power traces, vary the effective detector observation regime via one or more of:

* trial duration
* exposure time
* envelope truncation window
* detector step size / sampling horizon (if relevant)

Goal:

* test whether poor performance is due to too few expected clicks per trial.

### FR3 — Expected-click-count diagnostic

For each exported branch-power trace, compute the detector-model-implied expected event count:
[
\mu_k = \int \lambda_k(t),dt
]
under the current detector abstraction.

At minimum report:

* mean (\mu_k)
* distribution of (\mu_k) across benchmark cases
* relation between (\mu_k), decisive fraction, and winner-law error

### FR4 — Synthetic common-envelope sanity test

Construct a synthetic detector input trace using the same measured common envelope but analytically imposed branch weighting:
[
\tilde P_k(t)=\Gamma_{\text{meas}}(t),w_k
]

Then run the detector+latch chain on this synthetic trace.

This test must determine whether failure is due to:

* the physical export path itself, or
* the detector regime applied to the same time structure.

### FR5 — Root-cause recommendation

At the end of the ticket, provide a recommendation classifying the failure as one of:

* **regime mismatch**
* **adapter/export mismatch**
* **deeper detector abstraction mismatch**

and justify that classification from the measured diagnostics.

---

## Inputs / outputs

### Inputs

* existing physical front-end branch-power traces
* current exact branch weights (w_k)
* frozen detector parameter set
* frozen latch abstraction
* benchmark cases already used in the handoff refinement flow

### Outputs

* scale-sweep metrics
* exposure/time-window-sweep metrics
* expected-click-count summaries
* synthetic-envelope comparison results
* root-cause recommendation

---

## Deliverables

### Code deliverables

* [ ] boundary gain/scale sweep driver
* [ ] trial-window / exposure sweep driver
* [ ] expected-click-count diagnostic module
* [ ] synthetic common-envelope test module
* [ ] comparison/summary report builder

### Artifact deliverables

* [ ] `artifacts/physical_front_end_boundary_diagnosis/scale_sweep/`
* [ ] `artifacts/physical_front_end_boundary_diagnosis/time_window_sweep/`
* [ ] `artifacts/physical_front_end_boundary_diagnosis/expected_click_count/`
* [ ] `artifacts/physical_front_end_boundary_diagnosis/synthetic_envelope/`
* [ ] `artifacts/physical_front_end_boundary_diagnosis/summary_report.md`
* [ ] `artifacts/physical_front_end_boundary_diagnosis/summary_metrics.json`
* [ ] `artifacts/physical_front_end_boundary_diagnosis/summary_metrics.csv`

### Required design/analysis note

* [ ] `boundary_diagnosis_note.md`

This note must state:

* what was varied,
* what was held fixed,
* what the results imply about the source of failure,
* what the recommended next action is.

---

## Required plots

* [ ] decisive fraction vs power-scale gain
* [ ] winner-law RMS error vs power-scale gain
* [ ] decisive fraction vs trial window / exposure
* [ ] winner-law RMS error vs trial window / exposure
* [ ] expected-click-count histogram or summary plot
* [ ] synthetic-envelope vs physical-export comparison plot
* [ ] diagnosis summary plot

---

## Quantitative acceptance criteria

### Diagnostic success criterion

This is not a product acceptance ticket. It is a diagnosis ticket.

It succeeds if it can answer, with evidence, one of the following:

#### Outcome A — regime mismatch

A detector-boundary operating regime exists (via gain and/or exposure scaling) such that:

* decisive fraction rises substantially,
* winner-law RMS error falls below 0.03,
* without changing front-end topology or detector model.

#### Outcome B — export/adapter mismatch

Synthetic-envelope tests succeed while physical-export tests fail, indicating the issue lies in export/adapter representation.

#### Outcome C — deeper abstraction mismatch

No reasonable gain/exposure scaling or synthetic-envelope reconstruction restores winner-law fidelity, implying the frozen detector abstraction is incompatible with the physical front-end time structure.

Any of A, B, or C is a successful diagnostic outcome, provided it is supported clearly.

---

## Benchmark cases

Use the same benchmark set as the physical front-end candidate and handoff-refinement tickets.

For each case:

1. compute exact (w_1,w_2)
2. run physical front-end candidate
3. export branch-power traces
4. apply scale sweep and/or exposure sweep
5. run detector+latch
6. compare decisive fraction and winner-law fidelity

---

## Experimental / simulation plan

### Task 1 — Add power-scale sweep

For each benchmark case and export mode, multiply branch-power traces by scalar gain (g) before detector handoff.

Sweep:

* (g \in {0.25, 0.5, 1, 2, 4, 8, 16})

Record:

* decisive fraction
* RMS winner-law error
* max winner-law error

**Output**

* scale-sweep CSV
* scale-sweep plots

---

### Task 2 — Add trial-window / exposure sweep

Hold trace amplitudes fixed, vary detector exposure regime by one or more of:

* trial duration
* maximum detector observation time
* detector time horizon
* envelope support window

Record:

* decisive fraction
* RMS winner-law error

**Output**

* time-window-sweep CSV
* time-window plots

---

### Task 3 — Compute expected click count

For each branch trace under each diagnostic configuration, compute:
[
\mu_k=\int \lambda_k(t),dt
]

Report:

* mean (\mu_k)
* max/min (\mu_k)
* relation to decisive fraction

**Output**

* expected-click-count CSV
* histogram/summary plot

---

### Task 4 — Synthetic common-envelope sanity test

Construct synthetic traces of the form
[
\tilde P_k(t)=\Gamma_{\text{meas}}(t),w_k
]
using the measured front-end common envelope but exact target weighting.

Run the detector+latch chain on these traces.

Compare:

* physical-export result
* synthetic-envelope result

**Output**

* synthetic-vs-physical comparison CSV
* comparison plot

---

### Task 5 — Root-cause analysis and recommendation

Aggregate the diagnostics and classify the failure as:

* regime mismatch,
* export mismatch,
* deeper abstraction mismatch.

**Output**

* `boundary_diagnosis_note.md`
* recommendation in summary report

---

## Tests

Add tests for:

### T1

Scale sweep executes and records metrics for all benchmark cases.

### T2

Expected-click-count calculation is finite and monotone under simple scaling checks.

### T3

Synthetic-envelope trace generation preserves exact target branch-weight ratios.

### T4

Summary report classifies outcome deterministically based on metrics.

---

## Explicit failure conditions

This ticket is only a failure if it produces no interpretable answer.

Examples of unacceptable outcomes:

* [ ] diagnostics are run but do not isolate whether failure is amplitude/time-scale or abstraction mismatch
* [ ] no expected-click-count reporting is produced
* [ ] synthetic-envelope test is omitted
* [ ] summary recommendation is ambiguous or unsupported

---

## Decision gate after this ticket

### If Outcome A (regime mismatch)

Open next ticket:
**Calibrate the physical-front-end → detector boundary to the recovered operating regime and re-run the handoff validation.**

### If Outcome B (export/adapter mismatch)

Open next ticket:
**Redesign the detector-facing export/adapter while preserving the physical front-end and frozen detector family.**

### If Outcome C (deeper abstraction mismatch)

Open next ticket:
**Revisit frozen detector abstraction assumptions for physical front-end time-structured inputs before further SPICE scaling.**

---

## Suggested labels

`research`
`front-end`
`detector`
`boundary`
`diagnostics`
`high-priority`

---

## Summary

**Diagnose whether physical-front-end handoff failure is detector-regime mismatch or abstraction mismatch**
