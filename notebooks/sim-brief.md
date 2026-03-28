# Simulation Brief

**Project:** Sequential Anisotropic-Damping Modal Simulator
**Objective:** Test whether **finite-window anisotropic damping in a rotated (S_p/S_m) basis** can generate sphere-style projective state updates as an emergent dynamical mechanism.

---

## 1. Purpose

Build a simulation that tests the following hypothesis:

> If an analyzer damps one rotated modal component much more strongly than the orthogonal component during a finite extraction window, then passive depletion can approximate a **projective state update**.

This simulation is the next bridge between:

* the earlier **continuous PE-style geometry**,
* the **sphere/sequential-update model**,
* and a future **physically realizable circuit mechanism**.

This simulator should **not** hard-code Bell correlations, collapse probabilities, or pair outcomes.

Instead, it should simulate explicit **two-mode state evolution under anisotropic damping** and determine whether the desired discrete-update structure emerges.

---

## 2. Core question

Can a finite two-mode source state, evolved under **rotated anisotropic damping**, produce:

1. a clean outcome-conditioned residual branch,
2. a meaningful sequential second measurement,
3. discrete pair outcomes,
4. low marginal drift,
5. and possibly the target angle-law structure,

**without** imposing the sphere model by hand?

---

## 3. Immediate success criterion

The first success criterion is **not CHSH**.

The first success criterion is:

> Does the post-window state cluster near the complementary residual branch when damping is strongly anisotropic in the analyzer basis?

If that fails, the mechanism is probably not the right bridge.

If that succeeds, then sequential pair statistics become worth studying.

---

## 4. State model

## 4.1 Source state

Represent the source as a 2-mode state in the (S_p/S_m) basis.

Acceptable forms:

### Real 2D state

[
\psi =
\begin{bmatrix}
x_p\
x_m
\end{bmatrix}
]

### Complex 2-mode envelope

[
\psi =
\begin{bmatrix}
a_p\
a_m
\end{bmatrix}
]

The simulator should support whichever is cleaner numerically, but the code must make the basis explicit.

## 4.2 Initial condition

Each trial must support randomized initial state orientation, e.g.

* fixed radius with random phase/orientation,
* optional amplitude imbalance,
* optional noise.

At minimum:

* uniform phase sampling on the effective modal circle/sphere slice.

---

## 5. Analyzer model

## 5.1 Rotated analyzer basis

Each analyzer at angle (\phi) defines rotated basis vectors:
[
u_+(\phi),\quad u_-(\phi)
]

Equivalent matrix form:
[
R(\phi)=
\begin{bmatrix}
\cos\phi & -\sin\phi\
\sin\phi & \cos\phi
\end{bmatrix}
]

with analyzer-basis coordinates:
[
\psi_\phi = R(-\phi)\psi.
]

## 5.2 Damping operator

The analyzer acts through anisotropic damping in its own basis.

Define:
[
D_\phi = R(\phi)
\begin{bmatrix}
\gamma_+ & 0\
0 & \gamma_-
\end{bmatrix}
R(-\phi)
]

where:

* (\gamma_+) = damping rate along analyzer-aligned branch
* (\gamma_-) = damping rate along orthogonal branch

This is the central mechanism.

## 5.3 Finite-window update

Over extraction window (T_w), update the state by:
[
\psi' = e^{-D_\phi T_w}\psi
]

If using an ODE integration rather than matrix exponential, that is fine, but this is the reference behavior.

---

## 6. Window durations

The simulator must support:

* (T/6)
* (T/4)
* (T/3)
* (T/2)
* (T)

Primary focus:

* (T/4)

Reason:

* earlier analysis suggests (T/4) is the most promising for projective-like behavior.

Also test (T/2) and (T) explicitly to confirm whether they wash out useful structure in this model.

---

## 7. Single-analyzer mode: required studies

Before doing two-analyzer sequential statistics, the simulator must characterize the single-analyzer update.

For each initial state and analyzer angle:

1. rotate into analyzer basis
2. apply anisotropic damping
3. compute post-window state
4. measure how close the residual is to (u_+) or (u_-)

### Required outputs

* initial analyzer-basis components (c_+, c_-)
* post-window analyzer-basis components (c_+', c_-')
* total norm/energy before and after
* quality-to-(u_+)
* quality-to-(u_-)

### Required metric

Define a **projectivity score** that quantifies whether the post-window state moves toward the complementary residual branch.

At minimum, include:

* normalized branch dominance ratio
* residual branch purity
* clusterability across trials

---

## 8. Sequential two-analyzer mode

Once single-analyzer projectivity is characterized, implement sequential measurement.

For each trial:

### Step 1

Initialize source state (\psi_0)

### Step 2

Alice applies anisotropic damping at angle (\phi_A):
[
\psi_A = e^{-D_{\phi_A}T_w}\psi_0
]

### Step 3

Assign Alice’s discrete outcome using one of the outcome rules below.

### Step 4

Propagate the residual state to Bob:
[
\psi_{\text{in},B} = \psi_A
]
or optional free evolution between stages if configured.

### Step 5

Bob applies anisotropic damping at angle (\phi_B):
[
\psi_B = e^{-D_{\phi_B}T_w}\psi_{\text{in},B}
]

### Step 6

Assign Bob’s discrete outcome.

### Step 7

Record pair statistics.

---

## 9. Outcome assignment rules

Implement at least three selectable rules.

## Rule R1 — Dominant analyzer component

Before or after the window, compare analyzer-basis component magnitudes:

[
A=+1 \text{ if } |c_+|^2 > |c_-|^2,\qquad A=-1 \text{ otherwise}
]

Coder should allow:

* pre-update dominance
* post-update dominance
* dominance shift

as separate options.

## Rule R2 — Extracted-energy branch winner

Define extracted energy per branch from damping-induced norm loss:

[
E_+ = |c_+|^2 - |c_+'|^2,\qquad E_- = |c_-|^2 - |c_-'|^2
]

Then:
[
A=+1 \text{ if } E_+ > E_-,\qquad A=-1 \text{ otherwise}
]

## Rule R3 — Residual-state classifier

Assign the outcome according to which ideal branch residual the post-window state is closer to.

This rule is especially important for evaluating sphere-style behavior.

---

## 10. Required parameter sweeps

Sweep all of these.

## 10.1 Damping strengths

* (\gamma_+)
* (\gamma_-)

Must include regimes:

* isotropic: (\gamma_+ \approx \gamma_-)
* weak anisotropy
* moderate anisotropy
* strong anisotropy
* near-projective anisotropy

## 10.2 Anisotropy ratio

Explicitly sweep:
[
r = \gamma_+/\gamma_-
]

This is likely the key control parameter.

## 10.3 Window duration

All five window lengths listed above.

## 10.4 Analyzer angles

At minimum:

* (0^\circ)
* (22.5^\circ)
* (45^\circ)
* (67.5^\circ)
* (90^\circ)

Also support dense angle sweeps.

## 10.5 Initial state family

* fixed radius, random phase
* optional mode imbalance
* optional perturbation/noise

---

## 11. Primary metrics

These must be reported for every parameter sweep.

## M1 — Projectivity score

How strongly the post-window state aligns with the complementary residual branch.

Target:

* low for isotropic damping
* high for strongly anisotropic damping

## M2 — Residual branch quality

Quality metrics toward (u_+) and (u_-), before and after update.

## M3 — State-manifold closure

Whether the post-update state stays on the intended two-mode manifold.

## M4 — Single-analyzer angle law

Whether the extracted-energy response exhibits the expected double-angle structure.

## M5 — Sequential aligned-analyzer support

At (\phi_A=\phi_B), measure:

* same-sign mass
* anti-sign mass

This is a crucial diagnostic.

## M6 — Marginal drift

For sequential runs:

* Alice marginal drift vs Bob setting
* Bob marginal drift vs Alice setting

## M7 — Correlation function

Compute:
[
E(\phi_A,\phi_B)
]
from the generated pairs.

## M8 — CHSH summary

Only as a secondary metric, after M1–M7.

---

## 12. Required failure-mode detection

The simulator must explicitly identify and label these failure cases.

### F1 — Isotropic / nonprojective regime

Residual state does not select a complementary branch.

### F2 — Generic deformation

State moves, but not toward a clean branch.

### F3 — Signaling regime

Sequential dependence produces substantial marginal drift.

### F4 — Washout regime

Long windows erase useful branch-discriminating structure.

### F5 — Overfit outcome rule

If the output law looks good only because the readout rule is effectively imposing the answer, this must be called out.

---

## 13. Required comparisons

The final report must compare the anisotropic-damping mechanism qualitatively against these known families:

* independent local randomness
* deterministic local threshold
* shared classical threshold carrier
* weak shared-source dynamics
* strong shared-source dynamics
* sequential-update toy model

The report should answer:

> Does anisotropic damping behave more like generic depletion, or more like the sphere/sequential-update family?

---

## 14. Code structure requirements

Required modules/functions:

### `state.py`

* source state representation
* basis transforms
* initialization utilities

### `damping.py`

* construction of (D_\phi)
* matrix exponential or ODE integrator
* finite-window update

### `readout.py`

* outcome rules R1–R3
* extracted-energy metrics
* residual classifiers

### `simulate_single.py`

* single-analyzer sweeps

### `simulate_sequential.py`

* Alice→Bob sequential trials

### `metrics.py`

* projectivity score
* marginal drift
* aligned support
* correlation / CHSH summaries

### `run_sweeps.py`

* batch experiments
* save results

### `analyze_results.py`

* plots, tables, summaries

---

## 15. Output artifacts

For each sweep, save:

* config parameters
* initial state samples
* post-Alice state samples
* post-Bob state samples
* per-trial outcomes
* per-trial extracted energies
* per-sweep projectivity summary
* per-sweep marginal drift
* per-sweep aligned support
* per-sweep correlation summary

Formats:

* `.json` or `.csv` for tables
* `.npz` for raw arrays
* `.png` for plots

---

## 16. Required plots

At minimum, generate:

1. **Projectivity vs anisotropy ratio**
2. **Residual branch quality vs anisotropy ratio**
3. **Single-analyzer branch response vs analyzer angle**
4. **State clouds before/after update in analyzer basis**
5. **Marginal drift vs remote angle**
6. **Aligned same-sign mass vs anisotropy**
7. **Correlation function (E(\Delta))**
8. **CHSH vs anisotropy ratio** (secondary)

---

## 17. Explicit non-goals

Do **not**:

* hard-code (\cos^2) Bernoulli outcome probabilities
* hard-code collapse/update to (\phi) or (\phi+\pi/2)
* hard-code joint pair probabilities
* optimize directly for CHSH before projectivity is characterized
* disguise a pair-selector as a damping model

The purpose is to see whether sphere-like behavior can emerge from anisotropic modal depletion.

---

## 18. Final report questions

The coder’s final report must answer these directly:

1. Does strong anisotropic damping produce near-projective residual branches?
2. Which window durations preserve or destroy that behavior?
3. Which outcome rules are physically meaningful versus effectively imposed?
4. In sequential mode, do the pair statistics resemble generic depletion or sphere-style update?
5. Is marginal protection possible in this mechanism, or does stronger projectivity inevitably introduce drift?

---

## 19. One-sentence task summary

Build a sequential two-mode anisotropic-damping simulator that tests whether finite-window rotated damping can generate sphere-like projective residual-state updates and meaningful discrete pair statistics without hard-coding collapse or Bell correlations.

## 20. What not to smuggle in from the sphere model

Do not hard-code any part of the sphere model’s success conditions into the simulator.

Specifically, do **not**:

* sample outcomes from imposed (\cos^2(\theta-\phi)) Bernoulli probabilities
* force the post-measurement state to jump directly to (\phi) or (\phi+\pi/2)
* insert a hidden joint selector over ((++),(+-),(-+),(--))
* normalize branch weights to reproduce (-\cos(2\Delta)) by construction
* enforce exact 50/50 marginals by post-processing or balancing rules
* forbid aligned same-sign outcomes by explicit rule
* bake in Tsirelson or CHSH targets into thresholds, damping, or readout logic
* let the readout function directly reference both analyzer settings unless that dependence emerges through the simulated state evolution itself

The simulator must only contain:

1. a two-mode source state,
2. a rotated anisotropic damping operator,
3. finite-window evolution,
4. explicit outcome rules derived from simulated state/energy variables,
5. measurements of what behavior emerges.

If the model reproduces sphere-like behavior, it must do so because the **dynamics generate it**, not because the sphere model was reinserted under different names.