# Latch-enabled detector integration

Abstract: Integrate latch-enabled detector chain with the linear front-end and validate branch-weight → winner-law behavior end-to-end

## Objective

Connect the already validated detector layer

* branch detector cell
* first-arrival winner latch
* reset/re-arm logic

to the existing linear front-end so that the full chain can be tested end-to-end:

[
\text{linear branch weights} ;\to; \text{detector nucleation} ;\to; \text{winner latch} ;\to; \text{exclusive outcome}
]

This ticket must answer:

1. Does the latch-enabled detector chain preserve the target winner law when driven by the actual front-end branch weights?
2. Does the four-branch shared-state version still reproduce the target correlator and CHSH values after the full detector+latch layer is inserted?
3. Can the resulting composed system be summarized as a clean SPICE-facing abstraction for later circuit implementation?

---

## Background

The current work has already passed two key gates:

### Detector-cell gate

A matched absorber plus near-threshold avalanche/metastable latch cell exhibits:

* rare-event regime
* approximately linear hazard vs absorbed power
* acceptable dark counts
* stable dead time/reset
* strong two-cell race-law fidelity.

### Winner-latch gate

The common-mode / zero-sequence winner latch:

* captures first arrival correctly
* enforces exclusivity
* resets cleanly
* adds essentially zero measurable distortion to the detector race law.

So the next missing step is the **full integration** of:

* linear front-end branch-weight generator
* detector cells
* winner latch

before moving to SPICE or physical shared-core hardware.

---

## Scope

Included:

* two-branch end-to-end integration
* four-branch end-to-end integration
* exact vs empirical branch-weight comparison
* correlator and CHSH validation through detector+latch
* mismatch sweeps at the integrated level
* SPICE-facing abstraction document

Excluded:

* physical SPICE netlists of the full hardware
* physical shared-core tank implementation
* analog post-click drain hardware
* full zero-sequence/common-mode energy-drain circuit
* new detector-cell redesign

---

## Functional requirements

### FR1 — Two-branch end-to-end mapping

Given a two-branch front-end producing weights
[
w_1,; w_2,\qquad w_1+w_2=1,
]
the integrated detector+latch chain must produce winner frequencies
[
\hat p_1,; \hat p_2
]
that track (w_1,w_2) within tolerance.

### FR2 — Four-branch end-to-end mapping

Given a four-branch front-end producing weights
[
w_{++},w_{+-},w_{-+},w_{--},
\qquad \sum w_{xy}=1,
]
the integrated detector+latch chain must produce empirical branch frequencies
[
\hat p_{++},\hat p_{+-},\hat p_{-+},\hat p_{--}
]
that track the exact weights within tolerance.

### FR3 — Correlator preservation

Using the four-branch empirical frequencies,
[
E = p_{++}-p_{+-}-p_{-+}+p_{--}
]
must still match the target correlator.

### FR4 — CHSH preservation

For the benchmark settings,
[
a_0=0^\circ,\quad a_1=45^\circ,\quad b_0=22.5^\circ,\quad b_1=-22.5^\circ,
]
the empirical CHSH value must remain close to the target magnitude (2\sqrt2).

### FR5 — SPICE-facing abstraction

Produce a module/interface definition that represents:

* branch absorbed-power envelopes from the front-end
* detector-cell pulse generation
* winner-latch exclusivity
* post-click winner output for later drain/closure design

---

## Inputs / outputs

### Inputs

* exact front-end branch weights (2-branch or 4-branch)
* detector parameters (use current validated candidate by default)
* latch parameters (use current validated candidate by default)
* envelope model for branch absorbed power

### Outputs

* winner frequencies
* branch-weight error metrics
* correlator and CHSH summaries
* mismatch sensitivity summaries
* SPICE-facing abstraction document

---

## Deliverables

### Code deliverables

* [ ] integrated two-branch driver
* [ ] integrated four-branch driver
* [ ] end-to-end metrics module
* [ ] CHSH evaluation module
* [ ] mismatch sweep driver
* [ ] SPICE-facing abstraction markdown

### Artifact deliverables

* [ ] `artifacts/front_end_integration/two_branch/`
* [ ] `artifacts/front_end_integration/four_branch/`
* [ ] `artifacts/front_end_integration/mismatch/`
* [ ] `artifacts/front_end_integration/spice_abstraction.md`
* [ ] summary markdown report
* [ ] summary JSON/CSV metrics

### Required plots

* [ ] exact vs empirical two-branch winner frequencies
* [ ] exact vs empirical four-branch weights
* [ ] correlator exact vs empirical
* [ ] CHSH exact vs empirical
* [ ] integrated mismatch sensitivity

---

## Quantitative acceptance criteria

### Two-branch integration

Across benchmark states/analyzers:

* [ ] RMS winner-law error < 0.02
* [ ] max winner-law error < 0.05

### Four-branch integration

Across benchmark angle pairs:

* [ ] RMS four-branch weight error < 0.03
* [ ] max branch-frequency error < 0.05

### Correlator

* [ ] correlator RMS error vs target < 0.05

### CHSH

* [ ] empirical (|S|) within 0.1 of target in benchmark runs

### Integrated robustness

Under ±2% detector mismatch:

* [ ] no catastrophic failure of winner-law fidelity
* [ ] no large unexpected branch bias
* [ ] correlator and CHSH remain within documented tolerance

---

## Experimental / simulation plan

### Task 1 — Wire two-branch front-end into detector+latch chain

Use the existing two-branch front-end weights from the linear model.

For a set of benchmark states and analyzer settings:

1. compute exact (w_1,w_2)
2. drive detector cells with corresponding absorbed-power envelopes
3. apply winner latch
4. run many trials
5. compare empirical frequencies to exact weights

**Output**

* two-branch summary CSV
* two-branch winner plot
* RMS/max error summary

---

### Task 2 — Wire four-branch front-end into detector+latch chain

Use the existing reduced shared 4-mode front-end.

For benchmark ((a,b)) settings:

1. compute exact (w_{xy}(a,b))
2. drive four detector branches
3. apply winner latch
4. run many trials
5. compare empirical branch frequencies to exact weights

**Output**

* four-branch summary CSV
* four-branch weight plot
* RMS/max error summary

---

### Task 3 — Correlator and CHSH validation

From the empirical four-branch frequencies, compute:
[
E(a,b)=p_{++}-p_{+-}-p_{-+}+p_{--}
]
and the benchmark CHSH combination.

Compare:

* exact vs empirical correlator
* exact vs empirical CHSH

**Output**

* correlator comparison plot
* CHSH comparison plot
* summary metrics JSON

---

### Task 4 — Integrated mismatch sweeps

Repeat two-branch and four-branch runs under controlled perturbations:

* detector gain mismatch
* dark-count mismatch
* dead-time mismatch
* latch timing perturbation if relevant

**Output**

* mismatch CSV
* mismatch sensitivity plot
* robustness summary

---

### Task 5 — Write SPICE-facing abstraction

Write a short engineering note defining the abstraction boundary between:

* linear front-end
* detector cell
* winner latch
* future drain/closure block

The abstraction should define:

#### Front-end output

For each branch (k),
[
P_k(t)=\Gamma(t),w_k
]

#### Detector output

For each branch (k), a digital nucleation pulse with calibrated hazard approximately
[
\lambda_k(t)\approx \lambda_{\text{dark}}+\alpha P_k(t)
]

#### Latch output

* one winner line
* one winner-valid flag
* loser suppression semantics
* reset/re-arm semantics

**Output**

* `spice_abstraction.md`

---

## Required benchmark cases

### Two-branch

Use:

* pure pole states
* equatorial states
* several analyzer rotations

### Four-branch

Use singlet-like shared state and at least:

* (a=b=0^\circ)
* (a=45^\circ,\ b=22.5^\circ)
* (a=0^\circ,\ b=45^\circ)

### CHSH

Use:
[
a_0=0^\circ,\ a_1=45^\circ,\ b_0=22.5^\circ,\ b_1=-22.5^\circ
]

---

## Explicit failure conditions

Reject or revise the integration if any of the following occur:

* [ ] two-branch winner frequencies no longer track exact weights
* [ ] four-branch empirical frequencies drift materially from exact weights
* [ ] correlator deviates significantly from target
* [ ] CHSH degrades unexpectedly relative to reduced detector-only benchmark
* [ ] latch causes integrated branch bias not seen in standalone tests
* [ ] mismatch sensitivity becomes much worse after full integration

---

## Decision gate after this ticket

Proceed to SPICE-facing implementation work only if:

1. two-branch end-to-end winner-law behavior is preserved,
2. four-branch end-to-end branch frequencies match exact weights,
3. correlator and CHSH remain accurate after detector+latch integration,
4. the SPICE-facing abstraction is stable and well-defined.

If these conditions pass, the next ticket should be:

**Build the first SPICE-facing surrogate of the linear front-end + detector pulse abstraction, then begin physical closure/drain integration.**

If they do not pass, debug integration boundaries before any SPICE work.

---

## Labels

`research`
`integration`
`detector`
`latch`
`measurement`
`high-priority`

---

## Summary

**Validate end-to-end branch-weight → winner-law behavior with latch-enabled detector integration and define a SPICE-facing abstraction**
