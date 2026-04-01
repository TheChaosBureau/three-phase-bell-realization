# 1. Physical system: 3 LC tanks in delta

* **state** = the energy and phase distribution in the unloaded delta network
* **measurement** = adding a resistive extraction path and recording how much energy each channel absorbs

Take three identical branches:

* branch (ab): (L\parallel C)
* branch (bc): (L\parallel C)
* branch (ca): (L\parallel C)

connected in a delta ring.

Let the node voltages be
[
v_a(t),;v_b(t),;v_c(t).
]

Branch voltages are
[
v_{ab}=v_a-v_b,\qquad
v_{bc}=v_b-v_c,\qquad
v_{ca}=v_c-v_a.
]

For each branch, the instantaneous stored energy is
[
W_{ab}=\tfrac12 C v_{ab}^2+\tfrac12 L i_{L,ab}^2
]
and similarly for (bc,ca).

Total stored energy:
[
W = W_{ab}+W_{bc}+W_{ca}.
]

This is the actual physical energy in the network.

---

# 2. What is the state here?

If the delta is **unloaded** and weakly lossy or ideally lossless, then the state is the internal oscillatory condition of the ring.

You can represent it in several equivalent ways.

## A. Raw physical state

At the most physical level:
[
x(t)=
\begin{bmatrix}
v_{ab}(t)\
v_{bc}(t)\
v_{ca}(t)\
i_{L,ab}(t)\
i_{L,bc}(t)\
i_{L,ca}(t)
\end{bmatrix}
]
subject to the delta constraint
[
v_{ab}+v_{bc}+v_{ca}=0.
]

That is the full internal state.

## B. Modal state

Because the delta is symmetric, the natural modes are:

* **positive sequence**
* **negative sequence**
* possibly zero/common mode depending on how you define the node space, though branch-difference dynamics in a pure delta naturally emphasize the balanced subspace

So the clean reduced state is the two-mode complex amplitude vector
[
a=
\begin{bmatrix}
a_+\
a_-
\end{bmatrix}.
]

This is the thing that should map to the Bloch sphere.

So for the **unloaded delta**, the Bloch state is not “power.”
It is the **normalized internal modal state** of the oscillation.

---

# 3. What do (a_+) and (a_-) mean physically in the delta?

They mean:

* (a_+): amplitude/phase of the clockwise rotating balanced mode
* (a_-): amplitude/phase of the counterclockwise rotating balanced mode

Concrete branch-voltage example:

## Positive-sequence mode

[
\mathbf v^{(+)}(t)
==================

\Re\left{
A_+
\begin{bmatrix}
1\
a^2\
a
\end{bmatrix}
e^{j\omega_0 t}
\right},
\qquad a=e^{j2\pi/3}.
]

## Negative-sequence mode

[
\mathbf v^{(-)}(t)
==================

\Re\left{
A_-
\begin{bmatrix}
1\
a\
a^2
\end{bmatrix}
e^{j\omega_0 t}
\right}.
]

A general balanced ring state is
[
\mathbf v(t)=\mathbf v^{(+)}(t)+\mathbf v^{(-)}(t).
]

So:

* pure (a_+) = one rotation sense around the ring
* pure (a_-) = the opposite rotation sense
* mixture = standing or elliptic-like pattern in the modal space

That is the correct physical meaning of the two-mode state.

---

# 4. What is the Bloch sphere here?

Normalize the modal amplitudes so
[
|a_+|^2+|a_-|^2=1.
]

Then define
[
x_B = 2\Re(a_+^*a_-),
\qquad
y_B = 2\Im(a_+^*a_-),
\qquad
z_B = |a_+|^2-|a_-|^2.
]

These satisfy
[
x_B^2+y_B^2+z_B^2=1.
]

Now the Bloch sphere has a concrete meaning:

* **north pole** (z_B=+1): pure positive-sequence ring oscillation
* **south pole** (z_B=-1): pure negative-sequence ring oscillation
* **equator** (z_B=0): equal mixture of the two, i.e. standing-pattern-like states in the ring
* **longitude**: relative phase between the two rotation senses

That is a real, physical mapping.

---

# 5. What is observable with no load?

With **no load**, you do not have a terminal measurement yet. You only have internal state observables.

Examples of internal observables:

## A. Total stored energy

[
W = \tfrac12 x^\top K x
]
for the appropriate quadratic energy matrix (K).

In modal coordinates, for identical uncoupled sequence energies,
[
W = k\left(|a_+|^2+|a_-|^2\right).
]

So on the normalized Bloch sphere, all points can represent the same total stored energy, just distributed differently in modal composition.

## B. Sequence dominance

[
z_B = |a_+|^2-|a_-|^2
]
This is not a measurement outcome; it is a state descriptor.

## C. Internal circulating/exchange quantities

You may define internal sequence currents and internal complex powers if you want, but those are **network summaries of the state**, not terminal measurement outcomes.

So in the unloaded case:

* the Bloch sphere is a **state picture**
* the actual physical conserved quantity is stored energy
* no absorptive “measurement” has happened

That matches your intuition: **state = no load**.

---

# 6. What is measurement here?

Now add a **resistive extraction stage**.

That is exactly the right analogy.

The detector/measurement stage is a load that removes energy from the delta.

Examples:

* three equal resistors attached to some analyzer network
* a Clarke (\alpha\beta) projection followed by resistive loads
* two analyzer branches, each terminated by a resistor
* a single matched extraction resistor for one chosen mode

Then the measured quantity is not the Bloch coordinate itself. It is:

[
E_m[T] = \int_{t_0}^{t_0+T} p_m(t),dt
]
where
[
p_m(t)=v_m(t)i_m(t)
]
is the instantaneous power dissipated in measurement channel (m).

If you let the measurement run until the stored energy is gone, then
[
E_m^{(\infty)}=\int_{t_0}^{\infty} p_m(t),dt
]
is the total absorbed energy in that channel.

That is the clean analog of measurement outcome.

So yes:

* **state** = unloaded delta oscillation
* **measurement** = resistive extraction of the stored energy

That is the right remap.

---

# 7. Simplest concrete examples

## Example 1: Pure positive sequence initial state

Initial state:
[
a_+=1,\qquad a_-=0.
]

Bloch coordinates:
[
(x_B,y_B,z_B)=(0,0,1).
]

Meaning:

* the ring is oscillating in one rotation sense only
* all stored energy is in the positive-sequence mode

### No-load interpretation

The delta just keeps oscillating (ideal case), with fixed total stored energy.

### With measurement

If you connect a load/analyzer that is matched to the positive-sequence mode, it can extract nearly all the energy:
[
E_{+}^{(\infty)}\approx W_0,\qquad E_{-}^{(\infty)}\approx 0.
]

If instead you connect a negative-sequence-matched load, ideally it sees nothing:
[
E_{-}^{(\infty)}\approx 0.
]

This is the cleanest “eigenstate” example.

---

## Example 2: Pure negative sequence initial state

Initial state:
[
a_+=0,\qquad a_-=1.
]

Bloch point:
[
(0,0,-1).
]

Meaning:

* opposite rotation sense
* all stored energy in the negative-sequence mode

A positive-sequence analyzer/load ideally extracts nothing; a negative-sequence load extracts everything.

This is the opposite pole.

---

## Example 3: Equal superposition

Initial state:
[
a_+=\frac{1}{\sqrt2},\qquad
a_-=\frac{e^{j\phi}}{\sqrt2}.
]

Bloch coordinates:
[
z_B=0,\qquad
x_B=\cos\phi,\qquad
y_B=\sin\phi.
]

Meaning:

* equal positive and negative sequence content
* relative phase (\phi) determines which equatorial state you have

Physical ring meaning:

* not a pure rotating mode
* a standing or linearly oriented pattern in the balanced subspace

### With measurement

If your analyzer/load basis is aligned to the particular equatorial orientation, one channel can absorb more than the other.

This is the direct analog of linear polarization measured in a rotated basis.

---

# 8. Analyzer/load math for the delta

Suppose your analyzer defines two orthonormal extracted modes (u_1,u_2) in the ((+,-)) subspace. Let the prepared state be (a).

Then the state amplitudes in the analyzer basis are
[
c_1 = u_1^\dagger a,\qquad c_2=u_2^\dagger a.
]

If each analyzer branch is terminated in a resistor and the extraction is ideal and complete, then the absorbed energies are proportional to
[
E_1^{(\infty)} = W_0 |c_1|^2,
\qquad
E_2^{(\infty)} = W_0 |c_2|^2,
]
with
[
|c_1|^2+|c_2|^2=1.
]

This is the cleanest derivation.

So the actual measurement observable is absorbed energy in each resistive branch, and the state determines the split.

That is exactly the preparation/measurement separation you were looking for.

---

# 9. What applies and what does not

## What maps cleanly

For the unloaded 3-tank delta:

* Bloch sphere = normalized two-mode internal state
* north/south = pure positive/negative sequence
* equator = equal superpositions
* longitude = relative phase of those superpositions

For the loaded measurement stage:

* measurement outcome = absorbed energy in chosen resistive extraction channels
* long-time absorbed energy fractions = squared projection amplitudes in the analyzer basis

That is rigorous and concrete.

## What does not map cleanly

Do **not** identify the Bloch sphere directly with:

* complex power (S)
* (P) and (Q) coordinates
* delivered watts directly
* reactive vars directly

Those are all network functionals or measurement results built from the state, not the state manifold itself.

---

# 10. What is (Q) in this delta picture?

In the **unloaded** or lightly loaded resonant delta, (Q)-type language can describe the internal oscillatory exchange:

* capacitor energy ↔ inductor energy
* reversible sloshing within each tank and across the modal structure

So (Q) belongs to the **internal resonant dynamics**.

But in the **measurement** stage, if the resistive loads extract all the energy, the physically relevant quantity is:
[
E_m^{(\infty)}=\int_0^\infty p_m(t),dt.
]

That is absorbed energy, not (Q).

So again:

* internal resonant stage → (Q)-type thinking may help
* measurement stage → absorbed energy in resistors is the observable

---

# 11. Best dictionary for the 3-delta-LC system

## State

Unloaded delta oscillation:
[
a=
\begin{bmatrix}
a_+\
a_-
\end{bmatrix},\qquad |a_+|^2+|a_-|^2=1.
]

## Bloch coordinates

[
x_B=2\Re(a_+^*a_-),\quad
y_B=2\Im(a_+^*a_-),\quad
z_B=|a_+|^2-|a_-|^2.
]

## Physical meaning

* (z_B): sequence handedness dominance
* (x_B,y_B): relative phase/coherence between the two ring-rotation modes

## Observable with no load

* internal stored energy (W)
* internal oscillation pattern

## Observable with resistive measurement load

[
E_m^{(\infty)} = \int_0^\infty p_m(t),dt
]
the total energy extracted into measurement channel (m)

## Ideal analyzer result

[
E_m^{(\infty)} = W_0,|u_m^\dagger a|^2
]

That is the cleanest formula set.

---

# 12. One-sentence version

> For a 3-LC-tank delta, the Bloch sphere maps cleanly to the normalized internal two-mode state of the unloaded ring, with positive and negative sequence as the pole modes; measurement is modeled by attaching resistive extraction channels, and the actual observable is the energy each load absorbs as the initial stored energy is drained from the ring.