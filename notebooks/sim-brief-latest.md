Yes. Here is a coder-ready brief for that exact fork.

# Simulation Brief

**Project:** Mechanism-vs-Readout Disambiguation Study
**Objective:** Determine whether the current failure of the sequential bridge is caused primarily by:

1. the **anisotropic-depletion mechanism itself** failing to create usable residual branches, or
2. the **confidence/readout layer** being too brittle to detect and use good residual branches when they exist.

---

## 1. Purpose

The current audit established three things:

* single-analyzer anisotropic depletion still shows some meaningful residual-branch structure,
* the redesigned sequential layer does **not** yield any credible headline-eligible regime,
* and the remaining uncertainty is whether the failure is in the **dynamics** or in the **readout/confidence construction**.

This task is designed to resolve that uncertainty.

The simulator should now answer:

> If strong residual branches really exist in the sequential dynamics, does the current confidence/readout layer fail to detect them? Or are the branches themselves too weak/unstable to support a viable sequential mechanism?

This is now the main decision question for the project.

---

## 2. Scope

This task is **not** a search for better CHSH.

This task is **not** a new mechanism family.

This task is a controlled disambiguation study of the current anisotropic-damping family.

You must compare:

* the underlying **state-space structure** produced by the mechanism,
* against the behavior of the current **confidence and readout layers**.

The goal is to decide whether the bottleneck is:

* mechanism-limited,
* readout-limited,
* or both.

---

## 3. Core questions

The code and final report must answer these directly:

1. Do high-quality residual branches actually exist in the sequential dynamics at useful rates?
2. If they exist, do the current readout/confidence rules fail to recognize them?
3. If they do not exist, is the mechanism itself too weak/unstable to support a sequential bridge?
4. Is there any regime where improved residual detection changes the sequential conclusion materially?
5. Does the evidence support continuing the projective-depletion bridge, or pivoting toward an explicit joint-selector/global-constraint route?

---

## 4. Definitions

## 4.1 Mechanism failure

A regime is mechanism-limited if:

* post-Alice residual states do not form clean, stable, separable residual branches,
* or those branches occur too rarely / too ambiguously to support a usable sequential process,
* even when evaluated with generous but honest diagnostic methods.

## 4.2 Readout brittleness

A regime is readout-limited if:

* the post-Alice residual states do form meaningful branch structure,
* but the current confidence/readout layer fails to identify or use them consistently.

## 4.3 Usable residual branch

A residual branch is “usable” if it is:

* separable from alternatives,
* stable under small perturbations,
* consistent across nearby parameter settings,
* and detectable by multiple independent branch-quality diagnostics.

---

## 5. Required study design

You must perform the study in two layers.

### Layer A — Mechanism-only structural analysis

Ignore binary outcomes at first.
Analyze only the post-update state structure.

### Layer B — Readout sensitivity analysis

Given the same post-update state clouds, test multiple confidence/readout constructions and quantify how much the sequential verdict changes.

The point is to separate:

* “the state never gets there”
  from
* “the state gets there but the detector misses it.”

---

## 6. Inputs and regimes to analyze

Use the existing anisotropic-damping simulator and parameter families already in use.

Must include sweeps over:

* anisotropy ratio
* window fraction
* analyzer angle
* sequential angle pairs
* source phase/orientation

At minimum, include:

* anisotropy ratios: (1, 1.5, 2, 4, 8, 16)
* windows: (T/12, T/4, T/2, T) if currently supported as (0.0833, 0.25, 0.5, 1.0)
* Alice/Bob angles on the same 5-angle grid already used

Also include focused dense sweeps near:

* best single-analyzer projectivity region,
* lowest-drift sequential region,
* and highest-residual-agreement region. 

---

## 7. Layer A — Mechanism-only structural analysis

This is the most important new part.

For each sequential parameter group:

1. simulate post-Alice residual states for all trials
2. represent those states in at least two coordinate systems:

   * source basis
   * Alice analyzer basis
3. analyze whether the post-Alice cloud contains separable branch structure

### Required structural diagnostics

## A1. Residual separability score

Quantify how well the post-Alice states separate into two candidate residual branches.

Acceptable methods:

* two-cluster silhouette score
* between-cluster / within-cluster ratio
* Gaussian-mixture separation metric
* nearest-template separation margin

Must document exact formula.

## A2. Residual stability score

For each candidate branch, measure sensitivity to small perturbations in:

* initial phase
* source noise
* angle perturbation
* anisotropy perturbation

This must answer whether the branch structure is real or brittle.

## A3. Residual occupancy

Measure what fraction of trials fall into:

* strong branch 1
* strong branch 2
* ambiguous region

This is crucial. A branch structure that exists only on a tiny fraction of trials is not enough.

## A4. Residual manifold closure

Measure whether the post-Alice states stay on a low-dimensional manifold compatible with the sphere/projective picture.

## A5. Local branch continuity

Check whether nearby initial states map to nearby positions on the same residual branch, rather than scattering discontinuously.

### Required outputs for Layer A

For each parameter group, save:

* separability score
* stability score
* occupancy fractions
* ambiguity fraction
* manifold closure error
* branch continuity score

Also save representative state clouds and cluster plots.

---

## 8. Layer B — Readout sensitivity analysis

Take the same state clouds and evaluate multiple readout/confidence constructions.

### Required readout families

Implement and compare:

## B1. Energy-loss winner

Current physically motivated rule.

## B2. Residual-template classifier

Current diagnostic rule.

## B3. Margin-thresholded residual classifier

Same as B2, but with explicit confidence margins varied across a sweep.

## B4. Agreement-only rule

Assign outcome only when B1 and B2 agree.

## B5. Oracle-separability benchmark

This is important.

Use the best unsupervised/post-hoc cluster separation available from Layer A to define an **upper-bound branch detector**.

This is **not** a physically valid final readout.
It is a diagnostic ceiling:

* “if the branch structure is really there, how well could an ideal detector recover it?”

This is the cleanest way to distinguish mechanism failure from readout failure.

### Required comparison questions

For each parameter group:

* how much do outcome quality and support structure improve as readout sophistication increases?
* does the oracle benchmark materially outperform the current rules?
* if yes, readout brittleness is implicated
* if no, mechanism weakness is implicated

---

## 9. New key metrics

## M1. Oracle gap

Define:
[
\text{oracle gap} = \text{oracle branch quality} - \text{best practical readout quality}
]

Large oracle gap:

* mechanism may be okay,
* readout likely too brittle.

Small oracle gap:

* readout is not the main problem,
* mechanism likely weak.

## M2. Sequential branch recoverability

How accurately can the post-Alice branch identity be reconstructed from practical readouts vs oracle detector?

## M3. Confidence efficiency

Fraction of trials retained at a given confidence threshold versus resulting branch purity.

This gives a precision/coverage tradeoff curve.

## M4. Support recoverability

At aligned analyzers, compare same-sign suppression for:

* all trials
* practical high-confidence trials
* oracle high-confidence trials

This is a decisive diagnostic.

## M5. Drift recoverability

Compare marginal drift under:

* practical readouts
* oracle benchmark

If the oracle still shows bad drift, the mechanism is likely the problem.

If the oracle greatly improves drift/support, the readout is likely the problem.

---

## 10. Hard interpretation logic

The final report must classify each regime into one of these bins:

### Bin 1 — Mechanism-limited

* weak residual separability
* weak oracle performance
* no practical readout rescue

### Bin 2 — Readout-limited

* strong residual separability
* oracle substantially better than practical readouts
* current readout clearly missing usable structure

### Bin 3 — Mixed failure

* moderate residual structure
* some oracle improvement
* but still insufficient for credible sequential bridge

### Bin 4 — Bridge candidate

* strong residual separability
* practical readouts close to oracle
* low drift
* low aligned same-sign support
* credible sequential structure

Do not invent additional bins.

---

## 11. Required outputs

### Tables

Produce at minimum:

#### `mechanism_structure.csv`

One row per sequential parameter group with:

* rule-independent structural metrics from Layer A

#### `readout_sensitivity.csv`

One row per `(parameter group, readout family)` with:

* branch recoverability
* ambiguity
* confidence efficiency
* support recoverability
* drift recoverability

#### `oracle_gap_summary.csv`

One row per parameter group with:

* oracle gap
* best practical rule
* classification bin

#### `regime_classification.csv`

One row per parameter group with:

* mechanism-limited / readout-limited / mixed / bridge-candidate label
* justification fields

### Raw cases

Provide raw-case bundles for:

1. strongest mechanism-limited case
2. strongest readout-limited case
3. strongest mixed case
4. strongest bridge-candidate if any
5. current best single-analyzer case for comparison

---

## 12. Required plots

Generate at minimum:

1. `residual_separability_vs_anisotropy.png`
2. `residual_stability_vs_anisotropy.png`
3. `occupancy_vs_confidence_threshold.png`
4. `oracle_gap_vs_anisotropy.png`
5. `support_recoverability_practical_vs_oracle.png`
6. `drift_recoverability_practical_vs_oracle.png`
7. `mechanism_vs_readout_phase_map.png`
8. `state_clouds_with_oracle_clusters.png`

Save the plotted datasets too.

---

## 13. Required README / report answers

The final README/report must answer these directly:

1. Are the current sequential failures primarily mechanism-limited or readout-limited?
2. Does the mechanism generate strong residual branches often enough to matter?
3. Does an oracle detector recover much better behavior than practical rules?
4. Is there any evidence that improving readout alone could rescue the sequential bridge?
5. Should the project continue to refine projective modal depletion, or pivot toward explicit joint-selector/global-constraint mechanisms?

---

## 14. Explicit non-goals

Do **not**:

* optimize for CHSH
* add new physics mechanisms
* tune thresholds to make the answer look better
* hard-code branch identities using the sphere model
* use the oracle detector as a final physical readout

The oracle is diagnostic only.

---

## 15. Decision criterion

This task is successful if it produces a clear answer to:

> Is the current failure mainly in the mechanism, mainly in the readout, or both?

That answer will determine whether the next stage is:

* refine anisotropic projective depletion,
* redesign practical readout,
* or pivot away from this bridge entirely.

---

## 16. One-sentence summary

Use structural clustering and an oracle readout benchmark to determine whether the current sequential bridge fails because the anisotropic-depletion mechanism does not produce usable residual branches, or because the present confidence/readout layer is too brittle to detect and exploit them.
