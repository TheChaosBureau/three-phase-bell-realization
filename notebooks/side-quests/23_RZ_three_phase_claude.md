---
title: "Sequence Decomposition of Cubic L-Function Triples"
subtitle: "Prime splitting as exact symmetrical-component injection"
date: 2026-04-04
format:
  html:
    toc: true
    number-sections: true
    html-math-method: mathjax
---

## Notation and conventions

Throughout, $a = e^{2\pi i/3}$ is a primitive cube root of unity,
$K/\mathbb{Q}$ is a cyclic cubic extension with
$\operatorname{Gal}(K/\mathbb{Q}) \cong \mathbb{Z}_3$,
and $\chi$ is the associated primitive cubic Dirichlet character
satisfying $\chi^3 = \chi_0$ (trivial) and $\chi^2 = \bar{\chi}$.

The strongest exact result in this note is also the simplest to verify: the prime-splitting/sequence-injection theorem is a three-case computation in 3×3 linear algebra, using only $1+a+a^2=0$ and $a^3=1$.

The Fortescue analysis matrix and its inverse are

$$
T^{-1} = \frac{1}{3}\begin{pmatrix}1&1&1\\1&a&a^2\\1&a^2&a\end{pmatrix},
\qquad
T = \begin{pmatrix}1&1&1\\1&a^2&a\\1&a&a^2\end{pmatrix},
$$

with rows of $T^{-1}$ indexed by $(0,+,-)$ (zero, positive, negative
sequence).

## The arithmetic three-channel system

::: {#def-triple}
### Definition (Cubic L-function triple)
The **phase-domain channels** are

$$
G_a(s) = L(s,\chi_0), \qquad G_b(s) = L(s,\chi), \qquad G_c(s) = L(s,\bar{\chi}),
$$

and the **sequence-domain channels** are

$$
\begin{pmatrix}G_0\\G_+\\G_-\end{pmatrix}
= T^{-1}\begin{pmatrix}G_a\\G_b\\G_c\end{pmatrix}.
$$
:::

::: {#prp-factorization}
### Proposition (Artin factorization)
The Dedekind zeta function of $K$ factors as

$$\zeta_K(s) = G_a(s)\,G_b(s)\,G_c(s) = L(s,\chi_0)\,L(s,\chi)\,L(s,\bar{\chi}).$$
:::

*Proof.* Standard; follows from the decomposition of the regular
representation of $\operatorname{Gal}(K/\mathbb{Q})$ into characters.
$\square$

## Matrix-valued convolution square

::: {#def-matrix-power}
### Definition (Phase-domain power matrix)
Given Schwartz-class test functions $g_a, g_b, g_c$ on $(0,\infty)$
with Mellin transforms $\tilde{g}_a, \tilde{g}_b, \tilde{g}_c$, define

$$
\mathbf{G}(s) = \begin{pmatrix}\tilde{g}_a(s)\\\tilde{g}_b(s)\\\tilde{g}_c(s)\end{pmatrix},
\qquad
\mathbf{S}(s) = \mathbf{G}(s)\,\mathbf{G}(1-s)^T.
$$

The **sequence-domain power matrix** is

$$\mathbf{S}_{\mathrm{seq}} = T^{-1}\,\mathbf{S}_{\mathrm{phase}}\,(T^{-1})^*.$$
:::

::: {#thm-psd}
### Theorem (Positive semidefiniteness on the critical line)
If the centered half-densities $h_j(u) = e^{u/2}g_j(e^u)$ are
real-valued, then for all $\gamma \in \mathbb{R}$,

$$
\mathbf{S}\!\left(\tfrac{1}{2}+i\gamma\right) = \mathbf{G}(\gamma)\,\mathbf{G}(\gamma)^*
\succeq 0.
$$

In particular, $S_{jj}(1/2+i\gamma) = |\tilde{g}_j(1/2+i\gamma)|^2 \geq 0$
for each $j$, and $\mathbf{S}_{\mathrm{seq}}(1/2+i\gamma) \succeq 0$
with diagonal entries $|G_0|^2, |G_+|^2, |G_-|^2 \geq 0$.
:::

*Proof.* On the critical line, $1-s = \bar{s}$, so for real $h_j$
we have $\tilde{g}_j(1-s) = \overline{\tilde{g}_j(s)}$. Hence
$\mathbf{S} = \mathbf{v}\mathbf{v}^*$ with $\mathbf{v} = \mathbf{G}(1/2+i\gamma)$,
which is rank-1 PSD. The sequence-domain statement follows because
$T^{-1}$ is unitary (up to scaling): $\mathbf{S}_{\mathrm{seq}} = (T^{-1}\mathbf{v})(T^{-1}\mathbf{v})^*$. $\square$

## Prime-side injection

::: {#def-injection}
### Definition (Arithmetic injection vector)
At a prime power $p^k$, the **phase-domain injection vector** is

$$
\mathbf{I}(p^k) = \frac{\Lambda(p^k)}{\sqrt{p^k}}
\begin{pmatrix}1\\\chi(p^k)\\\bar{\chi}(p^k)\end{pmatrix}
$$

and the **sequence-domain injection vector** is

$$
\mathbf{I}_{\mathrm{seq}}(p^k) = T^{-1}\,\mathbf{I}(p^k).
$$
:::

For prime powers $p^k$ with $k \geq 2$, $\chi(p^k) = \chi(p)^k$, so
the sequence content depends on $\chi(p)^k \mod 3$. For the prime
$p$ itself ($k=1$), the following theorem gives the complete
classification.

::: {#thm-splitting}
### Theorem (Prime splitting determines sequence injection)
Let $p$ be a prime unramified in $K$. Then:

**(a)** If $p$ **splits completely** in $K$ (i.e., $\chi(p)=1$), then

$$\mathbf{I}_{\mathrm{seq}}(p) = \frac{\Lambda(p)}{\sqrt{p}}\begin{pmatrix}1\\0\\0\end{pmatrix}.$$

The prime injects **pure zero sequence**.

**(b)** If $p$ is **inert** in $K$ with $\chi(p) = a^2$, then

$$\mathbf{I}_{\mathrm{seq}}(p) = \frac{\Lambda(p)}{\sqrt{p}}\begin{pmatrix}0\\1\\0\end{pmatrix}.$$

The prime injects **pure positive sequence**.

**(c)** If $p$ is **inert** in $K$ with $\chi(p) = a$, then

$$\mathbf{I}_{\mathrm{seq}}(p) = \frac{\Lambda(p)}{\sqrt{p}}\begin{pmatrix}0\\0\\1\end{pmatrix}.$$

The prime injects **pure negative sequence**.

**(d)** If $p$ **ramifies** in $K$ (i.e., $\chi(p)=0$), then

$$\mathbf{I}_{\mathrm{seq}}(p) = \frac{\Lambda(p)}{3\sqrt{p}}\begin{pmatrix}1\\1\\1\end{pmatrix}.$$

The prime injects **equally into all three sequence channels**.
:::

*Proof.* Direct computation of $T^{-1}\mathbf{I}(p)$ in each case.

**(a)** $\chi(p) = 1$: $T^{-1}(1,1,1)^T = (1,0,0)^T$.
Row 0: $\frac{1}{3}(1+1+1) = 1$.
Row $+$: $\frac{1}{3}(1+a+a^2) = 0$.
Row $-$: $\frac{1}{3}(1+a^2+a) = 0$.

**(b)** $\chi(p) = a^2$: $T^{-1}(1,a^2,a)^T = (0,1,0)^T$.
Row 0: $\frac{1}{3}(1+a^2+a) = 0$.
Row $+$: $\frac{1}{3}(1+a\cdot a^2+a^2\cdot a) = \frac{1}{3}(1+a^3+a^3) = \frac{1}{3}(1+1+1) = 1$.
Row $-$: $\frac{1}{3}(1+a^2\cdot a^2+a\cdot a) = \frac{1}{3}(1+a^4+a^2) = \frac{1}{3}(1+a+a^2) = 0$.

**(c)** $\chi(p) = a$: $T^{-1}(1,a,a^2)^T = (0,0,1)^T$.
Row 0: $\frac{1}{3}(1+a+a^2) = 0$.
Row $+$: $\frac{1}{3}(1+a^2+a^4) = \frac{1}{3}(1+a^2+a) = 0$.
Row $-$: $\frac{1}{3}(1+a^3+a^3) = 1$.

**(d)** $\chi(p) = 0$: $T^{-1}(1,0,0)^T = \frac{1}{3}(1,1,1)^T$.
Each row: $\frac{1}{3}\cdot 1 = \frac{1}{3}$. $\square$

## Sequence-decomposed explicit formula

::: {#thm-sequence-explicit}
### Theorem (Explicit formula by sequence channel)
After applying $T^{-1}$ to the vector of explicit formulas for
$L(s,\chi_0)$, $L(s,\chi)$, and $L(s,\bar{\chi})$, the prime-side
forcing in each sequence channel draws from disjoint subsets of
the primes:

**(i)** The zero-sequence explicit formula is driven by
**split primes only** (plus ramified corrections).

**(ii)** The positive-sequence explicit formula is driven by
**inert primes with $\chi(p) = a^2$ only** (plus ramified corrections).

**(iii)** The negative-sequence explicit formula is driven by
**inert primes with $\chi(p) = a$ only** (plus ramified corrections).

In each case, ramified primes contribute $\frac{1}{3}$ of their
injection to each channel.
:::

*Proof.* Immediate from @thm-splitting and linearity of the
explicit formula. Since $\mathbf{I}_{\mathrm{seq}}(p)$ has
support on a single sequence component for each unramified
prime, the sum $\sum_p \mathbf{I}_{\mathrm{seq}}(p)\cdot h(\log p)$
decomposes into three independent sums, one per sequence channel,
each ranging over the corresponding subset of primes.  $\square$

::: {#cor-orthogonality}
### Corollary (Character orthogonality as sequence decoupling)
The sequence decoupling of the prime-side forcing is a direct
consequence of the orthogonality of the characters
$\{\chi_0, \chi, \bar{\chi}\}$ under the Fortescue transform.
Explicitly, for unramified $p$:

$$
\sum_{j \in \{0,\chi,\bar{\chi}\}} \chi_j(p)\,\overline{\chi_j(p')} =
\begin{cases} 3 & \text{if } p \equiv p' \text{ (same splitting type)}\\ 0 & \text{otherwise} \end{cases}
$$

This is the arithmetic content of the statement that different
sequence channels are driven by orthogonal prime subsets.
:::

## Summary

| Prime type | $\chi(p)$ | Phase vector | Sequence injection | Driven channel |
|---|---|---|---|---|
| Split | $1$ | $(1,1,1)^T$ | $(1,0,0)^T$ | Zero seq. only |
| Inert I | $a^2$ | $(1,a^2,a)^T$ | $(0,1,0)^T$ | Pos. seq. only |
| Inert II | $a$ | $(1,a,a^2)^T$ | $(0,0,1)^T$ | Neg. seq. only |
| Ramified | $0$ | $(1,0,0)^T$ | $\frac{1}{3}(1,1,1)^T$ | All channels |

The Fortescue/Clarke transform, applied to the character vector at
each prime, exactly classifies the sequence content of the
arithmetic injection by splitting type. This is an identity of
finite-dimensional linear algebra over the character group
$\mathbb{Z}_3$, requiring no analytic approximation.

---

## Structural conjectures {.appendix}

The following items are motivated by the exact core above but are
not established results. They are separated here to maintain the
integrity of the preceding sections.

### A. Cross-sequence reactive power

::: {#cnj-reactive}
### Conjecture (Reactive diagnostic)
Define the cross-sequence quantities

$$P_{+-} = \operatorname{Re}(G_+\overline{G_-}), \qquad Q_{+-} = \operatorname{Im}(G_+\overline{G_-}).$$

The sign of $Q_{+-}$, evaluated at a spectral height $\gamma$ where
one of the L-functions has a hypothetical off-critical zero,
distinguishes which L-function ($L(s,\chi)$ vs. $L(s,\bar{\chi})$)
carries the violation, via the handedness of the symmetry-breaking
in the $\mathbb{Z}_3$ structure.
:::

**Status.** Algebraically well-motivated: $Q_{+-}$ is invariant under
common phase rotation $G_\pm \mapsto e^{i\theta}G_\pm$, so it is
a genuine relative observable. Not yet tested numerically.

### B. Fault-type signatures

::: {#cnj-fault}
### Conjecture (GRH violation classification)
Different patterns of GRH violation across the triple produce
distinct signatures in the six-tuple $(P_0, P_+, P_-, P_{+-}, Q_{+-}, Q_{0+})$,
analogous to the fault-type classification in three-phase protective
relaying:

- Single off-critical zero in $L(s,\chi)$: nonzero $P_-, Q_{+-}$ with specific sign.
- Correlated off-critical zeros in $L(s,\chi)$ and $L(s,\bar\chi)$: nonzero $P_-$, $Q_{+-} = 0$.
- Off-critical zero in $\zeta(s)$ only: nonzero $P_0$, $P_- = 0$.
:::

**Status.** Structural pattern is sound. Quantitative verification
requires numerical computation with actual zeros and off-critical
hypothetical insertions, extending the scalar audit performed for
$\zeta(s)$ alone.

### C. Three-phase power constancy and zero independence

::: {#cnj-constancy}
### Conjecture (Constancy as independence)
The constancy of three-phase instantaneous power (cancellation of
double-frequency pulsations across the three L-functions) is
equivalent to the statistical independence of zeros of different
L-functions in the triple, in the sense of the Katz–Sarnak
philosophy.
:::

**Status.** Conceptually appealing. Connects the Fortescue framework
to random matrix theory predictions for zero correlations in families.
No proof or precise formulation exists.

### D. Matrix-valued Weil positivity

::: {#cnj-matrix-weil}
### Conjecture (Matrix Weil criterion)
There exists a matrix-valued positivity criterion of the form

$$\sum_{\rho \text{ of } \zeta_K} \operatorname{tr}\!\left[\mathbf{A}(\rho)\,\mathbf{S}_{\mathrm{seq}}(\rho)\right] \geq 0$$

for all admissible matrix-valued test functions, which is equivalent
to GRH for all three L-functions simultaneously and which is strictly
stronger than three individual scalar Weil criteria applied
separately.
:::

**Status.** Open. The correct formulation of the weighting
$\mathbf{A}(\rho)$ and the admissibility conditions is not known.
The completed L-functions with properly normalized root numbers
would be needed to make the PSD structure clean.