# 1. Minimal two-branch stochastic threshold model

**Abstract**
If you want an analytic route to

[
\Pr(1)=|c_1|^2,\qquad \Pr(2)=|c_2|^2,
]

then the simplest model is:

* the prepared state sets two nonnegative branch weights
  [
  w_1=|c_1|^2,\qquad w_2=|c_2|^2,\qquad w_1+w_2=1,
  ]
* each detector branch has a stochastic trigger rate proportional to its weight,
* the first branch to trigger wins.

That gives the square law exactly.

---

Let the prepared two-mode state be (a), and let the analyzer basis be (u_1,u_2). Define

[
c_1=u_1^\dagger a,\qquad c_2=u_2^\dagger a,
]
so
[
w_1=|c_1|^2,\qquad w_2=|c_2|^2,\qquad w_1+w_2=1.
]

Now model the two detector branches as stochastic event processes with hazards

[
\lambda_1(t)=\gamma(t),w_1,
\qquad
\lambda_2(t)=\gamma(t),w_2,
]

where (\gamma(t)\ge 0) is a common time-dependent measurement-strength function.

Interpretation:

* (\gamma(t)) captures detector aperture, coupling strength, reservoir depletion, etc.
* (w_i) is the state-dependent branch weighting.

A click occurs when one of the two processes fires first. After the first click, measurement stops.

---

# 2. Exact winner probability

The probability that branch 1 wins is

[
\Pr(1)=\int_0^\infty \lambda_1(t),
\exp!\left(-\int_0^t[\lambda_1(\tau)+\lambda_2(\tau)],d\tau\right),dt.
]

Substitute (\lambda_i(t)=\gamma(t)w_i):

[
\Pr(1)=\int_0^\infty \gamma(t)w_1,
\exp!\left(-\int_0^t \gamma(\tau)(w_1+w_2),d\tau\right),dt.
]

Since (w_1+w_2=1),

[
\Pr(1)=w_1\int_0^\infty \gamma(t),
\exp!\left(-\int_0^t \gamma(\tau),d\tau\right),dt.
]

Let
[
G(t)=\int_0^t\gamma(\tau),d\tau.
]
Then
[
\Pr(1)=w_1\int_0^\infty \gamma(t)e^{-G(t)},dt
= w_1\int_0^\infty e^{-u},du
= w_1.
]

So exactly:

[
\boxed{\Pr(1)=|c_1|^2,\qquad \Pr(2)=|c_2|^2.}
]

That is the cleanest exact derivation.

---

# 3. What this model means physically

This model says:

* the analyzer converts the prepared state into two branch weights (w_i),
* the detector is noisy and only produces one discrete event,
* the branch-specific event rates are proportional to those weights,
* the first event is the measured outcome.

So the square law enters through the **rate law**:
[
\lambda_i \propto |c_i|^2.
]

That is the crucial assumption.

---

# 4. Why this is not yet a full derivation

Because the model does **not** explain from lower-level tank physics why the click hazard must be proportional to ( |c_i|^2 ).

It only shows:

> if the detector branch event rate is proportional to the branch’s projected energy/intensity weight, then the first-click probability is exactly the Born rule.

So this is an **exact stochastic threshold realization** of Born’s rule, but not yet a derivation from raw LC hardware.

---

# 5. A more threshold-like version

If you want something closer to “energy accumulation to threshold,” define random threshold times through integrated hazard.

Let branch (i) accumulate a detection drive

[
H_i(t)=\int_0^t \lambda_i(\tau),d\tau.
]

Generate one exponential random variable (\Theta_i\sim \mathrm{Exp}(1)) per branch, and say branch (i) clicks when

[
H_i(t)=\Theta_i.
]

That is equivalent to the Poisson race above.

With
[
\lambda_i(t)=\gamma(t)|c_i|^2,
]
the first-click probabilities are still exactly

[
\Pr(i)=|c_i|^2.
]

So this is the cleanest “stochastic threshold” version.

---

# 6. Mapping to the delta-LC picture

For the 3-tank delta:

## Prepared state

[
a=
\begin{bmatrix}
a_+\
a_-
\end{bmatrix}
]
is the unloaded ring’s normalized (+)/(-) mode state.

## Analyzer

Two measurement branches define
[
c_i=u_i^\dagger a.
]

## Physical meaning of ( |c_i|^2 )

This is the fraction of initial stored energy that would go into branch (i) under ideal linear complete extraction.

## Detector model

Instead of smooth resistor split, assume each branch has a noisy threshold detector whose instantaneous event rate is proportional to its available extraction intensity:

[
\lambda_i(t)=\gamma(t),|c_i|^2.
]

Then first-click probabilities are exactly

[
\Pr(i)=|c_i|^2.
]

That is the simplest bridge from the delta energy split to discrete outcomes.

---

# 7. When this assumption is plausible

The assumption
[
\lambda_i \propto |c_i|^2
]
is plausible if:

* analyzer output amplitude is linear in the prepared state,
* available absorbed power in branch (i) is quadratic in that amplitude,
* microscopic trigger attempts are proportional to local absorbed power/intensity,
* branches share a common time envelope (\gamma(t)).

This is exactly the usual “linear field amplitude + quadratic detector response” logic.

So the whole question becomes:

> can a real delta-LC detector branch be reduced to a trigger process whose hazard is proportional to the branch’s projected absorbed power?

If yes, you get Born exactly in this race model.

---

# 8. A slightly more physical finite-reservoir variant

Let the ring contain remaining energy (W(t)), and let branch hazards be

[
\lambda_1(t)=\kappa W(t)|c_1|^2,\qquad
\lambda_2(t)=\kappa W(t)|c_2|^2.
]

As long as both branches share the same (W(t)), the same derivation goes through:

[
\Pr(1)=|c_1|^2,\qquad \Pr(2)=|c_2|^2.
]

So shared depletion does **not** spoil the exact rule, provided the branch dependence factors only through (|c_i|^2).

That is actually a useful result.

---

# 9. A diffusion/accumulator version

If you want a more “analog threshold crossing” model, use two stochastic accumulators:

[
dX_i = \mu |c_i|^2,dt + \sigma,dB_i(t),
\qquad i=1,2,
]

with click when (X_i) first reaches threshold (L).

This is more intuitive physically, but the winner probabilities are no longer exactly (|c_i|^2) in general. They depend on:

* (\mu),
* (\sigma),
* (L),
* whether the noises are independent or shared,
* whether there is depletion/coupling.

So the diffusion model is good for intuition, but bad if you want a clean exact analytic Born law.

The **Poisson race / integrated-hazard threshold** model is the one that gives the exact result.

---

# 10. Conditions for exact Born behavior

You get exact
[
\Pr(i)=|c_i|^2
]
if these hold:

## Condition 1: linear analyzer projection

[
c_i=u_i^\dagger a.
]

## Condition 2: normalized weights

[
\sum_i |c_i|^2=1.
]

## Condition 3: branch hazards factorize

[
\lambda_i(t)=\gamma(t),|c_i|^2.
]

## Condition 4: first-event selection

The measurement outcome is the first branch to cross its stochastic threshold.

That is the full minimal recipe.

---

# 11. What this says about your bigger program

This gives a very sharp target:

* the unloaded delta gives the state geometry,
* the analyzer gives the projections (c_i),
* the missing piece is a detector physics that makes branch event hazard proportional to projected absorbed intensity.

If you can build a credible detector mechanism with that property, then the stochastic threshold race gives Born exactly.

That is probably the cleanest reduced problem you have now.

---

# 12. The clean one-line answer

A minimal two-branch stochastic threshold model that yields Born exactly is:

[
c_i=u_i^\dagger a,\qquad
\lambda_i(t)=\gamma(t),|c_i|^2,
]
with the observed outcome defined as the first branch to trigger. Then
[
\Pr(i)=|c_i|^2
]
exactly.