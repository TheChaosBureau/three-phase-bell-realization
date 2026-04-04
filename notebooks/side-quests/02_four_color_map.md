# A Two-Bit Transport View of the Four-Color Theorem

## 1. Motivation

The usual statement of the four-color theorem is:

> Every planar map admits a coloring of its regions with at most four colors so that adjacent regions receive different colors.

A useful reformulation is to treat the four colors not as primitive labels, but as the four elements of a two-bit state space:

[
V_4 ;=; \mathbb Z_2 \times \mathbb Z_2
;=;
{(0,0),(1,0),(0,1),(1,1)}.
]

In this view, crossing a border does not merely “change color”; it applies a nonzero two-bit increment. The coloring problem becomes a transport/consistency problem on the dual graph.

This note records that reformulation.

---

## 2. Planar maps and dual graphs

Let (M) be a connected planar map. Its regions are called **faces**.

Let (M^*) be the **dual graph**:

* one vertex of (M^*) for each face of (M),
* one edge of (M^*) between two dual vertices whenever the corresponding faces of (M) share a border edge.

Then a proper face-coloring of (M) is the same thing as a proper vertex-coloring of (M^*).

---

## 3. Colors as a two-bit state space

Identify the four colors with the four elements of

[
V_4 = \mathbb Z_2^2.
]

Write addition in (V_4) componentwise mod 2. The nonzero elements are

[
(1,0),\quad (0,1),\quad (1,1).
]

These are the allowed nontrivial “state changes” across a border.

So instead of asking for a color at each face directly, we may ask for:

1. a base face color, and
2. a nonzero increment attached to each dual edge.

---

## 4. Edge transport data

Let each edge (e) of the dual graph (M^*) carry a label

[
g_e \in V_4 \setminus {(0,0)}.
]

Interpret (g_e) as the two-bit increment incurred when crossing that border.

If (\gamma = e_1 e_2 \cdots e_k) is a path in the dual graph, define its total transport by

[
T(\gamma) = \sum_{i=1}^k g_{e_i}.
]

Given a base face (F_0) with assigned color (c(F_0)\in V_4), any path (\gamma) from (F_0) to another face (F) suggests the color

[
c(F) = c(F_0) + T(\gamma).
]

For this to be well-defined, the result must not depend on the chosen path.

---

## 5. Flatness / zero-holonomy condition

Path-independence holds exactly when every closed loop has zero total transport.

So require that for every cycle (C) in the dual graph,

[
\sum_{e\in C} g_e = 0.
]

Call this the **flatness** or **zero-holonomy** condition.

Under this condition, the transported color of a face is independent of path.

---

## 6. Main forward theorem

**Theorem 1.**
Let (M) be a connected planar map and (M^*) its dual graph. Suppose each dual edge (e) is labeled by a nonzero element

[
g_e \in V_4 \setminus {0},
]

and suppose that for every cycle (C) in (M^*),

[
\sum_{e\in C} g_e = 0.
]

Then there exists a well-defined face labeling

[
c:\mathrm{Faces}(M)\to V_4
]

such that adjacent faces receive different labels. Hence (c) is a proper 4-coloring.

### Proof

Choose a base face (F_0) and assign it any color (c(F_0)\in V_4).

For any other face (F), choose a path (\gamma) in the dual graph from (F_0) to (F), and define

[
c(F)=c(F_0)+\sum_{e\in\gamma} g_e.
]

If (\gamma) and (\gamma') are two paths from (F_0) to (F), then traversing (\gamma) followed by (\gamma') in reverse gives a closed cycle. By the zero-holonomy condition, the total transport around that cycle is zero, so both path sums agree. Thus (c(F)) is well-defined.

Now let (F) and (F') be adjacent faces sharing a border corresponding to dual edge (e). Then

[
c(F') - c(F) = g_e.
]

Since (g_e\neq 0), we have (c(F')\neq c(F)). So adjacent faces receive distinct labels.

Therefore (c) is a proper 4-coloring. ∎

---

## 7. Inverse theorem

A proper 4-coloring also determines transport labels.

**Theorem 2.**
Let (c:\mathrm{Faces}(M)\to V_4) be a proper 4-coloring. For each dual edge (e) separating adjacent faces (F,F'), define

[
g_e = c(F')-c(F).
]

Then:

1. (g_e \neq 0) for every edge (e),
2. the sum of (g_e) around every cycle of (M^*) is zero.

### Proof

Since adjacent faces have different colors, (c(F')-c(F)\neq 0), so (g_e\neq 0).

For any cycle (F_0,F_1,\dots,F_k=F_0) in the dual graph,

[
\sum_{i=0}^{k-1} g_{e_i}
========================

\sum_{i=0}^{k-1} \bigl(c(F_{i+1})-c(F_i)\bigr).
]

This telescopes to

[
c(F_k)-c(F_0)=0.
]

So the cycle sum vanishes. ∎

---

## 8. Equivalence statement

The two previous theorems give:

**Corollary.**
Proper face 4-colorings of a connected planar map (M) are equivalent to nonzero (V_4)-valued edge labelings on the dual graph (M^*) satisfying zero holonomy on every cycle.

So the four-color problem may be restated as:

> Does every planar dual graph admit a flat nonzero (V_4)-edge connection?

This is not yet a new proof of the four-color theorem. It is a recoding of the same problem.

---

## 9. Interpretation

This recoding says that four colors can be viewed as a **two-bit internal state**, and that adjacency corresponds to a **nontrivial state transition** across a border.

In that language:

* colors are not primitive pigments,
* they are elements of a two-bit state space,
* borders carry nonzero increments,
* global consistency is enforced by zero holonomy around loops.

This is conceptually close to:

* transport on a graph,
* gauge-like flatness,
* parity propagation,
* local transitions with global cycle consistency.

---

## 10. What this does and does not do

This note does establish a clean equivalence:

[
\text{4-colorings}
;\longleftrightarrow;
\text{flat nonzero } \mathbb Z_2^2 \text{ transport data on the dual graph}.
]

It does **not** by itself prove that every planar map has such data. That existence statement is essentially the hard content of the four-color theorem.

So the value here is conceptual:

* four colors become two binary degrees of freedom,
* coloring becomes a transport problem,
* planarity enters through dual-cycle consistency.

---

## 11. Possible next directions

A natural next step is to investigate whether this transport view can be sharpened into:

1. a cohomological formulation,
2. a flow or network interpretation,
3. a comparison with known formulations using Tait colorings, nowhere-zero flows, or dual graph structure.

That would show whether this language is merely elegant, or whether it gives a genuinely useful proof perspective.

---

## 12. Summary statement

The four-color theorem can be reformulated as a statement about transporting a two-bit state across the dual graph of a planar map:

* each border applies a nonzero element of ( \mathbb Z_2^2 ),
* the total transport around every loop is zero,
* therefore each region gets a well-defined two-bit label,
* and neighboring regions must differ.

In this sense, four-colorability is equivalent to the existence of a flat nontrivial two-bit transport structure on the planar dual.
