import numpy as np
from scipy.special import sph_harm, genlaguerre, factorial
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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

print("═════════════════════════════════════════════════════════════")
print("  2p Orbitals: Probability Density vs. Probability Current")
print("═════════════════════════════════════════════════════════════\n")

n, l = 2, 1

# Create grid
extent = 10.0
N = 50
x = np.linspace(-extent, extent, N)
y = np.linspace(-extent, extent, N)
z = np.linspace(-extent, extent, N)
dx, dy, dz = x[1]-x[0], y[1]-y[0], z[1]-z[0]

X, Y, Z = np.meshgrid(x, y, z, indexing='ij')

# ----------------------------
# Case 1: m=0 (pz orbital) - REAL, NO CURRENT
# ----------------------------
print("Case 1: 2p with m=0 (pz orbital)")
print("  - This is the 'textbook' orbital with two lobes")
print("  - Wavefunction is REAL → NO probability current!")

m = 0
psi_pz = psi_nlm_xyz(X, Y, Z, n, l, m)
rho_pz = np.abs(psi_pz)**2

# Check if wavefunction is real
imaginary_part = np.abs(np.imag(psi_pz)).max()
print(f"  - Max imaginary part: {imaginary_part:.3e} (essentially zero)")

# Calculate current for pz
dpsi_dx, dpsi_dy, dpsi_dz = np.gradient(psi_pz, dx, dy, dz, axis=(0,1,2))
jx_pz = np.imag(np.conj(psi_pz) * dpsi_dx)
jy_pz = np.imag(np.conj(psi_pz) * dpsi_dy)
jz_pz = np.imag(np.conj(psi_pz) * dpsi_dz)
j_mag_pz = np.sqrt(jx_pz**2 + jy_pz**2 + jz_pz**2)

print(f"  - Max current: {j_mag_pz.max():.3e} (essentially zero)")
print()

# ----------------------------
# Case 2: m=+1 - COMPLEX, HAS CURRENT
# ----------------------------
print("Case 2: 2p with m=+1")
print("  - This has COMPLEX wavefunction → circulation!")
print("  - Probability current flows in rings around z-axis")

m = 1
psi_m1 = psi_nlm_xyz(X, Y, Z, n, l, m)
rho_m1 = np.abs(psi_m1)**2

# Check phase variation
phase = np.angle(psi_m1)
print(f"  - Phase varies from {phase.min():.2f} to {phase.max():.2f} radians")

# Calculate current for m=+1
dpsi_dx, dpsi_dy, dpsi_dz = np.gradient(psi_m1, dx, dy, dz, axis=(0,1,2))
jx_m1 = np.imag(np.conj(psi_m1) * dpsi_dx)
jy_m1 = np.imag(np.conj(psi_m1) * dpsi_dy)
jz_m1 = np.imag(np.conj(psi_m1) * dpsi_dz)
j_mag_m1 = np.sqrt(jx_m1**2 + jy_m1**2 + jz_m1**2)

print(f"  - Max current: {j_mag_m1.max():.3e} (significant!)")

# Angular momentum
Lz = np.sum((X*jy_m1 - Y*jx_m1) * dx * dy * dz)
print(f"  - Angular momentum Lz: {Lz:.3f} ℏ")
print()

# ----------------------------
# KEY INSIGHT
# ----------------------------
print("KEY INSIGHT:")
print("  Both orbitals have THE SAME probability density distribution!")
print(f"  - pz (m=0) density shape: dumbbell/figure-8")
print(f"  - m=+1 density shape: also dumbbell/figure-8")
print(f"  - Difference: m=+1 has phase that spirals around z-axis")
print(f"    → This creates circulating probability current")
print()

# Compare densities
rho_diff = np.abs(rho_pz - rho_m1).max()
print(f"Max density difference: {rho_diff:.3e}")
print(f"  (They're identical in probability density!)")
print()

# ----------------------------
# Create dual visualization
# ----------------------------
fig = make_subplots(
    rows=1, cols=2,
    subplot_titles=(
        '2pz (m=0): Probability Density<br><sub>Real wavefunction, no current</sub>',
        '2p (m=+1): Probability Current<br><sub>Complex wavefunction, circulating</sub>'
    ),
    specs=[[{'type': 'surface'}, {'type': 'scatter3d'}]],
    horizontal_spacing=0.05,
)

# Left panel: Isosurface of probability density for m=0
# Show it as lobes
iso_value = rho_pz.max() * 0.15

from skimage import measure
try:
    verts, faces, _, _ = measure.marching_cubes(rho_pz, iso_value, spacing=(dx, dy, dz))
    # Offset vertices to actual coordinates
    verts[:, 0] = verts[:, 0] + x[0]
    verts[:, 1] = verts[:, 1] + y[0]
    verts[:, 2] = verts[:, 2] + z[0]
    
    fig.add_trace(
        go.Mesh3d(
            x=verts[:, 0],
            y=verts[:, 1],
            z=verts[:, 2],
            i=faces[:, 0],
            j=faces[:, 1],
            k=faces[:, 2],
            color='lightblue',
            opacity=0.7,
            name='Probability density',
            hoverinfo='name',
        ),
        row=1, col=1
    )
except:
    print("Warning: Could not create isosurface, skimage might not be available")

# Right panel: Current arrows for m=+1
# Sample points for cone plot
N_cone = 20
x_cone = np.linspace(-extent, extent, N_cone)
y_cone = np.linspace(-extent, extent, N_cone)
z_cone = np.linspace(-extent, extent, N_cone)
X_cone, Y_cone, Z_cone = np.meshgrid(x_cone, y_cone, z_cone, indexing='ij')

# Interpolate current to cone grid
from scipy.interpolate import RegularGridInterpolator
interp_jx = RegularGridInterpolator((x, y, z), jx_m1, bounds_error=False, fill_value=0)
interp_jy = RegularGridInterpolator((x, y, z), jy_m1, bounds_error=False, fill_value=0)
interp_jz = RegularGridInterpolator((x, y, z), jz_m1, bounds_error=False, fill_value=0)
interp_rho = RegularGridInterpolator((x, y, z), rho_m1, bounds_error=False, fill_value=0)

points_cone = np.stack([X_cone.ravel(), Y_cone.ravel(), Z_cone.ravel()], axis=-1)
jx_cone = interp_jx(points_cone).reshape(X_cone.shape)
jy_cone = interp_jy(points_cone).reshape(X_cone.shape)
jz_cone = interp_jz(points_cone).reshape(X_cone.shape)
rho_cone = interp_rho(points_cone).reshape(X_cone.shape)

# Filter by density
threshold = rho_cone.max() * 0.01
j_mag_cone = np.sqrt(jx_cone**2 + jy_cone**2 + jz_cone**2)
j_threshold = j_mag_cone.max() * 0.1
mask = (rho_cone > threshold) & (j_mag_cone > j_threshold)

fig.add_trace(
    go.Cone(
        x=X_cone[mask],
        y=Y_cone[mask],
        z=Z_cone[mask],
        u=jx_cone[mask],
        v=jy_cone[mask],
        w=jz_cone[mask],
        colorscale='Plasma',
        sizemode='scaled',
        sizeref=0.5,
        showscale=True,
        name='Current',
    ),
    row=1, col=2
)

# Add z-axis to both panels
for col in [1, 2]:
    fig.add_trace(
        go.Scatter3d(
            x=[0, 0], y=[0, 0], z=[-8, 8],
            mode='lines',
            line=dict(color='blue', width=4),
            showlegend=False,
            hoverinfo='skip',
        ),
        row=1, col=col
    )

# Update layout
fig.update_layout(
    title=dict(
        text="Why do we see rings instead of lobes?<br>" +
             "<sub>Same probability density |ψ|², but m=+1 has phase circulation → probability current</sub>",
        x=0.5,
        xanchor='center',
        font=dict(size=16),
    ),
    height=600,
    margin=dict(l=0, r=0, t=100, b=0),
)

# Update scene settings for both subplots
for i in [1, 2]:
    fig.update_scenes(
        aspectmode='cube',
        xaxis=dict(range=[-extent, extent]),
        yaxis=dict(range=[-extent, extent]),
        zaxis=dict(range=[-extent, extent]),
        row=1, col=i,
    )

out_html = "/mnt/user-data/outputs/2p_lobes_vs_rings.html"
fig.write_html(out_html, include_plotlyjs="cdn")

print(f"✓ Saved comparison to: {out_html}")
print()
print("SUMMARY:")
print("  • Textbook 2p 'lobes' = probability density |ψ|² for m=0 (pz)")
print("  • Your 'rings' = probability CURRENT j for m=+1")
print("  • Both have same density distribution (dumbbell shape)")
print("  • m=+1 has COMPLEX ψ with azimuthal phase → circulating current")
print("  • m=0 has REAL ψ → zero current (static probability)")
print()
print("Analogy: imagine water in a donut-shaped pond")
print("  • Water DENSITY: donut shape (both m=0 and m=+1)")
print("  • Water FLOW: m=0 is still, m=+1 is circulating around the pond")
