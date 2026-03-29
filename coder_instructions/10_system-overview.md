# 1. System overview

Five boards:

[
\boxed{\text{Prep}}
\to
\boxed{\text{Hold}}
\to
\boxed{\text{Analyzers}}
\to
\boxed{\text{Parity Recombiner}}
\to
\boxed{\text{Closure / Branch Logic}}
]

Signals flow left to right.

---

# 2. Prep board

## Purpose

Generate the paired-sequence state
[
X_-=\pm jX_+
]
in real coordinates.

## Internal signals

Base quadratures:
[
q_c = A\cos\theta,
\qquad
q_s = A\sin\theta.
]

Positive-sequence coordinates:
[
x_{+\alpha}=q_c,
\qquad
x_{+\beta}=q_s.
]

Negative-sequence coordinates, plus-lock choice:
[
x_{-\alpha}=-q_s,
\qquad
x_{-\beta}=q_c
]
for (X_-=+jX_+),

or
[
x_{-\alpha}=q_s,
\qquad
x_{-\beta}=-q_c
]
for (X_-=-jX_+).

## Outputs

Four held analog state lines:

* (x_{+\alpha})
* (x_{+\beta})
* (x_{-\alpha})
* (x_{-\beta})

## Practical blocks

* quadrature oscillator or DDS
* sign-select matrix
* gain trim for equal magnitude
* phase trim for exact (90^\circ)

---

# 3. Hold board

## Purpose

Freeze the prepared state during one event.

## Inputs

* (x_{+\alpha},x_{+\beta},x_{-\alpha},x_{-\beta})

## Internal function

Sample-and-hold or buffered analog memory.

## Outputs

Held state:

* (X_{+\alpha})
* (X_{+\beta})
* (X_{-\alpha})
* (X_{-\beta})

These are the actual shared hidden-state wires feeding the analyzers.

---

# 4. Analyzer board

Two copies: Alice and Bob.

## 4.1 Alice analyzer

Angle control:
[
\phi_A
]

Direction coefficients:
[
c_A=\cos\phi_A,
\qquad
s_A=\sin\phi_A.
]

Outputs:
[
A_+ = c_A X_{+\alpha} + s_A X_{+\beta}
]
[
A_- = -s_A X_{-\alpha} + c_A X_{-\beta}
]

### Interpretation

* (A_+): positive-sequence projection onto Alice axis
* (A_-): negative-sequence projection onto Alice orthogonal sign axis

## 4.2 Bob analyzer

Angle control:
[
\phi_B
]

Direction coefficients:
[
c_B=\cos\phi_B,
\qquad
s_B=\sin\phi_B.
]

Outputs:
[
B_+ = c_B X_{+\alpha} + s_B X_{+\beta}
]
[
B_- = -s_B X_{-\alpha} + c_B X_{-\beta}
]

## Analyzer board outputs

Four analog lines:

* (A_+)
* (A_-)
* (B_+)
* (B_-)

---

# 5. Parity recombiner board

## Purpose

Construct the two joint parity-mode amplitudes.

## 5.1 Product cells

Use four analog multipliers.

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

These are internal overlap channels.

## 5.2 Parity bus summers

Same-parity bus:
[
S = X + W
]

Opposite-parity bus:
[
O = Y - Z
]

These are the key joint parity amplitudes.

## Expected identity on the prepared manifold

If the prep is correct,
[
S = A^2 \cos(\phi_A-\phi_B),
\qquad
O = -A^2 \sin(\phi_A-\phi_B).
]

So
[
S^2 \propto \cos^2\Delta,\qquad O^2 \propto \sin^2\Delta,
\quad \Delta=\phi_A-\phi_B.
]

## Outputs

Six analog lines:

* constituent channels: (X,Y,Z,W)
* parity buses: (S,O)

---

# 6. Closure / branch logic board

This board has two layers:

* sector competition
* branch competition inside sector

## 6.1 Square-law detectors

Create positive drive signals:

[
D_S = g_S S^2,
\qquad
D_O = g_O O^2
]

[
D_{++}=g_x X^2,
\quad
D_{+-}=g_x Y^2,
\quad
D_{-+}=g_x Z^2,
\quad
D_{--}=g_x W^2
]

with gains (g_S,g_O,g_x).

These can be literal square-law blocks or absolute-value plus multiplier.

---

## 6.2 Shared resource node

One shared scalar state (R(t)), represented physically as:

* common capacitor voltage,
* common envelope node,
* or common current-limited supply node.

Dynamics to approximate:
[
\dot R = -\mu_s sR - \mu_o oR
]

In circuit language:

* as sector accumulators grow, they load the common node and reduce available drive.

So (R) is the shared closure resource.

---

## 6.3 Sector competition layer

Two accumulators:

* (s(t)): same-sector activation
* (o(t)): opposite-sector activation

Idealized equations:
[
\dot s = \lambda_S D_S R - \eta_s s - \chi s o
]
[
\dot o = \lambda_O D_O R - \eta_o o - \chi s o
]

### Circuit realization

Each is an RC integrator.

Input current:

* into (s): proportional to (D_S R)
* into (o): proportional to (D_O R)

Leak:

* resistor to ground

Mutual inhibition:

* transconductance clamp or cross-coupled sink proportional to the other sector state

### Outputs

* (V_s): same-sector activation
* (V_o): opposite-sector activation

Sector winner logic:

* comparator declares same-sector if (V_s) crosses threshold first
* comparator declares opposite-sector if (V_o) crosses threshold first

Call these digital gates:

* (G_S)
* (G_O)

Only one should latch high.

---

## 6.4 Branch competition layer

Four branch accumulators:

* (x_{++})
* (x_{--})
* (x_{+-})
* (x_{-+})

### Same-sector branches

Driven only if (G_S=1):

[
\dot x_{++} = \sigma_S D_{++} s - \eta_x x_{++} - \chi_x x_{++}x_{--}
]
[
\dot x_{--} = \sigma_S D_{--} s - \eta_x x_{--} - \chi_x x_{++}x_{--}
]

### Opposite-sector branches

Driven only if (G_O=1):

[
\dot x_{+-} = \sigma_O D_{+-} o - \eta_x x_{+-} - \chi_x x_{+-}x_{-+}
]
[
\dot x_{-+} = \sigma_O D_{-+} o - \eta_x x_{-+} - \chi_x x_{+-}x_{-+}
]

### Circuit realization

Each is another RC integrator.

Gating:

* analog switch or multiplier controlled by (G_S) or (G_O)

Mutual inhibition:

* cross-coupled sink inside each sector pair only

### Final output latches

Comparators detect which branch threshold is crossed first:

* (L_{++})
* (L_{--})
* (L_{+-})
* (L_{-+})

Exactly one should latch high per event.

---

# 7. Signal list by wire

## Prep/Hold wires

* (X_{+\alpha})
* (X_{+\beta})
* (X_{-\alpha})
* (X_{-\beta})

## Analyzer wires

* (A_+)
* (A_-)
* (B_+)
* (B_-)

## Product wires

* (X=A_+B_+)
* (Y=A_+B_-)
* (Z=A_-B_+)
* (W=A_-B_-)

## Parity bus wires

* (S=X+W)
* (O=Y-Z)

## Sector drives

* (D_S=S^2)
* (D_O=O^2)

## Branch drives

* (D_{++}=X^2)
* (D_{+-}=Y^2)
* (D_{-+}=Z^2)
* (D_{--}=W^2)

## Sector states

* (R)
* (s)
* (o)

## Sector latch lines

* (G_S)
* (G_O)

## Branch states

* (x_{++})
* (x_{--})
* (x_{+-})
* (x_{-+})

## Event outputs

* (L_{++})
* (L_{--})
* (L_{+-})
* (L_{-+})

---

# 8. Bench-top operating sequence

## Step 1: prepare

Drive prep board until state reaches
[
(X_+,X_-) \propto (1,\pm j)e^{j\theta}.
]

## Step 2: freeze

Hold the four real coordinates.

## Step 3: set analyzers

Choose (\phi_A,\phi_B).

## Step 4: fire event

Connect held state into recombiner + closure board.

## Step 5: sector competition

(S) and (O) compete for shared resource (R).

## Step 6: branch competition

Winning sector gates its internal pair.

## Step 7: latch outcome

One of (L_{++},L_{--},L_{+-},L_{-+}) fires.

## Step 8: reset

Discharge all accumulators, release latches, choose new (\theta), repeat.

---

# 9. First measurements to make

Before any Bell-style statistics, verify each layer separately.

## 9.1 Prep verification

Check:
[
X_- \approx \pm jX_+
]
in the held state.

## 9.2 Recombiner verification

Sweep (\Delta=\phi_A-\phi_B) and measure:
[
S,\ O.
]
Verify:
[
S \sim \cos\Delta,\qquad O \sim \sin\Delta.
]

## 9.3 Sector competition verification

Check that sector winner frequency follows:
[
P(S)\sim \cos^2\Delta,\qquad P(O)\sim \sin^2\Delta.
]

## 9.4 Branch competition verification

At fixed winning sector, sweep hidden phase (\theta) and verify that branch dominance swaps under
[
\theta \mapsto \theta+\frac{\pi}{2}.
]

## 9.5 Averaged marginal verification

Average over uniform (\theta) and verify:
[
P(A=+)=P(B=+)=\frac12.
]

---

# 10. Brutal weak points

The design is coherent, but the soft spots are:

* the prep board is engineered, not natural,
* the parity recombiner uses explicit multipliers in the prototype,
* the closure/competition dynamics are phenomenological analog computing blocks, not derived passive magnetics.

That is okay for a first rig. The goal now is to test whether the architecture as such works, not to prove that standard hardware naturally realizes it.

---

# 11. Minimal component-level intuition

If you wanted literal component categories:

## Prep

* DDS or analog quadrature oscillator
* op-amp summers/inverters
* 4 sample-and-hold channels

## Analyzer

* coefficient pots or DAC-set gains
* 4 summing amplifiers

## Recombiner

* 4 four-quadrant analog multipliers
* 2 op-amp summing amplifiers

## Closure

* 6 square-law / rectifier-squaring channels
* 6 RC integrators
* cross-coupled transconductance inhibition
* 6 comparators / latches
* one common droop node (R)