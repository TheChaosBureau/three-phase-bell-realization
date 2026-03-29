# Python build spec: delayed-choice parity-closure rig

## 1. Goal

Implement a simulation package that models one trial of the system:

[
\text{Prep} \to \text{Hold} \to \text{Analyzers} \to \text{Parity Recombiner} \to \text{Closure / Branch Logic}
]

with explicit support for:

* delayed-choice analyzer settings
* held shared 4D state
* bilinear product recombination
* parity bus signals (S,O)
* sector competition
* branch competition
* single latched outcome per event
* sweeps over hidden phase and analyzer angles
* diagnostics and plots

The subsystem equations and signal names should match the earlier architecture exactly wherever possible .

---

# 2. Deliverable

A Python package, for example:

```text
delayed_choice_rig/
  __init__.py
  config.py
  types.py
  prep.py
  hold.py
  analyzers.py
  recombiner.py
  closure.py
  schedules.py
  trial.py
  stats.py
  plots.py
  experiments.py
  validation.py
  cli.py
tests/
  test_prep.py
  test_analyzers.py
  test_recombiner.py
  test_closure.py
  test_delayed_choice.py
  test_stats.py
```

Use:

* Python 3.12+
* numpy
* scipy
* matplotlib
* dataclasses
* pytest

No GPU requirement.

---

# 3. Design principles

## 3.1 Architectural separation

Keep these layers distinct:

1. prepared/held state
2. analyzer settings
3. continuous recombination signals
4. dynamic closure state
5. discrete latched event output

## 3.2 Delayed-choice compatibility

The simulation must support:

[
t_{\text{prep}} < t_{\text{hold}} < t_A, t_B < t_{\text{closure}}
]

where analyzer settings may change after the state is frozen and before closure begins.

## 3.3 Auditability

Every intermediate signal should be optionally recorded:

* held state coordinates
* analyzer outputs
* product channels
* parity buses
* square-law drives
* closure states
* latch times

## 3.4 Determinism

All runs must be reproducible from a seed.

---

# 4. Core mathematical model

## 4.1 Held state

Represent the shared held state as:

[
\mathbf{x}*H =
\begin{bmatrix}
X*{+\alpha}\
X_{+\beta}\
X_{-\alpha}\
X_{-\beta}
\end{bmatrix}
\in \mathbb{R}^4
]

The source-side hidden variables should minimally include:

* hidden phase (\theta)
* sign-lock choice (+j) or (-j)
* amplitude (A)

Optional later:

* gain mismatch
* quadrature error
* offsets
* hold droop parameters

---

## 4.2 Prep equations

For (X_- = +jX_+):

[
X_{+\alpha}=A\cos\theta,\quad
X_{+\beta}=A\sin\theta
]
[
X_{-\alpha}=-A\sin\theta,\quad
X_{-\beta}=A\cos\theta
]

For (X_- = -jX_+):

[
X_{-\alpha}=A\sin\theta,\quad
X_{-\beta}=-A\cos\theta
]

These match the earlier prep-board definition .

---

## 4.3 Analyzer equations

For Alice:

[
A_+ = \cos\phi_A,X_{+\alpha} + \sin\phi_A,X_{+\beta}
]
[
A_- = -\sin\phi_A,X_{-\alpha} + \cos\phi_A,X_{-\beta}
]

For Bob:

[
B_+ = \cos\phi_B,X_{+\alpha} + \sin\phi_B,X_{+\beta}
]
[
B_- = -\sin\phi_B,X_{-\alpha} + \cos\phi_B,X_{-\beta}
]

These must be implemented as pure functions of held state plus current setting .

---

## 4.4 Recombiner equations

[
X = A_+ B_+
]
[
Y = A_+ B_-
]
[
Z = A_- B_+
]
[
W = A_- B_-
]

[
S = X + W
]
[
O = Y - Z
]

Again, these are required exact signal names and equations .

---

## 4.5 Drive equations

Sector drives:

[
D_S = g_S S^2,\qquad
D_O = g_O O^2
]

Branch drives:

[
D_{++}=g_x X^2,\quad
D_{+-}=g_x Y^2,\quad
D_{-+}=g_x Z^2,\quad
D_{--}=g_x W^2
]

---

## 4.6 Closure dynamics

Minimum required model: ODE-based sector and branch competition.

Shared resource:
[
\dot R = -\mu_s sR - \mu_o oR
]

Sector states:
[
\dot s = \lambda_S D_S R - \eta_s s - \chi s o
]
[
\dot o = \lambda_O D_O R - \eta_o o - \chi s o
]

Branch states:
same-sector only when same-sector active:
[
\dot x_{++} = \sigma_S D_{++} s - \eta_x x_{++} - \chi_x x_{++}x_{--}
]
[
\dot x_{--} = \sigma_S D_{--} s - \eta_x x_{--} - \chi_x x_{++}x_{--}
]

opposite-sector only when opposite-sector active:
[
\dot x_{+-} = \sigma_O D_{+-} o - \eta_x x_{+-} - \chi_x x_{+-}x_{-+}
]
[
\dot x_{-+} = \sigma_O D_{-+} o - \eta_x x_{-+} - \chi_x x_{+-}x_{-+}
]

These are the default dynamics from the earlier closure sketch .

---

# 5. Data model

## 5.1 `types.py`

Define dataclasses.

### `HiddenState`

```python
@dataclass
class HiddenState:
    theta: float
    amplitude: float
    sign_lock: int   # +1 for +j, -1 for -j
```

### `HeldState`

```python
@dataclass
class HeldState:
    x_p_alpha: float
    x_p_beta: float
    x_m_alpha: float
    x_m_beta: float
```

### `AnalyzerSettings`

```python
@dataclass
class AnalyzerSettings:
    phi_a: float
    phi_b: float
```

### `AnalyzerOutputs`

```python
@dataclass
class AnalyzerOutputs:
    a_plus: float
    a_minus: float
    b_plus: float
    b_minus: float
```

### `RecombinerOutputs`

```python
@dataclass
class RecombinerOutputs:
    X: float
    Y: float
    Z: float
    W: float
    S: float
    O: float
```

### `DriveOutputs`

```python
@dataclass
class DriveOutputs:
    d_s: float
    d_o: float
    d_pp: float
    d_pm: float
    d_mp: float
    d_mm: float
```

### `ClosureState`

```python
@dataclass
class ClosureState:
    R: float
    s: float
    o: float
    x_pp: float
    x_mm: float
    x_pm: float
    x_mp: float
```

### `TrialOutcome`

```python
@dataclass
class TrialOutcome:
    label: str              # "++", "--", "+-", "-+"
    sector: str             # "same" or "opposite"
    latch_time: float
    branch_latch_time: float | None
    sector_latch_time: float | None
```

### `TrialTrace`

Contains arrays for all recorded internal signals over time.

---

# 6. Module responsibilities

## 6.1 `config.py`

Contain all tunable parameters.

### `ModelParams`

Must include:

* `g_s`, `g_o`, `g_x`
* `lambda_s`, `lambda_o`
* `eta_s`, `eta_o`, `eta_x`
* `chi_sector`, `chi_branch`
* `sigma_s`, `sigma_o`
* `sector_threshold`
* `branch_threshold`
* `t_prepare`
* `t_hold`
* `t_closure_start`
* `t_max`
* `dt`
* `record_trace`
* optional droop parameters
* optional mismatch parameters

---

## 6.2 `prep.py`

### Required functions

```python
def prepare_hidden_state(hidden: HiddenState) -> HeldState:
    """Map hidden variables to the 4D held state."""
```

```python
def sample_hidden_state(rng: np.random.Generator, params) -> HiddenState:
    """Draw theta, amplitude, sign_lock from configured distributions."""
```

Acceptance:

* exact equations for both sign-lock branches
* unit tests must verify norm and quadrature structure

---

## 6.3 `hold.py`

```python
def evolve_hold_state(state: HeldState, dt: float, params) -> HeldState:
    """Apply hold droop / drift over one timestep."""
```

```python
def freeze_state(state: HeldState) -> HeldState:
    """Return held copy of prepared state."""
```

Default initial version may implement ideal hold:

```python
return state
```

---

## 6.4 `schedules.py`

Need explicit delayed-choice scheduling.

```python
def phi_schedule_constant(phi: float):
    """Return callable phi(t)."""
```

```python
def phi_schedule_switch(t_switch: float, phi_before: float, phi_after: float):
    """Return callable phi(t) that switches at t_switch."""
```

```python
def sample_final_settings(t: float, phi_a_fn, phi_b_fn) -> AnalyzerSettings:
    """Sample settings at closure onset."""
```

The system must support setting changes after hold but before closure.

---

## 6.5 `analyzers.py`

```python
def project_alice(state: HeldState, phi_a: float) -> tuple[float, float]:
    """Return A_plus, A_minus."""
```

```python
def project_bob(state: HeldState, phi_b: float) -> tuple[float, float]:
    """Return B_plus, B_minus."""
```

```python
def project_both(state: HeldState, settings: AnalyzerSettings) -> AnalyzerOutputs:
    """Return all analyzer outputs."""
```

---

## 6.6 `recombiner.py`

```python
def recombine(outputs: AnalyzerOutputs) -> RecombinerOutputs:
    """Compute X,Y,Z,W,S,O."""
```

```python
def compute_drives(recomb: RecombinerOutputs, params) -> DriveOutputs:
    """Compute square-law sector and branch drives."""
```

Validation must include parity identities over angle sweeps.

---

## 6.7 `closure.py`

This is the core ODE and latch logic.

### Required functions

```python
def initial_closure_state(params) -> ClosureState:
    """Create zeroed closure state with configured initial R."""
```

```python
def closure_rhs(state: ClosureState, drives: DriveOutputs, params) -> ClosureState:
    """Return time derivatives of closure states."""
```

```python
def step_closure_euler(state: ClosureState, drives: DriveOutputs, dt: float, params) -> ClosureState:
    """Advance closure state one Euler step."""
```

Optional:

```python
def step_closure_rk4(...)
```

### Latch logic

```python
def detect_sector_latch(state: ClosureState, params) -> str | None:
    """Return 'same', 'opposite', or None."""
```

```python
def detect_branch_latch(state: ClosureState, sector: str, params) -> str | None:
    """Return '++', '--', '+-', '-+', or None."""
```

```python
def run_closure_until_latch(drives: DriveOutputs, params) -> tuple[TrialOutcome, TrialTrace | None]:
    """Integrate closure dynamics until a valid branch latch occurs or timeout."""
```

Rules:

* only one sector may win
* only one branch may win
* if multiple thresholds cross simultaneously within tolerance, flag ambiguous event
* ambiguous events must be recorded distinctly, not silently discarded

---

## 6.8 `trial.py`

Main orchestration.

```python
def run_trial(
    hidden: HiddenState,
    phi_a_fn,
    phi_b_fn,
    params,
    rng: np.random.Generator | None = None,
) -> tuple[TrialOutcome, TrialTrace | None]:
    """Run one complete delayed-choice trial."""
```

Sequence:

1. prepare state
2. freeze/hold
3. evolve hold until closure start
4. sample final analyzer settings at closure start
5. compute analyzer outputs
6. recombine
7. compute drives
8. integrate closure
9. return outcome and optional trace

Also provide:

```python
def run_many_trials(...)
```

---

## 6.9 `stats.py`

Compute:

* counts of (++, --, +-, -+)
* sector frequencies
* marginals (P(A=+), P(B=+))
* correlator
  [
  E = P_{++}+P_{--}-P_{+-}-P_{-+}
  ]
* CHSH quantity for angle sets
* no-signaling-style marginal checks across Bob/Alice settings

Functions:

```python
def correlator(counts: dict[str, int]) -> float:
    ...
```

```python
def marginal_probs(counts: dict[str, int]) -> dict[str, float]:
    ...
```

```python
def chsh(E_ab, E_abp, E_apb, E_apbp) -> float:
    ...
```

---

## 6.10 `validation.py`

Must contain formal checks.

```python
def validate_prep_manifold(...)
def validate_recombiner_trig_identity(...)
def validate_delayed_choice_independence(...)
def validate_one_hot_outcomes(...)
def validate_balanced_marginals(...)
```

These should be callable from tests and CLI.

---

## 6.11 `plots.py`

Support:

* time traces for one trial
* heatmaps over ((\phi_A,\phi_B))
* hidden-phase dependence
* parity bus curves (S,O)
* sector frequencies
* branch frequencies
* correlator grid

---

## 6.12 `experiments.py`

Predefined experiment runners.

Examples:

```python
def experiment_recombiner_sweep(...)
def experiment_delayed_choice_switch(...)
def experiment_correlation_grid(...)
def experiment_hidden_phase_scan(...)
```

---

## 6.13 `cli.py`

Simple command line entry points.

Examples:

```bash
python -m delayed_choice_rig.cli recombiner-sweep
python -m delayed_choice_rig.cli one-trial --phi-a 0 --phi-b 0.785398
python -m delayed_choice_rig.cli delayed-choice-demo
python -m delayed_choice_rig.cli chsh-grid
```

---

# 7. Required behaviors

## 7.1 Ideal recombiner verification

For the ideal prepared manifold, sweeping (\Delta=\phi_A-\phi_B) should show:

[
S \propto \cos\Delta,\qquad O \propto \sin\Delta
]

up to the configured amplitude scaling, matching the earlier expected identity .

## 7.2 Delayed-choice behavior

Changing (\phi_A,\phi_B) after hold but before closure must change the outcome distribution according to the final sampled settings.

The held state itself must remain unchanged by those setting changes.

## 7.3 One-hot event logic

Each non-ambiguous trial must produce exactly one of:

* `++`
* `--`
* `+-`
* `-+`

## 7.4 Timeout handling

If no valid sector and branch latch occurs before `t_max`, return a timeout status.

## 7.5 Ambiguity handling

If sector or branch latch is not uniquely resolved, return a structured ambiguous status. Do not coerce to a normal outcome.

---

# 8. Test suite requirements

## 8.1 `test_prep.py`

* verify sign-lock branches
* verify quadrature relations
* verify amplitude preservation

## 8.2 `test_analyzers.py`

* verify projections against known hand-computed cases
* verify angle periodicity

## 8.3 `test_recombiner.py`

* verify exact algebra for (X,Y,Z,W,S,O)
* verify (S,O) trigonometric dependence on (\Delta) for ideal states

## 8.4 `test_closure.py`

* verify closure state dimensions
* verify one-hot behavior in clear winner cases
* verify ambiguity detection

## 8.5 `test_delayed_choice.py`

* hold state frozen at (t_1)
* switch setting at (t_s) with (t_1 < t_s < t_c)
* confirm outputs match final settings at (t_c), not old settings
* confirm held state unchanged by switch

## 8.6 `test_stats.py`

* correlator formula
* marginals
* CHSH calculation

---

# 9. First implementation milestone

The coder should implement in this order:

## Milestone 1

Static ideal pipeline without closure ODE:

* prep
* analyzer projections
* recombiner
* drive computation
* plots of (S,O) vs (\Delta)

## Milestone 2

Ideal closure ODE with constant settings:

* sector/branch competition
* one-hot latching
* single-trial traces

## Milestone 3

Delayed-choice scheduling:

* setting switches after hold
* closure samples final settings only
* validation tests

## Milestone 4

Batch statistics:

* counts
* correlator grid
* marginals
* CHSH support

## Milestone 5

Nonidealities:

* droop
* gain errors
* threshold jitter
* timing jitter
* mismatch sweeps

---

# 10. Output artifacts expected from coder

At minimum, the coder should produce:

1. package code
2. pytest suite
3. one example notebook or script
4. generated plots:

   * `recombiner_sweep.png`
   * `delayed_choice_demo.png`
   * `correlator_grid.png`
   * `single_trial_trace.png`
5. short README explaining model and entry points

---

# 11. Non-goals for first version

Do **not** attempt in v1:

* SPICE integration
* transistor/op-amp realism
* noise-heavy analog device models
* passive-only enforcement
* automatic Bell-foundation claims

This first version is a **system-level truth model**.

---

# 12. Acceptance criteria

The handoff is complete when:

* all core equations are implemented exactly as specified
* delayed-choice scheduling works
* recombiner identities validate numerically
* closure produces structured one-hot outcomes
* batch runs produce marginals/correlators
* tests pass
* traces and plots are available from CLI or example script

---

# 13. Minimal README statement for coder

The package simulates a delayed-choice-compatible shared-state measurement architecture with four held state coordinates, analyzer-angle projections, bilinear parity recombination, and nonlinear closure logic that latches one of four branch outcomes. Equations and signal names should follow the architecture in the provided subsystem sketch exactly where possible. 