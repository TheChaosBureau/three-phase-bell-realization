# Python search harness structure

## Goal

Search over detector-cell parameter space and rank candidate regimes by whether they satisfy:

1. rare-event operation
2. approximately linear
   [
   \lambda(P)\approx \lambda_{\text{dark}}+\alpha P
   ]
3. correct two-branch race law
   [
   P(\text{branch 1 wins})\approx \frac{P_1}{P_1+P_2}
   ]
4. robustness to mismatch

---

# 1. Repo / file structure

```text id="x59eoq"
detector_search/
├── config.py
├── models/
│   ├── base.py
│   ├── poisson_linear.py
│   ├── shot_trigger.py
│   ├── metastable_escape.py
│   └── accumulator_bad_control.py
├── sim/
│   ├── single_branch.py
│   ├── race.py
│   ├── metrics.py
│   └── search.py
├── experiments/
│   ├── run_rate_scan.py
│   ├── run_race_scan.py
│   └── run_global_search.py
├── plots.py
└── test_detector_search.py
```

---

# 2. Core abstraction

## `models/base.py`

You want one abstract interface all candidate detector models obey.

```python id="rs2mfo"
from dataclasses import dataclass
from typing import Any

@dataclass
class DetectorState:
    data: Any

class DetectorModel:
    name: str

    def reset(self, rng) -> DetectorState:
        raise NotImplementedError

    def step(self, state: DetectorState, P_abs: float, dt: float, rng):
        """
        Advance one timestep.

        Returns:
            new_state: DetectorState
            event: bool   # True if nucleation/click occurred this step
        """
        raise NotImplementedError

    def default_param_grid(self) -> dict:
        """Parameter ranges for search."""
        raise NotImplementedError
```

This lets you plug in multiple detector hypotheses without rewriting the harness.

---

# 3. Candidate models

## A. `poisson_linear.py`

This is the ideal benchmark.

Behavior:
[
\lambda(P)=\lambda_{\text{dark}}+\alpha P
]

No internal physics, just direct Bernoulli/Poisson triggering.

Use it as:

* a correctness baseline
* a check that the rest of the harness works

Parameters:

* `lambda_dark`
* `alpha`
* `dead_time`

---

## B. `shot_trigger.py`

This is the best physical candidate.

Interpretation:

* absorption opportunities arrive as Poisson micro-events at rate
  [
  r(P)=P/\varepsilon
  ]
* each micro-event triggers with probability (p_{\text{trig}})
* latch fires on first success

This naturally gives
[
\lambda(P)\approx \lambda_{\text{dark}}+\frac{p_{\text{trig}}}{\varepsilon}P
]

Parameters:

* `eps_event`
* `p_trig`
* `lambda_dark`
* `dead_time`

This is the model I would expect to win.

---

## C. `metastable_escape.py`

This is the more analog candidate.

Internal variable (x), maybe:
[
dx = [a + bP - cx]dt + \sigma dW
]
click when (x>x_{\text{th}}), then latch/reset.

Parameters:

* `bias`
* `gain_P`
* `leak`
* `sigma`
* `threshold`
* `reset_value`

This model might have a narrow linear regime, or fail.

---

## D. `accumulator_bad_control.py`

This is the known-bad control.

Something like:
[
dE = P,dt + \sigma dW
]
click at threshold.

You already know it distorts Born-like probabilities, but it is useful as a negative control to verify the harness can reject bad mechanisms.

---

# 4. Single-branch simulation layer

## `sim/single_branch.py`

Functions:

```python id="jfxfy2"
def simulate_single_trial(model, params, P_abs, dt, t_max, rng):
    """
    Run one trial until click or timeout.
    Returns click_time or None.
    """

def simulate_many_trials(model, params, P_abs, n_trials, dt, t_max, seed):
    """
    Returns click times, timeout count, estimated rate.
    """
```

### Outputs

For each power level:

* number of clicks
* click-rate estimate
* waiting times
* timeout fraction

---

# 5. Two-branch race simulation

## `sim/race.py`

Functions:

```python id="7y6qfy"
def simulate_two_branch_race(model, params1, params2, P1, P2, dt, t_max, rng):
    """
    Runs two matched or mismatched detector cells in parallel.
    Returns:
        winner in {1,2,0}
        t1, t2
    """

def simulate_many_races(model, params1, params2, P1, P2, n_trials, dt, t_max, seed):
    """
    Returns empirical winner frequencies.
    """
```

### Why this is essential

Single-branch linearity is not enough.
A model can have nice (\lambda(P)) but still fail in competitive first-click behavior because of:

* dead time interactions
* hidden pre-click memory
* mismatch amplification

---

# 6. Metrics layer

## `sim/metrics.py`

This is where you score a candidate.

### A. Rate-vs-power fit

```python id="do5g6o"
def fit_rate_vs_power(P_values, rate_values):
    """
    Fit lambda(P) = lambda_dark + alpha * P
    Returns fit params and residual metrics.
    """
```

Metrics:

* fitted `lambda_dark`
* fitted `alpha`
* RMS relative residual
* max relative residual

### B. Waiting-time Poisson-ness

```python id="gwm79v"
def waiting_time_metrics(click_times):
    """
    Compare waiting-time distribution to exponential.
    """
```

Metrics:

* mean, variance
* coefficient of variation
* KS distance to exponential fit

### C. Race-law error

For a set of power pairs ((P_1,P_2)), compare empirical winner probability to target:
[
p_1^\star = \frac{P_1}{P_1+P_2}
]

```python id="16x9za"
def race_error_metric(target_probs, empirical_probs):
    """
    RMS and max error over race tests.
    """
```

### D. Mismatch sensitivity

Perturb branch parameters by small amounts and rerun race tests.

Metric:

* worst-case deviation under ±1%, ±2%, ±5% mismatch

---

# 7. Search layer

## `sim/search.py`

This is the main engine.

### Parameter sampling

Use:

* grid search for tiny models
* Latin hypercube or random search for moderate models
* maybe Bayesian optimization later

Functions:

```python id="7guj7o"
def sample_param_sets(param_grid, n_samples, rng):
    """
    Draw candidate parameter sets.
    """

def evaluate_candidate(model, params, config):
    """
    Run all tests and return metrics + score.
    """

def rank_candidates(results):
    """
    Sort by composite score.
    """
```

---

# 8. Composite score

Each candidate gets a score.

For example:

[
\text{score}
============

w_{\text{lin}},\epsilon_{\text{lin}}
+
w_{\text{race}},\epsilon_{\text{race}}
+
w_{\text{dark}},\epsilon_{\text{dark}}
+
w_{\text{pois}},\epsilon_{\text{pois}}
+
w_{\text{rob}},\epsilon_{\text{rob}}
]

Where:

* (\epsilon_{\text{lin}}): linearity residual
* (\epsilon_{\text{race}}): two-branch race error
* (\epsilon_{\text{dark}}): dark-count penalty
* (\epsilon_{\text{pois}}): deviation from rare-event exponential waiting times
* (\epsilon_{\text{rob}}): mismatch sensitivity

Concrete implementation:

```python id="m37gw4"
def composite_score(m):
    return (
        3.0 * m["linearity_rms_rel"]
        + 4.0 * m["race_rms_error"]
        + 2.0 * m["dark_penalty"]
        + 1.5 * m["waiting_time_penalty"]
        + 3.0 * m["mismatch_penalty"]
    )
```

I’d weight race error highest.

---

# 9. Configuration

## `config.py`

```python id="y89bbm"
DT = 1e-4
T_MAX = 50.0
N_RATE_TRIALS = 2000
N_RACE_TRIALS = 5000

P_SCAN = [0.0, 0.1, 0.2, 0.5, 1.0, 2.0]
RACE_PAIRS = [
    (0.75, 0.25),
    (0.70, 0.30),
    (0.60, 0.40),
    (0.50, 0.50),
]

MISMATCH_LEVELS = [0.01, 0.02, 0.05]
SEED = 1234
```

---

# 10. Concrete evaluation flow

For one candidate parameter set:

## Step 1

Run dark-count test at (P=0)

Extract:

* `lambda_dark`

## Step 2

Run rate scan over `P_SCAN`

Extract:

* `alpha_fit`
* linearity residuals

## Step 3

Check waiting-time statistics for 2–3 representative powers

Extract:

* exponentiality score

## Step 4

Run two-branch races for `RACE_PAIRS`

Compare empirical:
[
P(\text{branch 1 wins})
]
to target:
[
\frac{P_1}{P_1+P_2}
]

Extract:

* race RMS error

## Step 5

Repeat race tests with mismatch perturbations

Extract:

* robustness penalty

## Step 6

Compute composite score and store result

---

# 11. Outputs to save

For each candidate:

* parameter set
* fitted `lambda_dark`
* fitted `alpha`
* linearity residuals
* waiting-time metrics
* race metrics
* mismatch sensitivity
* composite score

Save as:

* JSONL row
* CSV summary
* maybe pickled detail for top candidates

---

# 12. Plots

## `plots.py`

Make:

* (\lambda(P)) with fit line
* residual plot
* waiting-time histogram + exponential fit
* winner probability vs (P_1/(P_1+P_2))
* robustness curves under mismatch
* score histogram across candidates

These will tell you quickly which detector class is promising.

---

# 13. Minimal experiment scripts

## `experiments/run_rate_scan.py`

For one model + one parameter set:

* plot (\lambda(P))

## `experiments/run_race_scan.py`

For one model + one parameter set:

* run race tests over multiple power splits

## `experiments/run_global_search.py`

For one model family:

* sample many parameter sets
* evaluate
* rank
* save top 20 candidates

---

# 14. Example workflow

### Phase 1

Run benchmark model:

* `poisson_linear.py`
* verify harness gives near-zero race error

### Phase 2

Run bad control:

* `accumulator_bad_control.py`
* verify harness rejects it

### Phase 3

Run `shot_trigger.py`

* search for broad low-score regimes

### Phase 4

Run `metastable_escape.py`

* see whether a usable linear window exists or is too fragile

Then pick the winning family for circuit realization.

---

# 15. The single most important design choice

The search harness should be built around **race-law fidelity**, not just rate-linearity.

Because a detector can look linear in (\lambda(P)) and still fail the two-branch competition test.

So the top-level KPI should be:

[
\text{Does first-click winner frequency track } \frac{P_1}{P_1+P_2}\text{?}
]

That is the real detector-layer target.
