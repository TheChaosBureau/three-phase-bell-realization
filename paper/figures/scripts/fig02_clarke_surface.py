"""
Figure 2: The Clarke power surface for a balanced positive+negative sequence
source, plus the analyzer "breathing bowls" at three settings.

Following notebooks/20_clarke-surface.qmd: equal positive- and negative-
sequence components V_+ = V_- = V on a balanced three-phase source produce
phase voltages v_a = 2V cos theta, v_b = v_c = -V cos theta. Under the
power-invariant Clarke transform, v_alpha = sqrt(6) V cos theta and
v_beta = 0 identically: the Clarke power surface is the bowl
p_alpha_beta(theta) = 6 V^2 cos^2 theta.

Park rotation by analyzer angle phi splits the bowl into a complementary
pair: a d-axis bowl scaled by cos^2 phi and a q-axis bowl scaled by
sin^2 phi, summing to a constant plane (the conservation law made
visible). At phi = 0 the d-axis bowl carries everything; at phi = pi/4
the two bowls are equal half-height copies; at phi = pi/2 they have
fully exchanged roles.

Run: python paper/figures/scripts/fig02_clarke_surface.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import cm
import numpy as np

OUT = Path(__file__).resolve().parent.parent

V = 1.0
theta = np.linspace(0, 2 * np.pi, 200)
r = np.linspace(0, 1, 60)
TH, RR = np.meshgrid(theta, r)
X = RR * np.cos(TH)
Y = RR * np.sin(TH)

p_base = 6 * V**2 * np.cos(theta) ** 2
Z_base = np.tile(p_base, (len(r), 1))

phi_values = [0.0, np.pi / 4, np.pi / 2]
phi_labels = [r"$\phi = 0$", r"$\phi = \pi/4$", r"$\phi = \pi/2$"]

fig = plt.figure(figsize=(11, 4.0), constrained_layout=True)
for k, (phi, lbl) in enumerate(zip(phi_values, phi_labels)):
    c2 = np.cos(phi) ** 2
    s2 = np.sin(phi) ** 2
    Z_d = Z_base * c2
    Z_q = Z_base * s2

    ax = fig.add_subplot(1, 3, k + 1, projection="3d")
    ax.plot_surface(X, Y, Z_d, cmap=cm.viridis, edgecolor="none",
                    alpha=0.85, vmin=0, vmax=6 * V**2, antialiased=True)
    ax.plot_surface(X, Y, Z_q, cmap=cm.magma, edgecolor="none",
                    alpha=0.65, vmin=0, vmax=6 * V**2, antialiased=True)
    ax.plot_surface(X, Y, np.full_like(X, 6 * V**2),
                    color="0.85", alpha=0.18, edgecolor="none")
    # rim curves
    p_d_rim = p_base * c2
    p_q_rim = p_base * s2
    ax.plot(np.cos(theta), np.sin(theta), p_d_rim, color="black", lw=1.4)
    ax.plot(np.cos(theta), np.sin(theta), p_q_rim, color="firebrick", lw=1.4)

    ax.set_title(lbl, fontsize=10)
    ax.set_xlabel("x", fontsize=8, labelpad=-6)
    ax.set_ylabel("y", fontsize=8, labelpad=-6)
    ax.set_zlabel(r"$p_{\alpha\beta}$", fontsize=8, labelpad=-6)
    ax.set_xticks([-1, 0, 1])
    ax.set_yticks([-1, 0, 1])
    ax.set_zticks([0, 3, 6])
    ax.tick_params(labelsize=7)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=24, azim=45)

fig.suptitle(
    r"Clarke power surface and breathing bowls: "
    r"$p_{d}(\theta,\phi) + p_{q}(\theta,\phi) = 6V^2\cos^2\theta$ for all $\phi$",
    fontsize=10,
)

for ext in ("pdf", "png"):
    out = OUT / f"fig02_clarke_surface.{ext}"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print(f"wrote {out}")
plt.close(fig)
