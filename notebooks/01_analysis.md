Yes. Here is a concrete ablation matrix that treats closure as the only changing block.

---

# Purpose

Hold fixed:

* shared-state preparation
* analyzer law
* front-end branch-weight computation
* detector-cell model
* winner-latch implementation
* trial generation and statistics pipeline

Vary only:

* **closure family**

Then measure whether Bell-relevant behavior is already present before closure, preserved by closure, or created by closure.

---

# Fixed architecture

For every ablation run, use the same chain:

[
\Psi \xrightarrow{\text{analyzers }(a,b)} w_{xy}(a,b)
\xrightarrow{\text{detector race}} r_{xy}
\xrightarrow{\text{winner latch}} \hat r_{xy}
\xrightarrow{\text{closure}} z_{xy}
]

where:

* (\Psi) = shared prepared state
* (w_{xy}) = front-end branch weights for joint branches (xy \in {++, +-, -+, --})
* (r_{xy}) = first-arrival winner before latch cleanup
* (\hat r_{xy}) = latched winner before closure-induced rerouting, if you want to distinguish it
* (z_{xy}) = final recorded winner after closure

In the simplest implementation you may only need two outcome layers:

* **pre-closure winner**
* **post-closure final winner**

---

# Core observables

For every closure family, compute all of these from both pre-closure and post-closure outcomes.

## Outcome probabilities

[
P_{\text{pre}}(xy|a,b), \qquad P_{\text{post}}(xy|a,b)
]

## Correlator

[
E_{\text{pre}}(a,b)
===================

P_{\text{pre}}^{++}+P_{\text{pre}}^{--}-P_{\text{pre}}^{+-}-P_{\text{pre}}^{-+}
]

[
E_{\text{post}}(a,b)
====================

P_{\text{post}}^{++}+P_{\text{post}}^{--}-P_{\text{post}}^{+-}-P_{\text{post}}^{-+}
]

## CHSH

Using one fixed CHSH angle set, e.g.

[
(a_0,a_1,b_0,b_1)=(0^\circ,45^\circ,22.5^\circ,67.5^\circ)
]

compute

[
S_{\text{pre}}
==============

E_{\text{pre}}(a_0,b_0)+E_{\text{pre}}(a_0,b_1)+E_{\text{pre}}(a_1,b_0)-E_{\text{pre}}(a_1,b_1)
]

[
S_{\text{post}}
===============

E_{\text{post}}(a_0,b_0)+E_{\text{post}}(a_0,b_1)+E_{\text{post}}(a_1,b_0)-E_{\text{post}}(a_1,b_1)
]

## Winner-flip fraction

[
f_{\text{flip}}
===============

\Pr!\left[r_{\text{pre}} \neq r_{\text{post}}\right]
]

Also compute conditional flip rates by branch:

[
f_{\text{flip}|xy}
==================

\Pr!\left[r_{\text{post}}\neq xy \mid r_{\text{pre}}=xy\right]
]

## Local marginals

Alice marginal:

[
P_{\text{pre}}(A=+|a,b)=P_{\text{pre}}(++|a,b)+P_{\text{pre}}(+-|a,b)
]

[
P_{\text{post}}(A=+|a,b)=P_{\text{post}}(++|a,b)+P_{\text{post}}(+-|a,b)
]

and similarly for (A=-), (B=+), (B=-).

Then define no-signaling deviations:

[
\Delta_A^{\text{pre}}(a;b,b')
=============================

\left|P_{\text{pre}}(A=+|a,b)-P_{\text{pre}}(A=+|a,b')\right|
]

[
\Delta_A^{\text{post}}(a;b,b')
==============================

\left|P_{\text{post}}(A=+|a,b)-P_{\text{post}}(A=+|a,b')\right|
]

and likewise for Bob.

Use max over tested settings as summary:

[
\Delta_{A,\max}^{\text{pre}},;
\Delta_{A,\max}^{\text{post}},;
\Delta_{B,\max}^{\text{pre}},;
\Delta_{B,\max}^{\text{post}}
]

## Shape error to target law

If target is singlet-like:

[
E_{\text{target}}(a,b)=-\cos 2(a-b)
]

Then define RMS error over the angular grid:

[
\varepsilon_E^{\text{pre}}
==========================

\sqrt{\frac{1}{N}\sum_{a,b}\left(E_{\text{pre}}(a,b)-E_{\text{target}}(a,b)\right)^2}
]

[
\varepsilon_E^{\text{post}}
===========================

\sqrt{\frac{1}{N}\sum_{a,b}\left(E_{\text{post}}(a,b)-E_{\text{target}}(a,b)\right)^2}
]

---

# Closure families to ablate

These are ordered from “most cleanup-like” to “most measurement-law-like.”

## C0 — No closure

After latch, do nothing further.

Purpose:
baseline for whether the detector race already contains the Bell structure.

Expected meaning:
if this already gives target-like outcomes, closure is probably secondary.

---

## C1 — Pure passive drain

Winner branch drains residual energy from its own local residual path only.
No cross-branch suppression beyond ordinary loading.

Interpretation:
engineering cleanup, minimally invasive.

---

## C2 — Local loser suppression

Once a winner is latched, only branches on that same local side are suppressed strongly.
No explicit global/common-mode coupling.

Interpretation:
still mostly local cleanup.

---

## C3 — Symmetric global drain

Winner triggers a shared closure path that drains the whole residual shared state symmetrically.
All losers are suppressed through a common path.

Interpretation:
global cleanup with symmetry, possible joint-measurement flavor.

---

## C4 — Common-mode / zero-sequence closure

Winner activates a physically shared common-mode or zero-sequence path that alters the residual network state after detection.

Interpretation:
explicitly shared closure mechanism; plausible place where joint enforcement may live.

---

## C5 — Competitive joint closure

Closure acts as a joint constraint among all four branches, enforcing exclusivity via shared competition.
This is the most “active measurement law” family.

Interpretation:
if Bell-like structure appears only here, closure is doing the substantive work.

---

## C6 — Delayed closure

Closure same as C3/C4/C5, but activated after a tunable delay (\tau_c).

Interpretation:
tests whether Bell-relevant structure depends on immediate closure or survives if closure is postponed.

---

# Parameter sweeps within each family

Each closure family should be swept over the same small set of normalized parameters.

## Sweep axes

* closure strength (g_c)
* closure onset delay (\tau_c)
* loser suppression time constant (\tau_s)
* residual drain impedance / coupling (Z_c) or equivalent
* symmetry mismatch (\delta_c) between branches
* optional noise/jitter in closure onset

Use dimensionless normalized forms where possible.

Example sweep grid:

* (g_c \in {0, 0.25, 0.5, 1, 2, 4})
* (\tau_c/T_0 \in {0, 0.05, 0.1, 0.25, 0.5})
* (\delta_c \in {0, 0.01, 0.05, 0.1})

where (T_0) is the characteristic front-end oscillation period or detector race timescale.

---

# Ablation matrix template

Use one row per closure family plus parameter regime.

| ID   |         Closure family | (g_c) | (\tau_c) | symmetry mismatch (\delta_c) | (S_{\text{pre}}) | (S_{\text{post}}) | (\Delta S) | (f_{\text{flip}}) | (\varepsilon_E^{\text{pre}}) | (\varepsilon_E^{\text{post}}) | (\Delta_{A,\max}^{\text{pre}}) | (\Delta_{A,\max}^{\text{post}}) | (\Delta_{B,\max}^{\text{pre}}) | (\Delta_{B,\max}^{\text{post}}) | interpretation    |
| ---- | ---------------------: | ----: | -------: | ---------------------------: | ---------------: | ----------------: | ---------: | ----------------: | ---------------------------: | ----------------------------: | -----------------------------: | ------------------------------: | -----------------------------: | ------------------------------: | ----------------- |
| C0-1 |                   none |     0 |      n/a |                            0 |                  |                   |            |                   |                              |                               |                                |                                 |                                |                                 | baseline          |
| C1-1 |          passive drain |   0.5 |        0 |                            0 |                  |                   |            |                   |                              |                               |                                |                                 |                                |                                 | cleanup test      |
| C2-1 |      local suppression |   1.0 |        0 |                            0 |                  |                   |            |                   |                              |                               |                                |                                 |                                |                                 | local enforcement |
| C3-1 | symmetric global drain |   1.0 |        0 |                            0 |                  |                   |            |                   |                              |                               |                                |                                 |                                |                                 | shared cleanup    |
| C4-1 |    common-mode closure |   1.0 |        0 |                            0 |                  |                   |            |                   |                              |                               |                                |                                 |                                |                                 | shared constraint |
| C5-1 |          joint closure |   1.0 |        0 |                            0 |                  |                   |            |                   |                              |                               |                                |                                 |                                |                                 | active law        |
| C6-1 |  delayed joint closure |   1.0 | 0.1T(_0) |                            0 |                  |                   |            |                   |                              |                               |                                |                                 |                                |                                 | timing test       |

Useful derived column:

[
\Delta S = S_{\text{post}}-S_{\text{pre}}
]

---

# Decision logic

This is the main point of the ablation.

## Signature of “closure is just cleanup”

You would expect:

* (S_{\text{pre}} \approx S_{\text{post}})
* (\Delta S) small across closure families
* (f_{\text{flip}}) very small
* no-signaling deviations similar before and after closure
* correlator shape error nearly unchanged
* closure details mainly affect timing and residual energy, not outcome law

Operational criterion:

[
|S_{\text{post}}-S_{\text{pre}}| \ll 1
\quad\text{and}\quad
f_{\text{flip}} \ll 1
]

across a wide closure parameter range.

---

## Signature of “closure carries the Bell-relevant structure”

You would expect:

* (S_{\text{pre}}) much weaker than (S_{\text{post}})
* (\Delta S) substantial for some closure families
* (f_{\text{flip}}) non-negligible
* no-signaling may improve only after symmetric/global closure
* correlator shape may become target-like only post-closure
* local closures fail while joint/global closures succeed

Operational criterion:

[
S_{\text{post}} - S_{\text{pre}}
\text{ is large and systematic}
]

especially if only shared/joint closure families achieve the target.

---

## Signature of “closure breaks the model”

You would expect:

* large winner-flip rates with unstable or noisy CHSH
* strong dependence of marginals on remote setting
* fragile tuning where only one narrow parameter pocket works
* high sensitivity to asymmetry mismatch (\delta_c)

That would mean closure is neither innocent cleanup nor a robust physical law, but a brittle patch.

---

# Minimal experiment set

To keep this manageable, start with three nested test tiers.

## Tier 1 — CHSH settings only

Use just one canonical CHSH angle set.
Fast, good for quick comparison.

Metrics:

* (S_{\text{pre}})
* (S_{\text{post}})
* (f_{\text{flip}})
* local marginals

## Tier 2 — angular sweep

Use a full grid, e.g. every (11.25^\circ) or (22.5^\circ).

Metrics:

* full (E_{\text{pre}}(a,b)), (E_{\text{post}}(a,b))
* RMS error to (-\cos 2(a-b))
* max no-signaling deviation

## Tier 3 — stress tests

Repeat Tier 1 and 2 under:

* one side open
* one side dump-loaded
* asymmetric detector delays
* delayed-choice switching
* closure mismatch (\delta_c > 0)

This is where you see whether closure is just housekeeping or is the actual mechanism.

---

# Additional per-trial logging

For later forensic analysis, save these fields per trial:

* trial id
* state label / seed
* analyzer settings (a,b)
* branch weights (w_{++},w_{+-},w_{-+},w_{--})
* detector hazard parameters
* pre-closure first-hit branch
* first-hit time
* latched branch
* closure family id
* closure parameters
* post-closure final branch
* closure activation time
* whether winner changed
* residual energy before closure
* residual energy after closure

That lets you trace exactly how closure changes outcomes.

---

# Best summary plots

These will tell the story fast.

## Plot 1

(S_{\text{pre}}) and (S_{\text{post}}) versus closure family / closure strength.

## Plot 2

Winner-flip fraction (f_{\text{flip}}) versus closure family / closure strength.

## Plot 3

Heatmaps of (E_{\text{pre}}(a,b)) and (E_{\text{post}}(a,b)).

## Plot 4

No-signaling deviation versus closure family.

## Plot 5

Scatter of (f_{\text{flip}}) versus (\Delta S).

That last one is especially useful:
if larger CHSH improvement comes only with more flips, closure is actively shaping the law.

---

# A compact pass/fail rubric

## Pass for “cleanup only”

* (f_{\text{flip}} < 10^{-3}) or similarly tiny
* (|\Delta S| < 0.02) across reasonable closure parameter range
* no-signaling metrics unchanged within Monte Carlo error
* target correlator already present pre-closure

## Pass for “closure is substantive but robust”

* shared/joint closure families consistently improve (S) and correlator shape
* no-signaling remains good
* results are stable over a moderate parameter range
* local-only closure families clearly fail

## Fail / red flag

* only one highly tuned closure parameter set works
* large remote-setting dependence in marginals
* CHSH improvement comes with obvious signaling or heavy asymmetry sensitivity
* closure must frequently rewrite winners in a fragile way

---

# My expectation of likely outcome

My guess is you will find three regimes:

1. **No closure / weak local closure**
   Good branch weights, decent race fidelity, but incomplete final Bell structure.

2. **Symmetric shared closure**
   Strongest candidate for robust Bell-like behavior with acceptable marginals.

3. **Overstrong active closure**
   Can force the right answer, but starts to look brittle, tuned, or effectively hard-coded.

That middle regime is probably what you want.

---

# The central scientific question this matrix answers

After you run this, you should be able to say one of the following:

* “The Bell-like structure is already present before closure; closure is just engineering cleanup.”
* “The Bell-like structure emerges only when a shared symmetric closure is present; closure is part of the measurement law.”
* “The apparent success depends on a fragile active closure; this is not yet a convincing physical mechanism.”

That is the real payoff of the ablation.

---
Below is a coder-ready implementation contract for the closure ablation program.

# Objective

Implement a reproducible ablation harness that holds constant:

* shared-state preparation
* analyzer mapping
* front-end joint branch-weight computation
* detector-cell race model
* winner latch

and varies only:

* closure family
* closure parameters

The harness must compute, save, and validate:

* pre-closure joint outcome statistics
* post-closure joint outcome statistics
* CHSH before and after closure
* local marginals before and after closure
* no-signaling deviations before and after closure
* winner-flip rates
* target-law error before and after closure

The purpose is to determine whether closure is:

* merely cleanup,
* an active part of the measurement law,
* or a brittle tuned patch.

---

# Required package layout

```text
src/
  closure_ablation/
    __init__.py
    config.py
    angle_sets.py
    state_model.py
    frontend.py
    detector.py
    latch.py
    closure_models.py
    trial.py
    metrics.py
    runner.py
    io.py
    plots.py
    cli.py

tests/
  test_smoke.py
  test_schema.py
  test_probabilities.py
  test_metrics.py
  test_closure_invariance.py
  test_ablation_matrix.py
```

---

# Core abstractions

## 1. TrialConfig

```python
from dataclasses import dataclass
from typing import Literal, Optional

ClosureFamily = Literal[
    "none",
    "passive_drain",
    "local_suppression",
    "symmetric_global_drain",
    "common_mode_closure",
    "competitive_joint_closure",
    "delayed_joint_closure",
]

@dataclass(frozen=True)
class TrialConfig:
    angle_a_deg: float
    angle_b_deg: float
    closure_family: ClosureFamily
    closure_strength: float
    closure_delay_s: float
    closure_suppression_tau_s: float
    closure_impedance_ohm: float
    closure_symmetry_mismatch: float
    detector_seed: int
    state_seed: int
```

## 2. Front-end result

This is the fixed upstream joint branch-weight computation.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class FrontendResult:
    w_pp: float
    w_pm: float
    w_mp: float
    w_mm: float

    def as_dict(self) -> dict[str, float]: ...
    def normalized(self) -> "FrontendResult": ...
```

Acceptance rule:

* all weights finite and nonnegative
* normalization sum > 0
* normalized sum = 1 within tolerance

## 3. Detector race result

```python
from dataclasses import dataclass
from typing import Literal

JointBranch = Literal["++", "+-", "-+", "--"]

@dataclass(frozen=True)
class DetectorRaceResult:
    pre_branch: JointBranch
    pre_hit_time_s: float
    hazard_pp: float
    hazard_pm: float
    hazard_mp: float
    hazard_mm: float
    pulse_count_pp: int
    pulse_count_pm: int
    pulse_count_mp: int
    pulse_count_mm: int
```

## 4. Latch result

```python
@dataclass(frozen=True)
class LatchResult:
    latched_branch: JointBranch
    latch_time_s: float
    exclusivity_ok: bool
```

## 5. Closure result

```python
@dataclass(frozen=True)
class ClosureResult:
    post_branch: JointBranch
    closure_activated: bool
    closure_activation_time_s: float | None
    winner_flipped: bool
    residual_energy_pre_j: float
    residual_energy_post_j: float
```

## 6. Full trial record

```python
@dataclass(frozen=True)
class TrialResult:
    trial_id: int
    angle_a_deg: float
    angle_b_deg: float
    closure_family: str
    closure_strength: float
    closure_delay_s: float
    closure_suppression_tau_s: float
    closure_impedance_ohm: float
    closure_symmetry_mismatch: float
    state_seed: int
    detector_seed: int

    w_pp: float
    w_pm: float
    w_mp: float
    w_mm: float

    hazard_pp: float
    hazard_pm: float
    hazard_mp: float
    hazard_mm: float

    pre_branch: str
    pre_hit_time_s: float
    latched_branch: str
    latch_time_s: float
    exclusivity_ok: bool

    closure_activated: bool
    closure_activation_time_s: float | None
    post_branch: str
    winner_flipped: bool
    residual_energy_pre_j: float
    residual_energy_post_j: float
```

---

# Required public function names

## angle_sets.py

```python
def get_default_chsh_angles_deg() -> dict[str, float]:
    """
    Returns:
        {"a0": 0.0, "a1": 45.0, "b0": 22.5, "b1": 67.5}
    """
```

```python
def get_angular_grid_deg(step_deg: float = 22.5) -> list[tuple[float, float]]:
    """Return full (a, b) angle grid."""
```

## frontend.py

```python
def compute_joint_branch_weights(angle_a_deg: float, angle_b_deg: float, state_seed: int) -> FrontendResult:
    """
    Fixed front-end model.
    Must not depend on closure family or closure parameters.
    """
```

## detector.py

```python
def run_detector_race(weights: FrontendResult, detector_seed: int) -> DetectorRaceResult:
    """
    Rare-event detector race using the fixed detector model.
    """
```

## latch.py

```python
def apply_winner_latch(race: DetectorRaceResult) -> LatchResult:
    """
    Enforce first-arrival exclusivity.
    """
```

## closure_models.py

```python
def apply_closure(
    family: str,
    latched_branch: str,
    weights: FrontendResult,
    race: DetectorRaceResult,
    closure_strength: float,
    closure_delay_s: float,
    closure_suppression_tau_s: float,
    closure_impedance_ohm: float,
    closure_symmetry_mismatch: float,
) -> ClosureResult:
    """
    Apply one closure family with specified parameters.
    """
```

Also required:

```python
def list_closure_families() -> list[str]:
    """Return supported closure family names."""
```

## trial.py

```python
def run_trial(config: TrialConfig, trial_id: int) -> TrialResult:
    """
    Execute front-end -> detector -> latch -> closure for one trial.
    """
```

## metrics.py

```python
def joint_counts_from_trials(trials, outcome_layer: str) -> dict[tuple[float, float, str], int]:
    """
    outcome_layer in {"pre", "post"}
    keys are (angle_a_deg, angle_b_deg, branch)
    """
```

```python
def joint_probabilities_from_trials(trials, outcome_layer: str) -> dict[tuple[float, float, str], float]:
    """Normalized per-angle probabilities."""
```

```python
def correlator_from_probabilities(
    probs: dict[tuple[float, float, str], float]
) -> dict[tuple[float, float], float]:
    """
    E(a,b) = P++ + P-- - P+- - P-+
    """
```

```python
def chsh_from_correlator(
    correlator: dict[tuple[float, float], float],
    a0: float,
    a1: float,
    b0: float,
    b1: float,
) -> float:
    """Compute CHSH S."""
```

```python
def winner_flip_fraction(trials) -> float:
    """Fraction of trials with pre_branch != post_branch."""
```

```python
def conditional_winner_flip_rates(trials) -> dict[str, float]:
    """Flip rate conditioned on pre-branch."""
```

```python
def local_marginals_from_probabilities(
    probs: dict[tuple[float, float, str], float]
) -> dict[tuple[str, float, float], float]:
    """
    Keys:
      ("A+", a, b), ("A-", a, b), ("B+", a, b), ("B-", a, b)
    """
```

```python
def max_no_signaling_deviation(
    marginals: dict[tuple[str, float, float], float]
) -> dict[str, float]:
    """
    Returns:
      {
        "delta_A_max": ...,
        "delta_B_max": ...,
      }
    """
```

```python
def target_correlator(angle_a_deg: float, angle_b_deg: float) -> float:
    """Default target: -cos(2(a-b)) with degree input."""
```

```python
def rms_correlator_error(
    correlator: dict[tuple[float, float], float],
    angle_pairs: list[tuple[float, float]],
) -> float:
    """RMS error to target correlator."""
```

```python
def summarize_run(trials, angle_pairs, chsh_angles) -> dict[str, float | str]:
    """
    Return one summary row for a closure family + parameter point.
    Required keys listed below in CSV schema.
    """
```

## runner.py

```python
def run_ablation_cell(
    closure_family: str,
    closure_strength: float,
    closure_delay_s: float,
    closure_suppression_tau_s: float,
    closure_impedance_ohm: float,
    closure_symmetry_mismatch: float,
    angle_pairs: list[tuple[float, float]],
    trials_per_angle: int,
    base_state_seed: int,
    base_detector_seed: int,
) -> tuple[list[TrialResult], dict]:
    """
    Run one ablation matrix cell and return full trial records plus summary.
    """
```

```python
def run_ablation_matrix(
    output_dir: str,
    closure_families: list[str],
    closure_strengths: list[float],
    closure_delays_s: list[float],
    closure_suppression_taus_s: list[float],
    closure_impedances_ohm: list[float],
    closure_symmetry_mismatches: list[float],
    angle_pairs: list[tuple[float, float]],
    trials_per_angle: int,
    base_state_seed: int = 1000,
    base_detector_seed: int = 2000,
) -> None:
    """
    Generate all ablation outputs.
    """
```

## io.py

```python
def write_trial_records_csv(path: str, trials: list[TrialResult]) -> None: ...
def write_summary_csv(path: str, rows: list[dict]) -> None: ...
def write_run_manifest_json(path: str, manifest: dict) -> None: ...
```

## cli.py

Required CLI entrypoint:

```bash
python -m closure_ablation.cli run-ablation \
  --output-dir artifacts/closure_ablation/run_001 \
  --trials-per-angle 5000 \
  --angle-step-deg 22.5
```

Optional focused run:

```bash
python -m closure_ablation.cli run-cell \
  --output-dir artifacts/closure_ablation/debug_cell \
  --closure-family symmetric_global_drain \
  --closure-strength 1.0 \
  --closure-delay-s 0.0 \
  --closure-suppression-tau-s 1e-6 \
  --closure-impedance-ohm 1.0 \
  --closure-symmetry-mismatch 0.0 \
  --trials-per-angle 2000
```

---

# Exact CSV schemas

## 1. trial_records.csv

One row per trial.

Required columns in exact order:

```text
trial_id
angle_a_deg
angle_b_deg
closure_family
closure_strength
closure_delay_s
closure_suppression_tau_s
closure_impedance_ohm
closure_symmetry_mismatch
state_seed
detector_seed
w_pp
w_pm
w_mp
w_mm
hazard_pp
hazard_pm
hazard_mp
hazard_mm
pre_branch
pre_hit_time_s
latched_branch
latch_time_s
exclusivity_ok
closure_activated
closure_activation_time_s
post_branch
winner_flipped
residual_energy_pre_j
residual_energy_post_j
```

Column constraints:

* `pre_branch`, `latched_branch`, `post_branch` must be one of `++`, `+-`, `-+`, `--`
* `closure_family` must be one of supported family names
* `exclusivity_ok`, `closure_activated`, `winner_flipped` must be boolean
* all weights and hazards must be finite and >= 0
* residual energies finite and >= 0
* `residual_energy_post_j <= residual_energy_pre_j + tol`

## 2. summary.csv

One row per ablation cell.

Required columns in exact order:

```text
run_id
closure_family
closure_strength
closure_delay_s
closure_suppression_tau_s
closure_impedance_ohm
closure_symmetry_mismatch
n_trials_total
n_angle_pairs
trials_per_angle
s_pre
s_post
delta_s
flip_fraction
flip_fraction_pp
flip_fraction_pm
flip_fraction_mp
flip_fraction_mm
rms_error_pre
rms_error_post
delta_A_max_pre
delta_A_max_post
delta_B_max_pre
delta_B_max_post
mean_residual_energy_pre_j
mean_residual_energy_post_j
closure_activation_fraction
interpretation_hint
```

Definitions:

* `delta_s = s_post - s_pre`
* `flip_fraction_*` are conditional on pre-branch
* `interpretation_hint` is a machine-generated label from simple rules:

  * `cleanup_like`
  * `closure_substantive`
  * `fragile_or_signaling`
  * `undetermined`

## 3. run_manifest.json

Required top-level keys:

```json
{
  "run_id": "string",
  "package_version": "string",
  "timestamp_utc": "string",
  "closure_families": ["..."],
  "closure_strengths": [0.0, 0.25, 0.5],
  "closure_delays_s": [0.0, 1e-7],
  "closure_suppression_taus_s": [1e-6],
  "closure_impedances_ohm": [1.0],
  "closure_symmetry_mismatches": [0.0, 0.01],
  "angle_pairs": [[0.0, 22.5], [45.0, 67.5]],
  "trials_per_angle": 5000,
  "base_state_seed": 1000,
  "base_detector_seed": 2000
}
```

---

# Closure-family behavioral requirements

These are contract-level, not physics-final.

## none

* must not change winner
* `closure_activated` must be `False`
* `post_branch == latched_branch`

## passive_drain

* may reduce residual energy
* should not directly rewrite winner except through explicitly modeled residual interaction
* expected low flip rate

## local_suppression

* suppression may only depend on latched branch and same-side local channels
* no explicit shared/global coupling term permitted in implementation

## symmetric_global_drain

* must apply symmetric shared drain to all nonwinning residual paths
* no branch-specific asymmetry unless injected through `closure_symmetry_mismatch`

## common_mode_closure

* must include an explicitly shared closure pathway
* implementation may reference common-mode/zero-sequence surrogate state

## competitive_joint_closure

* may implement joint branch competition at closure stage
* must remain symmetric when `closure_symmetry_mismatch == 0`

## delayed_joint_closure

* same as competitive or global shared closure, but activation delayed by `closure_delay_s`
* if `closure_delay_s == 0`, behavior must reduce to corresponding immediate case

---

# Summary metric rules

## Pre/post probability layers

Pre layer:

* use `pre_branch`

Post layer:

* use `post_branch`

Both must be computed from the same trial set.

## No-signaling summary

For Alice:

* for each fixed `a`, compare all tested `b` values
* compute max absolute difference in `P(A=+|a,b)`

For Bob:

* symmetric definition

Return exact keys:

* `delta_A_max`
* `delta_B_max`

## Conditional flip rates

For each branch `xy`:

```python
flip_fraction_xy = (
    number of trials with pre_branch == xy and post_branch != xy
    /
    number of trials with pre_branch == xy
)
```

If denominator is zero:

* return `nan`
* do not crash

---

# Acceptance tests

## tests/test_schema.py

### test_trial_records_schema_columns

Verify CSV columns exactly match required order.

### test_summary_schema_columns

Verify summary columns exactly match required order.

### test_manifest_keys_present

Verify required top-level JSON keys exist.

---

## tests/test_probabilities.py

### test_frontend_weights_are_nonnegative

For several angles:

* all `w_* >= 0`
* all finite

### test_frontend_weights_normalize

For several angles:

* normalized weights sum to 1 within `1e-12`

### test_probability_mass_per_angle_sums_to_one_pre

Aggregate pre probabilities from a smoke run.
For each angle pair:

* sum over `++, +-, -+, --` equals 1 within `1e-10`

### test_probability_mass_per_angle_sums_to_one_post

Same for post probabilities.

---

## tests/test_metrics.py

### test_correlator_bounds

For any valid probability table:

* `-1.0 - tol <= E(a,b) <= 1.0 + tol`

### test_chsh_finite

Computed `S_pre` and `S_post` must be finite.

### test_flip_fraction_bounds

* `0 <= flip_fraction <= 1`

### test_no_signaling_deviation_nonnegative

* `delta_A_max >= 0`
* `delta_B_max >= 0`

---

## tests/test_closure_invariance.py

### test_none_closure_never_flips_winner

Run a smoke set with family `none`.
Require:

* `winner_flipped` never true
* `post_branch == latched_branch` for all trials

### test_none_closure_never_activates

Require `closure_activated` false for all trials.

### test_delayed_closure_zero_delay_reduces_to_immediate_case

Using same seeds and same parameter point:

* delayed family with `closure_delay_s = 0`
* immediate counterpart
  Require exact equality of `post_branch` and key closure outputs for all trials.

### test_symmetric_global_drain_respects_zero_mismatch_symmetry

With `closure_symmetry_mismatch = 0` and symmetric conditions:

* branch relabel permutations should not change summary metrics beyond Monte Carlo tolerance

---

## tests/test_ablation_matrix.py

### test_run_ablation_cell_produces_outputs

Run one cell.
Require:

* nonempty trial records
* one summary dict
* expected keys present

### test_run_ablation_matrix_writes_files

Run tiny matrix.
Require output files:

* `trial_records.csv`
* `summary.csv`
* `run_manifest.json`

### test_summary_delta_s_consistency

For each summary row:

* `delta_s == s_post - s_pre` within `1e-12`

### test_summary_flip_fraction_consistency

Recompute from trial records and compare to summary value within `1e-12`

### test_summary_residual_energy_monotone

Require:

* `mean_residual_energy_post_j <= mean_residual_energy_pre_j + 1e-12`

---

# Physics-facing acceptance criteria

These are not universal truths; they are the contract for the current ablation program.

## Smoke acceptance

For a minimal smoke run:

* code executes end-to-end without error
* all schemas valid
* all probabilities normalize
* all summary metrics finite where defined

## Cleanup-like signature acceptance

If family is `none`, then:

* `flip_fraction == 0`
* `s_pre == s_post` within `1e-12`
* `rms_error_pre == rms_error_post` within `1e-12`
* `delta_A_max_pre == delta_A_max_post` within `1e-12`
* `delta_B_max_pre == delta_B_max_post` within `1e-12`

## Closure-substantive detection rule

`interpretation_hint = "closure_substantive"` if all hold:

* `abs(delta_s) >= 0.05`
* `flip_fraction >= 1e-3`
* `delta_A_max_post <= delta_A_max_pre + signaling_tol`
* `delta_B_max_post <= delta_B_max_pre + signaling_tol`

where recommended:

```python
signaling_tol = 0.01
```

## Fragile-or-signaling detection rule

`interpretation_hint = "fragile_or_signaling"` if either holds:

* `delta_A_max_post > 0.02`
* `delta_B_max_post > 0.02`
* or summary metrics change discontinuously across tiny parameter changes in dedicated robustness tests

## Cleanup-like detection rule

`interpretation_hint = "cleanup_like"` if all hold:

* `abs(delta_s) < 0.02`
* `flip_fraction < 1e-3`
* `abs(rms_error_post - rms_error_pre) < 0.02`

Else:

* `interpretation_hint = "undetermined"`

---

# Recommended default run grid

For first real run:

```python
closure_families = [
    "none",
    "passive_drain",
    "local_suppression",
    "symmetric_global_drain",
    "common_mode_closure",
    "competitive_joint_closure",
    "delayed_joint_closure",
]

closure_strengths = [0.0, 0.25, 0.5, 1.0, 2.0]
closure_delays_s = [0.0, 1e-8, 1e-7]
closure_suppression_taus_s = [1e-8, 1e-7]
closure_impedances_ohm = [0.5, 1.0, 2.0]
closure_symmetry_mismatches = [0.0, 0.01, 0.05]
angle_pairs = get_angular_grid_deg(step_deg=22.5)
trials_per_angle = 5000
```

Smoke grid:

```python
closure_families = ["none", "symmetric_global_drain", "competitive_joint_closure"]
closure_strengths = [0.0, 1.0]
closure_delays_s = [0.0]
closure_suppression_taus_s = [1e-7]
closure_impedances_ohm = [1.0]
closure_symmetry_mismatches = [0.0]
angle_pairs = get_angular_grid_deg(step_deg=45.0)
trials_per_angle = 200
```

---

# Required artifact outputs

For each run directory:

```text
artifacts/closure_ablation/<run_id>/
  trial_records.csv
  summary.csv
  run_manifest.json
  plots/
    s_pre_vs_post.png
    flip_fraction_vs_family.png
    rms_error_pre_vs_post.png
    no_signaling_pre_vs_post.png
    correlator_pre_heatmap.png
    correlator_post_heatmap.png
```

Optional but recommended:

```text
  tables/
    per_angle_probabilities_pre.csv
    per_angle_probabilities_post.csv
    per_angle_correlator_pre.csv
    per_angle_correlator_post.csv
```

---

# Minimal implementation notes

1. The front end must be closure-independent.
   That is a hard contract. No closure parameter may leak upstream.

2. The detector model must be identical across all ablations.
   Same hazard law, same pulse model, same latching logic.

3. The closure layer must be the only changed component.

4. All Monte Carlo runs must be seed-reproducible.

5. Summary values must be fully recomputable from `trial_records.csv`.

---

# Suggested docstring for the package

```python
"""
closure_ablation

A reproducible ablation harness for testing whether post-latch closure is
(a) merely engineering cleanup, or
(b) an active contributor to Bell-relevant outcome statistics.

The harness holds fixed:
  - shared-state preparation
  - analyzer law
  - front-end branch-weight computation
  - detector race
  - winner latch

and varies only closure family and closure parameters.

Outputs include pre/post outcome probabilities, correlators, CHSH values,
marginals, no-signaling deviations, and winner-flip statistics.
"""
```

---

# Suggested first coding order

1. define dataclasses and schemas
2. implement `none` closure
3. implement trial runner
4. implement metrics and summary
5. get smoke tests passing
6. implement passive/local/global closures
7. implement delayed and competitive closures
8. add plots and full matrix runner

If you want, I’ll turn this into a `README.md` plus `pyproject.toml` and a full pytest skeleton next.
