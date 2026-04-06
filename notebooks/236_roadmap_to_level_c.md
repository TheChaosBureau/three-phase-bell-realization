## Roadmap to Stop Level C

The project now has a working preferred physical chain and a coherent freeze baseline. The remaining question is no longer whether the architecture can work in principle. It can. The remaining question is how far the chain can be pushed toward an **actual circuit simulation and hardware-style realization** before its validated behavior breaks.

The right medium-term target is therefore **Stop Level C**:

> a stopping point at which the program has produced an actual SPICE-based front-end artifact, a documented handoff into the frozen detector/latch/closure stack, at least one SPICE-driven CHSH-like benchmark, and a bounded robustness study, without overclaiming what is physically implemented.

This section defines the roadmap to that stopping point.

---

### 1. Stop Level C: definition

Stop Level C is reached when all of the following are true:

#### 1.1 Real SPICE artifact exists

At least one actual SPICE netlist exists for the shared front-end and can be run directly in a real circuit simulator.

This means:

* a real `.cir`, `.sp`, or equivalent simulator input
* transient analysis that runs successfully
* node voltages, branch currents, and branch powers can be probed directly

#### 1.2 SPICE branch traces reproduce the front-end benchmark

The SPICE-generated branch traces reproduce the target front-end structure with acceptable accuracy.

At minimum:

* branch absorbed-energy fractions remain close to the current preferred-chain baseline
* benchmark angle/configuration cases run repeatably
* the traces are analyzable by scripts without hidden manual steps

#### 1.3 SPICE traces can drive the frozen downstream chain

The already frozen detector/latch/closure semantics remain usable when fed by actual SPICE-generated front-end traces.

In other words, the chain
[
\text{SPICE front-end}
\to
\text{frozen detector boundary}
\to
\text{frozen detector}
\to
\text{frozen latch}
\to
\text{frozen closure/drain}
]
must still preserve acceptable behavior.

#### 1.4 A SPICE-driven CHSH-like benchmark survives

At least one CHSH-like benchmark based on **actual SPICE front-end traces** must remain within documented tolerance.

This does not require that every part of the measurement chain be physically implemented in SPICE. It does require that the front-end traces driving the benchmark be real simulator outputs rather than surrogate traces.

#### 1.5 Modest non-ideality sweeps have been performed

The SPICE-based chain has been subjected to modest robustness checks, such as:

* component tolerances
* coupling mismatch
* source/load mismatch
* leakage/parasitic variation
* detector-boundary calibration variation

The goal is not perfection. The goal is to establish that the chain does not collapse immediately under small realistic perturbations.

#### 1.6 The final claim boundary is explicit

The final writeup must state plainly:

* what is physically implemented in SPICE
* what remains represented by frozen downstream abstractions
* what has been demonstrated
* what is not claimed

This is essential. Stop Level C is meant to be a strong and honest stopping point, not a place where the project drifts into overclaiming.

---

### 2. Why Stop Level C is the right target

The current program is already beyond the point of being a loose conceptual analogy. It has:

* a stable state/measurement split,
* exact front-end energy-fraction laws,
* a selected detector family,
* a validated latch,
* a preferred post-click closure interpretation,
* an integrated preferred physical chain,
* and explicit component-level front-end and co-designed chain candidates.

That is already enough for a strong architectural result.

However, the user’s stated goal is not only a coherent architecture. It is also:

> a circuit simulation that can be probed and analyzed directly.

That means the project is not fully aligned with its most satisfying stopping point until it crosses from “SPICE-style” and “SPICE-facing” into **actual SPICE execution**.

Stop Level C captures that goal without demanding a full hardware build or a full device-level implementation of every subblock.

---

### 3. Freeze the current preferred-chain baseline

Before pushing further, the current preferred chain should remain the benchmark against which all future SPICE work is judged.

The frozen baseline includes:

* frozen detector boundary
  `piecewise_envelope:linear:20.0ms`, gain `4.0x`, exposure `5.0s`
* frozen detector family
  `shot_trigger`
* frozen latch semantics
  first-arrival arbiter
* preferred closure interpretation
  common inhibit rail + winner-gated shunt/resonant drain
* current preferred-chain metrics
* current whole-trial energy-accounting summaries

This freeze matters because future work should answer:

> does deeper physicalization preserve the current baseline?

rather than:

> can we keep retuning the semantics until something works again?

---

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

That is a strong and honest stopping point.

---

### 9. What Stop Level C does not require

Stop Level C is intentionally ambitious but bounded. It does **not** require:

* full transistor-level detector implementation
* full transistor-level latch implementation
* fabricated hardware
* full explicit LC hardware for every subblock
* a claim of Bell-local completion
* a claim of deriving quantum mechanics

Those demands would raise the bar too far and risk turning a strong finish into an open-ended project.

---

### 10. Recommended ordering from here

To preserve the productive current line of work while bringing actual SPICE into view, the recommended order is:

1. finish the current device-level physicalization work
2. build the first actual SPICE front-end milestone
3. validate SPICE front-end traces against the frozen baseline
4. drive the frozen downstream chain from SPICE traces
5. run a modest robustness / non-ideality program
6. stop at Level C if the results hold

This keeps the current architecture and freeze discipline intact while putting the real SPICE artifact on the main path.

---

### 11. Practical stopping rule

The practical stopping rule for the whole project should now be:

> Stop when the integrated preferred chain remains quantitatively strong under modest physicalization and robustness stress, and the remaining abstractions are few enough to state cleanly and honestly — with at least one actual SPICE-simulated front-end artifact on the record.