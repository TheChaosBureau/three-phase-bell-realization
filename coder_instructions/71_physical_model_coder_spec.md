Here’s a coder-ready **circuit-level implementation contract** for the first physical stage: a **linear energy-partition demonstrator** of the reduced 4-mode model, using delta LC tanks as the primitive resonators. This keeps the roles clean: unloaded resonant core = state, resistive extraction = measurement.  

# Implementation contract: physical realization v0

## Goal

Build and simulate a **shared 4-mode resonant network** whose linear readout reproduces the reduced model:

[
\Psi'(a,b)=(R_A(a)\otimes R_B(b))\Psi_0,
\qquad
w_{xy}(a,b)=|\Psi'_{xy}(a,b)|^2
]

using actual circuit elements.

Success means:

* a prepared shared resonant mode exists, ideally singlet-like,
* local analyzer controls (a,b) act as tunable 2×2 rotations,
* four output branches (++, +-, -+, --) are physically realized,
* total absorbed energies satisfy
  [
  E_{xy}^{(\infty)} \propto w_{xy}(a,b),
  ]
* the correlator from energy fractions matches
  [
  E(a,b)=-\cos 2(a-b)
  ]
  for the singlet-like prepared mode.

---

## Scope of v0

This version is **linear only**.

Included:

* resonant preparation core
* passive couplings
* passive analyzer/readout
* resistive extraction
* long-time absorbed energy measurement

Excluded:

* stochastic nucleation
* latch / closure
* zero-sequence post-click completion
* nonlinear detector physics

---

# 1. Physical architecture

## 1.1 Primitive resonator

Use one **delta LC tank** as the local 2-mode primitive.

Each delta has three identical branches:

* (ab): (L \parallel C)
* (bc): (L \parallel C)
* (ca): (L \parallel C)

with branch voltages
[
v_{ab}=v_a-v_b,\quad
v_{bc}=v_b-v_c,\quad
v_{ca}=v_c-v_a.
]

Unloaded state is internal stored energy and phase distribution. Resistive extraction measures absorbed energy.

## 1.2 Shared 4-mode core

Use **four delta tanks**, labeled by the joint basis:

* Tank 1: (++)
* Tank 2: (+-)
* Tank 3: (-+)
* Tank 4: (--)

Each tank is identical in uncoupled resonance frequency.

Let the reduced complex modal amplitudes be
[
q=
\begin{bmatrix}
q_{++}\
q_{+-}\
q_{-+}\
q_{--}
\end{bmatrix}.
]

## 1.3 Core coupling target

Implement a linear coupling matrix whose reduced envelope dynamics are
[
\dot q = -iHq - \Gamma q + Bu_{\text{prep}}.
]

### Minimum target Hamiltonian

Start with
[
H=
\begin{bmatrix}
\omega_0 & 0 & 0 & 0\
0 & \omega_0+\kappa & -\kappa & 0\
0 & -\kappa & \omega_0+\kappa & 0\
0 & 0 & 0 & \omega_0
\end{bmatrix}.
]

This guarantees the singlet-like eigenmode
[
\Psi_s=\frac{1}{\sqrt2}
\begin{bmatrix}
0\
1\
-1\
0
\end{bmatrix}
]
with shifted eigenfrequency.

### Physical realization intent

This means:

* Tanks (+-) and (-+) are mutually coupled with equal and opposite interaction,
* Tanks (++) and (--) are initially uncoupled spectators,
* all four share the same nominal resonance.

### Recommended component class

Use:

* transformer/coupled-inductor links, or
* weak bridging capacitors

between the effective modal ports of tanks (+-) and (-+).

Do **not** start with full all-to-all coupling.

---

# 2. Preparation network

## 2.1 Required behavior

Prepare the shared core in the singlet-like mode:
[
q(0)\propto \Psi_s.
]

## 2.2 Implementation requirement

Provide two equal-magnitude preparation drives into the (+-) and (-+) tanks with opposite phase:
[
u_{\text{prep}} \propto
\begin{bmatrix}
0\
1\
-1\
0
\end{bmatrix}.
]

## 2.3 Acceptance criterion

After excitation and removal of the drive, modal decomposition of the free ring-down must show:

* dominant overlap with (\Psi_s),
* negligible projection onto orthogonal modes.

Quantitative target:

* (> 95%) energy in the singlet-like mode in the reduced basis.

---

# 3. Local analyzer stage

## 3.1 Required mathematics

Implement local analyzer action
[
U(a,b)=R(a)\otimes R(b),
]
with
[
R(\theta)=
\begin{bmatrix}
\cos\theta & \sin\theta\
-\sin\theta & \cos\theta
\end{bmatrix}.
]

## 3.2 Physical interpretation

Analyzer action must be realized as **passive readout couplers**, not by modifying the shared core Hamiltonian.

* Alice analyzer acts on the first factor
* Bob analyzer acts on the second factor

## 3.3 Minimum hardware representation

Implement two tunable 2×2 passive couplers:

### Alice coupler

Mixes the two A-indexed subspaces:

* ((++, +-))
* ((-+, --))

according to angle (a).

### Bob coupler

Mixes the two B-indexed subspaces:

* ((++, -+))
* ((+-, --))

according to angle (b).

## 3.4 Suggested implementation options

Use one of:

* transformer-based quadrature/sign coupler
* resistive/inductive bridge hybrid
* switched signed coupling matrix
* capacitive divider network with calibrated gain and sign inversion

For v0, switched signed couplings are acceptable if continuously tunable couplers are not yet practical.

## 3.5 Acceptance criterion

For injected basis states, measured analyzer outputs must match the matrix (R(a)\otimes R(b)) to within:

* amplitude error < 2%
* relative phase/sign error < 2°

---

# 4. Joint readout stage

## 4.1 Required outputs

Expose four physical output branches:

* (++)
* (+-)
* (-+)
* (--)

These must exist as distinct passive channels **before** any nonlinear detector model.

## 4.2 Required measurement

Each branch terminates in a matched resistor (R_{xy}).

Measure
[
E_{xy}^{(\infty)}=\int_0^\infty p_{xy}(t),dt
]
with
[
p_{xy}(t)=v_{xy}(t)i_{xy}(t).
]

## 4.3 Required normalization

Define
[
f_{xy}=\frac{E_{xy}^{(\infty)}}{\sum_{uv}E_{uv}^{(\infty)}}.
]

Acceptance requires
[
f_{xy}\approx w_{xy}(a,b).
]

Quantitative target:

* RMS error across four channels < 2% for benchmark settings.

---

# 5. Benchmark cases

## Case A

Prepared state: singlet-like
Angles:
[
a=0^\circ,\quad b=0^\circ
]

Expected:
[
w_{++}=w_{--}=0,\qquad
w_{+-}=w_{-+}=1/2.
]

## Case B

[
a=45^\circ,\quad b=22.5^\circ
]

Expected:
[
w_{++}=w_{--}=\tfrac12\sin^2(22.5^\circ),
\qquad
w_{+-}=w_{-+}=\tfrac12\cos^2(22.5^\circ).
]

Correlator target:
[
E=-\cos(45^\circ)=-0.70710678.
]

## Case C

CHSH set:
[
a_0=0^\circ,\quad a_1=45^\circ,\quad
b_0=22.5^\circ,\quad b_1=-22.5^\circ
]

Use energy fractions to compute
[
E(a,b)=f_{++}-f_{+-}-f_{-+}+f_{--}.
]

Target:
[
|S|=|E(a_0,b_0)+E(a_0,b_1)+E(a_1,b_0)-E(a_1,b_1)|\approx 2\sqrt2.
]

Acceptance target:

* (|S|-2\sqrt2|) < 0.05 in the linear demonstrator.

---

# 6. Simulation contract

## 6.1 State variables

At minimum, simulate either:

### Full branch-level ODEs

All 12 branch energy variables plus coupling network states

or

### Reduced envelope model

[
\dot q = -iHq - \Gamma q + Bu_{\text{prep}}
]
followed by analyzer/readout maps.

For v0, the reduced envelope model is acceptable **only if** a second pass maps each reduced element to an intended circuit component.

## 6.2 Required outputs

For each run:

* eigenfrequencies/eigenvectors of the uncoupled and coupled cores
* overlap of prepared state with singlet-like mode
* four branch energy integrals (E_{xy}^{(\infty)})
* normalized fractions (f_{xy})
* correlator (E(a,b))
* CHSH (S)

## 6.3 Required sweeps

* analyzer angle sweep over (a,b)
* coupling strength (\kappa) sweep
* damping/mismatch sensitivity sweep
* resistor termination tolerance sweep

---

# 7. Non-idealities to include

Must include:

* ±1% L/C mismatch
* weak damping in each tank
* coupler imbalance
* analyzer sign/gain mismatch
* finite resistor tolerance

Need to verify the intended geometry survives modest imperfection.

---

# 8. Deliverables

## 8.1 Code deliverables

* `shared_4tank_core.py`
* `analyzer_couplers.py`
* `joint_readout.py`
* `benchmarks.py`
* `test_physical_v0.py`

## 8.2 Plots

* core eigenmode spectra
* singlet-mode overlap
* (f_{xy}(a,b)) versus theory
* correlator surface (E(a,b))
* CHSH benchmark table

## 8.3 Tables

For each benchmark angle pair:

* exact (w_{xy})
* simulated (f_{xy})
* absolute error
* correlator exact/simulated

---

# 9. Explicit non-goals

This phase must **not** include:

* nonlinear detector thresholding
* avalanche / nucleation
* zero-sequence closure dynamics
* claims about Bell locality or quantum ontology

This is only the **linear shared-core demonstrator**.

---

# 10. Acceptance summary

The v0 physical demonstrator passes if it shows:

1. A real shared 4-mode resonant core with a singlet-like eigenmode
2. Local analyzer readout behaving like (R(a)\otimes R(b))
3. Four branch energy fractions matching (w_{xy}(a,b))
4. Correlator matching (-\cos 2(a-b))
5. CHSH magnitude near (2\sqrt2) from energy fractions alone

That is the right bridge from the reduced model to actual hardware.

If you want, I can turn this next into a **module-by-module coder spec** with function signatures and data structures.
