"""
Figure 4: The zero-sequence reservoir P_0(theta) at three analyzer-difference
angles, illustrating the three-party conservation law.

For a balanced source (V_+ = V_- = 1), the powers captured by the two
analyzers satisfy
    P_A(theta) + P_B(theta) = 1 + cos(Delta phi) cos(2 theta - phi_A - phi_B),
which oscillates in theta unless Delta phi in {0, pi/2}. The remaining
energy is in the zero-sequence channel:
    P_0(theta) = - cos(Delta phi) cos(2 theta - phi_A - phi_B)
            (relative to a normalized total of 1).

Aligned analyzers (Delta = 0): P_0 oscillates at full amplitude, mean 0.
Orthogonal (Delta = pi/2): P_0 identically 0; analyzers fully partition.
CHSH-optimal (Delta = pi/4 or pi/8): intermediate; correlation peaks here.

Run: python paper/figures/scripts/fig04_zero_sequence.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).resolve().parent.parent

theta = np.linspace(0, 2 * np.pi, 1024)


def P0(theta, dphi, sum_phi=0.0):
    return -np.cos(dphi) * np.cos(2 * theta - sum_phi)


regimes = [
    (r"$\Delta\phi = 0$ (aligned)",        0.0,         "C0", "-"),
    (r"$\Delta\phi = \pi/8$ (CHSH-opt.)",  np.pi / 8,    "C1", "--"),
    (r"$\Delta\phi = \pi/4$",              np.pi / 4,    "C2", "-."),
    (r"$\Delta\phi = \pi/2$ (orthogonal)", np.pi / 2,    "C3", ":"),
]

fig, axes = plt.subplots(1, 2, figsize=(11, 3.6), constrained_layout=True,
                         gridspec_kw={"width_ratios": [1.4, 1.0]})

# Left: P_0(theta) at four analyzer-difference angles
ax = axes[0]
for label, d, color, ls in regimes:
    ax.plot(theta, P0(theta, d), color=color, ls=ls, lw=1.6, label=label)
ax.axhline(0, color="0.7", lw=0.5)
ax.set_xlim(0, 2 * np.pi)
ax.set_xticks([0, np.pi / 2, np.pi, 3 * np.pi / 2, 2 * np.pi])
ax.set_xticklabels(["$0$", r"$\pi/2$", r"$\pi$", r"$3\pi/2$", r"$2\pi$"])
ax.set_ylim(-1.15, 1.15)
ax.set_xlabel(r"$\theta$ (hidden source phase)")
ax.set_ylabel(r"$P_0(\theta)$  (normalized)")
ax.set_title(r"Zero-sequence energy reservoir $P_0(\theta) = -\cos(\Delta\phi)\cos(2\theta-\phi_A-\phi_B)$")
ax.legend(fontsize=9, frameon=False, loc="upper right")
ax.grid(True, alpha=0.25)

# Right: amplitude of P_0(theta) vs Delta phi, with CHSH-optimal angles
ax = axes[1]
dphi_grid = np.linspace(-np.pi / 2, np.pi / 2, 401)
amp = np.abs(np.cos(dphi_grid))
ax.plot(dphi_grid, amp, color="C4", lw=1.6, label=r"$|\cos(\Delta\phi)|$")
ax.fill_between(dphi_grid, 0, amp, alpha=0.15, color="C4")
for x, lbl in [(0, "aligned"),
                (np.pi / 8, r"$\pi/8$"),
                (np.pi / 4, r"$\pi/4$"),
                (np.pi / 2, r"$\pi/2$")]:
    ax.axvline(x, color="0.5", lw=0.7, ls=":")
    ax.scatter([x], [np.abs(np.cos(x))], color="C4", s=24, zorder=5)
ax.set_xlim(-np.pi / 2, np.pi / 2)
ax.set_xticks([-np.pi / 2, 0, np.pi / 8, np.pi / 4, np.pi / 2])
ax.set_xticklabels([r"$-\pi/2$", "$0$", r"$\pi/8$", r"$\pi/4$", r"$\pi/2$"])
ax.set_ylim(0, 1.05)
ax.set_xlabel(r"$\Delta\phi$")
ax.set_ylabel(r"reservoir oscillation amplitude")
ax.set_title("Reservoir depth across analyzer-difference angles")
ax.legend(fontsize=9, frameon=False, loc="lower center")
ax.grid(True, alpha=0.25)

for ext in ("pdf", "png"):
    out = OUT / f"fig04_zero_sequence.{ext}"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print(f"wrote {out}")
plt.close(fig)
