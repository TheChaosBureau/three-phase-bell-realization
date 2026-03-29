# Bell Violations as Signatures of Quadratic Conservation Laws: A Three-Party Accounting Framework

**David [Surname]**

**Draft — March 2026**

---

## Abstract

We demonstrate that the hierarchy of Bell-inequality violations arises directly from the algebraic order of conservation laws governing correlated systems. Linear conservation (momentum-type) produces correlations bounded by $S = \sqrt{2}$, well within the classical Bell-CHSH limit of $S = 2$. Quadratic conservation (power/energy-type) produces correlations that saturate the Tsirelson bound at $S = 2\sqrt{2}$. The factor-of-two amplification in angular frequency — $\cos(2\Delta\phi)$ versus $\cos(\Delta\phi)$ — is a direct algebraic consequence of the double-angle identity inherent in squaring.

We further argue that the standard two-party CHSH framework constitutes an incomplete accounting of what is intrinsically a three-party conservation law. Using the Clarke decomposition from three-phase power systems theory, we identify the third party as the zero-sequence mode — the energy carried by the field between measurement stations. This mode is the analogue of the quantum vacuum in field-theoretic treatments of entanglement.

When all three modes (positive sequence, negative sequence, zero sequence) are treated as participants in a joint quadratic conservation law, the correlations that appear "nonlocal" in the two-party projection become the natural consequence of a global conservation constraint — no more mysterious than momentum conservation in a two-body decay, but richer by exactly the factor that separates classical from quantum correlations.

---

## 1. Introduction

Bell's theorem (Bell 1964) and its experimental confirmations establish that quantum correlations between spacelike-separated measurements exceed the bounds achievable by any local hidden variable (LHV) model. The Clauser-Horne-Shimony-Holt (CHSH) inequality provides the standard quantitative test: for any LHV model,

$$|S| \leq 2$$

where $S = E(a,b) - E(a,b') + E(a',b) + E(a',b')$ and $E(a,b)$ is the expectation value of the product of binary ($\pm 1$) measurement outcomes at settings $a$ and $b$. Quantum mechanics predicts $|S| \leq 2\sqrt{2}$ (the Tsirelson bound), achieved by singlet-state measurements at appropriately chosen angles.

The standard interpretation frames this violation as evidence that nature is fundamentally nonlocal, or that realism (the assignment of pre-existing values to unmeasured observables) must be abandoned. We propose a complementary interpretation: Bell violations are signatures of the algebraic order of the conservation law governing the correlated system, and the apparent nonlocality arises from incomplete accounting — the omission of a third participant in a tripartite conservation constraint.

Our framework draws on the mathematical apparatus of three-phase power systems, specifically the Clarke transform (Clarke 1943) and its decomposition into symmetrical components (Fortescue 1918). These tools, developed for entirely classical electrical engineering applications, provide the natural language for describing the structure we identify.

---

## 2. Conservation Laws and Correlation Functions

### 2.1 The General Setup

Consider a source that emits two correlated subsystems, $A$ and $B$, propagating to spatially separated measurement stations. Each station applies a projection at an independently chosen angle $\phi_A$ or $\phi_B$, yielding outcomes that, when correlated over many trials, produce the function $E(\phi_A, \phi_B)$.

The form of $E$ is determined by the conservation law governing the source decay. We examine two cases.

### 2.2 Case I: Linear Conservation (Momentum-Type)

A particle at rest decays into two fragments with momenta $\mathbf{p}_A + \mathbf{p}_B = 0$. Each fragment carries a definite momentum vector determined at the decay event. An analyzer at angle $\phi$ projects the momentum onto the measurement axis:

$$m_A(\theta, \phi_A) = \cos(\theta - \phi_A)$$
$$m_B(\theta, \phi_B) = -\cos(\theta - \phi_B)$$

where $\theta$ is the (hidden) emission angle, uniformly distributed, and the minus sign enforces anti-correlation from $\mathbf{p}_A = -\mathbf{p}_B$.

The correlation function is:

$$E_{\text{lin}}(a,b) = \int_0^{2\pi} m_A(\theta, \phi_A) \, m_B(\theta, \phi_B) \, \frac{d\theta}{2\pi}$$

$$= -\int_0^{2\pi} \cos(\theta - \phi_A)\cos(\theta - \phi_B) \, \frac{d\theta}{2\pi}$$

By the product-to-sum identity and orthogonality of cosines:

$$E_{\text{lin}}(a,b) = -\frac{1}{2}\cos(\Delta\phi)$$

where $\Delta\phi = \phi_A - \phi_B$.

**CHSH evaluation.** Choose $\phi_A = 0$, $\phi_{A'} = \pi/4$, $\phi_B = \pi/8$, $\phi_{B'} = 3\pi/8$ (the angles that maximize $S$ for a $\cos$ correlation):

$$S_{\text{lin}} = \left| -\tfrac{1}{2}\cos(\pi/8) + \tfrac{1}{2}\cos(3\pi/8) \right| + \left| -\tfrac{1}{2}\cos(\pi/8) - \tfrac{1}{2}\cos(\pi/8) \right| = \sqrt{2} \approx 1.414$$

This is well below the classical bound $S \leq 2$. Linear conservation produces no Bell violation.

### 2.3 Case II: Quadratic Conservation (Power-Type)

Now consider a source that emits two correlated subsystems whose conserved quantity is quadratic in the fundamental field variable. In electrical terms: the conserved quantity is power ($P = V^2/R$), not voltage ($V$). In quantum terms: the conserved quantity is probability ($|\psi|^2$), not amplitude ($\psi$).

The source emits two counter-rotating phasor sequences — positive (counterclockwise) and negative (clockwise) — with equal amplitude $V$. The measurement apparatus is the Clarke transform (Section 3), which projects the three-phase signal onto orthogonal axes $\alpha$ and $\beta$.

For a positive-sequence signal measured at analyzer angle $\phi$, the power captured is:

$$P_+(\theta, \phi) = V^2 \cos^2(\theta - \phi)$$

For the anti-correlated negative sequence:

$$P_-(\theta, \phi) = V^2 \sin^2(\theta - \phi)$$

Normalizing and computing outcomes as $A = 2P_+/V^2 - 1 = \cos(2(\theta - \phi_A))$, we obtain:

$$E_{\text{quad}}(a,b) = -\int_0^{2\pi} \cos(2(\theta - \phi_A)) \cos(2(\theta - \phi_B)) \, \frac{d\theta}{2\pi}$$

$$= -\frac{1}{2}\cos(2\Delta\phi)$$

The critical difference is the factor of 2 inside the cosine argument, which arises directly from the double-angle identity:

$$\cos^2(x) = \frac{1 + \cos(2x)}{2}$$

The squaring operation — the passage from amplitude to power, from $\psi$ to $|\psi|^2$ — doubles the angular frequency of the correlation pattern.

**CHSH evaluation.** Choosing optimal angles $\phi_A = 0$, $\phi_{A'} = \pi/4$, $\phi_B = \pi/8$, $\phi_{B'} = 3\pi/8$:

$$S_{\text{quad}} = 2\sqrt{2} \approx 2.828$$

This saturates the Tsirelson bound. The violation of the classical limit $S > 2$ is a direct consequence of the quadratic nature of the conservation law.

### 2.4 The Hierarchy

| Conservation type | Conserved form | $E(a,b)$ | $S_{\max}$ | Status |
|---|---|---|---|---|
| Linear (momentum) | $V_\alpha + V_\beta$ | $-\frac{1}{2}\cos(\Delta\phi)$ | $\sqrt{2}$ | Below Bell bound |
| Quadratic (power) | $V_\alpha^2 + V_\beta^2$ | $-\frac{1}{2}\cos(2\Delta\phi)$ | $2\sqrt{2}$ | Tsirelson bound (QM) |
| Deterministic threshold | Binary $\text{sgn}(\cos^2)$ | $-1 + 4|\Delta\phi|/\pi$ | $2$ | Bell bound (classical) |

The Bell bound $S = 2$ sits precisely between the linear and quadratic cases. It corresponds to the deterministic threshold model (Section 5.1), where the continuous quadratic distribution is binarized, destroying the cos² structure and linearizing the correlation.

---

## 3. The Clarke Transform as Measurement Apparatus

### 3.1 Definition and Properties

The Clarke transform maps a three-phase signal $(v_a, v_b, v_c)$ onto orthogonal components $(v_\alpha, v_\beta, v_0)$:

$$\begin{pmatrix} v_\alpha \\ v_\beta \\ v_0 \end{pmatrix} = \sqrt{\frac{2}{3}} \begin{pmatrix} 1 & -\frac{1}{2} & -\frac{1}{2} \\ 0 & \frac{\sqrt{3}}{2} & -\frac{\sqrt{3}}{2} \\ \frac{1}{\sqrt{2}} & \frac{1}{\sqrt{2}} & \frac{1}{\sqrt{2}} \end{pmatrix} \begin{pmatrix} v_a \\ v_b \\ v_c \end{pmatrix}$$

The transform is unitary (orthonormal). Its defining property is power invariance (Parseval's theorem):

$$v_a^2 + v_b^2 + v_c^2 = v_\alpha^2 + v_\beta^2 + v_0^2$$

This is the quadratic conservation law. The Clarke transform preserves the norm of the signal vector — total power is identical in both frames. This is mathematically identical to the statement that quantum mechanical basis changes (unitary transformations) preserve $\langle\psi|\psi\rangle$.

### 3.2 Symmetrical Components

The Clarke/Fortescue decomposition separates any three-phase signal into three sequence components:

- **Positive sequence** ($+$): Phasors rotating counterclockwise at angular frequency $\omega$. In the $\alpha\beta$ plane, this traces a circle with sense $(+)$.
- **Negative sequence** ($-$): Phasors rotating clockwise at $\omega$. Traces a circle with sense $(-)$.
- **Zero sequence** ($0$): Common-mode component. No rotation; equal value on all three phases.

For a balanced system (no zero sequence), the total power decomposes as:

$$P_{\text{total}} = P_+ + P_- + P_0$$

This tripartite decomposition is the key structural feature. Standard Bell analysis uses only two of these three terms.

### 3.3 The Analyzer: Park Rotation

A measurement at angle $\phi$ is implemented by the Park transform — a rotation of the Clarke frame by angle $\phi$:

$$\begin{pmatrix} v_d \\ v_q \end{pmatrix} = \begin{pmatrix} \cos\phi & \sin\phi \\ -\sin\phi & \cos\phi \end{pmatrix} \begin{pmatrix} v_\alpha \\ v_\beta \end{pmatrix}$$

This is a rotation of the measurement basis. The power captured in the $d$-axis ("direct") channel is:

$$P_d(\phi) = v_d^2 = (v_\alpha \cos\phi + v_\beta \sin\phi)^2$$

For a positive-sequence signal with $v_\alpha = V\cos(\theta)$, $v_\beta = V\sin(\theta)$:

$$P_d(\phi) = V^2 \cos^2(\theta - \phi)$$

This is Malus's law — the intensity of polarized light transmitted through a polarizer at angle $\phi$. The Clarke-Park projection is a classical polarization measurement.

---

## 4. Two-Party Accounting: The CHSH Projection

### 4.1 The Standard Setup

The source emits equal-amplitude positive and negative sequences: $V_+ = V_- = V$. In the $\alpha\beta$ frame, the positive sequence traces a counterclockwise circle and the negative sequence traces a clockwise circle. Their superposition at any instant is a linearly polarized oscillation — the net signal swings back and forth along a fixed axis.

Analyzer $A$ at angle $\phi_A$ captures power:

$$P_A = V^2 \cos^2(\theta - \phi_A) \quad \text{(from + sequence)}$$

Analyzer $B$ at angle $\phi_B$ captures the complementary distribution:

$$P_B = V^2 \sin^2(\theta - \phi_B) \quad \text{(complement of + sequence)} = V^2\cos^2(\theta - \phi_B + \pi/2)$$

The complementarity arises because the negative sequence, at any angle $\phi$, delivers $\sin^2(\theta - \phi)$ wherever the positive sequence delivers $\cos^2(\theta - \phi)$.

### 4.2 Local Uniformity (No-Signaling)

A critical feature: neither observer, locally, can determine the other's analyzer setting. Observer $A$ does not know whether they received the positive or negative sequence. Their expectation over the hidden variable (rotation sense $\pm$, equally probable):

$$\langle P_A \rangle_\pm = \frac{1}{2}\cos^2(\theta - \phi_A) + \frac{1}{2}\sin^2(\theta - \phi_A) = \frac{1}{2}$$

Uniform. Independent of $\phi_A$. This is the no-signaling theorem, derived here from the $\pm$ symmetry of the sequence decomposition.

In density matrix language, tracing over particle $B$ (i.e., averaging over the unknown sequence label) yields the maximally mixed state $\rho_A = I/2$. The rotation sense is the hidden variable; its inaccessibility to individual observers is what produces local uniformity.

### 4.3 The Correlation

The joint correlation, computed by integrating over the shared hidden variable $\theta$ (the emission phase, uniformly distributed):

$$E(a,b) = -\cos(2\Delta\phi)$$

(derivation in Section 2.3). This matches the quantum mechanical singlet-state prediction exactly. The CHSH value $S = 2\sqrt{2}$ follows.

### 4.4 The Puzzle

The derivation above is entirely classical: deterministic phasors, linear projections, power computation. Yet it reproduces the quantum prediction, including the Bell violation. Bell's theorem states that no local hidden variable model can achieve $S > 2$. So either the derivation contains an error, or the model is not local in the sense Bell requires.

The resolution, we argue, lies not in an error but in an omission. The two-party accounting ignores the third term in the conservation law.

---

## 5. The Threshold Problem and Binary Outcomes

Before addressing the three-party resolution, we must confront the binarization problem: real Bell tests produce binary outcomes ($\pm 1$), not continuous power values.

### 5.1 Model 1: Deterministic Threshold

Assign outcome $A = +1$ if $\cos^2(\theta - \phi_A) > 1/2$, else $A = -1$:

$$A(\theta, \phi_A) = \text{sgn}[\cos(2(\theta - \phi_A))]$$
$$B(\theta, \phi_B) = -\text{sgn}[\cos(2(\theta - \phi_B))]$$

Integration over uniform $\theta$:

$$E_{\text{det}}(a,b) = -1 + \frac{4|\Delta\phi|}{\pi}$$

This is piecewise linear. CHSH yields $S = 2$ exactly — the Bell bound, but no violation. The $\text{sgn}$ function destroys the quadratic structure. The cos² bowl is flattened into a step function, and the double-angle information is lost.

### 5.2 Model 2: Stochastic Local

Let $\cos^2(\theta - \phi)$ be the *probability* of outcome $+1$, with independent local coin flips:

$$P(A=+1 \mid \theta) = \cos^2(\theta - \phi_A), \quad P(B=+1 \mid \theta) = \sin^2(\theta - \phi_B)$$

Independence given $\theta$ (the locality condition):

$$\langle AB \mid \theta \rangle = \langle A \mid \theta \rangle \cdot \langle B \mid \theta \rangle = \cos(2(\theta - \phi_A)) \cdot (-\cos(2(\theta - \phi_B)))$$

Integrating:

$$E_{\text{stoch}}(a,b) = -\frac{1}{2}\cos(2\Delta\phi)$$

Correct shape, but half amplitude. CHSH yields $S = \sqrt{2}$. The independent coin flips — the factorization condition that defines locality — introduce noise that dilutes the correlation by exactly a factor of 2.

### 5.3 The Gap

| Model | $E(a,b)$ | $S$ | Mechanism |
|---|---|---|---|
| Stochastic local | $-\frac{1}{2}\cos(2\Delta\phi)$ | $\sqrt{2}$ | Independent coin flips dilute |
| Deterministic threshold | $-1 + 4|\Delta\phi|/\pi$ | $2$ | Binarization linearizes |
| Quantum / quadratic conservation | $-\cos(2\Delta\phi)$ | $2\sqrt{2}$ | Full quadratic, strict complementarity |

Each step is a factor of $\sqrt{2}$. The gap between stochastic local ($S = \sqrt{2}$) and quantum ($S = 2\sqrt{2}$) is a factor of 2 in correlation amplitude. This factor is the signature of strict complementarity: when $A$ registers $+1$, $B$ *must* register $-1$ at $\Delta\phi = 0$. Not "probably" — *must*. The conservation law enforces perfect anti-correlation, which the factorized (local) model cannot achieve without also constraining the marginals.

This is the core tension. Strict complementarity at all angles simultaneously — $\cos^2 + \sin^2 = 1$ enforced event-by-event, not just in expectation — is a nonlocal constraint. And it is precisely this constraint that produces the factor of 2 that separates $S = \sqrt{2}$ from $S = 2\sqrt{2}$.

---

## 6. The Third Party: Zero-Sequence Mode

### 6.1 The Missing Energy

Consider analyzers at angles $\phi_A \neq \phi_B$. Analyzer $A$ captures $\cos^2(\theta - \phi_A)$. Analyzer $B$ captures $\cos^2(\theta - \phi_B)$. Their sum:

$$P_A + P_B = \cos^2(\theta - \phi_A) + \cos^2(\theta - \phi_B)$$

Using the identity $\cos^2 x + \cos^2 y = 1 + \cos(x-y)\cos(x+y)$:

$$P_A + P_B = 1 + \cos(\Delta\phi)\cos(2\theta - \phi_A - \phi_B)$$

This oscillates. It is *not* constant (unless $\Delta\phi = 0$ or $\pi/2$). Power is not conserved between the two measurement channels alone.

Where is the remaining power? In the zero-sequence mode:

$$P_0(\theta) = P_{\text{total}} - P_A(\theta) - P_B(\theta)$$

Since $P_{\text{total}}$ is constant (the conserved quadratic form), $P_0$ absorbs whatever $A$ and $B$ do not capture. It is the energy in the field between the detectors — the mode that neither analyzer projects onto.

### 6.2 Properties of the Zero-Sequence Power

At $\Delta\phi = 0$ (aligned analyzers): $P_0 = 0$ at all $\theta$. The two analyzers fully partition the power budget. This corresponds to perfect anti-correlation ($E = -1$): all information is in the measurements, none is in the channel.

At $\Delta\phi = \pi/2$ (orthogonal analyzers): $P_0$ is maximized and $\theta$-independent. The channel absorbs all correlation energy. The measurements become independent ($E = 0$): no information flows between the detectors through the measurement record.

At $\Delta\phi = \pi/4$ (the CHSH violation angle): $P_0$ is at an intermediate value. Correlation energy is *partially* in the channel and partially in the measurements. This intermediate configuration is precisely what produces the Bell violation.

### 6.3 The Three-Party Conservation Law

The complete accounting is:

$$P_+ + P_- + P_0 = P_{\text{total}} = \text{const}$$

or equivalently in the Clarke frame:

$$P_\alpha + P_\beta + P_0 = v_\alpha^2 + v_\beta^2 + v_0^2 = \text{const}$$

This is a *three-party* conservation law. The CHSH inequality tracks only two of the three terms. The third term — $P_0$, the zero-sequence power, the energy in the vacuum/channel mode — acts as a reservoir that absorbs and releases correlation energy as the analyzer angles change.

The "nonlocality" of quantum correlations, in this framework, is not action at a distance. It is the constraint imposed by a global conservation law on the joint statistics of two subsystems that are coupled through a third. The correlations are mediated by the conserved total, just as the correlation between the kinetic energies of two decay fragments is mediated by conservation of total energy — except that the conserved quantity is quadratic, which doubles the angular frequency and pushes $S$ past the Bell bound.

### 6.4 Analogy to Quantum Field Theory

This interpretation aligns with the field-theoretic understanding of entanglement. In algebraic quantum field theory (Haag 1996, Witten 2018), entanglement is not a property of particles but of the state of the field in a region of spacetime. The entanglement entropy between two spatial regions $A$ and $B$ is a property of the field modes at the boundary between them — the "edge modes" or "zero modes" that neither region fully contains.

The zero-sequence component plays exactly this role. It is the mode that belongs to neither $A$ nor $B$ individually but participates in the joint conservation law. The correlations between $A$ and $B$ exist *because* the zero-sequence mode couples them through the conserved quadratic form.

In the Bohmian interpretation, this structure has a natural counterpart. The quantum potential — the nonlocal term in the guidance equation — encodes the global conservation constraint. In our framework, the "quantum potential" is the zero-sequence power: the energy in the channel that constrains the joint statistics of the measured subsystems.

---

## 7. Extension to Mermin: Three-Party Violations

### 7.1 Why Three Phases Matter

The three-phase structure is not an analogy — it is the natural mathematical habitat for three-party entanglement. The Clarke transform provides three orthogonal modes ($\alpha$, $\beta$, $0$). The symmetrical component decomposition provides three sequence types ($+$, $-$, $0$). The group structure of the three-phase system provides the symmetry constraints.

The Mermin inequality for three parties with binary outcomes (Mermin 1990) states:

$$|M| \leq 2 \quad \text{(LHV)}, \quad |M| \leq 4 \quad \text{(QM)}$$

The quantum-to-classical violation ratio is $4/2 = 2$, compared to $2\sqrt{2}/2 = \sqrt{2}$ for CHSH. The three-party inequality permits larger violations because the additional party provides additional conserved quadratic forms that the two-party inequality cannot access.

### 7.2 Multiple Quadratic Invariants

The three-phase system possesses multiple independent quadratic invariants:

**Active power (real part of the quadratic form):**
$$P = v_\alpha i_\alpha + v_\beta i_\beta$$

**Reactive power (imaginary part):**
$$Q = v_\alpha i_\beta - v_\beta i_\alpha$$

**Apparent power (magnitude):**
$$S^2 = P^2 + Q^2$$

Each of these is a conserved quadratic form under the Clarke transform. The CHSH inequality, being a two-party test, probes only one of these invariants (e.g., $P$). The Mermin inequality, being a three-party test, can probe the joint structure of $P$, $Q$, and $S$ simultaneously.

### 7.3 The D4 Connection

The delta-connected LC tank network studied in (author's prior work) possesses D4 symmetry — the dihedral group of the square. This group has five irreducible representations and correspondingly five independent quadratic invariants. The standard three-phase system (with $C_3$ symmetry) has fewer.

The additional invariants from D4 symmetry provide additional conserved quadratic forms, each capable of contributing cos² correlation structure. Whether these additional invariants produce violations of generalized Bell inequalities beyond what $C_3$ symmetry alone provides is an open question and the subject of ongoing investigation.

### 7.4 Volume Conservation on Higher-Dimensional Surfaces

In the two-party case, the conservation law $\cos^2 + \sin^2 = 1$ constrains the power allocation to a circle (the unit circle in the power plane). The two bowls tile a plane.

In the three-party case, the conservation law $P_\alpha^2 + P_\beta^2 + P_0^2 = P_{\text{total}}^2$ constrains the power allocation to the surface of a sphere. The three bowls tile a sphere in three orthogonal great-circle planes. The volume enclosed by this sphere is the conserved total, and the Bell inequality violation measures how much of this volume is accessible to the measurement channels versus how much is hidden in the zero-sequence mode.

The violation grows with the number of independent conserved quadratic forms precisely because each additional form adds a dimension to the conservation surface, allowing tighter constraints on the joint statistics. This is the geometric content of the Mermin inequality's larger violation ratio.

---

## 8. The Tsirelson Bound as a Conservation Theorem

### 8.1 Tsirelson's Proof in the Conservation Framework

Tsirelson (1980) proved that $|S| \leq 2\sqrt{2}$ for any quantum system. His proof requires only:

1. Observables are Hermitian with eigenvalues $\pm 1$ (i.e., $A^2 = I$).
2. Alice's observables commute with Bob's ($[A, B] = 0$).
3. The state space has a positive-definite inner product.

In our framework, these translate to:

1. **$A^2 = I$**: Outcomes are binary. The power distribution is binarized into $\pm 1$ clicks.
2. **$[A, B] = 0$**: The analyzers act independently. Their projections do not interfere.
3. **Positive-definite inner product**: The conserved quadratic form is positive-definite (power is non-negative).

The Tsirelson bound is therefore the maximum correlation achievable by binary projections of a single positive-definite quadratic form. The $2\sqrt{2}$ value reflects the geometry of binary projections on a circle — the cos² structure admits at most this much correlation before the binary constraint saturates.

### 8.2 Exceeding Tsirelson

The Popescu-Rohrlich (PR) box (1994) achieves $S = 4$ with correlations $E(a,b) = (-1)^{a \cdot b}$ — a pure step function. In our framework, this corresponds to a conservation law so rigid that the power allocation snaps between channels discontinuously, with zero leakage. No known physical conservation law produces this behavior, because physical conservation laws operate on continuous (Lie group) symmetries, which produce smooth (cosine-type) correlation functions.

The hierarchy is:

| Regime | $S_{\max}$ | Conservation structure |
|---|---|---|
| Stochastic local | $\sqrt{2}$ | Independent marginals, no conservation enforcement |
| Deterministic local (Bell) | $2$ | Single linear conservation, binary outcomes |
| Quantum (Tsirelson) | $2\sqrt{2}$ | Single quadratic conservation, binary outcomes |
| PR box | $4$ | Discontinuous conservation (unphysical) |

Each step reflects a tighter conservation constraint. The quantum case is distinguished by having exactly one positive-definite quadratic invariant and continuous symmetry. Adding more invariants (Mermin, three parties) does not exceed Tsirelson in the CHSH framework but permits larger violations in generalized inequalities.

---

## 9. Discussion

### 9.1 What This Framework Claims

The central claim is interpretive, not mathematical. The mathematics of Bell violations is settled. What we offer is a physical interpretation:

**Bell violations measure the algebraic order of conservation laws.** Linear conservation ($p_A + p_B = 0$) produces sub-Bell correlations. Quadratic conservation ($P_A + P_B + P_0 = \text{const}$) produces Tsirelson-saturating correlations. The "mystery" is not nonlocality but incomplete accounting: the two-party CHSH framework omits the zero-sequence mode that mediates the conservation constraint.

### 9.2 Relation to Prior Work

**Bohmian mechanics.** Our framework shares Bohm's commitment to a definite underlying dynamics (the phasor field) with nonlocal constraints (the conservation law). The difference is representational: where Bohm uses a guidance equation and quantum potential in configuration space, we use Clarke-Park projections and power conservation in the $\alpha\beta 0$ frame. The zero-sequence mode plays the role of the quantum potential — it is the nonlocal term that couples the subsystems through the conserved quadratic form.

**Information-theoretic approaches.** The volume conservation picture aligns with the monogamy of entanglement (Coffman, Kundu, Wootters 2000): the total correlation budget is fixed, and any correlation with $A$ reduces available correlation with $C$. This is $P_A + P_B + P_0 = \text{const}$ — the power allocated to $A$-$B$ correlations is unavailable for $A$-$C$ correlations.

**Geometric approaches.** The connection between cos² and the Bloch sphere is well known. Our contribution is identifying the *conservation law* as the primitive, with the Bloch sphere geometry being a consequence of quadratic conservation on a two-dimensional phase space.

### 9.3 Predictions and Testable Consequences

1. **Three-party tests.** If the zero-sequence mode is a physical degree of freedom (not merely a bookkeeping device), then three-party Bell tests with explicit access to the channel mode should yield violations consistent with Mermin's bound, and the zero-sequence contribution should be directly measurable.

2. **Classical electromagnetic tests.** Three-phase power systems with controlled sequence injection should reproduce the correlation statistics predicted here. The Clarke-Park measurement apparatus already exists in every power systems laboratory. The required experiment is: prepare equal positive and negative sequence signals, measure at two independently chosen Park angles, and compute $E(\phi_A, \phi_B)$ over many trials with random emission phase $\theta$.

3. **Symmetry-enhanced violations.** Systems with D4 or higher symmetry, providing additional independent quadratic invariants, should produce larger violations of generalized (multi-party, multi-setting) Bell inequalities than systems with only $C_3$ symmetry.

### 9.4 Limitations

This framework does not resolve the measurement problem. It provides a picture of *why* quantum correlations have the structure they do (quadratic conservation) and *where* the nonlocality lives (zero-sequence mode), but it does not explain how individual measurement outcomes are selected from the cos² distribution. The threshold models of Section 5 show that binarization is the critical step, and neither deterministic nor stochastic local binarization reproduces the full quantum prediction. A nonlocal binarization mechanism — event-by-event enforcement of the conservation constraint — is required.

This is, essentially, the measurement problem restated in power-systems language. We do not solve it, but we localize it: the mystery is not in the correlations (which follow from conservation) nor in the conservation law (which is Parseval's theorem) but in the event-by-event enforcement of a global constraint. That enforcement is what Bohm's quantum potential provides, and our framework is consistent with (though not dependent on) Bohmian mechanics.

---

## 10. Conclusion

We have shown that:

1. The form of Bell-inequality correlations is determined by the algebraic order of the conservation law governing the correlated system: linear conservation produces $E \propto \cos(\Delta\phi)$, quadratic conservation produces $E \propto \cos(2\Delta\phi)$.

2. The CHSH violation arises specifically from the double-angle identity $\cos^2(x) = (1 + \cos(2x))/2$, which is a direct algebraic consequence of the conserved quantity being quadratic (power, probability) rather than linear (momentum, amplitude).

3. The two-party CHSH framework constitutes an incomplete accounting of a three-party conservation law. The third party — the zero-sequence mode, corresponding to the field between measurement stations — carries correlation energy that the standard framework omits.

4. The apparent nonlocality of quantum correlations is the signature of a global conservation constraint on a quadratic form. It is no more mysterious than momentum conservation in a two-body decay, but the quadratic structure doubles the angular frequency and pushes correlations beyond the Bell bound.

5. The Clarke transform from three-phase power systems provides the natural mathematical language for this decomposition, with positive/negative sequences mapping to the two measured particles and the zero sequence mapping to the vacuum/channel mode.

The three-phase framework suggests that the foundations of quantum mechanics and the foundations of power systems engineering share more than superficial structural similarity: they are different representations of the same underlying geometry of quadratic conservation laws on phase spaces with rotational symmetry.

---

## References

- Bell, J. S. (1964). On the Einstein Podolsky Rosen paradox. *Physics Physique Fizika*, 1(3), 195–200.
- Clauser, J. F., Horne, M. A., Shimony, A., & Holt, R. A. (1969). Proposed experiment to test local hidden-variable theories. *Physical Review Letters*, 23(15), 880.
- Clarke, E. (1943). *Circuit Analysis of A-C Power Systems*, Vol. I. Wiley.
- Coffman, V., Kundu, J., & Wootters, W. K. (2000). Distributed entanglement. *Physical Review A*, 61(5), 052306.
- Fortescue, C. L. (1918). Method of symmetrical co-ordinates applied to the solution of polyphase networks. *AIEE Transactions*, 37(2), 1027–1140.
- Haag, R. (1996). *Local Quantum Physics*. Springer.
- Mermin, N. D. (1990). Extreme quantum entanglement in a superposition of macroscopically distinct states. *Physical Review Letters*, 65(15), 1838.
- Popescu, S., & Rohrlich, D. (1994). Quantum nonlocality as an axiom. *Foundations of Physics*, 24(3), 379–385.
- Tsirelson, B. S. (1980). Quantum generalizations of Bell's inequality. *Letters in Mathematical Physics*, 4(2), 93–100.
- Witten, E. (2018). APS Medal for Exceptional Achievement in Research: Invited article on entanglement properties of quantum field theory. *Reviews of Modern Physics*, 90(4), 045003.
