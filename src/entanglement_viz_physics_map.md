# Physics Mapping for `entanglement_viz.py`

## Purpose

This document explains the current visualization in direct equation-to-code terms. It replaces the earlier "bowl metaphor" reading with a stricter split:

- the 3D scene shows propagation geometry in Clarke `α-β-z` space
- detector planes show analyzer response by color, not by height
- the lower plot shows the actual `θ`-dependent power accounting
- the Bell correlation readout is kept as an analytic overlay and is labeled as such

The app also makes an important paper-level distinction explicit. The paper currently uses two related constructions:

1. **Sequence response view** from Section 4:
   `P_A(θ) = cos²(θ-φ_A)`, `P_B(θ) = sin²(θ-φ_B)`
2. **Three-party closure view** from Section 6:
   `P_A(θ) = cos²(θ-φ_A)`, `P_B(θ) = cos²(θ-φ_B)`, `P_0(θ) = 1 - P_A(θ) - P_B(θ)`

The app does not silently collapse those into one picture. The user chooses which equation set is being visualized.

## Direct Mapping from Equations to Code and Scene

| Visualization element | Code / function | Equation or paper section | Literal meaning in the current app | Physics interpretation |
|---|---|---|---|---|
| Model selector | `MODEL_SEQUENCE`, `MODEL_CLOSURE`, `model_metadata()` | Paper Sec. 4 vs Sec. 6 | Chooses which equation set is active | Makes the paper's two constructions explicit instead of blending them |
| Propagation phase | `phase_progression(time, handedness)` | Paper Sec. 3.2 rotating sequence phasors | Maps normalized propagation coordinate `z` to phase angle `θ(z)` | Shared phase variable for both sequence helices and the lower accounting plot |
| Positive-sequence helix | `positive_sequence_coords()` | Paper Sec. 3.2 positive sequence | Draws a counterclockwise helix in `α-β-z` | Positive-sequence field component |
| Negative-sequence helix | `negative_sequence_coords()` | Paper Sec. 3.2 negative sequence | Draws a clockwise helix in `α-β-z` | Negative-sequence field component |
| Equal-sequence superposition trace | `superposition_coords()` | Paper Sec. 4.1 linear polarization from equal positive and negative sequence superposition | Draws the fixed-axis `β = 0` trace | Net linearly polarized Clarke-space oscillation |
| Detector A response plane | `clarke_energy_profile(_TH, phi_a)` passed into `detector_plane_trace()` | Paper Sec. 3.3 and Sec. 4.1: `P_A = cos²(θ-φ_A)` | Flat disk at `z_A`, color-coded by `P_A(θ)` | Literal analyzer response map for detector A |
| Detector B response plane in sequence mode | `complementary_energy_profile(_TH, phi_b)` | Paper Sec. 4.1: `P_B = sin²(θ-φ_B)` | Flat disk at `z_B`, color-coded by `P_B(θ)` | Complementary channel response from the sequence-response construction |
| Detector B response plane in closure mode | `clarke_energy_profile(_TH, phi_b)` | Paper Sec. 6.1: second analyzer capture `cos²(θ-φ_B)` | Flat disk at `z_B`, color-coded by `P_B(θ)` | Second measured channel in the shared-accounting construction |
| Explicit third-party plane | `p_extra_disk = 1 - p_a_disk - p_b_disk` rendered in `build_scene_figure()` when closure mode is active | Paper Sec. 6.3: `P_0 = P_total - P_A - P_B` | Flat channel disk at the midpoint between `z_A` and `z_B` | Zero-sequence / channel term in the three-party closure model |
| Detector axis lines | `detector_axis_trace()` | Paper Sec. 3.3 Park rotation angle `φ` | Dashed line through each detector disk at `φ_A` or `φ_B` | Analyzer basis orientation |
| Hidden-phase marker | `hidden_phase_marker()` and `current_hidden_phase()` | Shared hidden/emission phase `θ` used throughout Sec. 2, 4, and 6 | Marks the currently sampled phase `θ*` on each disk | Connects the animated propagation sample to the accounting curves below |
| Lower accounting plot | `build_accounting_figure()` | Paper Sec. 4 and Sec. 6 | Plots the active model's functions over `θ` | Quantitative view of the response profiles instead of a purely geometric metaphor |
| `P_A(θ)` curve | `clarke_energy_profile(theta, phi_a)` | `P_A(θ)=cos²(θ-φ_A)` | Blue curve on the lower plot | Direct detector-A response function |
| `P_B(θ)` curve in sequence mode | `complementary_energy_profile(theta, phi_b)` | `P_B(θ)=sin²(θ-φ_B)` | Red curve on the lower plot | Complementary detector-B response in the sequence model |
| `P_B(θ)` curve in closure mode | `clarke_energy_profile(theta, phi_b)` | `P_B(θ)=cos²(θ-φ_B)` | Red curve on the lower plot | Second measured channel in the closure model |
| Residual / third term curve | `sequence_response_profiles()` or `three_party_profiles()` | `1 - P_A - P_B` or `P_0` | Dashed third curve on the lower plot | Either explicit closure term (`P_0`) or residual mismatch, depending on model |
| Bell readout | `bell_metrics(phi_a, phi_b)` and `info_panel_children()` | Paper Sec. 2.3 and Sec. 4.3: `E(a,b) = -cos(2Δφ)` | Displays `Δφ`, `cos²(Δφ)`, and analytic `E(a,b)` | Analytic quadratic-correlation overlay from the paper |
| Local averages and ranges | `info_panel_children()` | Paper discussion of local means and channel accounting | Displays `⟨P_A⟩`, `⟨P_B⟩`, third-term range, and closure error | Makes explicit what the plotted functions actually do, averaged over `θ` |

## What Changed Relative to the Old Scene

The old scene used raised and inverted bowls, a `180°` viewpoint equivalence, and a breathing envelope. Those have been displaced from the main interpretation:

- `z` now means propagation only
- detector response is shown by **color on flat planes**, not by height
- positive and negative sequences are both rendered explicitly
- the third party is rendered explicitly in closure mode
- the lower plot exposes the full `θ`-dependent accounting
- the Bell value is still shown, but it is now clearly labeled as an analytic overlay rather than a numerical result extracted from the scene

Legacy helpers such as `analyzer_surface_height()` and `complementary_surface_sum()` remain in the module for continuity and comparison, but the Dash app no longer uses them as the primary physics picture.

## What Is Now Literal and What Is Still Assumed

### Literal in the current app

- The propagation helices literally represent positive and negative sequence rotation.
- Detector disks literally evaluate the selected analyzer response formula on a circular `θ` domain.
- The lower plot literally shows the functions being used by the active model.
- In closure mode, the third-party disk and dashed curve literally show `1 - P_A - P_B`.

### Still an assumption or overlay

- `E(a,b) = -cos(2Δφ)` is not numerically derived from sampled binary outcomes inside the app; it is displayed as the paper's analytic law.
- The app does not yet simulate the threshold and stochastic-local binarization models from paper Section 5.
- In closure mode, the sign and range of `P_0` come directly from the chosen formula; the app does not impose extra positivity or field-theoretic constraints beyond what that formula gives.

## Practical Reading Guide

1. Start with the model selector. That determines which equations the rest of the app is showing.
2. Read the 3D scene as propagation geometry plus detector basis planes.
3. Read detector color as normalized analyzer response, not as spatial height.
4. Use the lower plot to inspect the full `θ`-dependence of `P_A`, `P_B`, and the third term.
5. Read the Bell line in the info panel as an analytic overlay connected to the paper's quadratic-correlation claim, not as a sampled measurement statistic.
