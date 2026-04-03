# Coder Spec: SPICE-Facing Linear Front-End Surrogate

## Objective

Implement a **physical/SPICE-facing surrogate of the linear front-end only**.

This phase must realize a front-end block that produces branch absorbed-power envelopes approximating

[
P_k(t)=\Gamma(t),w_k
]

where:

* (w_k) are the exact branch weights from the reduced front-end model,
* (\Gamma(t)) is a common envelope shared across branches.

The output of this front-end surrogate is **not** a click and **not** a latch state. It is only:

* branch voltages/currents,
* branch absorbed powers,
* branch integrated absorbed energies.

Those envelopes will then feed the already validated **abstract detector + winner latch** layer.

This preserves the architecture already frozen:

* linear front-end computes branch weights,
* detector generates rare-event pulses,
* latch enforces exclusivity.

---

## Scope

Included:

* SPICE-facing or SPICE-compatible linear front-end surrogate
* two-branch single-particle front-end surrogate
* four-branch shared-state front-end surrogate
* branch power/energy extraction
* exact-vs-surrogate comparison
* interface handoff to abstract detector+latch
* report and artifacts

Excluded:

* physical detector SPICE model
* physical latch SPICE model
* physical post-click drain/closure hardware
* nonlinear detector physics
* final multi-tank physical netlist unless needed for the surrogate

---

# 1. Design intent

## 1.1 Purpose of the surrogate

This phase is the bridge between:

* pure reduced-state math, and
* full physical circuit implementation.

The surrogate should answer:

> Can a linear physical/SPICE-facing front-end produce branch powers whose normalized energies match the target weights (w_k), so that the validated detector+latch abstraction can sit downstream unchanged?

## 1.2 Architectural boundary

The front-end surrogate ends at branch power export:

[
{P_k(t)}_{k}
]

The detector+latch begins at:

* branch absorbed-power envelope input
* branch pulse output
* exclusive winner output

So the front-end must provide a stable interface for later coupling to the frozen abstraction note.

---

# 2. Required models

## 2.1 Two-branch front-end surrogate

Implement a linear front-end for the single-particle / 2-mode case.

### Inputs

* prepared state (a\in\mathbb C^2)
* analyzer definition (u_1,u_2) or angle (\theta)
* optional common envelope choice

### Required target

Produce branch powers (P_1(t),P_2(t)) such that
[
P_1(t)\approx \Gamma(t),w_1,
\qquad
P_2(t)\approx \Gamma(t),w_2,
]
with
[
w_i=|u_i^\dagger a|^2.
]

### Required measurement outputs

* branch voltage waveforms
* branch current waveforms
* instantaneous powers (p_i(t))
* integrated absorbed energies
  [
  E_i^{(\infty)}=\int_0^\infty p_i(t),dt
  ]
* normalized energy fractions
  [
  f_i=\frac{E_i}{E_1+E_2}
  ]

### Acceptance

[
f_i \approx w_i
]
within tolerance.

---

## 2.2 Four-branch front-end surrogate

Implement a linear front-end for the shared 4-mode case.

### Inputs

* shared reduced state (\Psi_0\in\mathbb C^4)
* analyzer settings (a,b)
* optional common envelope choice

### Required target

Produce branch powers
[
P_{++}(t),P_{+-}(t),P_{-+}(t),P_{--}(t)
]
such that
[
P_k(t)\approx \Gamma(t),w_k
]
with
[
w_k = w_{xy}(a,b)=|c_{xy}(a,b)|^2.
]

### Required outputs

* branch voltages/currents
* instantaneous branch powers
* integrated absorbed energies (E_k^{(\infty)})
* normalized fractions
  [
  f_k=\frac{E_k}{\sum_j E_j}
  ]

### Acceptance

[
f_k \approx w_k
]
within tolerance.

---

# 3. Surrogate implementation options

The coder may choose either implementation path, but must document which one is used.

## Option A — SPICE-compatible behavioral surrogate

Use controlled sources / linear subcircuits to realize:

* branch amplitudes proportional to target projections,
* branch loads for absorbed-power measurement.

This is acceptable for the first pass.

## Option B — explicit resonant-envelope surrogate

Use a reduced linear state-space model
[
\dot x = Ax + Bu
]
or equivalent complex-envelope model, then export branch signals through a readout matrix.

This is also acceptable if the branch outputs can be interpreted as SPICE-facing ports.

### Preferred first pass

Start with **Option A** if it is faster and clearer.

The purpose of this phase is not yet to prove the exact hardware topology. It is to prove the front-end can be rendered in a circuit-facing form while preserving branch weights.

---

# 4. Required front-end interface

Each front-end implementation must export the same interface.

## 4.1 Data contract

For each run, export:

```python
{
    "branch_labels": [...],
    "time_s": [...],
    "branch_voltage_v": {label: [...]},
    "branch_current_a": {label: [...]},
    "branch_power_w": {label: [...]},
    "branch_energy_j": {label: float},
    "branch_energy_fraction": {label: float},
    "exact_weight": {label: float},
}
```

## 4.2 Detector-facing abstraction

Also export detector-facing branch envelopes:
[
P_k(t)
]
in a format that the validated detector+latch abstraction can consume directly.

---

# 5. Benchmark cases

## 5.1 Two-branch benchmarks

Use at minimum:

* pure pole state
* equatorial state
* rotated analyzer basis

For example:

* (a=[1,0]^T), (\theta=30^\circ)
* (a=[1,e^{j\phi}]^T/\sqrt2), selected (\phi), rotated analyzer

These are already established as reference cases for the single-delta analog.

## 5.2 Four-branch benchmarks

Use the singlet-like shared state and benchmark angles:

* (a=b=0^\circ)
* (a=45^\circ,;b=22.5^\circ)
* (a=0^\circ,;b=45^\circ)

Also include CHSH settings:
[
a_0=0^\circ,\quad a_1=45^\circ,\quad b_0=22.5^\circ,\quad b_1=-22.5^\circ
]

---

# 6. Acceptance criteria

## 6.1 Two-branch front-end

Across benchmark cases:

* RMS energy-fraction error < 0.02
* max energy-fraction error < 0.05

## 6.2 Four-branch front-end

Across benchmark cases:

* RMS weight error < 0.03
* max branch error < 0.05

## 6.3 Correlator preservation

From normalized surrogate branch energies,
[
E = f_{++}-f_{+-}-f_{-+}+f_{--}
]
must match the exact correlator with:

* RMS error < 0.05

## 6.4 CHSH preservation

Using surrogate branch energies only, compute empirical CHSH-like value from the benchmark settings.
Require:

* (|S|) within 0.1 of exact reduced-model target

---

# 7. Integration with detector+latch abstraction

After the front-end surrogate is validated alone, feed its branch envelopes into the already frozen detector+latch abstraction.

## Required step

For each benchmark case:

1. compute exact branch weights
2. run front-end surrogate
3. export branch powers (P_k(t))
4. feed those into abstract detector model
5. feed detector pulses into abstract latch
6. compare exclusive winner statistics to exact weights

## Acceptance

The integrated front-end-surrogate + abstract-detector+latch chain should remain close to the previously validated reduced integration performance.

---

# 8. Required artifacts

## Output directories

* `artifacts/front_end_surrogate/two_branch/`
* `artifacts/front_end_surrogate/four_branch/`
* `artifacts/front_end_surrogate/integration/`
* `artifacts/front_end_surrogate/spice_facing/`

## Required files

* `two_branch_summary.csv`
* `four_branch_summary.csv`
* `integration_summary.csv`
* `summary_report.md`
* `summary_metrics.json`
* `spice_facing_interface.md`

## Required plots

* exact vs surrogate branch fractions (two-branch)
* exact vs surrogate branch fractions (four-branch)
* correlator comparison
* CHSH comparison
* integrated winner-frequency comparison after detector+latch handoff

---

# 9. Required modules

Suggested package structure:

```text
front_end_surrogate/
├── two_branch_surrogate.py
├── four_branch_surrogate.py
├── export_interface.py
├── integration_adapter.py
├── metrics.py
├── plots.py
├── experiments/
│   ├── run_two_branch_surrogate.py
│   ├── run_four_branch_surrogate.py
│   ├── run_surrogate_integration.py
│   └── build_summary_report.py
└── test_front_end_surrogate.py
```

---

# 10. Tests

The coder must add tests for:

## Two-branch

* normalized fractions sum to 1
* surrogate fractions match exact weights

## Four-branch

* normalized fractions sum to 1
* surrogate fractions match exact (w_{xy})

## Integration

* detector adapter accepts exported branch envelopes
* end-to-end winner frequencies remain near exact branch weights

---

# 11. Explicit non-goals

Do **not** do any of the following in this ticket:

* physical detector SPICE modeling
* physical latch SPICE modeling
* post-click drain hardware
* zero-sequence closure hardware
* full multi-tank final netlist
* hardware interpretation claims beyond the surrogate boundary

This ticket is about the **linear front-end in circuit-facing form**, nothing beyond that.

---

# 12. Decision gate after this ticket

Proceed to the next phase only if:

1. the front-end surrogate reproduces the target branch weights/energies,
2. the front-end-surrogate + abstract detector+latch chain preserves winner-law fidelity,
3. the SPICE-facing interface is stable and documented.

If those pass, the next ticket should be:

**Design the first physical/SPICE front-end implementation candidate and connect it to the frozen detector+latch abstraction.**

---

# 13. Short rationale

This is the cleanest bridge because it preserves the architecture already established:

* front-end computes weights,
* detector generates clicks,
* latch enforces exclusivity.

It lets you move toward physical realization one boundary at a time, instead of trying to physicalize the entire chain at once.