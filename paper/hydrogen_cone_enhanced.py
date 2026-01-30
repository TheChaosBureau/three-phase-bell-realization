import numpy as np
from scipy.special import sph_harm, genlaguerre, factorial
import plotly.graph_objects as go

def R_nl(r, n, l, a0=1.0):
    """Radial wavefunction for hydrogen atom"""
    rho = 2.0 * r / (n * a0)
    L = genlaguerre(n - l - 1, 2*l + 1)(rho)
    pref = (2.0/(n*a0))**3
    norm = np.sqrt(pref * factorial(n - l - 1) / (2*n * factorial(n + l)))
    return norm * np.exp(-rho/2) * rho**l * L

def psi_nlm_xyz(X, Y, Z, n, l, m, a0=1.0):
    """Complete hydrogen wavefunction in Cartesian coordinates"""
    r = np.sqrt(X*X + Y*Y + Z*Z)
    theta = np.arccos(np.clip(Z / np.where(r == 0, 1.0, r), -1.0, 1.0))
    phi = np.mod(np.arctan2(Y, X), 2*np.pi)
    Ylm = sph_harm(m, l, phi, theta)
    return R_nl(r, n, l, a0=a0) * Ylm

# ----------------------------
# Parameters
# ----------------------------
n, l, m = 2, 1, 1
print(f"═══════════════════════════════════════════════")
print(f"  Hydrogen 2p (m=+1) Probability Current")
print(f"  Using CONE/ARROW Visualization")
print(f"═══════════════════════════════════════════════\n")

extent = 10.0
N = 25  # Resolution for cone grid
x = np.linspace(-extent, extent, N)
y = np.linspace(-extent, extent, N)
z = np.linspace(-extent, extent, N)
dx, dy, dz = x[1]-x[0], y[1]-y[0], z[1]-z[0]

print(f"Grid: {N}×{N}×{N}, extent ±{extent} a₀, spacing {dx:.2f} a₀")

X, Y, Z = np.meshgrid(x, y, z, indexing='ij')
psi = psi_nlm_xyz(X, Y, Z, n, l, m)
rho = np.abs(psi)**2

# Calculate probability current j = Im(ψ* ∇ψ)
dpsi_dx, dpsi_dy, dpsi_dz = np.gradient(psi, dx, dy, dz, axis=(0,1,2))
psi_conj = np.conj(psi)
jx = np.imag(psi_conj * dpsi_dx)
jy = np.imag(psi_conj * dpsi_dy)
jz = np.imag(psi_conj * dpsi_dz)

# Angular momentum verification
Lz = np.sum((X*jy - Y*jx) * dx * dy * dz)
print(f"\nPhysics verification:")
print(f"  Angular momentum Lz = {Lz:.4f} ℏ (expected: {m} ℏ)")
print(f"  Error: {abs(Lz - m)/m * 100:.2f}%")

# Current magnitude
j_mag = np.sqrt(jx**2 + jy**2 + jz**2)
print(f"\nCurrent statistics:")
print(f"  Max magnitude: {j_mag.max():.3e}")
print(f"  Mean magnitude: {j_mag.mean():.3e}")

# Filter by density - only show where electron actually is
# Use adaptive threshold based on percentile
rho_percentile = np.percentile(rho, 75)  # Top 25% density
threshold = max(rho.max() * 1e-4, rho_percentile)
mask = rho > threshold

# Also filter by current magnitude to reduce clutter
j_threshold = j_mag.max() * 0.05  # Only show significant currents
mask = mask & (j_mag > j_threshold)

# Flatten and filter
X_f = X[mask]
Y_f = Y[mask]
Z_f = Z[mask]
jx_f = jx[mask]
jy_f = jy[mask]
jz_f = jz[mask]
rho_f = rho[mask]
j_mag_f = j_mag[mask]

print(f"\nVisualization:")
print(f"  Total grid points: {X.size:,}")
print(f"  Displayed cones: {len(X_f):,} ({100*len(X_f)/X.size:.1f}%)")
print(f"  Density threshold: {threshold:.3e}")
print(f"  Current threshold: {j_threshold:.3e}")

# ----------------------------
# Create enhanced visualization
# ----------------------------
fig = go.Figure()

# Main cone plot - colored by current magnitude
fig.add_trace(go.Cone(
    x=X_f,
    y=Y_f,
    z=Z_f,
    u=jx_f,
    v=jy_f,
    w=jz_f,
    colorscale='Turbo',  # High contrast colormap
    sizemode='scaled',
    sizeref=0.4,  # Smaller cones to reduce overlap
    showscale=True,
    colorbar=dict(
        title=dict(text="Current<br>|j|", font=dict(size=12)),
        thickness=20,
        len=0.7,
        x=1.02,
    ),
    cmin=j_mag_f.min(),
    cmax=j_mag_f.max(),
    name='Current',
    hovertemplate='<b>Position</b><br>' +
                  'x: %{x:.2f} a₀<br>' +
                  'y: %{y:.2f} a₀<br>' +
                  'z: %{z:.2f} a₀<br>' +
                  '<b>Current</b><br>' +
                  'jx: %{u:.3e}<br>' +
                  'jy: %{v:.3e}<br>' +
                  'jz: %{w:.3e}<br>' +
                  '<extra></extra>',
))

# Add coordinate axes for reference
axis_length = extent * 0.7
axes_data = [
    ([axis_length, 0, 0], 'red', 'x-axis'),
    ([0, axis_length, 0], 'green', 'y-axis'),
    ([0, 0, axis_length], 'blue', 'z-axis (Lz)'),
]

for end_pos, color, name in axes_data:
    fig.add_trace(go.Scatter3d(
        x=[0, end_pos[0]],
        y=[0, end_pos[1]],
        z=[0, end_pos[2]],
        mode='lines',
        line=dict(color=color, width=6),
        name=name,
        showlegend=True,
        hoverinfo='name',
    ))

# Add a faint sphere at the Bohr radius for reference
theta_sph = np.linspace(0, np.pi, 20)
phi_sph = np.linspace(0, 2*np.pi, 40)
theta_sph, phi_sph = np.meshgrid(theta_sph, phi_sph)

# Sphere at radius where 2p has maximum radial probability
r_max_2p = 4.0  # ~4 Bohr radii for 2p
x_sph = r_max_2p * np.sin(theta_sph) * np.cos(phi_sph)
y_sph = r_max_2p * np.sin(theta_sph) * np.sin(phi_sph)
z_sph = r_max_2p * np.cos(theta_sph)

fig.add_trace(go.Surface(
    x=x_sph, y=y_sph, z=z_sph,
    colorscale=[[0, 'rgba(200,200,200,0.1)'], [1, 'rgba(200,200,200,0.1)']],
    showscale=False,
    name='Reference sphere (r=4a₀)',
    hoverinfo='name',
    lighting=dict(ambient=0.9, diffuse=0.3),
))

# Layout with detailed annotations
fig.update_layout(
    title=dict(
        text=f"Hydrogen 2p (m=+1) Probability Current<br>" + \
             f"<sub>Toroidal flow around z-axis | ⟨Lz⟩ = {Lz:.3f} ℏ (error: {abs(Lz-m)/m*100:.1f}%)</sub>",
        x=0.5,
        xanchor='center',
        font=dict(size=16),
    ),
    scene=dict(
        xaxis=dict(
            title="x / a₀",
            showbackground=True,
            backgroundcolor="rgba(230, 230, 250, 0.5)",
            gridcolor="white",
            range=[-extent, extent],
        ),
        yaxis=dict(
            title="y / a₀",
            showbackground=True,
            backgroundcolor="rgba(230, 250, 230, 0.5)",
            gridcolor="white",
            range=[-extent, extent],
        ),
        zaxis=dict(
            title="z / a₀",
            showbackground=True,
            backgroundcolor="rgba(250, 230, 230, 0.5)",
            gridcolor="white",
            range=[-extent, extent],
        ),
        aspectmode="cube",
        camera=dict(
            eye=dict(x=1.6, y=1.6, z=1.3),
            center=dict(x=0, y=0, z=0),
        ),
    ),
    margin=dict(l=0, r=120, t=80, b=0),
    showlegend=True,
    legend=dict(
        x=0.02,
        y=0.98,
        bgcolor="rgba(255, 255, 255, 0.8)",
        bordercolor="black",
        borderwidth=1,
    ),
)

# Add annotation explaining the physics
fig.add_annotation(
    text="Arrow direction = current flow<br>" +
         "Arrow color = magnitude<br>" +
         "Blue z-axis = rotation axis",
    xref="paper", yref="paper",
    x=0.02, y=0.02,
    showarrow=False,
    bgcolor="rgba(255, 255, 255, 0.8)",
    bordercolor="black",
    borderwidth=1,
    font=dict(size=10),
)

out_html = "/mnt/user-data/outputs/hydrogen_cone_enhanced.html"
fig.write_html(out_html, include_plotlyjs="cdn")

print(f"\n✓ Saved to: {out_html}")
print(f"\nInterpretation:")
print(f"  • Arrows show direction of electron probability flow")
print(f"  • Color shows current magnitude (red=high, blue=low)")
print(f"  • Pattern should show toroidal (donut) circulation around z-axis")
print(f"  • For m=+1: counterclockwise rotation when viewed from +z")
print(f"  • Reference sphere at r=4a₀ shows typical 2p orbital size")
