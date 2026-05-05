# Paper Outline

**Title:** Bell Violations as Three-Party Quadratic Conservation: A Classical Three-Phase Realization

**Author:** [TBD] (placeholder; fill before submission)

**Target venue:** Foundations of Physics (Springer)

**Estimated length:** ~30–40 pages plus appendices; ~60–80 references

---

## Editorial framing — what this paper is, and what it isn't

This paper makes two distinct claims that must be presented in lockstep, because separated they each invite misreading:

1. **Interpretive claim.** The hierarchy of Bell-inequality violations is governed by the algebraic order of the conservation law on the source. Linear conservation produces sub-Bell correlations; quadratic conservation (power, intensity, |ψ|²) produces Tsirelson-saturating correlations. The factor-of-two in cos(2Δφ) is the double-angle identity made physical. The two-party CHSH framework is an incomplete accounting of an intrinsically three-party conservation law, with the third party being the Clarke decomposition's zero-sequence mode — the energy in the field between measurement stations.

2. **Constructive claim.** A classical three-phase analog system — passive linear front-end (four delta-LC tanks with shared resonant core), shot-trigger Born-rule detector, zero-sequence closure latch — reproduces Tsirelson-saturating CHSH (S ≈ 2.828, error 0.043) under explicit and disclosed detector assumptions. The numerical results are real: winner-law RMS error 0.013, decisive rate 99.5%, energy conservation 100%, winner-drain dominance 99.97%.

**What this paper does NOT claim.** It does not refute Bell's theorem, which is a theorem about local hidden-variable models with binary outcomes. The construction requires a *non-local* conservation constraint — specifically, the zero-sequence mode mediates correlations between the two measurement stations through the conserved quadratic form. The paper's contribution is structural, not foundational: it makes the locus of nonlocality concrete (zero-sequence energy flow) and gives the apparent "spookiness" of CHSH violations a physical interpretation in terms of conservation accounting, not a refutation of locality.

This framing must appear in the abstract, the introduction, and the discussion. Without it, the constructive result will be misread as a "classical Bell-buster," and the paper will be desk-rejected.

---

## Abstract (~250 words)

> The hierarchy of Bell-inequality violations arises from the algebraic order of the conservation law governing the correlated source. Linear conservation (momentum-type) produces correlations bounded by S = √2; quadratic conservation (power, |ψ|²) produces correlations that saturate the Tsirelson bound at S = 2√2. The factor-of-two in cos(2Δφ) versus cos(Δφ) is the double-angle identity inherent in squaring the field amplitude. We argue that the standard two-party CHSH framework constitutes an incomplete accounting of an intrinsically three-party conservation law, with the third party identified as the zero-sequence mode of the Clarke decomposition — the energy carried by the field between measurement stations, structurally analogous to vacuum / edge-mode contributions in algebraic quantum field theory and to the quantum potential in Bohmian mechanics. We construct a classical three-phase analog system — a passive linear front-end (four delta-LC tanks with shared resonant core), a shot-trigger Born-rule detector, and a zero-sequence closure latch — and show by reduced-model simulation and a SPICE-driven realization that it reproduces Tsirelson-saturating CHSH (S ≈ 2.828, error 0.043; winner-law RMS error 0.013; decisive rate 99.5%; energy conservation 100%). We position this construction relative to prequantum classical models (Khrennikov's PCSFT, Spekkens, 't Hooft, Bohmian mechanics) and clarify scope: the system requires a non-local conservation constraint and therefore does not refute Bell's theorem. Its contribution is to make the locus of nonlocality concrete — the zero-sequence energy flow — and to give the apparent nonlocality of quantum correlations a structural interpretation in terms of three-party quadratic conservation accounting.

---

## Section structure

### 1. Introduction (3–4 pages)

1.1 Bell's theorem and the standard interpretation.
1.2 The interpretive thesis: violations as signatures of conservation order. Pitch the linear-vs-quadratic dichotomy in plain language.
1.3 The structural claim: missing third party = zero-sequence.
1.4 The constructive claim: classical three-phase analog reproduces Tsirelson, with disclosed assumptions.
1.5 What this paper does *not* claim. (Bell stays standing; we have a nonlocal constraint.)
1.6 Relation to prior frameworks (one paragraph each: AQFT entanglement, Bohmian, Khrennikov's PCSFT). Full prior-art positioning deferred to §10.
1.7 Roadmap.

**Source material:** notebooks/30_bell_conservation_paper.qmd §1, plus new framing.

---

### 2. The Conservation Hierarchy (4–5 pages)

2.1 General setup: source, two analyzers at independently chosen angles, hidden emission phase θ.
2.2 **Case I — linear conservation (momentum-type).** Derivation of E_lin(a,b) = −½cos(Δφ); CHSH evaluation S = √2.
2.3 **Case II — quadratic conservation (power-type).** Derivation of E_quad(a,b) = −½cos(2Δφ); CHSH evaluation S = 2√2.
2.4 The double-angle identity cos²(x) = (1+cos(2x))/2 as the algebraic engine. The squaring is not metaphor; it doubles the angular frequency of correlation patterns and that is what pushes S past the Bell bound.
2.5 The hierarchy table: stochastic-local (√2) / deterministic-threshold (2) / quantum-quadratic (2√2) / PR-box (4).

**Source material:** notebooks/30_bell_conservation_paper.qmd §2, §5.

**Figure 1.** Side-by-side plots of E_lin(Δφ) = −½cos(Δφ) and E_quad(Δφ) = −½cos(2Δφ), with the four CHSH analyzer-angle settings overlaid as vertical lines. Shaded regions show the contributions to S. Reproducible from a short numpy script.

---

### 3. The Clarke Transform as Measurement Apparatus (3–4 pages)

3.1 Definition; the Clarke matrix; orthonormality.
3.2 Power invariance (Parseval): v_a² + v_b² + v_c² = v_α² + v_β² + v_0². This is the quadratic conservation law.
3.3 Symmetrical components: positive sequence, negative sequence, zero sequence.
3.4 The Park rotation as analyzer; Malus's law from Clarke-Park projection.
3.5 The Clarke surface and Born-rule isomorphism. Three structural identities: counter-rotation ↔ particle DoF; power ↔ probability; cos² maximal correlation ↔ single-particle axis alignment.

**Source material:** notebooks/20_clarke-surface.qmd; notebooks/30_bell_conservation_paper.qmd §3.

**Figure 2.** The Clarke power surface p_αβ(θ) = 6V²cos²θ as a 3D bowl, alongside its mapping to a hemisphere of the Bloch sphere. (Reproducible from notebooks/20_clarke-surface.)

---

### 4. Two-Party CHSH from a Three-Phase Source (4–5 pages)

4.1 Standard setup with positive and negative sequences from the source.
4.2 Local uniformity (no-signaling) from ±-sequence symmetry; reduced state ρ_A = I/2 from tracing out the rotation-sense hidden variable.
4.3 Derivation of E(a,b) = −cos(2Δφ) for the full quadratic distribution.
4.4 The threshold/binarization problem: real Bell tests yield ±1 outcomes.
4.5 **Stochastic local model:** P(A=+1|θ) = cos²(θ−φ_A), independent coin flips. Yields E = −½cos(2Δφ), S = √2. Factorization dilutes by ½.
4.6 **Deterministic threshold:** A = sgn[cos(2(θ−φ_A))]. Yields piecewise linear E = −1 + 4|Δφ|/π, S = 2 exactly. Binarization linearizes.
4.7 The gap: each step in the hierarchy is √2. The factor of 2 between stochastic-local and quantum is the signature of strict event-by-event complementarity, which is what no factorized local model can deliver.

**Source material:** notebooks/30_bell_conservation_paper.qmd §4, §5.

**Figure 3.** All three correlator shapes — stochastic-local, deterministic-threshold, full quadratic — on one axis vs. Δφ.

---

### 5. The Third Party: Zero-Sequence as Vacuum Mode (4–5 pages)

5.1 The missing energy. P_A + P_B = 1 + cos(Δφ)cos(2θ−φ_A−φ_B); not constant unless analyzers are aligned or orthogonal.
5.2 P_0 absorbs the difference. At Δφ = 0: P_0 = 0 (analyzers fully partition the budget). At Δφ = π/2: P_0 maximal and θ-independent (channel absorbs all correlation energy). At Δφ = π/4: intermediate — exactly where CHSH violation peaks.
5.3 The three-party conservation law: P_+ + P_- + P_0 = constant. This is Parseval applied to the symmetrical-components decomposition.
5.4 Analogy to AQFT: zero-sequence ↔ edge / vacuum modes that belong to neither region but participate in the joint state.
5.5 Analogy to Bohmian mechanics: zero-sequence ↔ quantum potential. Both are nonlocal terms that couple subsystems through a conserved global quantity.
5.6 Connection to monogamy of entanglement (Coffman–Kundu–Wootters): a fixed total correlation budget allocated across pairs.

**Source material:** notebooks/30_bell_conservation_paper.qmd §6; notebooks/53_born_rule_zeroseq.qmd.

**Figure 4.** P_0(Δφ) over a CHSH sweep, computed from the analytic expressions and from the reduced 4-mode simulation. Vertical lines at the four CHSH analyzer settings.

---

### 6. The Reduced 4-Mode Model and Joint Measurement (3–4 pages)

6.1 Shared 4-mode state Ψ₀ ∈ ℂ⁴ in basis {|++⟩, |+−⟩, |−+⟩, |−−⟩}; the singlet projection.
6.2 Local analyzer rotations R_A(a) ⊗ R_B(b).
6.3 Joint branch weights w_xy(a,b) = |c_xy(a,b)|².
6.4 **Theorem 6.1 (squared-projection law at linear energy level).** Statement and proof from notebooks/102_detector-layer_note.qmd. The exact reduced model produces branch energies proportional to |projections|² with no post-hoc multiplication.
6.5 Numerical verification: S = 2√2 exactly for the singlet; explicit angle sweeps from src/joint_readout.py and src/benchmarks.py.

**Source material:** notebooks/60–65_entanglement.qmd; notebooks/102_detector-layer_note.qmd; src/shared_4tank_core.py; src/joint_readout.py; src/benchmarks.py.

**Figure 5.** CHSH(angle settings) sweep from the reduced model showing S → 2√2 at optimal angles. Tsirelson bound dashed at 2√2.

---

### 7. Born Rule from Energy-Threshold Detection (4–5 pages)

7.1 The three functional layers (from notebooks/73): linear branch-intensity generator; stochastic nucleation element; zero-sequence latch.
7.2 **Theorem 7.1 (Born law from noisy energy threshold first arrival).** Statement and proof from notebooks/50_born_rule.qmd. Conditions: matched thresholds, drift-dominated crossing, slow envelope, weak pre-click backaction.
7.3 Why shot-trigger over accumulation (notebooks/81): hazard λ(P) = αP linear in absorbed power preserves Born statistics because the quadratic order is in the front-end, not the detector.
7.4 Compound-Poisson and metastable-escape variants (notebooks/51, 52).
7.5 Detector-search results from detector_search/: family-wise fidelity ranking; shot-trigger wins.

**Source material:** notebooks/50–54_born_rule*.qmd; notebooks/73–75_detector_spec*.qmd; notebooks/81_investigation.qmd; notebooks/101_detector_notes.qmd; notebooks/102_detector-layer_note.qmd; detector_search/ package.

**Figure 6.** Detector family fidelity comparison (race-law fidelity vs. parameter sweeps for shot_trigger, poisson_linear, accumulator_bad_control, metastable_escape). Reproducible via `make detector-search`.

---

### 8. The Zero-Sequence Latch: Post-Click Closure (2–3 pages)

8.1 Common-mode inhibit + winner drain (from notebooks/53; coder_instructions/200, 201).
8.2 Latch suppresses losers, routes shared energy to winner drain via the zero-sequence rail.
8.3 Backaction analysis (notebooks/54): timescale separation prevents pre-click contamination.
8.4 Validation: 99.97% winner-drain dominance, 99.5% decisive (one-click) rate.

**Source material:** notebooks/53_born_rule_zeroseq.qmd; notebooks/54_born_rule_backaction.qmd; detector_rig/latch.py; detector_rig/latch_report.py; physical_front_end_candidate/closure_path.py.

**Figure 7.** Closure-drain timing diagram with energy accounting on a representative trial — pre-click branch energies, click event, drain dynamics, residual energies in losers.

---

### 9. Classical Three-Phase Realization: SPICE Implementation (5–6 pages — flagship section)

9.1 Architecture (from notebooks/70_physical_model.qmd): four delta-LC tanks {++, +−, −+, −−} as joint basis states; shared resonant core for inter-tank coupling; analyzer couplers for local R_A(a) ⊗ R_B(b); resistive extraction → branch energies.
9.2 Codesign and device physicalization. Component values (L, C, R, coupling coefficients) from coder_instructions/230, 232, 233 and physical_front_end_candidate/preferred_chain_device_physicalization.py. Bill of materials.
9.3 The actual SPICE front-end: physical_front_end_candidate/actual_spice_front_end.py (PySpice-driven netlist).
9.4 Phase-descent calibration (from notebooks/15_calibration.qmd): error-lineage diagnostics distinguishing analyzer asymmetry (odd harmonics, phase-locked) from recombiner asymmetry (even harmonics, DC offset). Phase-locking preserved to <10⁻⁴ rad under 20% severity perturbation.
9.5 **Results.** Winner-law RMS error 0.013, max 0.039; correlator RMS 0.024; CHSH absolute error 0.043 against exact target 2√2; decisive rate 99.5%; winner-drain dominance 99.97%; energy conservation 100% (within numerical tolerance).
9.6 Error budget. Sources: nonlinearity, parametric tolerances, numerical noise.
9.7 Reproducibility: every quantitative claim is anchored in a make-target. Table of make-targets ↔ artifacts ↔ numerical results.

**Source material:** notebooks/70_physical_model.qmd; physical_front_end_candidate/ package (entire); notebooks/15_calibration.qmd; coder_instructions/230, 232, 233, 240; Makefile.

**Figures.**
- **Figure 8.** Architecture schematic: four delta-LC tanks, shared resonant core, analyzer couplers, resistive extraction, latch.
- **Figure 9.** Full SPICE chain CHSH(a,b) angle sweep with the Tsirelson bound dashed; achieves S ≈ 2.828.
- **Figure 10.** Fidelity table as a graphic: winner-law RMS, correlator RMS, CHSH error, decisive rate, conservation.
- **Figure 11.** Phase-descent calibration figure (from notebooks/15) — odd vs. even harmonic signatures.
- **Figure 12.** Closure dynamics: representative one-trial trace from physical chain.

---

### 10. Position Among Prequantum Classical Models (3–4 pages)

*Light survey. The user will deepen this engagement.*

10.1 **Khrennikov's prequantum classical statistical field theory (PCSFT).** Closest comparison. Shared: classical fields, quadratic functionals, no hidden particles. Different: we use a lumped finite-dimensional power network, not a continuous field functional integral; we have an explicit zero-sequence mode rather than a renormalized vacuum; we make the role of the conservation law structural.
10.2 **Spekkens toy theory.** Different aim (epistemic restriction in a discrete model); the cos² in our system is geometrically continuous, not toy-stipulated.
10.3 **'t Hooft cellular automaton interpretation.** Far more ambitious (deterministic theory underlying QM). We are structural analog, not fundamental theory.
10.4 **Bohmian mechanics.** Zero-sequence energy ↔ quantum potential; both nonlocal terms enforcing a global constraint.
10.5 **Hess–Philipp time-dependent LHV.** Not the same mechanism; we don't introduce a time-dependent hidden variable. The cosine emerges from quadratic conservation, not time-correlated noise.
10.6 **Field-theoretic / AQFT entanglement (Witten 2018; Haag 1996).** Strong alignment: zero-sequence ↔ edge / vacuum modes between regions.
10.7 **Detection-loophole literature (Larsson, Adenier).** Our result does not depend on detection-loophole arguments; the SPICE chain reaches 99.5% decisive rate, well above fair-sampling thresholds.
10.8 **Honest disclaimer panel.** What we share with each, what we differ on, what we don't claim.

**Source material:** notebooks/00_objection.md; notebooks/900_related.md; user-supplied sources.

---

### 11. Discussion (3–4 pages)

11.1 Predictions and testable consequences:
  - Three-party Bell tests (Mermin) where the zero-sequence mode is directly measurable should saturate Mermin's bound.
  - Classical EM tests in three-phase laboratories should reproduce E(a,b) = −½cos(2Δφ) in stochastic-local mode; the gap to 2√2 then localizes the strict-complementarity assumption.
  - Higher symmetry groups (D4, with multiple independent quadratic invariants) should permit larger violations of generalized inequalities.
11.2 Limitations: the construction does not solve the measurement problem. It localizes it: the mystery is in event-by-event enforcement of the global conservation constraint.
11.3 Implications for foundations. The apparent nonlocality lives in the zero-sequence mode, which in the analog is a real, measurable physical degree of freedom. The field-theoretic analogy suggests it is a real degree of freedom in the quantum case as well — and the framework asks whether the "spookiness" is irreducible nonlocality or honest accounting of a third participant.
11.4 Open questions: (a) D4 LC tank invariants and Mermin extensions (notebooks/80_brainstorm); (b) microscopic origin of nucleation linearity; (c) timescale-separation regime for latch non-contamination.

**Source material:** notebooks/72_discussion.qmd; notebooks/80_brainstorm.qmd; notebooks/30_bell_conservation_paper.qmd §9.

---

### 12. Conclusion (1–2 pages)

The five core findings, restated cleanly:
1. Bell-correlation form is determined by the algebraic order of the conservation law.
2. The CHSH violation arises from the double-angle identity inherent in squaring the field.
3. The two-party CHSH is an incomplete accounting of a three-party conservation law.
4. The third party is the zero-sequence mode; in the field-theoretic analogy, it is the vacuum/edge mode.
5. A classical three-phase analog with linear front-end + shot-trigger detector + zero-sequence latch reproduces Tsirelson-saturating CHSH (S ≈ 2.828) under disclosed assumptions and a non-local conservation constraint, demonstrating that the structure of quantum correlations is reproducible by a classical conservation-respecting analog and localizing the residual mystery.

---

## Appendices

- **A.** Clarke transform conventions, identities, and proofs.
- **B.** Reduced 4-mode model: full derivation of joint branch weights w_xy(a,b) under R_A(a) ⊗ R_B(b).
- **C.** Detector family characterization: full results from `detector_search/`.
- **D.** SPICE netlist of the preferred chain (from preferred_front_end_netlist_candidate.py).
- **E.** Full numerical results table from physical_front_end_candidate/ — all sweeps, all metrics, all seeds.
- **F.** Reproducibility: make-target table mapping every quantitative claim to a script and an artifact.

---

## Figure inventory

| # | Title | Source | Generation status |
|---|---|---|---|
| 1 | Linear vs. quadratic correlator + CHSH overlay | new numpy script | needs writing |
| 2 | Clarke surface bowl + Bloch hemisphere mapping | notebooks/20_clarke-surface | rerun |
| 3 | Three correlator shapes overlaid | new numpy script | needs writing |
| 4 | P_0(Δφ) zero-sequence energy curve | new + reduced model | needs writing |
| 5 | CHSH sweep (reduced model) | src/joint_readout, src/benchmarks | rerun |
| 6 | Detector family fidelity | detector_search/ + plots | `make detector-search` |
| 7 | Closure-drain timing | physical_front_end_candidate/closure_path | new run |
| 8 | Architecture schematic | hand-drawn / TikZ | needs creation |
| 9 | SPICE chain CHSH sweep | preferred chain LC report | `make preferred-physical-chain-lc-report` |
| 10 | Fidelity table graphic | metrics from artifacts | needs styling |
| 11 | Phase-descent calibration | notebooks/15_calibration | rerun |
| 12 | Closure dynamics one-trial trace | physical_front_end_candidate | new plot |

---

## References — initial spine (to expand)

Anchor citations the paper *must* engage with:

- Bell, J. S. (1964). On the Einstein Podolsky Rosen paradox. *Physics Physique Fizika* 1(3), 195–200.
- CHSH: Clauser, Horne, Shimony, Holt (1969). *PRL* 23, 880.
- Tsirelson, B. S. (1980). Quantum generalizations of Bell's inequality. *Letters in Mathematical Physics* 4(2), 93–100.
- Mermin, N. D. (1990). *PRL* 65, 1838.
- Popescu & Rohrlich (1994). Quantum nonlocality as an axiom. *Foundations of Physics* 24, 379–385.
- Coffman, Kundu, Wootters (2000). Distributed entanglement. *PRA* 61, 052306.
- Clarke, E. (1943). *Circuit Analysis of A-C Power Systems*, Vol. I. Wiley.
- Fortescue, C. L. (1918). Method of symmetrical co-ordinates. *AIEE Transactions* 37(2), 1027–1140.
- Khrennikov, A. (multiple works on PCSFT — user to specify the canonical citation).
- Spekkens, R. W. (2007). In defense of the epistemic view of quantum states. *PRA* 75, 032110.
- 't Hooft, G. (2016). *The Cellular Automaton Interpretation of Quantum Mechanics*. Springer.
- Haag, R. (1996). *Local Quantum Physics*. Springer.
- Witten, E. (2018). APS Medal article on entanglement properties of QFT. *RMP* 90, 045003.
- Larsson, J.-Å. (2014). Loopholes in Bell inequality tests. *J. Phys. A* 47, 424003.

User to add: Adenier, Hess–Philipp, Khrennikov canonical refs, any specific PCSFT volume, Bohm 1952 + Holland 1993, Aspect milestone experiments, Hensen 2015 / Giustina 2015 / Shalm 2015 loophole-free experiments.

---

## Open questions for author before drafting prose

1. **Authorship line.** Currently `[TBD]`. The pyproject lists "David, david.nobles@sontric.org." Use "David Nobles, Sontric"? Add affiliation/ORCID later?
2. **Ordering of §6 (reduced model) vs. §3–§5 (Clarke / CHSH / zero-sequence).** Current order: physics-up — derive correlator shapes from conservation, then identify the third party, then introduce the reduced 4-mode model that operationalizes both. Alternative: introduce the reduced model first as the formal target. I recommend current ordering for FoP.
3. **Length of §10 (prior art).** Currently allocated 3–4 pages with you doing the deep engagement. If you want me to expand it, that flips to 6–8 pages. Recommend keeping it tight.
4. **Phase-descent calibration (§9.4).** This is methodologically independent and could be its own paper. Keeping it as a §9 subsection signals "we know how to instrument this." Alternative: relegate to Appendix C.
5. **Section 7 Theorem 7.1 (Born from energy threshold).** This is an actual theorem with explicit conditions. It deserves a careful proof. Should I include the full proof in §7 (~3 pages) or move proof to Appendix B and keep statement-only in §7?
