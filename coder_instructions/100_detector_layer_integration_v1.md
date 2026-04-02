# Coder spec: detector-layer integration v1

## Goal

Build a simulation package that takes branch weights from the existing linear front-end and tests whether the detector layer turns them into correct one-click outcome statistics.

This step should answer:

> given target branch weights (w_i) or (w_{xy}), does the detector layer produce winner frequencies matching those weights?

## Reuse from existing work

Reuse as-is:

* reduced 2-branch / 4-branch weight generation
* detector search harness
* `shot_trigger` model
* benchmark `poisson_linear`
* race-law metrics
* mismatch sensitivity tooling

Do **not** rewrite these.

## New deliverable

One integrated package, for example:

```text
detector_integration/
├── frontends/
│   ├── two_branch.py
│   └── four_branch.py
├── detectors/
│   ├── shot_trigger_adapter.py
│   └── closure_latch.py
├── sim/
│   ├── run_two_branch_integration.py
│   ├── run_four_branch_integration.py
│   └── metrics.py
├── experiments/
│   ├── sweep_two_branch_states.py
│   ├── sweep_four_branch_angles.py
│   └── compare_with_exact.py
└── test_detector_integration.py
```

---

# 1. Front-end interfaces

## 1.1 Two-branch front-end

Input:

* prepared 2-mode state (a\in\mathbb C^2)
* analyzer angle or basis (u_1,u_2)

Output:

* branch weights
  [
  w_1=|u_1^\dagger a|^2,\qquad w_2=|u_2^\dagger a|^2
  ]

Required function:

```python
def two_branch_weights(state: np.ndarray, analyzer) -> np.ndarray:
    """Return np.array([w1, w2]) with sum 1."""
```

## 1.2 Four-branch front-end

Input:

* shared 4-mode state (\Psi_0\in\mathbb C^4)
* analyzer settings (a,b)

Output:

* joint weights
  [
  w_{xy}(a,b)=|c_{xy}(a,b)|^2
  ]

Required function:

```python
def four_branch_weights(state4: np.ndarray, a_deg: float, b_deg: float) -> np.ndarray:
    """Return np.array([w_pp, w_pm, w_mp, w_mm]) with sum 1."""
```

---

# 2. Detector adapter

## 2.1 Required detector abstraction

Wrap the existing `shot_trigger` model so it can be driven by branch weights.

For branch (k), define absorbed-power envelope
[
P_k(t)=\Gamma(t),w_k
]

Minimal first version:

* use constant envelope (\Gamma(t)=P_0)
* later allow decaying envelope

Required function:

```python
def simulate_branch_nucleation(detector_params: dict, weight: float, envelope_params: dict, rng):
    """
    Return branch nucleation time or None.
    """
```

## 2.2 Required detector law to test

The integration package does **not** assume Born. It tests whether the calibrated detector behaves approximately like:
[
\lambda_k(t)\approx \lambda_{\text{dark}}+\alpha,\Gamma(t),w_k
]

---

# 3. Common closure latch

## 3.1 Role

Once one branch nucleates:

* declare winner
* suppress other branches
* stop the race
* optionally model post-click drain

This is a logic block, not a pre-click weight generator.

## 3.2 First implementation

Use the simplest latch:

* first nucleation event wins
* all others are ignored after that moment

Required function:

```python
def first_event_latch(event_times: np.ndarray) -> int:
    """
    Return winning branch index.
    Ignore all later events.
    """
```

## 3.3 Optional post-click model

Add a placeholder closure state (Z(t)) only after winner selection.

No need for pre-click zero-sequence feedback yet.

---

# 4. Simulation modes

## 4.1 Mode A — two-branch detector integration

Purpose:

* validate single-particle detector layer

Workflow:

1. generate (w_1,w_2) from state/analyzer
2. drive detector branches
3. first-click latch selects winner
4. repeat many trials
5. compare empirical winner frequencies to ([w_1,w_2])

Required driver:

```python
def run_two_branch_trials(state, analyzer, detector_params, n_trials, seed) -> dict:
    """
    Return exact weights, empirical frequencies, race metrics.
    """
```

## 4.2 Mode B — four-branch detector integration

Purpose:

* validate shared-state detector layer

Workflow:

1. generate (w_{++},w_{+-},w_{-+},w_{--})
2. drive four detector branches
3. first-click latch selects winner
4. repeat many trials
5. compare empirical frequencies to exact four-branch weights
6. compute correlator and CHSH from empirical outcome frequencies

Required driver:

```python
def run_four_branch_trials(state4, a_deg, b_deg, detector_params, n_trials, seed) -> dict:
    """
    Return exact weights, empirical frequencies, correlator, errors.
    """
```

---

# 5. Metrics

## 5.1 Two-branch metrics

For each run compute:

* exact weights
* empirical frequencies
* RMS error
* max absolute error
* winner-law error
  [
  \epsilon_{\text{race}}=\sqrt{\frac{1}{2}\sum_i(\hat p_i-w_i)^2}
  ]

## 5.2 Four-branch metrics

For each angle pair compute:

* exact (w_{xy})
* empirical (\hat p_{xy})
* RMS error over four branches
* correlator exact vs empirical
  [
  E = p_{++}-p_{+-}-p_{-+}+p_{--}
  ]

## 5.3 CHSH

For default settings
[
a_0=0^\circ,\ a_1=45^\circ,\ b_0=22.5^\circ,\ b_1=-22.5^\circ
]
compute empirical
[
S=E(a_0,b_0)+E(a_0,b_1)+E(a_1,b_0)-E(a_1,b_1)
]

Report:

* exact (S)
* empirical (S)
* absolute error

---

# 6. Required experiments

## Experiment 1 — two-branch sanity sweep

Sweep representative states:

* pole states
* equatorial states
* rotated analyzer angles

Acceptance:

* winner frequencies track (w_1,w_2) with RMS error below target

## Experiment 2 — four-branch angle sweep

Use singlet-like shared state and sweep ((a,b)).

Acceptance:

* four-branch empirical frequencies track exact (w_{xy}(a,b))

## Experiment 3 — correlator check

Verify empirical correlator matches target
[
E(a,b)=-\cos 2(a-b)
]
within tolerance.

## Experiment 4 — CHSH check

Verify empirical (|S|) is close to (2\sqrt2) within finite-sampling tolerance.

## Experiment 5 — mismatch robustness

Perturb detector parameters branch by branch:

* gain
* dark count
* dead time

Measure degradation in:

* branch-frequency accuracy
* correlator
* CHSH

---

# 7. Acceptance criteria

## Two-branch acceptance

Across benchmark states:

* RMS winner-law error < 0.02
* max winner-law error < 0.05

## Four-branch acceptance

Across benchmark angle pairs:

* RMS four-branch error < 0.03
* correlator error < 0.05

## CHSH acceptance

For default settings:

* empirical (|S|) within 0.1 of exact target in nominal runs

## Robustness acceptance

Under ±2% detector gain mismatch:

* no catastrophic bias
* race-law error increase remains bounded and reported

---

# 8. Non-goals for this step

Do **not** implement yet:

* SPICE
* physical tank-level netlists
* nonlinear pre-click closure feedback
* Kuramoto-style competition
* analog energy-drain dynamics after click, except as a placeholder

This step is only about:

* branch weights in
* detector race out

---

# 9. Outputs

Each experiment should write:

* JSON summary
* CSV summary
* plots

Required plots:

* exact vs empirical winner frequencies
* exact vs empirical four-branch weights
* correlator exact vs empirical
* CHSH exact vs empirical
* mismatch sensitivity curves

---

# 10. Suggested order of implementation

1. wire existing two-branch weights into detector race
2. verify two-branch integration still matches prior standalone detector results
3. wire four-branch reduced shared-state weights into detector race
4. compute empirical correlator and CHSH
5. add mismatch sweeps
6. only then decide whether to move to SPICE or closure dynamics

---

# 11. Minimal theorem this step is testing

This whole integration step is testing whether the practical detector model behaves like:

[
\lambda_k(t)\approx \lambda_{\text{dark}}+\alpha,\Gamma(t),w_k
]

If yes, then first-click latch should yield:

* two-branch:
  [
  P(k)\approx w_k
  ]

* four-branch:
  [
  P(x,y\mid a,b)\approx w_{xy}(a,b)
  ]

That is the exact bridge from the linear front-end to discrete outcomes.