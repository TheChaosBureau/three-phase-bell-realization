"""
Figure 3: The four correlator shapes that span the conservation hierarchy.

Linear (S = sqrt 2):   E_lin     = -(1/2) cos(Delta phi)
Stochastic local (S = sqrt 2):   E_stoch   = -(1/2) cos(2 Delta phi)
Deterministic threshold (S = 2): E_det     = -1 + 4 |Delta phi|/pi (pp on |.|<=pi/2)
Quantum / quadratic (S = 2 sqrt 2): E_quad = -cos(2 Delta phi)

Each step in the hierarchy is a factor of sqrt(2) in CHSH: independent coin
flips dilute the amplitude by 1/2 (stochastic local), sign-thresholding
linearizes the bowl into a triangle (deterministic threshold), and strict
event-by-event complementarity recovers the full Tsirelson amplitude.

Run: python paper/figures/scripts/fig03_hierarchy.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).resolve().parent.parent

dphi = np.linspace(-np.pi, np.pi, 1024)


def E_det(d: np.ndarray) -> np.ndarray:
    # piecewise linear triangle: -1 + 4|d|/pi on |d|<=pi/2,
    # extended periodically to (-pi, pi] by 3 - 4|d|/pi on pi/2 < |d| <= pi.
    a = np.abs(d)
    out = np.where(a <= np.pi / 2, -1 + 4 * a / np.pi, 3 - 4 * a / np.pi)
    return out


curves = [
    ("Linear conservation",                   -0.5 * np.cos(dphi),       r"$|S| = \sqrt{2}$"),
    ("Stochastic local quadratic",            -0.5 * np.cos(2 * dphi),    r"$|S| = \sqrt{2}$"),
    ("Deterministic threshold",                E_det(dphi),                r"$|S| = 2$"),
    ("Quantum / quadratic conservation",      -np.cos(2 * dphi),          r"$|S| = 2\sqrt{2}$"),
]

fig, ax = plt.subplots(1, 1, figsize=(8.4, 4.4), constrained_layout=True)

styles = [("C0", "-"), ("C2", "--"), ("C1", "-."), ("C3", "-")]
for (name, y, smax), (color, ls) in zip(curves, styles):
    ax.plot(dphi, y, color=color, ls=ls, lw=1.6,
            label=f"{name}    {smax}")

ax.axhline(0, color="0.7", lw=0.5)
ax.axvline(0, color="0.7", lw=0.5)
ax.set_xlim(-np.pi, np.pi)
ax.set_xticks([-np.pi, -np.pi / 2, 0, np.pi / 2, np.pi])
ax.set_xticklabels([r"$-\pi$", r"$-\pi/2$", "$0$", r"$\pi/2$", r"$\pi$"])
ax.set_ylim(-1.1, 1.1)
ax.set_xlabel(r"$\Delta\phi$")
ax.set_ylabel(r"$E(\Delta\phi)$")
ax.set_title("The conservation hierarchy: four correlator shapes that span the Bell--Tsirelson regime")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2,
          fontsize=9, frameon=False)
ax.grid(True, alpha=0.25)

for ext in ("pdf", "png"):
    out = OUT / f"fig03_hierarchy.{ext}"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print(f"wrote {out}")
plt.close(fig)
