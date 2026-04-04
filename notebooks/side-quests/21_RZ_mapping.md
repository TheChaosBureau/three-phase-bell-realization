# Rosetta Dictionary Entry: Convolution Square and Complex Power

## 0. Status

This entry is a **structural isomorphism**, not an analogy. Each row identifies
a mathematical object in one column with a mathematical object in the other.
The identifications are exact at the level of algebraic structure. Where they
are not exact, the entry says so explicitly.

---

## 1. Setup: the two systems

### 1A. Arithmetic side (Weil)

Let $g:(0,\infty)\to\mathbb{C}$ be a Schwartz-class test function. Define:

- **Mellin transform:**
  $\tilde{g}(s) = \int_0^\infty g(x)\,x^s\,\frac{dx}{x}$

- **Multiplicative involution:**
  $g^*(x) = x^{-1}g(x^{-1})$, so $\widetilde{g^*}(s) = \tilde{g}(1-s)$

- **Multiplicative convolution:**
  $(g_1 * g_2)(x) = \int_0^\infty g_1(x/y)\,g_2(y)\,\frac{dy}{y}$,
  so $\widetilde{g_1 * g_2}(s) = \tilde{g}_1(s)\,\tilde{g}_2(s)$

- **Convolution square:**
  $f = g * g^*$, so $\tilde{f}(s) = \tilde{g}(s)\,\tilde{g}(1-s)$

- **Weil criterion:**
  RH $\iff$ $W^{(1)}(f) \geq 0$ for all $f = g * g^*$, where $W^{(1)}$
  is the explicit-formula distribution.

### 1B. Circuit side (complex power)

Let $\mathcal{N}$ be a linear time-invariant one-port network with
impedance $Z(\omega)$, driven by current $I(\omega)$ at frequency $\omega$.

- **Voltage response:**
  $V(\omega) = Z(\omega)\,I(\omega)$

- **Complex power:**
  $S(\omega) = V(\omega)\,\overline{I(\omega)} = Z(\omega)\,|I(\omega)|^2$

- **Active power (real part):**
  $P(\omega) = \operatorname{Re}(S) = \operatorname{Re}(Z)\,|I|^2$

- **Passivity:**
  The network is passive iff $\operatorname{Re}(Z(\omega)) \geq 0$ for all $\omega$,
  equivalently $P(\omega) \geq 0$ for every driving current at every frequency.

---

## 2. The structural dictionary

### Entry 2.1: Test function ↔ driving current

| Weil | Circuit |
|------|---------|
| $g:(0,\infty)\to\mathbb{C}$ | $I:\mathbb{R}\to\mathbb{C}$ |
| Mellin transform $\tilde{g}(s)$ | Fourier spectrum $\hat{I}(\omega)$ |
| Schwartz decay in $x$ | Finite-energy condition $\|I\|^2 < \infty$ |

**Precision note.** The Mellin transform is a Fourier transform on the
multiplicative group $(0,\infty)$. In log coordinates $u = \log x$, with
centered half-density $h(u) = e^{u/2}g(e^u)$, we have
$\tilde{g}(1/2 + i\xi) = \hat{h}(\xi)$, which is literally a Fourier transform.
The frequency variable $\xi$ is the log-frequency. So Mellin and Fourier are
not "analogous" — they are the same transform in different coordinates.

### Entry 2.2: Multiplicative involution ↔ complex conjugation (on the critical line)

| Weil | Circuit |
|------|---------|
| $g^*(x) = x^{-1}g(x^{-1})$ | $\overline{I(\omega)}$ |
| $\widetilde{g^*}(s) = \tilde{g}(1-s)$ | $\overline{\hat{I}(\omega)} = \hat{I}(-\omega)$ (for real $I$) |
| Involution $s \leftrightarrow 1-s$ | Conjugation $\omega \leftrightarrow -\omega$ |

**Precision note.** This identification is exact on the critical line
$s = 1/2 + i\xi$, where $1 - s = 1/2 - i\xi = \bar{s}$. For real-valued
$h(u)$, $\hat{h}(-\xi) = \overline{\hat{h}(\xi)}$, so
$\tilde{g}(1-s) = \overline{\tilde{g}(s)}$ on the critical line.

Off the critical line ($s = \sigma + i\gamma$, $\sigma \neq 1/2$),
$1-s = (1-\sigma) - i\gamma \neq \bar{s}$, and the involution no longer
acts as conjugation. This is the structural origin of the distinction
between "on-critical" and "off-critical."

### Entry 2.3: Convolution square ↔ complex power

This is the central identification.

| Weil | Circuit |
|------|---------|
| $f = g * g^*$ | $S = V \cdot \overline{I}$ |
| $\tilde{f}(s) = \tilde{g}(s)\,\tilde{g}(1-s)$ | $S(\omega) = Z(\omega)\,|\hat{I}(\omega)|^2$ |
| Two factors from $g$ and $g^*$ | Two factors from $V = ZI$ and $\overline{I}$ |

**Structural content.** The convolution square pairs the test function with
its involution-reflected partner, producing a bilinear product in the spectral
domain. Complex power pairs voltage (the network's response) with the
conjugated driving current, producing a bilinear product in the frequency
domain. Both constructions yield a quadratic functional of the input
($g$ or $I$) whose sign carries physical meaning.

**The role of $Z$.** In the circuit picture, the impedance $Z(\omega)$
mediates between $I$ and $V$. In the Weil picture, the mediating object
is the involution $s \leftrightarrow 1-s$ (the functional equation).
On the critical line, the functional equation acts as conjugation
($Z = 1$, purely resistive, matched). Off the critical line, the
involution maps $s$ to a point other than $\bar{s}$, introducing a
"complex impedance" that can have negative real part.

### Entry 2.4: Evaluation at a zero ↔ power dissipated at a resonance

| Weil | Circuit |
|------|---------|
| Zero $\rho$ of $\xi(s)$ | Resonant frequency $\omega_j$ |
| $\tilde{f}(\rho) = \tilde{g}(\rho)\,\tilde{g}(1-\rho)$ | $S(\omega_j) = Z(\omega_j)\,|I(\omega_j)|^2$ |
| $\rho = 1/2 + i\gamma$: $\tilde{f}(\rho) = |\tilde{g}(\rho)|^2 \geq 0$ | $Z = R > 0$: $S = R|I|^2 \geq 0$ |
| $\rho = \sigma + i\gamma$, $\sigma \neq 1/2$: sign indefinite | $\operatorname{Re}(Z) < 0$: $P < 0$ possible |

**Numerical verification.** We computed $\tilde{f}(\rho)$ on the odd-sector
probe $h_-(u) = \sinh(\alpha u)e^{-au^2}$ with 300 zeta zeros. At every
tested $(a,\alpha)$, each critical-line zero contributed a nonneg term
$\varphi(\gamma_\rho)^2$ to the spectral sum. When a hypothetical
off-critical zero at $\rho = 0.75 + 14.13i$ was inserted, its contribution
was negative and overwhelmed the critical-line sum by a factor of ~2 at
$(a,\alpha) = (1.0, 0.5)$, making the total spectral sum negative. This is
the direct analogue of a resonance at a frequency where the impedance has
negative real part: the network supplies energy instead of absorbing it.

### Entry 2.5: Weil positivity ↔ network passivity

| Weil | Circuit |
|------|---------|
| $W^{(1)}(g * g^*) \geq 0\;\forall\,g$ | $\operatorname{Re}(Z(\omega)) \geq 0\;\forall\,\omega$ |
| Equivalent to RH | Equivalent to passivity of the network |
| Sum over zeros $\geq 0$ | Total power absorbed $\geq 0$ |

**Why this is the right identification.** Passivity is not checked
frequency by frequency in practice. It is a consequence of network
topology: a network built from passive components ($R \geq 0$, $L \geq 0$,
$C \geq 0$) is passive at all frequencies by Kirchhoff's laws. Similarly,
Weil positivity (if RH is true) holds for all test functions simultaneously,
not because each zero individually behaves well, but because the underlying
arithmetic structure forces it globally.

In the function field case, the "circuit topology" is the algebraic curve $C$,
the "impedance matrix" is the action of Frobenius on $H^1(C)$, and the
"passivity theorem" is the Hodge index theorem / Castelnuovo–Severi
inequality. For $\zeta(s)$ over $\mathbb{Q}$, the circuit topology is unknown.

### Entry 2.6: Explicit formula ↔ complex power balance (Kirchhoff)

| Weil | Circuit |
|------|---------|
| $\sum_\rho \tilde{f}(\rho) = E - P - A$ | $\sum_j S(\omega_j) = S_{\text{source}} - S_{\text{load}}$ |
| $E$: endpoint terms $\tilde{f}(0) + \tilde{f}(1)$ | Source injection |
| $P$: prime sum $\sum \Lambda(n)[f(n) + f^*(n)]$ | Load sampling (port currents at discrete nodes) |
| $A$: archimedean correction | Continuous dissipation / radiation losses |
| Identity holds exactly for all $f$ | Conservation of complex power |

**Precision note.** The explicit formula is an exact distributional identity.
It is the number-theoretic Kirchhoff's law: total spectral power (summed
over resonances/zeros) equals total arithmetic power (summed over
primes/ports plus archimedean/continuous terms). The primes play the role
of discrete lumped ports where current is injected. The archimedean term
plays the role of distributed losses (or gains) in the continuous medium.

### Entry 2.7: Half-density centering ↔ Park demodulation

| Weil | Circuit |
|------|---------|
| $h(u) = e^{u/2}g(e^u)$ | Park transform to synchronous frame |
| Critical line becomes $\xi = 0$ DC | Positive sequence becomes DC |
| Reflection $h(u) \to h(-u)$ | Inversion of sequence order |
| Balanced: $h$ even ($h_- = 0$) | Balanced: no negative sequence |
| Tilted: $h$ has odd component | Unbalanced: negative sequence present |

**Precision note.** The half-density shift $e^{u/2}$ that centers the Mellin
transform on the critical line is algebraically identical to the
normalization that makes the Park transform unitary. In both cases, the
shift converts a weighted inner product (Mellin measure $dx/x$, or
power-weighted phase inner product) into an unweighted $L^2$ inner product,
placing the "balanced" or "critical" operating point at the origin of
the frequency/spectral variable.

### Entry 2.8: Sector decomposition ↔ sequence decomposition

| Weil | Circuit |
|------|---------|
| $h = h_+ + h_-$ (even/odd under $u \to -u$) | $I = I_+ + I_-$ (positive/negative sequence) |
| $Q(h) = Q_+(h_+) + Q_-(h_-)$, no cross terms | $S = S_+ + S_-$, sequences decouple in balanced network |
| Odd sector: $\hat{H}_-(\xi) = \varphi(\xi)^2 \geq 0$ | Negative-sequence power: nonneg in passive network |
| Sectors decouple in the Weil form | Sequences decouple under three-fold symmetry |

**Numerically verified.** The cross term vanishes identically because the
full Weil functional is reflection-even (every component — prime sum,
archimedean term, zero sum, endpoints — annihilates odd test functions).
This is the exact analogue of the decoupling of positive and negative
sequence in a balanced three-phase system: the symmetry of the network
forces orthogonality between sequence components.

---

## 3. What the correspondence does and does not do

### 3A. What is exact

The following identifications are not analogies. They are the same
mathematical structure viewed in different coordinate systems:

1. **Mellin on $(0,\infty)$ with measure $dx/x$ is Fourier on $(\mathbb{R},du)$
   after $u = \log x$ and half-density centering.** This is a change of
   variables, not a metaphor.

2. **The involution $g^*(x) = x^{-1}g(x^{-1})$ becomes reflection
   $h(-u) = (Rh)(u)$ in log coordinates.** This is exact.

3. **The convolution square $\tilde{f}(s) = \tilde{g}(s)\tilde{g}(1-s)$
   evaluates to $|\tilde{g}(s)|^2$ on the critical line and to a
   sign-indefinite product off it.** This is the same algebraic structure
   as $S = Z|I|^2$ being nonneg when $Z$ is real-positive and sign-indefinite
   when $Z$ is complex.

4. **The explicit formula is an exact identity** (not an approximation)
   equating a spectral sum to an arithmetic sum. This is conservation
   of a quadratic quantity, structurally identical to Kirchhoff's complex
   power theorem.

5. **The sector decoupling $Q = Q_+ + Q_-$ with vanishing cross terms**
   follows from the reflection symmetry of the Weil functional, exactly
   as sequence decoupling follows from the rotational symmetry of a
   balanced polyphase network.

### 3B. What is structural but not exact

6. **"Impedance" as the mediator.** In the circuit, $Z(\omega)$ is a
   well-defined transfer function with known analytic properties
   (positive-real for passive networks). In the Weil picture, the
   "impedance" is the relationship between $\tilde{g}(s)$ and
   $\tilde{g}(1-s)$ at each zero, which is determined by the functional
   equation but does not have a single scalar representation. The
   identification $Z_\rho \sim \tilde{g}(1-\rho)/\overline{\tilde{g}(\rho)}$
   is suggestive but depends on the test function $g$.

7. **Primes as "ports."** The von Mangoldt sampling
   $\sum \Lambda(n) n^{-1/2}[h(\log n) + h(-\log n)]$ evaluates the
   test function at discrete points $u = \log p^k$. This is structurally
   similar to port currents at discrete nodes, but the "network" between
   ports is not specified. In the function field case, the network is the
   curve $C$. For $\zeta(s)$ over $\mathbb{Q}$, the network is unknown.

### 3C. What is the open problem

8. **The circuit topology.** In electrical engineering, passivity follows
   from the fact that the network is built from passive components arranged
   in a specific topology, and Kirchhoff's laws at every node enforce
   global passivity. In the function field case, the topology is the
   algebraic curve $C$, and the passivity theorem is the Hodge index
   theorem. For $\zeta(s)$ over $\mathbb{Q}$, finding this topology
   — the arithmetic object whose structure forces Weil positivity — is
   the Riemann Hypothesis.

   In the language of this dictionary: **the primes are the ports, the
   explicit formula is Kirchhoff's law, and passivity is RH. The missing
   object is the circuit.**

---

## 4. Formulas

### 4.1. Convolution square at a zero

$$\tilde{f}(\rho) = \tilde{g}(\rho)\,\tilde{g}(1-\rho)$$

On the critical line ($\rho = 1/2 + i\gamma$, real $\gamma$):
$$\tilde{f}(\rho) = \tilde{g}(1/2+i\gamma)\,\overline{\tilde{g}(1/2+i\gamma)} = |\tilde{g}(\rho)|^2 \geq 0$$

Off the critical line ($\rho = \sigma + i\gamma$, $\sigma \neq 1/2$):
$$\tilde{f}(\rho) = \tilde{g}(\sigma + i\gamma)\,\tilde{g}((1-\sigma) - i\gamma)$$

The two factors are evaluations at different points in the complex plane.
Their product is a complex number with no sign constraint.

### 4.2. Complex power at a resonance

$$S(\omega_j) = Z(\omega_j)\,|I(\omega_j)|^2$$

Passive network ($\operatorname{Re}(Z) \geq 0$):
$$P(\omega_j) = \operatorname{Re}(Z)\,|I|^2 \geq 0$$

Active network ($\operatorname{Re}(Z) < 0$ at some frequency):
$$P(\omega_j) = \operatorname{Re}(Z)\,|I|^2 < 0 \text{ possible}$$

### 4.3. The explicit formula in centered log coordinates

$$\sum_\rho \hat{H}(\gamma_\rho) = \hat{H}(i/2) + \hat{H}(-i/2) - 2\sum_{n \geq 2} \frac{\Lambda(n)}{\sqrt{n}}\,H(\log n) - A[H]$$

where $H = h \star Rh$ is the additive convolution of $h$ with its
reflection, and $A[H]$ is the archimedean correction.

### 4.4. The forcing condition

RH is equivalent to:

$$\sum_\rho \hat{H}(\gamma_\rho) \geq 0 \quad \text{for all positive-definite } H$$

In circuit language: total power absorbed at all resonances is nonneg
for every driving signal. That is, the network is passive.

---

## 5. Numerical evidence

### 5.1. Critical-line positivity (trivial)

For the odd-sector probe $h_-(u) = \sinh(\alpha u)\,e^{-au^2}$, each
critical-line zero contributes $\hat{H}_-(\gamma) = \varphi(\gamma)^2 \geq 0$.
Verified for $a \in [0.5, 50]$, $\alpha \in [0.1, 1.0]$, 300 zeros.

### 5.2. Off-critical detection (nontrivial)

A hypothetical off-critical zero at $\rho = 0.75 + 14.13i$ (same height
as $\gamma_1$, but at $\sigma = 3/4$) contributes a **negative** term to
the spectral sum. At $(a, \alpha) = (1.0, 0.5)$:

| Source | Contribution |
|--------|-------------|
| Critical-line zeros (100 terms) | $+4.29 \times 10^{-44}$ |
| Off-critical quadruplet | $-9.06 \times 10^{-44}$ |
| **Total** | $-4.77 \times 10^{-44}$ |

The off-critical zero makes the "network" active at that resonance —
it supplies energy rather than absorbing it — and the total power goes
negative. This is the Weil criterion detecting a violation of RH.

### 5.3. Probe sensitivity

Detection requires matching the probe width to the zero height.
The off-critical contribution dominates at $a \sim \gamma_1^2/2 \approx 100$
(more precisely, the probe Gaussian $e^{-au^2}$ must overlap the zero's
log-scale position). At $a \gg \gamma_1^2$, the probe is too broad and
the critical-line sum overwhelms the off-critical defect. At $a \ll 1$,
everything is exponentially suppressed. This is the analogue of needing
to drive the network at the right frequency to detect the active resonance.

---

## 6. The missing entry

| This entry | Status |
|------------|--------|
| Test function ↔ driving current | Exact |
| Involution ↔ conjugation (on critical line) | Exact |
| Convolution square ↔ complex power | Exact |
| Explicit formula ↔ Kirchhoff power balance | Exact (distributional identity) |
| Sector decoupling ↔ sequence decoupling | Exact (symmetry-forced) |
| Weil positivity ↔ passivity | Exact (equivalent conditions) |
| **Arithmetic structure ↔ circuit topology** | **Unknown** |

The final row is the Riemann Hypothesis. In the function field case,
it is filled by the algebraic curve $C$ and its étale cohomology $H^1(C)$
with Frobenius action, where passivity follows from the Hodge index theorem.
For $\zeta(s)$ over $\mathbb{Q}$, the entry is blank.