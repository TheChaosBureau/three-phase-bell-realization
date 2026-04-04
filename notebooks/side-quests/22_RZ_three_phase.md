# Rosetta Dictionary Entry: Matrix-Valued Convolution Square and Three-Phase Power

## 0. Status

This entry extends the scalar convolution-square / complex-power
correspondence to a **vector-valued** setting where three coupled
L-functions play the role of three-phase voltages. The Clarke/Fortescue
sequence decomposition is exact. The prime-splitting / sequence-injection
correspondence is exact. The reactive-power sign interpretation and
GRH-violation fault signatures are structural and (to our knowledge) new.

---

## 1. Setup: the three-phase arithmetic system

### 1A. The L-function triple

Let $K/\mathbb{Q}$ be a cyclic cubic extension with
$\operatorname{Gal}(K/\mathbb{Q}) = \langle\sigma\rangle \cong \mathbb{Z}_3$.
Let $\chi$ be the associated primitive cubic Dirichlet character with
$\chi^3 = \chi_0$ (trivial). The three L-functions are:

$$G_a(s) = L(s, \chi_0), \qquad G_b(s) = L(s, \chi), \qquad G_c(s) = L(s, \bar{\chi})$$

with the factorization:

$$\zeta_K(s) = G_a(s)\,G_b(s)\,G_c(s) = L(s,\chi_0)\,L(s,\chi)\,L(s,\bar{\chi})$$

This is the arithmetic three-phase system. The three L-functions are
the "phase voltages," and the Dedekind zeta function is the "total
three-phase power."

### 1B. The $\mathbb{Z}_3$ symmetry

The character group $\{\chi_0, \chi, \chi^2 = \bar{\chi}\}$ carries
the natural $\mathbb{Z}_3$ action $\chi \mapsto \chi \cdot \chi$.
This is the rotational symmetry of the three-phase system. Each
L-function is a different "phase" of the same arithmetic object (the
number field $K$).

### 1C. Functional equations

Each L-function satisfies its own functional equation relating $s$
and $1-s$. After completion (including gamma factors and conductor):

$$\Lambda(s, \chi_j) = \varepsilon(\chi_j)\,\Lambda(1-s, \bar{\chi}_j)$$

where $|\varepsilon(\chi_j)| = 1$. On the critical line $s = 1/2 + i\gamma$,
the functional equation again makes $1-s = \bar{s}$, so evaluation of
the convolution square gives $|\cdot|^2 \geq 0$ for each L-function
individually — exactly as in the scalar case.

---

## 2. Matrix convolution square

### 2A. Definition

Given test functions $g_a, g_b, g_c$ on $(0,\infty)$, form the
**phase-domain power matrix:**

$$\mathbf{S}(s) = \mathbf{G}(s)\,\mathbf{G}(1-s)^T$$

where $\mathbf{G}(s) = (\tilde{g}_a(s),\, \tilde{g}_b(s),\, \tilde{g}_c(s))^T$.
Entry by entry:

$$S_{ij}(s) = \tilde{g}_i(s)\,\tilde{g}_j(1-s)$$

### 2B. On the critical line

At $s = 1/2 + i\gamma$ with real-valued centered half-densities:

$$\mathbf{S}\!\left(\tfrac{1}{2}+i\gamma\right) = \mathbf{G}(\gamma)\,\mathbf{G}(\gamma)^* = \mathbf{v}\mathbf{v}^*$$

This is a **rank-1 Hermitian positive semidefinite** matrix. All
eigenvalues are nonneg. The diagonal entries are $|G_i|^2 \geq 0$.
The off-diagonal entries $G_i \overline{G_j}$ are complex and carry
relative phase information.

**This is the three-phase generalization:** the scalar Weil criterion
gives a single nonneg real number; the matrix version gives a $3\times 3$
PSD matrix whose off-diagonal phases encode inter-channel coherence.

### 2C. Off the critical line

At $s = \sigma + i\gamma$ with $\sigma \neq 1/2$:

$$\mathbf{S}(s) = \mathbf{G}(\sigma+i\gamma)\,\mathbf{G}((1{-}\sigma)-i\gamma)^T$$

The two vectors $\mathbf{G}(s)$ and $\mathbf{G}(1-s)$ are evaluated at
different points. The matrix $\mathbf{S}$ is not Hermitian, not PSD,
and its entries are unconstrained complex numbers.

---

## 3. Sequence decomposition (Clarke/Fortescue)

### 3A. The transform

The standard Fortescue analysis matrix with $a = e^{2\pi i/3}$:

$$T^{-1} = \frac{1}{3}\begin{pmatrix} 1 & 1 & 1 \\ 1 & a & a^2 \\ 1 & a^2 & a \end{pmatrix}, \qquad
\begin{pmatrix} G_0 \\ G_+ \\ G_- \end{pmatrix} = T^{-1} \begin{pmatrix} G_a \\ G_b \\ G_c \end{pmatrix}$$

with inverse (synthesis):

$$T = \begin{pmatrix} 1 & 1 & 1 \\ 1 & a^2 & a \\ 1 & a & a^2 \end{pmatrix}$$

where subscripts $0, +, -$ denote zero, positive, negative sequence.

### 3B. Sequence power matrix

$$\mathbf{S}_{\mathrm{seq}} = T^{-1}\,\mathbf{S}_{\mathrm{phase}}\,(T^{-1})^* = \mathbf{G}_{\mathrm{seq}}\,\mathbf{G}_{\mathrm{seq}}^*$$

On the critical line, $\mathbf{S}_{\mathrm{seq}}$ is PSD with entries:

| Entry | Formula | Meaning |
|-------|---------|---------|
| $(0,0)$ | $\|G_0\|^2$ | Zero-sequence power |
| $(+,+)$ | $\|G_+\|^2$ | Positive-sequence power |
| $(-,-)$ | $\|G_-\|^2$ | Negative-sequence power |
| $(+,-)$ | $G_+ \overline{G_-}$ | Cross-sequence complex power |
| $(0,+)$ | $G_0 \overline{G_+}$ | Zero–positive coupling |
| $(0,-)$ | $G_0 \overline{G_-}$ | Zero–negative coupling |

### 3C. What "balanced" means

A perfectly balanced state has $G_- = 0$ and $G_0 = 0$:

$$\mathbf{S}_{\mathrm{seq}} = \begin{pmatrix} 0 & 0 & 0 \\ 0 & |G_+|^2 & 0 \\ 0 & 0 & 0 \end{pmatrix}$$

All power is in the positive sequence. No negative sequence, no zero
sequence, no off-diagonal coupling. This is the arithmetic analogue
of a balanced three-phase load.

---

## 4. Prime splitting as sequence injection

This is the cleanest new correspondence in this entry.

### 4A. Phase-domain current at prime $p$

The explicit formula for $L(s, \chi_j)$ samples the test function at
primes with character-weighted coefficients. The "current injection"
at prime $p$ across the three phases is:

$$\mathbf{I}(p) = \frac{\Lambda(p)}{\sqrt{p}}\begin{pmatrix} 1 \\ \chi(p) \\ \bar{\chi}(p) \end{pmatrix}$$

### 4B. Sequence decomposition of the current

$$\mathbf{I}_{\mathrm{seq}}(p) = T^{-1}\,\mathbf{I}(p)$$

**Split primes** ($p$ splits completely in $K$, $\chi(p) = 1$):

$$T^{-1}\begin{pmatrix}1\\1\\1\end{pmatrix} = \begin{pmatrix}1\\0\\0\end{pmatrix}$$

**Pure zero-sequence injection.** All three phases are excited in
unison. The prime drives the system symmetrically — no rotation.

**Inert primes, type I** ($p$ inert, $\chi(p) = a^2$):

$$T^{-1}\begin{pmatrix}1\\a^2\\a\end{pmatrix} = \begin{pmatrix}0\\1\\0\end{pmatrix}$$

**Pure positive-sequence injection.** The prime drives a
forward-rotating excitation across the three L-functions.

**Inert primes, type II** ($p$ inert, $\chi(p) = a$):

$$T^{-1}\begin{pmatrix}1\\a\\a^2\end{pmatrix} = \begin{pmatrix}0\\0\\1\end{pmatrix}$$

**Pure negative-sequence injection.** The prime drives a
backward-rotating excitation.

**Ramified primes** ($p | \operatorname{disc}(K)$, $\chi(p) = 0$):

$$T^{-1}\begin{pmatrix}1\\0\\0\end{pmatrix} = \frac{1}{3}\begin{pmatrix}1\\1\\1\end{pmatrix}$$

**Equal injection into all three sequences.** The ramified prime does
not respect the $\mathbb{Z}_3$ symmetry — it excites all sequence
channels equally.

### 4C. Summary table

| Splitting type | $\chi(p)$ | Phase vector | Sequence content | Circuit analogue |
|----------------|-----------|-------------|------------------|------------------|
| Splits completely | $1$ | $(1,1,1)$ | Pure zero seq. | Balanced (common-mode) drive |
| Inert, type I | $a^2$ | $(1,a^2,a)$ | Pure positive seq. | Forward-rotating drive |
| Inert, type II | $a$ | $(1,a,a^2)$ | Pure negative seq. | Backward-rotating drive |
| Ramifies | $0$ | $(1,0,0)$ | All sequences equal | Symmetry-breaking (fault) drive |

**This correspondence is exact.** The Clarke transform of the character
vector at each prime gives its sequence content, and the sequence content
is entirely determined by the splitting type of the prime in the cubic
field $K$. No approximation or analogy is involved.

---

## 5. The six power quantities and their signs

### 5A. Sequence powers (diagonal)

$$P_0 = |G_0|^2, \qquad P_+ = |G_+|^2, \qquad P_- = |G_-|^2$$

All three are nonneg on the critical line (each is $|\cdot|^2$).
They measure the *magnitude* of each sequence component.

In the arithmetic: $P_-$ and $P_0$ being nonzero means the spectral
data of the three L-functions is not perfectly balanced — zeros of
$L(s,\chi)$ and $L(s,\bar{\chi})$ are not a pure $\mathbb{Z}_3$
rotation of each other at that spectral height.

### 5B. Cross-sequence powers (off-diagonal)

The genuinely new quantities are the complex off-diagonal entries:

$$S_{+-} = G_+\overline{G_-} = |G_+||G_-|\,e^{i\phi_{+-}}$$

Decompose into "active" and "reactive" parts:

$$P_{+-} = \operatorname{Re}(G_+\overline{G_-}), \qquad Q_{+-} = \operatorname{Im}(G_+\overline{G_-})$$

**$P_{+-}$ (cross-sequence active power):** measures the degree to
which positive and negative sequence are "in phase." If $P_{+-} > 0$,
the two sequences reinforce; if $P_{+-} < 0$, they partially cancel.

**$Q_{+-}$ (cross-sequence reactive power):** measures the degree to
which positive and negative sequence are "in quadrature." Its *sign*
distinguishes the handedness of the phase relationship:

- $Q_{+-} > 0$: positive sequence leads negative sequence
- $Q_{+-} < 0$: negative sequence leads positive sequence

**These signs have no single-phase analogue.** In the scalar Weil
criterion, there is no off-diagonal term and hence no reactive power.
The cross-sequence phase $\phi_{+-}$ is genuinely three-phase information.

### 5C. Arithmetic content of $Q_{+-}$

In centered log coordinates with $h_j(u) = e^{u/2}g_j(e^u)$ and
Fourier transforms $\hat{h}_j(\xi)$:

$$G_+\overline{G_-} = \hat{h}_+(\gamma)\,\overline{\hat{h}_-(\gamma)}$$

where

$$\hat{h}_\pm = \frac{1}{3}(\hat{h}_a + a^{\pm 1}\hat{h}_b + a^{\mp 1}\hat{h}_c)$$

So $Q_{+-} = \operatorname{Im}(\hat{h}_+\overline{\hat{h}_-})$ depends
on the relative phases of the Fourier transforms of the three test
functions at spectral height $\gamma$. It encodes the **angular
relationship** between the spectral probes at that frequency — something
that has no meaning when there is only one probe.

---

## 6. GRH violation signatures

### 6A. Balanced operation (GRH holds for all three)

If all zeros of $L(s,\chi_0)$, $L(s,\chi)$, and $L(s,\bar{\chi})$ lie on
the critical line, then at every zero $\rho_j = 1/2 + i\gamma_j$:

$$\mathbf{S}_{\mathrm{seq}}(\rho_j) \text{ is positive semidefinite}$$

The spectral sum $\sum_\rho \operatorname{tr}[\mathbf{S}(\rho)]$ is
nonneg, and the system is "passive."

### 6B. Fault-type classification

When GRH is violated for one or more of the three L-functions, the
pattern of nonzero sequence powers diagnoses the violation type.
The following table gives the expected signature of the sequence
power matrix when a hypothetical off-critical zero is inserted.

| Violation | $P_+$ | $P_-$ | $P_0$ | $Q_{+-}$ | Circuit analogue |
|-----------|--------|--------|--------|----------|------------------|
| None (GRH holds) | $+$ | $0$ | $0$ | $0$ | Balanced 3Φ |
| $L(\chi)$ off, others on | $+$ | $+$ | $+$ | specific sign | Line-ground fault |
| $L(\chi)$ and $L(\bar\chi)$ off, correlated | $+$ | $+$ | $0$ | specific sign | Line-line fault |
| All three off, correlated | $+$ | $+$ | $+$ | $0$ | Three-phase fault |
| $\zeta$ off, $L(\chi)$ on | $+$ | $+$ | $+$ | opposite sign | Ground fault on neutral |

**Precision note.** "Specific sign" means the sign of $Q_{+-}$
distinguishes which L-function has the off-critical zero and on which
side of the critical line ($\sigma > 1/2$ vs. $\sigma < 1/2$). This is
because the off-critical zero breaks the $\mathbb{Z}_3$ symmetry in a
handed way, and the handedness shows up as the sign of the reactive
cross-power.

### 6C. What the signs detect that scalar positivity cannot

Consider two distinct GRH violations:

**(i)** $L(s,\chi)$ has a zero at $\rho = 0.75 + i\gamma_1$, all
others on the critical line.

**(ii)** $L(s,\bar{\chi})$ has a zero at $\rho = 0.75 + i\gamma_1$,
all others on the critical line.

These produce the same $P_-$ (same magnitude of sequence imbalance)
but **opposite signs of $Q_{+-}$**. In scalar Weil positivity, both
would show up as "the spectral sum is negative" with no way to
distinguish which L-function is at fault. In the three-phase framework,
the reactive power sign uniquely identifies the faulty phase.

This is the exact analogue of how a power system relay distinguishes
an A-ground fault from a B-ground fault by the sign of the negative-
sequence reactive power.

---

## 7. Explicit formula in sequence coordinates

### 7A. Phase-domain explicit formulas

Each L-function has its own explicit formula. Schematically:

$$\sum_{\rho_j} \hat{H}_j(\gamma_{\rho_j}) = E_j - \sum_p \frac{\Lambda(p)\,\chi_j(p)}{\sqrt{p}}\,[h(\log p) + h(-\log p)] - A_j$$

where $j \in \{0, +, -\}$ indexes the character $\chi_j \in \{\chi_0, \chi, \bar{\chi}\}$.

### 7B. Sequence-domain explicit formula

Apply $T^{-1}$ to the vector of three explicit formulas. The spectral
side becomes:

$$\sum_{\rho_0} \hat{H}_0 + \sum_{\rho_+} \hat{H}_+ + \sum_{\rho_-} \hat{H}_-$$

(zeros of each L-function summed with their respective sequence-projected
test functions). The prime side becomes:

$$\sum_p \frac{\Lambda(p)}{\sqrt{p}}\,\mathbf{I}_{\mathrm{seq}}(p) \cdot \mathbf{h}_{\mathrm{seq}}(\log p)$$

where $\mathbf{I}_{\mathrm{seq}}(p)$ is the sequence-decomposed
character vector from Section 4, and $\mathbf{h}_{\mathrm{seq}}$ is
the sequence-decomposed test function vector.

**Key structural consequence:** split primes ($\chi(p) = 1$) couple
only to the zero-sequence test function. Inert primes couple only
to the positive or negative sequence test function, depending on
$\chi(p)$. So the three explicit formulas, after sequence decomposition,
are **driven by different subsets of the primes.**

This is the arithmetic content of sequence decoupling: different
types of primes feed different sequence channels.

### 7C. Three-phase Kirchhoff balance

The total Dedekind zeta function satisfies:

$$\sum_{\text{all } \rho \text{ of } \zeta_K} \hat{H}(\gamma_\rho) = E_K - P_K - A_K$$

This is the three-phase power balance: total spectral power (summed
over all resonances of the field) equals total arithmetic power (summed
over all primes with field-theoretic multiplicities) plus corrections.

The GRH for $K$ is the statement that this total is nonneg for all
positive-definite test functions. This is three-phase passivity:
total power absorbed is nonneg for every driving signal.

---

## 8. Three-phase instantaneous power and zero correlations

### 8A. The constancy condition

In a balanced three-phase circuit, instantaneous power is constant:

$$p(t) = v_a(t)i_a(t) + v_b(t)i_b(t) + v_c(t)i_c(t) = \text{const.}$$

The double-frequency pulsations of the three phases cancel exactly.
This is a **stronger condition** than each phase having nonneg
average power.

### 8B. Arithmetic analogue

The analogue is a condition on the *smoothness* of the spectral sum
of $\zeta_K(s)$ as a function of spectral height. If the zeros of
the three L-functions are "balanced" — i.e., the local densities of
zeros of $L(s,\chi)$, $L(s,\bar{\chi})$, and $\zeta(s)$ near height
$\gamma$ are in the right phase relationship — then the
oscillations in the individual spectral sums cancel, and the
combined spectral counting function $N_K(T)$ is smooth.

This connects to **zero repulsion** in families: the GUE statistics
of zeros of distinct L-functions are expected to be *independent*
(no repulsion between zeros of $L(s,\chi)$ and $L(s,\bar\chi)$), which
is the analogue of the three phases being $120°$ apart and hence
non-interacting.

### 8C. What constancy adds beyond positivity

Three-phase power constancy implies positivity but is strictly
stronger. In the arithmetic setting:

- **Positivity** (GRH): $\sum_\rho \hat{H}(\gamma_\rho) \geq 0$ for all
  PD test functions. Each resonance absorbs nonneg power on average.

- **Constancy** (stronger): the spectral sum is not only nonneg but
  *insensitive to the specific spectral window*. No matter where you
  put the test function, the three L-functions' zero contributions
  balance each other's fluctuations.

This is a falsifiable prediction: if zero statistics of different
L-functions in a cubic family showed unexpected correlations (violations
of independence), it would correspond to a three-phase power pulsation
— an imbalance detectable in $Q_{+-}$ but invisible to scalar Weil
positivity.

---

## 9. Assessment: exact, structural, open

### 9A. Exact

| Identification | Status |
|----------------|--------|
| Clarke/Fortescue transform on character group $\{\chi_0,\chi,\bar\chi\}$ | Exact: unitary change of basis |
| $\zeta_K(s) = L(s,\chi_0)\,L(s,\chi)\,L(s,\bar\chi)$ | Exact: Artin factorization |
| Matrix $\mathbf{S}(s) = \mathbf{G}(s)\mathbf{G}(1-s)^T$ is PSD on critical line | Exact: $\mathbf{v}\mathbf{v}^*$ structure |
| Split primes → zero sequence, inert → positive/negative sequence | Exact: Clarke transform of character vectors |
| Ramified primes → equal all-sequence injection | Exact: $\chi(p) = 0$ gives $(1,0,0)^T$ |
| Each L-function has its own explicit formula | Exact: standard analytic number theory |
| Sequence decomposition decouples the prime-sum by splitting type | Exact: consequence of character orthogonality |

### 9B. Structural (well-motivated, not yet formalized)

| Identification | Status |
|----------------|--------|
| Off-diagonal $G_+\overline{G_-}$ as cross-sequence reactive power | Structural: algebraically correct, arithmetic interpretation new |
| Sign of $Q_{+-}$ distinguishing which L-function violates GRH | Structural: follows from symmetry-breaking analysis, not yet tested numerically |
| Fault-type signature table (Section 6B) | Structural: pattern is sound, quantitative thresholds unknown |
| Three-phase power constancy ↔ zero-correlation independence | Structural: connects to Katz–Sarnak philosophy but not proven |
| Sequence-decomposed explicit formula driven by prime-splitting subsets | Structural: exact decomposition, arithmetic implications unexplored |

### 9C. Open

| Question | Status |
|----------|--------|
| Matrix-valued Weil positivity criterion for $\zeta_K$ | Open: correct formulation not established |
| Does $Q_{+-}$ carry information independent of individual GRH? | Open |
| Is three-phase power constancy equivalent to zero independence? | Open: would connect GRH to random matrix statistics |
| Does the reactive power sign predict zero locations more sharply than scalar methods? | Open: requires numerical experiment |
| What is the three-phase "circuit topology" for $K/\mathbb{Q}$? | Open: this is GRH for number fields |

---

## 10. The single-phase vs. three-phase boundary

The scalar dictionary entry (convolution square / complex power) captures
the passivity condition: is the network passive at every resonance?
$S = |I|^2 R \geq 0$ is the entire content of the scalar Weil criterion.

The matrix entry adds:

1. **Directional information.** Which phase is at fault?
   The sign of $Q_{+-}$ diagnoses this.

2. **Correlation information.** Are the faults on different phases
   correlated or independent? The rank structure of
   $\mathbf{S}_{\mathrm{seq}}$ diagnoses this.

3. **Constancy beyond positivity.** Is the total power constant or
   pulsating? The smoothness of the combined spectral sum diagnoses this.

None of these are accessible in the scalar setting. They are the
three-phase signs whose meanings David identified as absent from the
single-phase picture.

---

## 11. Formulas

### 11.1. Matrix power at a zero

At a zero $\rho_j$ of $L(s, \chi_j)$ on the critical line:

$$\mathbf{S}_{\mathrm{phase}}(\rho_j) = \mathbf{G}(\gamma_j)\,\mathbf{G}(\gamma_j)^* \succeq 0$$

Sequence form:

$$(\mathbf{S}_{\mathrm{seq}})_{kl} = G_k(\gamma_j)\,\overline{G_l(\gamma_j)}, \qquad k,l \in \{0,+,-\}$$

### 11.2. Six power quantities

$$P_0 = |G_0|^2, \quad P_+ = |G_+|^2, \quad P_- = |G_-|^2$$
$$P_{+-} = \operatorname{Re}(G_+\overline{G_-}), \quad Q_{+-} = \operatorname{Im}(G_+\overline{G_-})$$
$$P_{0+} = \operatorname{Re}(G_0\overline{G_+}), \quad Q_{0+} = \operatorname{Im}(G_0\overline{G_+})$$

### 11.3. Prime splitting as sequence current

$$\mathbf{I}_{\mathrm{seq}}(p) = \frac{\Lambda(p)}{\sqrt{p}}\;T^{-1}\begin{pmatrix}1\\\chi(p)\\\bar\chi(p)\end{pmatrix} = \frac{\Lambda(p)}{\sqrt{p}} \times \begin{cases} (1,0,0)^T & \chi(p)=1 \;\text{(split)} \\ (0,1,0)^T & \chi(p)=a^2 \;\text{(inert, type I)} \\ (0,0,1)^T & \chi(p)=a \;\text{(inert, type II)} \\ \tfrac{1}{3}(1,1,1)^T & \chi(p)=0 \;\text{(ramified)} \end{cases}$$

### 11.4. Three-phase passivity (GRH for $K$)

$$\sum_{\rho \text{ of } \zeta_K} \operatorname{tr}\!\left[\mathbf{S}_{\mathrm{seq}}(\rho)\right] = \sum_\rho \left(P_0(\rho) + P_+(\rho) + P_-(\rho)\right) \geq 0$$

for all admissible matrix-valued test functions. This is the total
absorbed power across all three sequences. GRH says it is nonneg.

### 11.5. The reactive diagnostic

For a hypothetical off-critical zero of $L(s,\chi)$ at height $\gamma$:

$$Q_{+-}(\gamma) = \operatorname{Im}\!\left(\hat{h}_+(\gamma)\,\overline{\hat{h}_-(\gamma)}\right)$$

The sign of $Q_{+-}$ tells you whether $L(s,\chi)$ or $L(s,\bar\chi)$ is
the source of the imbalance, by the handedness of the phase shift
introduced into the sequence decomposition.

---

## 12. Connection to the scalar entry

The scalar entry is the $G_b = G_c = 0$ reduction of this entry.
Setting $G_b = G_c = 0$ collapses the matrix to:

$$\mathbf{S} = \begin{pmatrix} |G_a|^2 & 0 & 0 \\ 0 & 0 & 0 \\ 0 & 0 & 0 \end{pmatrix}$$

All sequence powers vanish except $P_0 + P_+ + P_- = |G_a|^2$, which
is the scalar Weil criterion. There is no off-diagonal information,
no reactive power, no fault-type signature. The three-phase structure
is invisible.

The scalar dictionary entry corresponds to testing the system with a
single-phase probe. This entry corresponds to testing with a
three-phase probe that can detect both the magnitude and the
rotational direction of spectral imbalance.