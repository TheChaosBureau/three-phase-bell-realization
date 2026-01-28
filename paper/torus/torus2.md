# The Torus of Joint Angles: A Geometric Picture of Entanglement

This is a **configuration-space** picture: the “donut” is not in 3D space.
It’s the joint space of two periodic orientation variables.

You can read this in either of two common lab contexts:

- **Spin-1/2 singlet (Stern–Gerlach / qubits):** correlation \(E(a,b)=-\cos(a-b)\)
- **Photon polarization (linear polarizers):** correlation \(E(a,b)=-\cos(2(a-b))\)

The geometry is the same; polarization effectively uses a **double-angle**.

---

## 1) What the “Torus” Is

Each side has an analyzer setting (an angle on a circle):

- Alice chooses an angle \( \theta_A \)
- Bob chooses an angle \( \theta_B \)

Angles are periodic, so each lives on a circle \(S^1\).
The joint setting space is therefore:

\[
S^1 \times S^1 \;\;\cong\;\; \text{torus}
\]

> **Note on periodicity:**  
> - For **linear polarization**, physical settings satisfy \(\theta \sim \theta+\pi\) (a half-turn gives the same polarizer axis).  
> - For **spinors**, there’s a famous \(4\pi\) phase twist (the *phase* needs \(4\pi\) to return), even though measurement outcomes are \(2\pi\)-periodic.

For intuition, you can “unwrap” the torus as a square \([0,2\pi)\times[0,2\pi)\) with opposite edges identified.

---

## 2) What Lives on the Torus

Think of a complex field over the torus:

\[
\Psi(\theta_A,\theta_B)=R(\theta_A,\theta_B)e^{iS(\theta_A,\theta_B)}
\]

- \(R^2 = |\Psi|^2\) is the **Born weight** (bright/dark texture)
- \(S\) is a **phase field** (a “guiding landscape”)

### Product vs entangled texture

**Unentangled (factorized)**
\[
\Psi(\theta_A,\theta_B)=\psi_A(\theta_A)\,\psi_B(\theta_B)
\]
Geometrically: separable “stripes” aligned with the axes.

**Maximally entangled (relative-angle structure)**  
A canonical “relative angle” texture depends mainly on
\(\Delta = \theta_A-\theta_B\), e.g.
\[
R(\theta_A,\theta_B)\propto \cos\!\left(\frac{\Delta}{2}\right)
\quad\Rightarrow\quad
R^2\propto \cos^2\!\left(\frac{\Delta}{2}\right)
\]
This produces **diagonal bands** on the unwrapped torus: a helical winding when you re-identify the edges.

For the **spin-1/2 singlet**, the *observable* joint probabilities can be written as:
\[
P(\text{different outcomes})=\cos^2\!\left(\frac{\Delta}{2}\right),\qquad
P(\text{same outcomes})=\sin^2\!\left(\frac{\Delta}{2}\right)
\]
which implies the correlation
\[
E(\theta_A,\theta_B)=\langle s_A s_B\rangle = -\cos(\Delta)
\]
For **photon polarization** with linear polarizers, replace \(\Delta\to 2\Delta\), giving \(E=-\cos(2\Delta)\).

---

## 3) Measurement as Slicing the Torus

Each analyzer setting defines a partition of outcomes on its own circle:

- Alice’s outcome \(+\) vs \(-\) corresponds to two complementary regions in \(\theta_A\)
- Bob’s outcome \(+\) vs \(-\) corresponds to two complementary regions in \(\theta_B\)

On the torus, that becomes a grid of four joint regions:

\[
(+,+),\; (+,-),\; (-,+),\; (-,-)
\]

The observed correlations come from how the **diagonal/helical texture** \(R^2(\theta_A,\theta_B)\) overlaps these four regions as you change the **relative angle** \(\Delta\).

---

## 4) Why No-Signaling Falls Out Geometrically

Bob’s local statistics are what you get by ignoring Alice’s result—i.e. integrating out \(\theta_A\):

\[
P_B(\pm \mid \theta_B)=\int d\theta_A\,|\Psi(\theta_A,\theta_B)|^2
\]

Geometrically: “sum the texture along the \(\theta_A\) direction.”

For a maximally entangled state, the texture is arranged so that **every horizontal slice** carries equal total weight in Bob’s \(+\) and \(-\) regions, independent of Alice’s setting. So:

- **Correlations** vary with \(\Delta\)
- **Marginals** stay fixed (typically 50/50)

That’s nonlocal structure without a signaling channel: the *joint* texture changes the coincidences, not the single-party totals.

---

## 5) The “Double Helix” on the Torus

The diagonal winding can be read as a “double-helix” story:

- two counter-winding phase strands (two spinor/polarization components)
- their interference sets the bright/dark banding in \(R^2\)
- the object is inherently **pair-defined**: it lives naturally on \((\theta_A,\theta_B)\), not as two independent local states

So the “thing that’s real” in this picture is the **global joint geometry** on \(S^1\times S^1\).

---

## 6) Bohmian / Pilot-Wave Re-Reading (as a Guiding Field)

If you adopt a pilot-wave style ontology over these angle coordinates, write:

\[
\Psi(\theta_A,\theta_B)=R(\theta_A,\theta_B)e^{iS(\theta_A,\theta_B)}
\]

and interpret the phase gradient as a guide:

\[
\dot{\theta}_A \propto \frac{\partial S}{\partial \theta_A},\qquad
\dot{\theta}_B \propto \frac{\partial S}{\partial \theta_B}
\]

Then:

- the “pilot wave” is the **phase landscape** on the torus
- each side’s local orientation can be guided by a **global** field \(S(\theta_A,\theta_B)\)
- the strange part (“nonlocality”) becomes: the guiding field lives on configuration space, not 3D space

(For strict Bohmian mechanics, spin is handled a bit differently; this is the clean *geometric analogy* version.)

---

## 7) Why This Demystifies Entanglement

Entanglement is not:
- superluminal messaging
- prewritten lookup tables for outcomes
- probability magic floating in space

In this picture it is:

> A continuous joint geometry on the torus of angles,  
> probed locally by square-law (Born-rule) detection.

The conceptual shift is from:
“what does each particle carry?”
to:
“what *joint structure* does the pair inhabit?”

Answer: a twisted, helical texture on \(S^1\times S^1\).
