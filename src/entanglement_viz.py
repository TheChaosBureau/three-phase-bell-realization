"""
Entangled Sequences Visualizer
==============================
Two counter-rotating helices (positive & negative sequence) represent 
the pre-measurement entangled state. Analyzer bowls show cos²(θ − φ) 
measurement projections. The inverted bowl IS the other particle.

Run:  python entanglement_viz.py
Then open http://localhost:8050

Requires: pip install dash plotly numpy
"""

import numpy as np
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go

# ── Constants ──────────────────────────────────────────────────────
N_HELIX = 600          # points per helix
N_BOWL_TH = 120        # angular resolution of bowl
N_BOWL_R = 40          # radial resolution of bowl
N_TURNS = 5            # helix winding count
T_MAX = 1.0            # total time axis height
BOWL_H = 0.10          # vertical extent of bowl surfaces
HELIX_R = 0.85         # helix radius in α-β plane

# ── Dash app ───────────────────────────────────────────────────────
app = dash.Dash(__name__)
app.title = "Entangled Sequences"

slider_style = {"marginBottom": "18px"}
section_style = {
    "padding": "16px",
    "backgroundColor": "#fafafa",
    "borderRadius": "8px",
    "marginBottom": "12px",
    "border": "1px solid #e0e0e0",
}

app.layout = html.Div(
    [
        html.H2(
            "Entangled Sequences → Measurement",
            style={"textAlign": "center", "fontFamily": "monospace", "marginBottom": "4px"},
        ),
        html.P(
            "Counter-rotating helices collapse into complementary cos²/sin² bowls at measurement.",
            style={"textAlign": "center", "color": "#666", "fontSize": "14px", "marginTop": "0"},
        ),
        html.Div(
            [
                # ── Left panel: controls ──
                html.Div(
                    [
                        # Analyzer A
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.H4("Analyzer A", style={"color": "#1565C0", "margin": "0", "display": "inline-block"}),
                                        dcc.Checklist(
                                            id="a-on",
                                            options=[{"label": " On", "value": "on"}],
                                            value=["on"],
                                            style={"display": "inline-block", "marginLeft": "16px"},
                                            inputStyle={"marginRight": "4px"},
                                        ),
                                    ],
                                    style={"marginBottom": "12px"},
                                ),
                                html.Label("Angle φ_A", style={"fontWeight": "bold", "fontSize": "13px"}),
                                dcc.Slider(
                                    id="phi-a", min=0, max=180, value=0, step=5,
                                    marks={i: f"{i}°" for i in range(0, 181, 45)},
                                    tooltip={"placement": "bottom", "always_visible": False},
                                ),
                                html.Label("Measurement time", style={"fontWeight": "bold", "fontSize": "13px"}),
                                dcc.Slider(
                                    id="t-a", min=0.15, max=0.85, value=0.45, step=0.05,
                                    marks={0.15: "early", 0.5: "mid", 0.85: "late"},
                                    tooltip={"placement": "bottom"},
                                ),
                            ],
                            style=section_style,
                        ),
                        # Analyzer B
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.H4("Analyzer B", style={"color": "#C62828", "margin": "0", "display": "inline-block"}),
                                        dcc.Checklist(
                                            id="b-on",
                                            options=[{"label": " On", "value": "on"}],
                                            value=["on"],
                                            style={"display": "inline-block", "marginLeft": "16px"},
                                            inputStyle={"marginRight": "4px"},
                                        ),
                                    ],
                                    style={"marginBottom": "12px"},
                                ),
                                html.Label("Angle φ_B", style={"fontWeight": "bold", "fontSize": "13px"}),
                                dcc.Slider(
                                    id="phi-b", min=0, max=180, value=90, step=5,
                                    marks={i: f"{i}°" for i in range(0, 181, 45)},
                                    tooltip={"placement": "bottom"},
                                ),
                                html.Label("Measurement time", style={"fontWeight": "bold", "fontSize": "13px"}),
                                dcc.Slider(
                                    id="t-b", min=0.15, max=0.85, value=0.65, step=0.05,
                                    marks={0.15: "early", 0.5: "mid", 0.85: "late"},
                                    tooltip={"placement": "bottom"},
                                ),
                            ],
                            style=section_style,
                        ),
                        # Display options
                        html.Div(
                            [
                                html.H4("Display", style={"margin": "0 0 8px 0"}),
                                dcc.Checklist(
                                    id="show-opts",
                                    options=[
                                        {"label": " Superposition (linear pol.)", "value": "super"},
                                        {"label": " Conservation planes", "value": "planes"},
                                        {"label": " Analyzer axis lines", "value": "axes"},
                                    ],
                                    value=["super", "axes"],
                                    inputStyle={"marginRight": "4px"},
                                    labelStyle={"display": "block", "marginBottom": "4px"},
                                ),
                            ],
                            style=section_style,
                        ),
                        # Info
                        html.Div(
                            id="info-panel",
                            style={
                                "padding": "12px",
                                "backgroundColor": "#fff3e0",
                                "borderRadius": "8px",
                                "fontSize": "13px",
                                "lineHeight": "1.5",
                                "border": "1px solid #ffe0b2",
                            },
                        ),
                    ],
                    style={
                        "width": "300px",
                        "padding": "12px",
                        "flexShrink": "0",
                        "overflowY": "auto",
                        "maxHeight": "90vh",
                    },
                ),
                # ── Right panel: 3D plot ──
                html.Div(
                    [dcc.Graph(id="main-plot", style={"height": "85vh"}, config={"displayModeBar": True})],
                    style={"flexGrow": "1", "minWidth": "0"},
                ),
            ],
            style={"display": "flex", "gap": "12px", "padding": "8px 16px"},
        ),
    ],
    style={"fontFamily": "system-ui, sans-serif", "maxWidth": "1500px", "margin": "auto"},
)


# ── Precompute static geometry ─────────────────────────────────────
_t_helix = np.linspace(0, T_MAX, N_HELIX)
_omega_t = N_TURNS * 2 * np.pi * _t_helix / T_MAX
_hx_pos = HELIX_R * np.cos(_omega_t)
_hy_pos = HELIX_R * np.sin(_omega_t)
_hx_neg = HELIX_R * np.cos(_omega_t)
_hy_neg = -HELIX_R * np.sin(_omega_t)

_bowl_theta = np.linspace(0, 2 * np.pi, N_BOWL_TH)
_bowl_r = np.linspace(0, 1, N_BOWL_R)
_TH, _RR = np.meshgrid(_bowl_theta, _bowl_r)
_BX = _RR * np.cos(_TH)
_BY = _RR * np.sin(_TH)


def _make_bowl(phi, t_meas, inverted, colorscale, name):
    """Generate bowl surface + rim traces."""
    power = np.cos(_TH - phi) ** 2
    if inverted:
        Z = t_meas - power * BOWL_H
    else:
        Z = t_meas + power * BOWL_H

    traces = []

    # Surface
    traces.append(
        go.Surface(
            x=_BX, y=_BY, z=Z,
            colorscale=colorscale,
            opacity=0.82,
            showscale=False,
            name=name,
            hoverinfo="skip",
        )
    )

    # Rim curve
    rim_x = np.cos(_bowl_theta)
    rim_y = np.sin(_bowl_theta)
    rim_power = np.cos(_bowl_theta - phi) ** 2
    if inverted:
        rim_z = t_meas - rim_power * BOWL_H
    else:
        rim_z = t_meas + rim_power * BOWL_H

    traces.append(
        go.Scatter3d(
            x=rim_x, y=rim_y, z=rim_z,
            mode="lines",
            line=dict(color=colorscale[-1][1], width=5),
            name=f"{name} rim",
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # Base circle (reference)
    base_z = np.full_like(_bowl_theta, t_meas)
    traces.append(
        go.Scatter3d(
            x=np.cos(_bowl_theta) * 1.02,
            y=np.sin(_bowl_theta) * 1.02,
            z=base_z,
            mode="lines",
            line=dict(color="rgba(100,100,100,0.3)", width=2),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    return traces


# ── Main callback ──────────────────────────────────────────────────
@app.callback(
    [Output("main-plot", "figure"), Output("info-panel", "children")],
    [
        Input("phi-a", "value"),
        Input("phi-b", "value"),
        Input("a-on", "value"),
        Input("b-on", "value"),
        Input("t-a", "value"),
        Input("t-b", "value"),
        Input("show-opts", "value"),
    ],
)
def update(phi_a_deg, phi_b_deg, a_on, b_on, t_a, t_b, show_opts):
    phi_a = np.radians(phi_a_deg)
    phi_b = np.radians(phi_b_deg)
    a_enabled = "on" in (a_on or [])
    b_enabled = "on" in (b_on or [])
    show_super = "super" in (show_opts or [])
    show_planes = "planes" in (show_opts or [])
    show_axes = "axes" in (show_opts or [])

    fig = go.Figure()

    # ── Helices ────────────────────────────────────────────────────
    fig.add_scatter3d(
        x=_hx_pos, y=_hy_pos, z=_t_helix,
        mode="lines",
        line=dict(color="#1976D2", width=3.5),
        name="+ seq (CCW)",
    )
    fig.add_scatter3d(
        x=_hx_neg, y=_hy_neg, z=_t_helix,
        mode="lines",
        line=dict(color="#E53935", width=3.5),
        name="− seq (CW)",
    )

    # ── Superposition trace (linear polarization) ──────────────────
    if show_super:
        sup_x = HELIX_R * np.cos(_omega_t)
        sup_y = np.zeros(N_HELIX)
        fig.add_scatter3d(
            x=sup_x, y=sup_y, z=_t_helix,
            mode="lines",
            line=dict(color="#43A047", width=2.5, dash="dot"),
            name="superposition",
        )

    # ── Analyzer A bowl (upright) ──────────────────────────────────
    if a_enabled:
        cs_a = [[0, "#BBDEFB"], [0.5, "#64B5F6"], [1, "#1565C0"]]
        for tr in _make_bowl(phi_a, t_a, inverted=False, colorscale=cs_a, name="A: cos²"):
            fig.add_trace(tr)

        if show_axes:
            L = 1.15
            fig.add_scatter3d(
                x=[-L * np.cos(phi_a), L * np.cos(phi_a)],
                y=[-L * np.sin(phi_a), L * np.sin(phi_a)],
                z=[t_a, t_a],
                mode="lines+text",
                line=dict(color="#1565C0", width=5, dash="dash"),
                text=["", f"φ_A={phi_a_deg}°"],
                textposition="top center",
                textfont=dict(size=11, color="#1565C0"),
                name=f"φ_A axis",
                showlegend=False,
            )

    # ── Analyzer B bowl (inverted) ─────────────────────────────────
    if b_enabled:
        cs_b = [[0, "#FFCDD2"], [0.5, "#EF5350"], [1, "#B71C1C"]]
        for tr in _make_bowl(phi_b, t_b, inverted=True, colorscale=cs_b, name="B: cos² (inv)"):
            fig.add_trace(tr)

        if show_axes:
            L = 1.15
            fig.add_scatter3d(
                x=[-L * np.cos(phi_b), L * np.cos(phi_b)],
                y=[-L * np.sin(phi_b), L * np.sin(phi_b)],
                z=[t_b, t_b],
                mode="lines+text",
                line=dict(color="#B71C1C", width=5, dash="dash"),
                text=["", f"φ_B={phi_b_deg}°"],
                textposition="bottom center",
                textfont=dict(size=11, color="#B71C1C"),
                name=f"φ_B axis",
                showlegend=False,
            )

    # ── Conservation planes ────────────────────────────────────────
    if show_planes:
        px = np.array([[-1.3, 1.3], [-1.3, 1.3]])
        py = np.array([[-1.3, -1.3], [1.3, 1.3]])
        if a_enabled:
            pz = np.full_like(px, t_a + BOWL_H)
            fig.add_surface(
                x=px, y=py, z=pz,
                colorscale=[[0, "#E3F2FD"], [1, "#E3F2FD"]],
                opacity=0.12, showscale=False, hoverinfo="skip",
            )
        if b_enabled:
            pz = np.full_like(px, t_b)
            fig.add_surface(
                x=px, y=py, z=pz,
                colorscale=[[0, "#FFEBEE"], [1, "#FFEBEE"]],
                opacity=0.12, showscale=False, hoverinfo="skip",
            )

    # ── Correlation readout in title ───────────────────────────────
    delta_phi = abs(phi_a_deg - phi_b_deg)
    corr = np.cos(phi_a - phi_b) ** 2
    chsh_term = 2 * np.sqrt(2) * corr  # suggestive scaling

    title_text = (
        f"Δφ = {delta_phi}°  │  "
        f"cos²(Δφ) = {corr:.4f}  │  "
        f"E(a,b) = {-np.cos(2*(phi_a - phi_b)):.4f}"
    )

    fig.update_layout(
        scene=dict(
            xaxis_title="α",
            yaxis_title="β",
            zaxis_title="time →",
            aspectmode="manual",
            aspectratio=dict(x=1, y=1, z=1.6),
            camera=dict(
                eye=dict(x=1.7, y=1.3, z=0.7),
                up=dict(x=0, y=0, z=1),
            ),
            xaxis=dict(range=[-1.5, 1.5], showgrid=True, gridcolor="#eee"),
            yaxis=dict(range=[-1.5, 1.5], showgrid=True, gridcolor="#eee"),
            zaxis=dict(range=[0, T_MAX], showgrid=True, gridcolor="#eee"),
            bgcolor="white",
        ),
        margin=dict(l=0, r=0, t=50, b=0),
        legend=dict(
            x=0.01, y=0.99,
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="#ddd",
            borderwidth=1,
            font=dict(size=11),
        ),
        title=dict(text=title_text, x=0.5, font=dict(size=14, family="monospace")),
        paper_bgcolor="white",
    )

    # ── Info panel ─────────────────────────────────────────────────
    info = []
    info.append(html.B("Bell correlation"))
    info.append(html.Br())
    info.append(f"E(a,b) = −cos(2Δφ) = {-np.cos(2*(phi_a - phi_b)):.4f}")
    info.append(html.Br())
    info.append(html.Br())
    info.append(html.B("What you're seeing"))
    info.append(html.Br())
    if delta_phi == 0:
        info.append("Analyzers aligned → perfect anti-correlation. A's peaks are B's valleys.")
    elif delta_phi == 90:
        info.append("Analyzers orthogonal → zero correlation. Bowls rotated 90°, independent.")
    elif delta_phi == 45:
        info.append("45° → maximal CHSH violation angle. This is where S = 2√2 comes from.")
    else:
        info.append(f"Bowls offset by {delta_phi}°. Overlap encodes correlation strength.")
    info.append(html.Br())
    info.append(html.Br())
    info.append(html.B("Conservation"))
    info.append(html.Br())
    info.append("cos²(θ) + sin²(θ) = 1 → bowl + flipped bowl = flat plane (constant total power).")

    return fig, info


if __name__ == "__main__":
    print("\n  ╔══════════════════════════════════════════╗")
    print("  ║   Entangled Sequences Visualizer         ║")
    print("  ║   Open http://localhost:8050              ║")
    print("  ╚══════════════════════════════════════════╝\n")
    app.run(debug=True, port=8050)
