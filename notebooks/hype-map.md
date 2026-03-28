# Hypothesis Map

**Target question:**
**What mechanism can make outcome selection joint, discrete, and no-signaling, without reducing to ordinary shared-source signaling or local thresholding?**

---

# 0. What must be explained

A viable mechanism has to produce all of these at once:

## Required properties

* **Discrete outcomes:** (A,B \in {+1,-1})
* **Joint selection:** the pair law is not just two independent local threshold events
* **No-signaling:** local marginals stay exactly (1/2), independent of remote setting
* **Angle law:**
  [
  E(a,b) = -\cos(2(a-b))
  ]
* **Aligned anti-support:** at (a=b), only ((+,-)) and ((-,+)) occur
* **Physical interpretability:** should correspond to some source / field / extraction mechanism

---

# 1. Mechanism families

## Family A — Local threshold + local/shared hidden variables

Form:
[
A=f(a,\lambda),\qquad B=g(b,\lambda)
]

### A1. Independent local randomness

* Each side samples locally from (\cos^2)-type probabilities
* Preserves local marginals
* Gives diluted correlation amplitude

**Prediction:**

* shape can survive
* amplitude stalls low
* (S \le \sqrt2) or similar depending on exact model

**Status:** explored, insufficient

---

### A2. Deterministic local threshold

* Hard threshold on local continuous variables
* Stronger complementarity at some settings
* Destroys smooth quadratic geometry

**Prediction:**

* tent / piecewise-linear correlator
* (S \le 2)

**Status:** explored, insufficient

---

### A3. Shared classical randomness / shared carrier

Form:
[
A=f(a,\lambda,c),\qquad B=g(b,\lambda,c)
]

* Better coordinated binarization
* Still Bell-local in structure if outcomes are local functions of shared variables
* Can raise covariance but not cross the true boundary without artifacts

**Prediction:**

* can approach Bell bound
* cannot yield Tsirelson unless hidden signaling / parameter dependence sneaks in

**Status:** explored, boundary result

---

## Family B — Shared-source classical circuit dynamics

Form:

* two loads on a common finite source
* local readouts emerge from actual network dynamics

### B1. Weak-coupling regime

* Source barely perturbed
* No-signaling approximately preserved
* Correlations weak/classical

**Prediction:**

* (S \le 2)
* local marginals stable

**Status:** observed

---

### B2. Strong-coupling regime

* Loads significantly reshape source during extraction
* Correlations strengthen
* Local marginals drift with remote setting

**Prediction:**

* apparent (S>2) possible
* but accompanied by signaling / parameter dependence

**Status:** observed

---

### B3. Key lesson from Family B

Ordinary shared-source dynamics gives the **wrong kind of nonlocality**:

* physical coupling boosts correlation
* but also leaks information into local marginals

**Interpretation:**
This family maps the **classical boundary**, not the quantum mechanism.

---

## Family C — Projective modal depletion

Form:

* finite source has two complementary modes (S_p,S_m)
* analyzer couples to rotated basis
* extraction removes one modal component
* source updates to structured residual state

### C1. Generic depletion

* extraction changes source
* but residual state is messy droop/distortion

**Prediction:**

* signaling-like marginal leakage
* no clean sphere-style update

**Status:** likely common in ordinary hardware

---

### C2. Projective depletion

* extraction selectively removes one mode
* residual remains on a clean low-dimensional state manifold
* second measurement sees complementary updated state

**Prediction:**

* could realize sphere-style sequential update physically
* key gateway question: does passive extraction produce clean residual branches?

**Status:** open, high priority experimental question

---

### C3. Importance of this family

This is the most natural engineering candidate for making the sphere model physical.

**Key test:**
Can passive real-power extraction update the source **projectively**, not just perturb it?

---

## Family D — Sequential joint-state update

Form:

1. Alice outcome sampled
2. source state updated conditioned on that outcome
3. Bob samples updated state
4. local marginals protected by symmetry after averaging

This is the structure of the sphere model.

### D1. Pure mathematical toy / Monte Carlo model

* reproduces exact (-\cos(2\Delta))
* saturates Tsirelson
* no-signaling after averaging
* not Bell-local by construction

**Prediction:**

* works exactly
* already demonstrated in code/spec

**Status:** established as a model

---

### D2. Physical realization question

Can Family D be realized by actual hardware, rather than imposed as an abstract update law?

**Depends on:** Family C succeeding

**Status:** open

---

## Family E — Joint selector in pair space

Form:
[
(A,B)\sim \Pi_{ab,\lambda}
]
The pair is chosen jointly, not factorized into two local decisions.

### E1. Exact-fit joint rule

* build four-outcome law directly
* allocate weights over ((++),(+-),(-+),(--))
* marginals and support rules imposed at pair level

**Prediction:**

* can reproduce target exactly
* but may be more formal than physical unless a mechanism is found

**Status:** mathematically promising

---

### E2. Physical interpretations

Possible realizations:

* central joint projection stage
* hidden normalization / allocation rule
* global field mode that only closes on pair space

**Status:** conceptual, not yet physically grounded

---

## Family F — Global constraint / boundary-value mechanisms

Form:

* outcome pair selected by a global compatibility condition
* not by local thresholding plus communication

### F1. Global variational closure

* source + settings define one admissible discrete solution
* no ordinary signal path required

**Prediction:**

* can, in principle, be joint and no-signaling
* may look more like a boundary-value problem than an ordinary circuit

**Status:** open, conceptually serious

---

### F2. Retrocausal / two-boundary models

* settings act like future boundary conditions
* pair outcome is globally consistent solution

**Prediction:**

* joint, nonfactorizable, potentially no-signaling
* hard to engineer, but structurally viable

**Status:** speculative but relevant

---

## Family G — Superdeterministic common-cause models

Form:

* hidden variables correlated with settings

**Prediction:**

* can evade Bell formally
* usually not the direction you want

**Status:** logically available, low interest here

---

# 2. Current evidence map

## Strongly constrained / likely ruled out as final answer

* **A1** independent local randomness
* **A2** deterministic local threshold
* **A3** shared classical carrier
* **B1/B2** ordinary shared-source circuit dynamics as the full answer

These are useful, but they appear to define the **classical boundary**, not cross it cleanly.

---

## Most promising engineering direction

* **C2** projective modal depletion

This is the best candidate for a real hardware analog of the sphere update.

**Immediate question:**
Does passive extraction ever produce a **clean complementary residual mode**?

---

## Most promising formal mechanism direction

* **E1/E2** joint selector in pair space

This is the cleanest mathematical structure for producing:

* joint outcomes
* exact marginals
* forbidden supports
* target correlator

**Immediate question:**
Can this be derived from a physical mechanism rather than imposed?

---

## Most promising deep-physics direction

* **F1/F2** global constraint / boundary-value mechanisms

This is the best candidate if ordinary local field dynamics keep failing.

**Immediate question:**
Can pair selection be derived as a global admissibility rule rather than local event generation?

---

# 3. Main forks in the road

## Fork 1 — Engineering gateway

**Can passive extraction update the source projectively?**

If no:

* sphere model remains interpretive
* ordinary hardware likely stays on classical boundary

If yes:

* real hardware analog of sphere update becomes plausible

---

## Fork 2 — Formal mechanism

**What is the minimal four-outcome joint law consistent with all constraints?**

This tells you what the mechanism must at least do, independent of implementation.

---

## Fork 3 — Physics interpretation

**Is the correct mechanism local-but-subtle, or genuinely global/nonlocal in pair space?**

This is the deepest branch.

---

# 4. Research priorities

## Priority 1

**Test Family C2 experimentally**

* finite two-mode source
* quarter-cycle extraction
* reconstruct post-extraction residual state
* look for outcome-conditioned residual clustering

This is the clearest next experiment.

---

## Priority 2

**Solve Family E formally**
Derive the most general four-outcome law satisfying:

* normalization
* exact 50/50 marginals
* aligned anti-support
* (E=-\cos(2\Delta))

Then classify what extra degrees of freedom remain.

---

## Priority 3

**Use Family B to map the classical boundary**
Make the result explicit:

* shared-source coupling raises correlation
* but also raises marginal leakage
* no-signaling limit recovers (S\le 2)

This is already a strong result.

---

# 5. Best current synthesis

## What the analogy has already succeeded at

* explaining the double-angle geometry
* showing why quadratic conservation matters
* identifying the role of a shared residual channel
* locating the classical tradeoff physically

## What remains unresolved

* discrete pair selection
* exact marginal protection
* the mechanism that combines those without ordinary signaling

---

# 6. One-sentence summary of the map

**The classical/local families explain the geometry and the boundary; the remaining candidates for the full mechanism are projective modal depletion, a genuine pair-space joint selector, or a global constraint law that selects the outcome pair without ordinary signaling.**