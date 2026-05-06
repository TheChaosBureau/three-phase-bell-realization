"""
Figure 1: Linear vs. quadratic correlators with CHSH analyzer-pair overlay.

Linear conservation produces $E_\\text{lin}(\\Delta\\phi) = -\\frac{1}{2}\\cos(\\Delta\\phi)$;
quadratic conservation produces $E_\\text{quad}(\\Delta\\phi) = -\\cos(2\\Delta\\phi)$
(full Tsirelson amplitude). The angular frequency doubles when the conserved
quantity is intensity rather than amplitude --- the algebraic engine of the
Bell-Tsirelson gap (Section 2 of the paper).

The optimal CHSH analyzer-angle scale halves accordingly: the linear
correlator peaks at \\Delta\\phi = pi/4, the quadratic at \\Delta\\phi = pi/8.

Run: python paper/figures/scripts/fig01_correlator_hierarchy.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).resolve().parent.parent  # paper/figures/

dphi = np.linspace(-np.pi, np.pi, 1024)
E_lin = -0.5 * np.cos(dphi)
E_quad = -np.cos(2 * dphi)

# CHSH-optimal analyzer-pair settings for each frequency:
#   linear (omega=1):    a=0, a'=pi/2, b=pi/4, b'=3pi/4
#   quadratic (omega=2): a=0, a'=pi/4, b=pi/8, b'=3pi/8
chsh_lin = {
    "Delta(a,b)":  0 - np.pi / 4,
    "Delta(a,b')": 0 - 3 * np.pi / 4,
    "Delta(a',b)": np.pi / 2 - np.pi / 4,
    "Delta(a',b')": np.pi / 2 - 3 * np.pi / 4,
}
chsh_quad = {
    "Delta(a,b)":  0 - np.pi / 8,
    "Delta(a,b')": 0 - 3 * np.pi / 8,
    "Delta(a',b)": np.pi / 4 - np.pi / 8,
    "Delta(a',b')": np.pi / 4 - 3 * np.pi / 8,
}

fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), constrained_layout=True)

# Linear panel
ax = axes[0]
ax.plot(dphi, E_lin, color="C0", lw=1.6,
        label=r"$E_\mathrm{lin} = -\frac{1}{2}\cos(\Delta\phi)$")
ax.axhline(0, color="0.7", lw=0.5, ls="-")
for label, x in chsh_lin.items():
    ax.axvline(x, color="0.5", lw=0.7, ls=":")
ax.scatter(list(chsh_lin.values()),
           [-0.5 * np.cos(x) for x in chsh_lin.values()],
           color="C0", s=24, zorder=5)
ax.set_xlim(-np.pi, np.pi)
ax.set_xticks([-np.pi, -np.pi / 2, 0, np.pi / 2, np.pi])
ax.set_xticklabels([r"$-\pi$", r"$-\pi/2$", "$0$", r"$\pi/2$", r"$\pi$"])
ax.set_ylim(-1.05, 1.05)
ax.set_xlabel(r"$\Delta\phi$")
ax.set_ylabel(r"$E(\Delta\phi)$")
ax.set_title("Linear conservation\n" r"$|S|_{\max} = \sqrt{2} \approx 1.414$")
ax.legend(loc="upper right", fontsize=9, frameon=False)
ax.grid(True, alpha=0.25)

# Quadratic panel
ax = axes[1]
ax.plot(dphi, E_quad, color="C3", lw=1.6,
        label=r"$E_\mathrm{quad} = -\cos(2\Delta\phi)$")
ax.axhline(0, color="0.7", lw=0.5, ls="-")
for label, x in chsh_quad.items():
    ax.axvline(x, color="0.5", lw=0.7, ls=":")
ax.scatter(list(chsh_quad.values()),
           [-np.cos(2 * x) for x in chsh_quad.values()],
           color="C3", s=24, zorder=5)
ax.set_xlim(-np.pi, np.pi)
ax.set_xticks([-np.pi, -np.pi / 2, 0, np.pi / 2, np.pi])
ax.set_xticklabels([r"$-\pi$", r"$-\pi/2$", "$0$", r"$\pi/2$", r"$\pi$"])
ax.set_ylim(-1.05, 1.05)
ax.set_xlabel(r"$\Delta\phi$")
ax.set_ylabel(r"$E(\Delta\phi)$")
ax.set_title("Quadratic conservation\n" r"$|S|_{\max} = 2\sqrt{2} \approx 2.828$")
ax.legend(loc="upper right", fontsize=9, frameon=False)
ax.grid(True, alpha=0.25)

fig.suptitle("Linear vs. quadratic conservation: correlator shape and CHSH-optimal angles",
             fontsize=11)

for ext in ("pdf", "png"):
    out = OUT / f"fig01_correlator_hierarchy.{ext}"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print(f"wrote {out}")
plt.close(fig)
