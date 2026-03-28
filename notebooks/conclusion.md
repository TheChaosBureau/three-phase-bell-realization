## Decision memo

The anisotropic-damping program has produced a useful split result.

The **single-analyzer side is promising**. The best single-analyzer case reached projectivity (0.874) at anisotropy ratio (16), window (1/3), angle (90^\circ), with very high residual-branch quality. That is strong evidence that finite-window anisotropic depletion can generate a meaningful state update and is not just generic amplitude shrinkage.

The **sequential side is not trustworthy yet**. The audit’s direct answers say the strongest sequential CHSH rows are mainly signaling-driven, and no sequential regime currently clears the conservative trust screen as both low-drift and sphere-like. The top CHSH row reaches (3.167), but it comes with Bob marginal drift (1.333), aligned same-sign mass (0.75), and is flagged signaling and overfit. The trust-ranking table confirms that the best trust score is only (0.545), labeled “caution.”

That means the current audit supports this conclusion:

**Projective residual formation looks real in the single-analyzer mechanism, but the present sequential readout layer is not yet a credible bridge to sphere-like no-signaling pair statistics.**

## What this means

You do **not** currently have evidence for a realizable Bell-like circuit mechanism.

You **do** have evidence for a narrower and still important result:

**Strong anisotropic damping can produce near-projective residual-state structure in a two-mode model.**

That is enough to justify continuing the mechanism search, but not enough to justify claims about the full sequential sphere bridge.

The audit also clarifies that the current sequential results are being distorted by readout design. The README identifies `dominant_pre` as the riskiest rule and `dominance_shift` as the least drift-prone, while the rule comparison shows `dominant_pre` has the highest average CHSH and the highest Bob drift, with the most overfit-style rows.

So the problem is no longer vague. The issue is not “anisotropic damping failed.” The issue is:

**the current way discrete pair outcomes are extracted from the sequential dynamics is not physically trustworthy.**

## Decision

Proceed, but pivot the effort.

Do **not** continue optimizing the current sequential CHSH layer.

Do **not** spend time trying to rescue the current high-CHSH rows.

Do **continue** the anisotropic-damping mechanism program, but refocus it around:

1. validating and strengthening the single-analyzer projective update,
2. redesigning the sequential readout/update layer from scratch,
3. treating CHSH as a late-stage diagnostic, not a target.

## Next-step plan

### Phase 1 — Lock down the single-analyzer mechanism

The immediate goal is to turn the promising single-analyzer result into a solid mechanism result.

Tasks:

* reproduce the best single-analyzer regime with denser sweeps around anisotropy ratio, window, and angle
* quantify robustness to small perturbations in initial state, noise, and slight mode imbalance
* verify whether the projectivity optimum is broad or narrow
* compare (T/6, T/4, T/3, T/2, T) carefully, since the audit currently reports the best average projectivity near (T=1.0) but the best listed combo at (T=1/3), which needs reconciliation 

Deliverable:

* a short mechanism note showing where projective residual formation is strongest and how robust it is.

### Phase 2 — Redesign the sequential readout layer

The current sequential rules are not acceptable as a final bridge.

Tasks:

* retire `dominant_pre` from any headline analysis; keep it only as a negative-control rule
* treat `dominant_post`, `residual_classifier`, and `dominance_shift` as provisional only
* build a new sequential readout family that is explicitly constrained to avoid:

  * pre-window answer leakage,
  * same-sign dominance at aligned analyzers,
  * large marginal drift,
  * trivial overfitting to branch geometry

The new rule family should be judged first on:

* aligned same-sign suppression,
* Bob drift vs Alice setting,
* Alice drift vs Bob setting,
* consistency with residual-state geometry.

CHSH should only be computed after those are acceptable.

### Phase 3 — Separate mechanism validation from Bell-style diagnostics

The current audit shows that high CHSH can appear long before the mechanism is trustworthy.

Tasks:

* create two distinct scorecards:

  * **mechanism scorecard**: projectivity, residual purity, manifold closure, rule locality
  * **operational scorecard**: aligned support, marginal drift, no-signaling flags, CHSH
* require mechanism scorecard to pass before operational scorecard is even interpreted

This avoids repeating the current situation where CHSH dominates attention despite obvious signaling artifacts.

### Phase 4 — Decide between two theoretical branches

Once the redesigned sequential layer is tested, choose between:

**Branch A: continue mechanism-first**

* keep asking whether a physically plausible anisotropic-depletion process can generate the needed pair law

**Branch B: admit the need for an explicit joint selector**

* if every trustworthy sequential readout underperforms, then the remaining gap is likely not in damping but in the absence of a true pair-space selection law

That would align with the earlier conclusion from the PE-style and sphere discussions: geometry and residual update may be necessary, but not sufficient; the final obstacle may still be joint event formation.

## Immediate action items for the coder

1. Run a focused **single-analyzer refinement sweep** around the best regime.
2. Add a **negative-control label** to `dominant_pre` and remove it from “best result” summaries.
3. Implement a **new sequential readout prototype** designed around residual-state geometry rather than pre-window dominance.
4. Report sequential results only if:

   * aligned same-sign mass is low,
   * marginal drift is low,
   * overfit flag is false,
   * and trust score exceeds the current caution range.

## Recommended wording for current status

A good, honest summary is:

> The audit supports anisotropic modal depletion as a plausible mechanism for near-projective single-analyzer state update, but the current sequential readout rules do not yet yield a trustworthy sphere-like pair mechanism. High sequential CHSH values are presently explained by signaling and readout artifacts rather than credible emergent no-signaling joint behavior.

## Bottom line

The right move is **not** to stop.

The right move is to narrow the claim and sharpen the program:

* keep the single-analyzer projective depletion result,
* discard the current sequential hype,
* redesign the sequential mechanism carefully,
* and treat the remaining gap as real.

That is progress, not failure.
