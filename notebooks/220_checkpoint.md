# Resonant Shared-State Measurement Program
## Status Freeze Note

### Purpose of this note
This document freezes the current status of the program: what was done, what was learned, how the work was staged, what is now frozen, what remains open, and where the program should go next.

The aim is not to claim that quantum mechanics is “really” a power-system circuit. The aim is narrower and more defensible:

> to build a physically intelligible resonant-network analog in which  
> 1. the **state geometry** is real and shared,  
> 2. the **measurement branches** are computed physically,  
> 3. **discrete one-click outcomes** emerge from an explicit detector/latch/closure stack, and  
> 4. in the joint case the resulting statistics reproduce the target Born/CHSH structure to good accuracy.

At this freeze point, the program has reached a major milestone: a full **preferred physical chain** now works end-to-end at the reduced / SPICE-style candidate level, with good winner-law fidelity, good correlator and CHSH fidelity, exact pre-click transparency, strong post-click exclusivity, and coherent whole-trial energy accounting. :contentReference[oaicite:0]{index=0}

---

## 1. Executive status

The current preferred chain is:

1. **resonant shared four-branch front-end**
2. **frozen detector boundary**  
   `piecewise_envelope:linear:20.0ms`, gain `4.0x`, exposure `5.0s`
3. **frozen detector family**  
   `shot_trigger`
4. **frozen winner latch**
5. **tuned post-click closure/drain**  
   common inhibit rail + winner-gated shunt drain

At the full-chain level, the current summary is:

- winner-law RMS error: **0.013075**
- winner-law max error: **0.038679**
- correlator RMS error: **0.024136**
- CHSH absolute error: **0.042854**
- mean decisive fraction: **0.995694**
- winner-frequency RMS shift vs baseline: **0.000000**
- mean winner drain fraction of post-click energy: **0.857711**
- mean loser residual fraction of post-click energy: **0.003896**
- winner-drain dominance rate: **0.999721**
- mean terminal loser suppression: **0.993587**
- max energy-balance absolute fraction: **3.256213e-14**. :contentReference[oaicite:1]{index=1}

Those numbers are good enough to treat the present preferred chain as the program’s working baseline.

---

## 2. Core conceptual move: state is not measurement

A decisive step in the program was separating **state** from **measurement**.

For the 3-delta-LC analog:

- **state** = the unloaded internal oscillatory condition of the ring
- **measurement** = resistive extraction and absorbed energy in analyzer branches

The reduced balanced state is naturally represented as
\[
a=
\begin{bmatrix}
a_+\\
a_-
\end{bmatrix},
\qquad
|a_+|^2+|a_-|^2=1,
\]
where \(a_+\) and \(a_-\) are the positive- and negative-sequence modal amplitudes. The earlier notes were explicit that this Bloch/Poincaré-like picture belongs to the **unloaded modal state**, not to delivered energy itself. 

This distinction resolved an earlier conceptual knot:

- the Bloch/Poincaré sphere is a **state manifold**
- absorbed branch energy is the **measurement observable**
- directional power delivery and integrated absorbed energy come later, after loading

That separation has remained stable throughout the program and should be treated as frozen.

---

## 3. What was proved at the linear front-end level

For the unloaded delta followed by ideal orthogonal resistive extraction, the absorbed energies satisfy
\[
E_i = W_0\,|u_i^\dagger a|^2.
\]

This means the fraction of initial stored energy delivered to each analyzer channel is exactly the squared projection in the analyzer basis:
\[
f_i=\frac{E_i}{W_0}=|u_i^\dagger a|^2.
\]

This is the strongest rigorous “Born-like” statement established at the linear analog level: **linear projection** plus **quadratic energy absorption** gives an exact squared-law energy split. 

However, that result is only an **energy-fraction** law. It does **not** by itself explain why a single trial yields one exclusive click rather than simultaneous partial absorption in multiple branches. That gap is what led the program into the detector/latch/closure stack.

This remains one of the program’s most important lessons:

> the square-law energy split is easy; the one-click outcome law is the hard part.

---

## 4. What the analogy does and does not claim

The mapping between polarization/qubit-style state geometry and balanced sequence/modal structure is real and useful at the level of:

- finite-dimensional complex state spaces
- orthogonal decompositions
- unitary basis changes
- quadratic observables
- projection rules. 

That is why the sequence-component / Bloch / Poincaré / state-geometry dictionary has genuine pedagogical and technical value.

But the analogy does **not** automatically provide:

- tensor-product structure in the strict quantum sense
- collapse
- discrete one-click measurement semantics
- Bell nonlocality claims
- a final microscopic detector theory

The program’s later architecture exists precisely because those pieces had to be built explicitly rather than assumed.

This is an important “safe claims / unsafe claims” boundary and should remain explicit in all future writeups.

---

## 5. Detector problem: the real bottleneck

Once the linear front-end result was secure, the correct next question became:

> how do deterministic branch energy fractions become discrete one-click outcomes?

This was the right bottleneck.

The detector search showed that not all detector models preserve the branch weights as one-click probabilities. In particular:

- accumulator-style detectors fail
- many-packet threshold models fail
- rare first-event detectors work
- the best candidate family is a **shot-trigger / rare-event nucleation** model

This was not just an implementation detail. It was one of the main conceptual achievements of the program: the detector mechanism space was narrowed sharply instead of being left hand-wavy.

---

## 6. Detector-cell and two-cell rig

A concrete two-cell detector rig was then specified and characterized.

The chosen detector-cell candidate was:

- matched branch absorber
- near-threshold avalanche/metastable latch stage
- pulse shaper
- explicit reset path. :contentReference[oaicite:5]{index=5}

The bench setup used:

- one calibrated source
- fixed attenuator
- splitter
- branch trim attenuators
- two matched detector cells
- timestamp / winner capture
- reset control. 

The resulting detector characterization was strong:

- selected operating bias: **2.780 V**
- rare-event regime found
- dark-count behavior acceptable
- linear fit \(\lambda_{\text{dark}}\approx 0.4077\text{ Hz}\)
- linear fit \(\alpha\approx 1.5467\text{ Hz}/\mu\text{W}\)
- linearity RMS residual: **0.0268**
- dead-time mean: **3.5458 µs**
- recovery-90: **6.0 µs**
- two-cell race RMS error: **0.0048**. :contentReference[oaicite:7]{index=7}

The biasing/reset scheme was also stabilized:
- independent fine bias trim
- dark-count sweep before operation
- reset quench after each click
- holdoff longer than recovery-90. :contentReference[oaicite:8]{index=8}

At that point, the detector layer stopped being speculative and became an actual calibrated block.

---

## 7. Winner latch and exclusivity

A separate winner-latch layer was then introduced:

- first-arrival capture
- deterministic tie rule
- loser masking
- reset/re-arm

The most important result here was that the latch added essentially **zero measurable pre-click distortion**. That preserved the clean architectural separation:

1. front-end computes branch weights  
2. detector produces rare first clicks  
3. latch declares one winner  
4. closure/drain handles post-click energy completion

This separation is now one of the strongest design choices in the whole program and should remain frozen.

---

## 8. Reduced shared-state / joint structure

In parallel, the shared-state side of the program produced a reduced four-branch joint model with:

- a shared four-dimensional joint basis
- local analyzer dependence
- exact target branch weights
- target correlator and CHSH structure

This provided the reference benchmark for all later shared-front-end work:
- exact \(w_{++}, w_{+-}, w_{-+}, w_{--}\)
- target correlator
- target CHSH
- no post-hoc multiplication

This reduced shared-state model became the standard against which all four-branch physical/SPICE-style candidates were measured.

---

## 9. From surrogate front-end to physical/SPICE-style front-end

The next major program transition was from pure reduced mathematics to circuit-facing front-end realizations.

The staged progression was:

1. SPICE-facing surrogate front-end  
2. physical/SPICE-style two-branch front-end candidate  
3. calibrated detector boundary  
4. physical/SPICE-style four-branch candidate  
5. refined shared-core candidate  
6. explicit resonant shared-mode candidate

A key lesson from this entire branch was that the main difficulty was **not** getting the front-end branch fractions right. The main difficulty was calibrating the **front-end → detector boundary** so that the detector consumed the front-end outputs in its validated operating regime.

That boundary was eventually frozen successfully as:

- export mode: `piecewise_envelope:linear:20.0ms`
- gain: `4.0x`
- exposure: `5.0s`

After high-statistics reproducibility checks, that calibrated regime was shown to be real and reusable. This was a crucial step because it converted a fragile-seeming handoff into a stable engineering contract.

---

## 10. Physical/SPICE-style four-branch front-end progression

Three increasingly physical shared-front-end candidates were then validated.

### 10.1 First four-branch physical candidate
A mild physical/SPICE-style scale-up from the two-branch candidate:
- explicit physical ports
- finite source impedance
- matched loads
- measurable branch power
- detector/latch boundary held fixed

This passed cleanly with small errors.

### 10.2 Refined shared-core candidate
The direct exact-weight-to-branch-driver mapping was removed and replaced with:
- an explicit internal 4-state shared core
- analyzer-dependent output map
- finite branch ports

This made the architecture meaningfully less abstract while preserving good performance.

### 10.3 Resonant shared-mode candidate
The refined 4-state core was then pushed one step further into a modal resonator picture:
- explicit eigenmodes
- drive-to-mode response
- modal ringdown
- analyzer/readout coupling
- branch reconstruction from the resonant internal state

The resonant candidate still passed:
- RMS four-branch energy-fraction error: **0.001789**
- RMS four-branch winner-law error: **0.009385**
- correlator RMS error: **0.020437**
- CHSH absolute error: **0.013433**
- mean decisive fraction: **0.936167**.

This is the current front-end baseline.

---

## 11. Post-click closure / drain path

The remaining missing role was post-click completion:
- suppress losers
- redirect remaining stored/shared energy
- define trial completion physically after winner capture

A reduced closure/drain study compared interpretations and selected the preferred one:

> **common-mode inhibit + winner-gated shunt drain**

This then became the first physical/SPICE-style closure/drain candidate and was tuned until it passed on the right metrics.

The important tuned result is:

- tuned winner drain fraction, all trials: **0.967831**
- tuned winner drain fraction, activated trials: **0.973510**
- loser residual fraction: **0.002279**
- winner path activation rate: **0.994167**
- pre-click transparency: preserved
- completion: preserved

This was another major milestone, because it gave the post-click “collapse-like” stage a physically intelligible role:
- no pre-click feedback
- common inhibit after winner capture
- winner-directed drain of the remaining energy

That interpretation is now the preferred closure/drain baseline.

---

## 12. Preferred physical chain

At this freeze point, the preferred physical chain is:

1. resonant shared four-branch front-end  
2. frozen detector-boundary export  
3. frozen `shot_trigger` detector  
4. frozen winner latch  
5. tuned common inhibit rail + winner-gated shunt drain closure/drain

This full chain now works end-to-end.

### 12.1 Full-chain fidelity
- winner-law RMS error: **0.013075**
- winner-law max error: **0.038679**
- correlator RMS error: **0.024136**
- CHSH absolute error: **0.042854**
- mean decisive fraction: **0.995694**. :contentReference[oaicite:9]{index=9}

### 12.2 Pre-click transparency
- winner-frequency RMS shift vs baseline: **0.000000**
- winner-frequency max shift vs baseline: **0.000000**. :contentReference[oaicite:10]{index=10}

### 12.3 Post-click exclusivity
- mean winner drain fraction of post-click energy: **0.857711**
- mean loser residual fraction of post-click energy: **0.003896**
- winner-drain dominance rate: **0.999721**
- mean terminal loser suppression: **0.993587**
- monotonic shared-energy decay: **True**. :contentReference[oaicite:11]{index=11}

### 12.4 Whole-trial energy accounting
- mean pre-click fraction of total energy: **0.187699**
- mean winner drain fraction of total energy: **0.696775**
- mean loser fraction of total energy: **0.003163**
- mean shared-leak fraction of total energy: **0.036669**
- max energy-balance absolute fraction: **3.256213e-14**. :contentReference[oaicite:12]{index=12}

This is probably the strongest integrated milestone of the entire program so far.

---

## 13. What was learned

### 13.1 The important split is state vs measurement
This was not just a semantic cleanup. It prevented repeated conceptual confusion and gave the architecture stable roles.

### 13.2 The square-law energy result is robust
The linear front-end result is one of the strongest parts of the whole program and should remain central.

### 13.3 Detector family matters
Not every detector mechanism can preserve the branch weights as one-click winner probabilities.

### 13.4 Boundary calibration matters
Even a correct front-end can look wrong if it drives the detector outside the detector’s validated rare-event regime.

### 13.5 Post-click closure must remain downstream
The cleanest architecture is one in which:
- pre-click branch competition is untouched,
- post-click closure handles only completion and drain.

### 13.6 Energy accounting is a major credibility anchor
The fact that whole-trial energy accounting closes cleanly is one of the strongest reasons to take the preferred chain seriously.

---

## 14. What remains open

Even with the current success, several things remain open.

### 14.1 The front-end is still not a final LC/coupled-port hardware netlist
The resonant shared-mode front-end is much more physical now, but it is still reduced-order and not yet a final explicit hardware netlist.

### 14.2 The detector is still a calibrated candidate abstraction
The detector family is well supported, but it is not yet a full final device-level implementation.

### 14.3 The closure/drain is still a SPICE-style candidate
It is preferred and tuned, but not yet a finished hardware design.

### 14.4 The full chain is still a staged physical surrogate
It is physically intelligible and integrated, but not yet a production-quality circuit realization.

### 14.5 Interpretation against Bell remains subtle
A successful shared resonant physical analog is not automatically a Bell-local microphysical theory. The program should continue to avoid claiming that.

---

## 15. What we are not claiming

At this freeze point, the program does **not** claim:

- that quantum mechanics is literally a power-system circuit
- that full Born collapse has been derived from first principles
- that a Bell-local completion has been found
- that the preferred chain is a final hardware realization
- that the quantum tensor-product structure has been fully reproduced

The safe claim is narrower:

> there now exists a staged, physically intelligible resonant-network analog in which state geometry, branch-weight computation, detector selection, latch exclusivity, and post-click energy drain can all be specified and integrated coherently while reproducing the target weight/correlator structure to good accuracy.

That is already a substantial result.

---

## 16. Current frozen items

The following should be treated as frozen unless a clear failure appears:

### 16.1 Detector boundary
- export mode: `piecewise_envelope:linear:20.0ms`
- gain: `4.0x`
- exposure: `5.0s`

### 16.2 Detector family
- `shot_trigger`
- frozen operating-point parameter set from the validated detector work

### 16.3 Winner latch semantics
- first-arrival arbiter
- deterministic tie rule
- no pre-click distortion
- reset/re-arm external to trial

### 16.4 Closure interpretation
- common inhibit rail + winner-gated shunt drain

### 16.5 Program-level role split
- front-end computes branch weights
- detector produces rare first clicks
- latch declares the winner
- closure/drain handles post-click exclusivity and energy completion

These freezes matter. Future work should reduce abstraction in the hardware realization while keeping these semantics fixed unless a strong reason appears.

---

## 17. Where the program should go next

The current best next direction is:

> move one step deeper toward an explicit **LC/coupled-port realization** of the preferred chain.

That means reducing abstraction in:
- the resonant shared front-end,
- and eventually the closure/drain path,

while preserving:
- the frozen detector boundary,
- the frozen detector family,
- the frozen latch semantics,
- the preferred post-click closure interpretation.

The central next question is no longer “does the architecture work?” It does.

The next question is:

> how far can the preferred chain be pushed toward explicit coupled-port / LC-style circuit realization before its validated behavior breaks?

That is the right next frontier.

---

## 18. Risks and cautions to keep visible

### 18.1 Overfitting to reduced interfaces
The interfaces are now frozen for a reason. Resist the urge to keep retuning detector/latch semantics unless a genuine failure appears.

### 18.2 Mistaking calibration for derivation
The detector boundary is calibrated and reproducible. That is good engineering, but it is not the same thing as a first-principles derivation.

### 18.3 Re-collapsing state into measurement
Do not drift back into language where Bloch geometry is confused with delivered power.

### 18.4 Over-interpreting the shared chain
A successful shared resonant analog is not automatically a microscopic claim about Bell-local reality.

### 18.5 Dropping energy accounting
Energy accounting is one of the strongest credibility anchors in the current program and should remain central in all future stages.

---

## 19. Program status at freeze

The program has now completed, in a meaningful sense:

1. state/measurement split  
2. single-delta linear energy-weight law  
3. reduced shared 4-mode model  
4. detector-family selection  
5. detector-cell validation  
6. winner-latch validation  
7. reduced end-to-end integration  
8. SPICE-facing front-end surrogate  
9. physical/SPICE two-branch front-end candidate  
10. calibrated and reproducible detector boundary  
11. physical/SPICE four-branch candidate  
12. refined shared-core candidate  
13. resonant shared-mode candidate  
14. tuned post-click closure/drain candidate  
15. full preferred physical chain integration

That is a real staged implementation program, not just a loose conceptual analogy.

---

## 20. Final status sentence

At this freeze point, the program’s strongest statement is:

> a physically intelligible preferred chain now exists, from resonant shared-state front-end through detector, latch, and post-click closure/drain, that reproduces the target joint weight/correlator structure with good fidelity while preserving pre-click transparency, strong post-click exclusivity, and coherent whole-trial energy accounting.

That is the baseline from which the next LC/coupled-port realization phase should proceed.