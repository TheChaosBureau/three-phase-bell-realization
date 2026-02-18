import numpy as np
import plotly.graph_objects as go

# ----------------------------
# Parameters you can tweak
# ----------------------------
N = 400                       # grid resolution for the unwrapped torus
texture_mode = "spin_singlet" # "spin_singlet" or "photon_polarization"
# texture_mode = "photon_polarization" # "spin_singlet" or "photon_polarization"

# Texture on the (theta_A, theta_B) torus
# We'll visualize a Born-weight-like texture R^2 that depends only on the relative angle Δ.
thetaA = np.linspace(0, 2*np.pi, N, endpoint=False)
thetaB = np.linspace(0, 2*np.pi, N, endpoint=False)
TA, TB = np.meshgrid(thetaA, thetaB, indexing="xy")
Delta = TA - TB

if texture_mode == "spin_singlet":
    # Representative relative-angle texture: cos^2(Δ/2)
    W = np.cos(Delta/2.0)**2
elif texture_mode == "photon_polarization":
    # For linear polarizers the relevant physics often appears with a double-angle: cos^2(Δ)
    W = np.cos(Delta)**2
else:
    raise ValueError("texture_mode must be 'spin_singlet' or 'photon_polarization'")

# Normalize 0..1 for consistent mapping
Wn = (W - W.min()) / (W.max() - W.min() + 1e-12)

# ----------------------------
# 3D interactive surface over [0, 2π) × [0, 2π)
# ----------------------------
ticks = [0, np.pi / 2, np.pi, 3 * np.pi / 2, 2 * np.pi]
ticklabels = ["0", "π/2", "π", "3π/2", "2π"]

fig = go.Figure(
    data=[
        go.Surface(
            x=TA,
            y=TB,
            z=Wn,
            colorscale="Viridis",
            colorbar=dict(title="Normalized weight W"),
        )
    ]
)
fig.update_layout(
    title="Unwrapped torus texture on (θA, θB) ∈ [0, 2π) × [0, 2π)",
    scene=dict(
        camera=dict(projection=dict(type="orthographic")),
        xaxis=dict(title="θA", tickvals=ticks, ticktext=ticklabels),
        yaxis=dict(title="θB", tickvals=ticks, ticktext=ticklabels),
        zaxis=dict(title="W(θA, θB)"),
    ),
    margin=dict(l=0, r=0, t=40, b=0),
)
fig.show()
