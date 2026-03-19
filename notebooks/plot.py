'''
Here’s a small self-contained Python script that draws:

Alice’s 
αβ plane

Bob’s 
αβ plane

the doubled-angle correlation circle

It uses the simple Bell-like state with

T=sI,s=±1

so the correlation is

E(α,β)=scos2(α−β).

state_sign = +1 gives the “same-orientation” version, and state_sign = -1 gives the singlet-like version.
---
A few notes on what you’re looking at:

In the Alice and Bob panels, the solid long line is the local oscillation line, the dashed line is the analyzer axis, and the arrow is the instantaneous Clarke vector.

The shorter arrow is the projection onto the analyzer axis, which is the local geometric origin of the 
cos2(ϕ−θ) law.

In the right panel, the vectors live in doubled-angle line-orientation space, not the physical 
αβ plane. That’s where the Bell/polarization correlation naturally becomes a dot product.

One important caveat: the left two panels are an intuition layer. A true Bell pair is not literally just “Alice has line ϕA
Bob has line ϕB at all times." The exact pair state lives in the correlation structure summarized by the right-hand panel. So this script is best read as:

local picture on the left,

true joint geometry on the right.

'''
import numpy as np
import matplotlib.pyplot as plt


def unit(theta: float) -> np.ndarray:
    """Ordinary unit vector in the physical alpha-beta plane."""
    return np.array([np.cos(theta), np.sin(theta)])


def doubled_unit(theta: float) -> np.ndarray:
    """Unit vector in doubled-angle line-orientation space."""
    return np.array([np.cos(2 * theta), np.sin(2 * theta)])


def draw_plane(ax, title: str, phi: float, analyzer: float, t: float) -> None:
    """
    Draw one local alpha-beta plane.

    phi      : physical oscillation-line angle
    analyzer : analyzer axis angle
    t        : time sample used to place the instantaneous Clarke-vector tip
    """
    ax.set_title(title)
    ax.set_aspect("equal")
    ax.set_xlim(-1.25, 1.25)
    ax.set_ylim(-1.25, 1.25)
    ax.axhline(0.0, linewidth=1.0)
    ax.axvline(0.0, linewidth=1.0)

    # Alpha-beta axes labels
    ax.text(1.18, 0.03, r"$\alpha$")
    ax.text(0.03, 1.12, r"$\beta$")

    # Oscillation line (undirected physical line through origin)
    u_phi = unit(phi)
    p1 = -u_phi
    p2 = u_phi
    ax.plot([p1[0], p2[0]], [p1[1], p2[1]], linewidth=2.0, label="oscillation line")

    # Instantaneous oscillating Clarke vector tip
    rho = 0.9 * np.cos(t)
    tip = rho * u_phi
    ax.arrow(
        0.0, 0.0, tip[0], tip[1],
        length_includes_head=True,
        head_width=0.05,
        linewidth=2.0
    )

    # Analyzer axis
    u_a = unit(analyzer)
    q1 = -u_a
    q2 = u_a
    ax.plot(
        [q1[0], q2[0]], [q1[1], q2[1]],
        linestyle="--", linewidth=2.0, label="analyzer axis"
    )

    # Perpendicular analyzer axis
    v_a = unit(analyzer + np.pi / 2)
    r1 = -v_a
    r2 = v_a
    ax.plot(
        [r1[0], r2[0]], [r1[1], r2[1]],
        linestyle=":", linewidth=1.5, label="orthogonal channel"
    )

    # Projection of tip onto analyzer axis
    proj_mag = np.dot(tip, u_a)
    proj = proj_mag * u_a
    ax.arrow(
        0.0, 0.0, proj[0], proj[1],
        length_includes_head=True,
        head_width=0.04,
        linewidth=2.0
    )

    # A small connector from tip to its projection
    ax.plot([tip[0], proj[0]], [tip[1], proj[1]], linewidth=1.0)

    # Annotate angles
    ax.text(
        0.02, -1.16,
        rf"$\phi={np.degrees(phi):.1f}^\circ,\ \theta={np.degrees(analyzer):.1f}^\circ$",
        fontsize=10
    )

    # Local pass probability for a linear oscillation line
    p_pass = np.cos(phi - analyzer) ** 2
    ax.text(
        0.02, -1.05,
        rf"$P_+ = \cos^2(\phi-\theta) = {p_pass:.3f}$",
        fontsize=10
    )

    ax.set_xticks([])
    ax.set_yticks([])


def draw_correlation_circle(ax, alpha: float, beta: float, state_sign: int) -> float:
    """
    Draw doubled-angle line-orientation space and return correlation E(alpha, beta).

    state_sign = +1  -> T = +I   => E = cos 2(alpha - beta)
    state_sign = -1  -> T = -I   => E = -cos 2(alpha - beta)
    """
    ax.set_title("Doubled-angle correlation space")
    ax.set_aspect("equal")
    ax.set_xlim(-1.25, 1.25)
    ax.set_ylim(-1.25, 1.25)

    # Unit circle
    th = np.linspace(0, 2 * np.pi, 400)
    ax.plot(np.cos(th), np.sin(th), linewidth=1.5)

    ax.axhline(0.0, linewidth=1.0)
    ax.axvline(0.0, linewidth=1.0)

    n_alpha = doubled_unit(alpha)
    n_beta = doubled_unit(beta)

    # Correlation map T = s I
    mapped_beta = state_sign * n_beta

    # Draw Alice analyzer vector n(alpha)
    ax.arrow(
        0.0, 0.0, n_alpha[0], n_alpha[1],
        length_includes_head=True,
        head_width=0.05,
        linewidth=2.0
    )

    # Draw Bob analyzer vector n(beta)
    ax.arrow(
        0.0, 0.0, n_beta[0], n_beta[1],
        length_includes_head=True,
        head_width=0.05,
        linewidth=2.0
    )

    # Draw transformed Bob vector T n(beta)
    ax.arrow(
        0.0, 0.0, mapped_beta[0], mapped_beta[1],
        length_includes_head=True,
        head_width=0.05,
        linewidth=2.0,
        linestyle="--"
    )

    # Correlation
    E = float(np.dot(n_alpha, mapped_beta))

    ax.text(-1.18, 1.08, rf"$n(\alpha)=(\cos 2\alpha,\ \sin 2\alpha)$", fontsize=10)
    ax.text(-1.18, 0.94, rf"$n(\beta)=(\cos 2\beta,\ \sin 2\beta)$", fontsize=10)

    if state_sign == 1:
        ax.text(-1.18, 0.78, r"$T = +I$", fontsize=10)
        ax.text(-1.18, 0.64, rf"$E=\cos 2(\alpha-\beta)={E:.3f}$", fontsize=10)
    else:
        ax.text(-1.18, 0.78, r"$T = -I$", fontsize=10)
        ax.text(-1.18, 0.64, rf"$E=-\cos 2(\alpha-\beta)={E:.3f}$", fontsize=10)

    ax.text(
        -1.18, -1.10,
        rf"$\alpha={np.degrees(alpha):.1f}^\circ,\ \beta={np.degrees(beta):.1f}^\circ$",
        fontsize=10
    )

    ax.set_xticks([])
    ax.set_yticks([])
    return E


def main() -> None:
    # ----------------------------
    # User-adjustable parameters
    # ----------------------------
    alpha = np.deg2rad(10.0)   # Alice analyzer angle
    beta = np.deg2rad(35.0)    # Bob analyzer angle

    # Choose a simple local oscillation-line picture for visualization.
    # These are physical line angles in the local alpha-beta planes.
    phi_A = np.deg2rad(25.0)
    phi_B = np.deg2rad(25.0)

    # Time sample for showing instantaneous Clarke-vector tips
    t = 0.7

    # +1 -> E = cos 2(alpha-beta)
    # -1 -> E = -cos 2(alpha-beta)
    state_sign = +1

    # ----------------------------
    # Plot
    # ----------------------------
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    draw_plane(
        axes[0],
        title="Alice local $\\alpha\\beta$ plane",
        phi=phi_A,
        analyzer=alpha,
        t=t,
    )

    draw_plane(
        axes[1],
        title="Bob local $\\alpha\\beta$ plane",
        phi=phi_B,
        analyzer=beta,
        t=t + 0.8,
    )

    E = draw_correlation_circle(
        axes[2],
        alpha=alpha,
        beta=beta,
        state_sign=state_sign,
    )

    fig.suptitle(
        rf"Local oscillating-line picture + doubled-angle correlation circle    "
        rf"$E(\alpha,\beta)={E:.3f}$",
        fontsize=14
    )

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()