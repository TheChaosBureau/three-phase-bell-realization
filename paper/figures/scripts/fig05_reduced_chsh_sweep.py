"""
Figure 5: CHSH magnitude sweep for the reduced 4-mode singlet model.

Computes the joint correlator
    E(a, b) = -cos(2(a-b))
from the reduced 4-mode model on the singlet state psi = (0, 1, -1, 0)/sqrt 2,
sweeps Bob's analyzer pair (b, b') and computes the CHSH magnitude
    S(a, a', b, b') = E(a,b) - E(a,b') + E(a',b) + E(a',b')
for fixed Alice settings (a, a') = (0, pi/4) and (b, b') = (b0, b0 + pi/4),
parameterized by b0.

The peak |S| = 2 sqrt 2 lands at b0 = pi/8, exactly on the Tsirelson bound.

Run: python paper/figures/scripts/fig05_reduced_chsh_sweep.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).resolve().parent.parent


def R(theta: float) -> np.ndarray:
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, s], [-s, c]])


PSI_S = np.array([0.0, 1.0, -1.0, 0.0]) / np.sqrt(2.0)


def correlator(a: float, b: float) -> float:
    U = np.kron(R(a), R(b))
    psi = U @ PSI_S
    w = psi**2  # real, so |.|^2 = .^2
    # outcome coding: ++ -> +1, +- -> -1, -+ -> -1, -- -> +1
    return float(w[0] - w[1] - w[2] + w[3])


def S_chsh(a: float, ap: float, b: float, bp: float) -> float:
    return correlator(a, b) - correlator(a, bp) + correlator(ap, b) + correlator(ap, bp)


# Sweep Bob's b0 across the full circle, fix b' = b0 + pi/4
# Fix Alice at the canonical CHSH-optimal pair (0, pi/4)
b0_grid = np.linspace(-np.pi / 2, np.pi / 2, 401)
S_vals = np.array([S_chsh(0.0, np.pi / 4, b0, b0 + np.pi / 4) for b0 in b0_grid])
S_target = -np.cos(2 * (0 - b0_grid)) + np.cos(2 * (0 - b0_grid - np.pi / 4)) \
           - np.cos(2 * (np.pi / 4 - b0_grid)) - np.cos(2 * (np.pi / 4 - b0_grid - np.pi / 4))

fig, axes = plt.subplots(1, 2, figsize=(11, 4.0), constrained_layout=True)

# Left: |S| vs. b0 with bounds
ax = axes[0]
ax.plot(b0_grid, np.abs(S_vals), color="C3", lw=1.8,
        label="reduced 4-mode model")
ax.axhline(2 * np.sqrt(2), color="C3", ls="--", lw=1.2,
           label=r"Tsirelson bound  $2\sqrt{2}$")
ax.axhline(2.0, color="0.4", ls=":", lw=1.0,
           label=r"Bell bound  $2$")
ax.axhline(np.sqrt(2), color="0.6", ls=":", lw=1.0,
           label=r"$\sqrt{2}$")

# Mark the optimal angle
ax.axvline(np.pi / 8, color="0.5", lw=0.7, ls=":")
ax.scatter([np.pi / 8], [2 * np.sqrt(2)], color="C3", s=32, zorder=5)
ax.annotate(r"$b = \pi/8$, $|S| = 2\sqrt{2}$",
            xy=(np.pi / 8, 2 * np.sqrt(2)), xytext=(np.pi / 12, 2.5),
            fontsize=9,
            arrowprops=dict(arrowstyle="->", color="0.4", lw=0.7))

ax.set_xlim(-np.pi / 2, np.pi / 2)
ax.set_xticks([-np.pi / 2, -np.pi / 4, 0, np.pi / 8, np.pi / 4, np.pi / 2])
ax.set_xticklabels([r"$-\pi/2$", r"$-\pi/4$", "$0$", r"$\pi/8$", r"$\pi/4$", r"$\pi/2$"])
ax.set_ylim(0, 3.1)
ax.set_xlabel(r"Bob's first angle $b$ (with $b' = b + \pi/4$, fixed $a=0,\ a'=\pi/4$)")
ax.set_ylabel(r"$|S|$")
ax.set_title("CHSH sweep, reduced 4-mode singlet model")
ax.legend(fontsize=9, frameon=False, loc="lower right")
ax.grid(True, alpha=0.25)

# Right: |S| as a function of (a, b) over the 2D angle plane (heatmap),
# with the canonical (b, b') = (b, b+pi/4) embedded.
N = 121
a_grid = np.linspace(0, np.pi, N)
b_grid = np.linspace(0, np.pi, N)
S_mat = np.empty((N, N))
for i, a_val in enumerate(a_grid):
    for j, b_val in enumerate(b_grid):
        S_mat[i, j] = S_chsh(a_val, a_val + np.pi / 4, b_val, b_val + np.pi / 4)

ax = axes[1]
im = ax.imshow(np.abs(S_mat),
               origin="lower",
               extent=[0, np.pi, 0, np.pi],
               aspect="auto",
               cmap="RdYlBu_r",
               vmin=0, vmax=2 * np.sqrt(2))
ax.set_xlabel(r"$b$ (with $b' = b + \pi/4$)")
ax.set_ylabel(r"$a$ (with $a' = a + \pi/4$)")
ax.set_title(r"$|S|$ over the analyzer-pair plane")
ax.set_xticks([0, np.pi / 4, np.pi / 2, 3 * np.pi / 4, np.pi])
ax.set_xticklabels(["$0$", r"$\pi/4$", r"$\pi/2$", r"$3\pi/4$", r"$\pi$"])
ax.set_yticks([0, np.pi / 4, np.pi / 2, 3 * np.pi / 4, np.pi])
ax.set_yticklabels(["$0$", r"$\pi/4$", r"$\pi/2$", r"$3\pi/4$", r"$\pi$"])
# Mark the canonical optimum (a, b) = (0, pi/8)
ax.scatter([np.pi / 8], [0], facecolors="white", edgecolors="black", s=40,
           zorder=5)
ax.annotate("CHSH optimum", xy=(np.pi / 8, 0), xytext=(np.pi / 5, np.pi / 8),
            fontsize=9, color="black",
            arrowprops=dict(arrowstyle="->", color="black", lw=0.7))
fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label=r"$|S|$")

for ext in ("pdf", "png"):
    out = OUT / f"fig05_reduced_chsh_sweep.{ext}"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print(f"wrote {out}")
plt.close(fig)

print()
print(f"Verification: |S| at canonical optimum (0, pi/4, pi/8, 3pi/8) = "
      f"{abs(S_chsh(0, np.pi/4, np.pi/8, 3*np.pi/8)):.6f}  "
      f"(Tsirelson 2sqrt2 = {2*np.sqrt(2):.6f})")
