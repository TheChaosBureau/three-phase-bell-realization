## Proposition (approximate Born law from noisy energy-threshold detection)

Consider a prepared two-mode state
[
a \in \mathbb C^2,\qquad |a|^2=1,
]
and an orthonormal analyzer basis ({u_1,u_2}). Define branch amplitudes
[
c_i = u_i^\dagger a,\qquad i=1,2,
]
so that
[
|c_1|^2+|c_2|^2=1.
]

Assume each detector branch accumulates absorbed energy (E_i(t)) according to
[
dE_i = \Gamma(t),|c_i|^2,dt + \sigma,dB_i(t),
\qquad E_i(0)=0,
]
where:

* (\Gamma(t)\ge 0) is a common envelope shared by both branches,
* (\sigma>0) is small,
* (B_1,B_2) are independent standard Brownian motions.

Define the observed outcome as the first branch to hit threshold (L>0):
[
T_i = \inf{t\ge 0: E_i(t)=L},
\qquad
i_*=\arg\min(T_1,T_2).
]

If the following hold:

1. **Matched branches**: both branches have the same threshold (L), same noise scale (\sigma), and same coupling apart from the factor (|c_i|^2),
2. **Drift-dominated crossing**: over the typical detection interval,
   [
   \Gamma(t),|c_i|^2
   ]
   dominates the noise in setting the mean first-passage time,
3. **Slow envelope**: (\Gamma(t)) varies slowly compared to the local first-passage dynamics,
4. **Weak pre-click backaction**: the analyzer weights (c_i) remain effectively fixed until the first click,

then the detector winner probabilities satisfy
[
\Pr(i_*=1)\approx |c_1|^2,\qquad
\Pr(i_*=2)\approx |c_2|^2.
]

### Proof sketch

Freeze the common envelope locally over the relevant crossing window:
[
\Gamma(t)\approx \Gamma.
]
Then each branch is a drift-diffusion process
[
dE_i = \mu_i,dt+\sigma,dB_i,
\qquad
\mu_i=\Gamma |c_i|^2.
]

For drift-dominated first passage to threshold (L), the mean hitting time is approximately
[
\mathbb E[T_i]\approx \frac{L}{\mu_i}.
]
So the effective click rate is
[
\lambda_i^{\mathrm{eff}} \approx \frac{1}{\mathbb E[T_i]}
\approx \frac{\mu_i}{L}
= \frac{\Gamma}{L}|c_i|^2.
]

Thus the two-branch first-click race is approximately a hazard race with
[
\lambda_i(t)\propto |c_i|^2.
]
For a two-branch first-event race with matched common envelope, winner probabilities are proportional to the rates, hence
[
\Pr(i_*=1)\approx
\frac{|c_1|^2}{|c_1|^2+|c_2|^2}
===============================

|c_1|^2,
]
and similarly for branch 2.

That is the result.

---

## More physical version for the 3-delta-LC picture

Let the unloaded delta contain remaining stored energy (W(t)), and let analyzer branch (i) see projected amplitude
[
c_i=u_i^\dagger a.
]

Assume branch (i) absorbs power
[
p_i(t)=g,W(t),|c_i|^2,
]
with matched branch coupling (g), and accumulates noisy absorbed energy
[
dE_i = g,W(t),|c_i|^2,dt + \sigma,dB_i(t).
]

If (W(t)) is common to both branches before the first click, then the same reasoning gives
[
\Pr(i_*=1)\approx |c_1|^2,\qquad
\Pr(i_*=2)\approx |c_2|^2.
]

So in delta-LC language, the approximation works when:

* the analyzer projection is linear,
* absorbed branch power is quadratic in projection amplitude,
* the noisy detector threshold converts absorbed power into click rate approximately linearly,
* branches are matched,
* the first click ends the trial.

---

## What would break it

The approximation fails or distorts if:

[
\lambda_i \propto |c_i|^{2\nu},\qquad \nu\neq 1,
]
or if branch thresholds/couplings differ, or if one branch significantly changes the state before threshold.

Then the outcome law becomes biased away from Born.

---

## Concrete SDE model

Use:
[
c_i=u_i^\dagger a,\qquad |c_1|^2+|c_2|^2=1,
]
and
[
dE_i = g,W_0 e^{-\beta t},|c_i|^2,dt + \sigma,dB_i(t),
\qquad i=1,2.
]

Thresholds:
[
T_i=\inf{t:E_i(t)=L}.
]

Recorded outcome:
[
i_*=\arg\min(T_1,T_2).
]

In the regime
[
\sigma^2 \ll L,gW_0,\qquad \beta T_i \ll 1,
]
you get approximately
[
\Pr(i_*=1)\approx |c_1|^2,\qquad
\Pr(i_*=2)\approx |c_2|^2.
]