### 4. Phase 1: first actual SPICE front-end milestone

The first phase toward Stop Level C is the most important alignment step:

> build the first actual SPICE netlist for the shared front-end only.

This phase should not include the detector, latch, or closure as physical SPICE subcircuits yet. It should focus on the front-end.

#### 4.1 Goal

Produce an actual SPICE netlist that:

* contains explicit front-end components,
* runs in a real circuit simulator,
* produces probeable transient branch waveforms,
* reproduces the front-end benchmark cases reasonably well.

#### 4.2 Required outputs

From real SPICE simulation, extract:

* node voltages
* branch currents
* instantaneous powers
* integrated branch energies
* normalized branch fractions

#### 4.3 Acceptance

The SPICE front-end should reproduce the current preferred-chain front-end behavior within reasonable tolerance, especially for benchmark angle cases.

#### 4.4 Why this phase matters

This is the moment the program stops merely approaching SPICE and starts actually being SPICE-driven.

---

### 5. Phase 2: SPICE-to-detector boundary handoff

Once real SPICE front-end traces exist, the next phase is:

> feed actual SPICE-generated branch traces into the frozen detector/latch/closure stack.

This is the cleanest way to preserve the productive line of work already built while aligning it with the actual desired artifact.

#### 5.1 Goal

Demonstrate that the chain
[
\text{SPICE front-end traces}
\to
\text{frozen detector boundary}
\to
\text{frozen detector}
\to
\text{frozen latch}
\to
\text{frozen closure/drain}
]
still reproduces the key benchmark behavior.

#### 5.2 Required outputs

At minimum:

* winner-law fidelity
* correlator fidelity
* CHSH fidelity
* decisive fraction
* whole-trial energy accounting

#### 5.3 Acceptance

The SPICE-driven chain should remain within the same qualitative “works” regime as the current preferred physical chain.

#### 5.4 Why this phase matters

This is the first honest point at which the project can say:

> the CHSH-like benchmark is being driven by actual SPICE front-end traces.

That is a much stronger statement than “the architecture is SPICE-facing.”

---

### 6. Phase 3: SPICE-compatible closure/drain milestone

The third phase toward Stop Level C is to move more of the post-click path into a SPICE-compatible representation.

This does not yet require a transistor-level design. It requires only that the closure/drain semantics be represented in a way that is more directly netlist- or simulator-compatible.

#### 6.1 Goal

Represent the closure/drain path in a SPICE or SPICE-coupled form that preserves:

* pre-click transparency
* winner drain dominance
* loser suppression
* monotonic shared-energy decay
* reproducible completion

#### 6.2 Why this phase matters

At that point, much more of the physically interesting chain is represented in actual circuit form rather than downstream semantic blocks.

---

### 7. Phase 4: robustness and non-ideality sweep

This is probably the most important remaining engineering phase.

A chain that works only in ideal conditions is not yet a credible physical analog. Stop Level C therefore requires at least a modest robustness study.

#### 7.1 Goal

Run non-ideality sweeps on the SPICE-driven preferred chain, including variations such as:

* component tolerances
* coupling mismatch
* parasitic/leakage effects
* source/load mismatch
* detector-boundary calibration perturbation
* closure/drain strength perturbation

#### 7.2 Metrics to track

The same metrics that already define the current baseline:

* winner-law RMS/max error
* correlator RMS error
* CHSH error
* decisive fraction
* pre-click transparency shift
* winner drain dominance
* loser residual fraction
* energy-accounting balance

#### 7.3 Acceptance

The criterion is not perfection. The criterion is that the chain remain structurally credible and not collapse immediately under modest perturbations.

#### 7.4 Why this phase matters

This is the difference between:

* an interesting simulation artifact,
  and
* a plausible physical analog with some engineering credibility.

---

### 8. Phase 5: final Stop Level C package

The final phase is packaging the result honestly and cleanly.

The final Stop Level C package should contain:

* the frozen baseline note
* the actual SPICE front-end netlist(s)
* analysis scripts and benchmark harnesses
* SPICE-driven preferred-chain report
* robustness / non-ideality report
* safe claims / unsafe claims note
* open problems / remaining abstractions note

At this point, the project should have a final bounded claim of the form:

> a physically intelligible shared resonant measurement chain has been built in which the front-end branch structure is realized by an explicit SPICE-simulated network, and the resulting branch traces, when fed into a fixed detector/latch/closure stack, reproduce the target branch-weight and CHSH-like benchmark structure to good accuracy, with coherent energy accounting and documented robustness bounds.