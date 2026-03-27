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
from dash import dcc, html, ctx, no_update
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go

# ── Constants ──────────────────────────────────────────────────────
N_HELIX = 600          # points per helix
N_BOWL_TH = 120        # angular resolution of bowl
N_BOWL_R = 40          # radial resolution of bowl
N_TURNS = 5            # helix winding count
T_MAX = 1.0            # total time axis height
BOWL_H = 0.10          # vertical extent of bowl surfaces
HELIX_R = 0.85         # helix radius in α-β plane
FADE_DUR = 0.06        # bowl fade-in duration (fraction of T_MAX)
TICK_MS = 40           # base interval ms (~25 fps)

# ── Precompute static geometry ─────────────────────────────────────
_t_helix = np.linspace(0, T_MAX, N_HELIX)
_omega_t = N_TURNS * 2 * np.pi * _t_helix / T_MAX
_hx_pos = HELIX_R * np.cos(_omega_t)
_hy_pos = HELIX_R * np.sin(_omega_t)
_hx_neg = HELIX_R * np.cos(_omega_t)
_hy_neg = -HELIX_R * np.sin(_omega_t)
_sup_x = HELIX_R * np.cos(_omega_t)
_sup_y = np.zeros(N_HELIX)

_bowl_theta = np.linspace(0, 2 * np.pi, N_BOWL_TH)
_bowl_r = np.linspace(0, 1, N_BOWL_R)
_TH, _RR = np.meshgrid(_bowl_theta, _bowl_r)
_BX = _RR * np.cos(_TH)
_BY = _RR * np.sin(_TH)


# ── Dash app ───────────────────────────────────────────────────────
app = dash.Dash(__name__)
app.title = "Entangled Sequences"

section_style = {
    "padding": "14px",
    "backgroundColor": "#fafafa",
    "borderRadius": "8px",
    "marginBottom": "10px",
    "border": "1px solid #e0e0e0",
}
btn_base = {
    "padding": "8px 20px",
    "border": "none",
    "borderRadius": "6px",
    "fontWeight": "bold",
    "fontSize": "14px",
    "cursor": "pointer",
    "marginRight": "8px",
}

app.layout = html.Div(
    [
        # Stores & interval
        dcc.Store(id="sim-time", data=0.0),
        dcc.Store(id="is-playing", data=False),
        dcc.Interval(id="tick", interval=TICK_MS, n_intervals=0, disabled=True),

        html.H2(
            "Entangled Sequences \u2192 Measurement",
            style={"textAlign": "center", "fontFamily": "monospace", "marginBottom": "4px"},
        ),
        html.P(
            "Counter-rotating helices collapse into complementary cos\u00b2/sin\u00b2 bowls at measurement.",
            style={"textAlign": "center", "color": "#666", "fontSize": "14px", "marginTop": "0"},
        ),
        html.Div(
            [
                # ── Left panel: controls ──
                html.Div(
                    [
                        # Simulation controls
                        html.Div(
                            [
                                html.H4("Simulation", style={"margin": "0 0 10px 0"}),
                                html.Div(
                                    [
                                        html.Button(
                                            "\u25b6  Play", id="play-btn",
                                            style={**btn_base, "backgroundColor": "#43A047", "color": "white"},
                                        ),
                                        html.Button(
                                            "\u27f2  Reset", id="reset-btn",
                                            style={**btn_base, "backgroundColor": "#757575", "color": "white"},
                                        ),
                                    ],
                                    style={"marginBottom": "12px"},
                                ),
                                html.Label("Speed", style={"fontWeight": "bold", "fontSize": "13px"}),
                                dcc.Slider(
                                    id="speed", min=0.2, max=3.0, value=1.0, step=0.1,
                                    marks={0.2: "0.2\u00d7", 1: "1\u00d7", 2: "2\u00d7", 3: "3\u00d7"},
                                    tooltip={"placement": "bottom"},
                                ),
                                html.Div(
                                    [
                                        dcc.Checklist(
                                            id="loop",
                                            options=[{"label": " Loop", "value": "loop"}],
                                            value=["loop"],
                                            inputStyle={"marginRight": "4px"},
                                            style={"display": "inline-block"},
                                        ),
                                    ],
                                    style={"marginTop": "4px"},
                                ),
                                # Time progress bar
                                html.Div(
                                    [
                                        html.Div(
                                            id="time-bar-fill",
                                            style={
                                                "width": "0%",
                                                "height": "6px",
                                                "backgroundColor": "#43A047",
                                                "borderRadius": "3px",
                                                "transition": "width 0.05s linear",
                                            },
                                        )
                                    ],
                                    style={
                                        "width": "100%",
                                        "height": "6px",
                                        "backgroundColor": "#e0e0e0",
                                        "borderRadius": "3px",
                                        "marginTop": "10px",
                                    },
                                ),
                                html.Div(
                                    id="time-label",
                                    style={"fontSize": "12px", "color": "#888", "marginTop": "4px", "textAlign": "center"},
                                ),
                            ],
                            style={**section_style, "backgroundColor": "#f0f7f0", "border": "1px solid #c8e6c9"},
                        ),
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
                                    style={"marginBottom": "10px"},
                                ),
                                html.Label("Angle \u03c6_A", style={"fontWeight": "bold", "fontSize": "13px"}),
                                dcc.Slider(
                                    id="phi-a", min=0, max=180, value=0, step=5,
                                    marks={i: f"{i}\u00b0" for i in range(0, 181, 45)},
                                    tooltip={"placement": "bottom", "always_visible": False},
                                ),
                                html.Label("Measurement time", style={"fontWeight": "bold", "fontSize": "13px"}),
                                dcc.Slider(
                                    id="t-a", min=0.10, max=0.90, value=0.45, step=0.05,
                                    marks={0.1: "early", 0.5: "mid", 0.9: "late"},
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
                                    style={"marginBottom": "10px"},
                                ),
                                html.Label("Angle \u03c6_B", style={"fontWeight": "bold", "fontSize": "13px"}),
                                dcc.Slider(
                                    id="phi-b", min=0, max=180, value=90, step=5,
                                    marks={i: f"{i}\u00b0" for i in range(0, 181, 45)},
                                    tooltip={"placement": "bottom"},
                                ),
                                html.Label("Measurement time", style={"fontWeight": "bold", "fontSize": "13px"}),
                                dcc.Slider(
                                    id="t-b", min=0.10, max=0.90, value=0.65, step=0.05,
                                    marks={0.1: "early", 0.5: "mid", 0.9: "late"},
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
                        # Info panel
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
                        "width": "310px",
                        "padding": "12px",
                        "flexShrink": "0",
                        "overflowY": "auto",
                        "maxHeight": "92vh",
                    },
                ),
                # ── Right panel: 3D plot ──
                html.Div(
                    [dcc.Graph(id="main-plot", style={"height": "88vh"}, config={"displayModeBar": True})],
                    style={"flexGrow": "1", "minWidth": "0"},
                ),
            ],
            style={"display": "flex", "gap": "12px", "padding": "8px 16px"},
        ),
    ],
    style={"fontFamily": "system-ui, sans-serif", "maxWidth": "1500px", "margin": "auto"},
)


# ── Play / Pause / Reset callbacks ─────────────────────────────────

@app.callback(
    [
        Output("is-playing", "data"),
        Output("tick", "disabled"),
        Output("play-btn", "children"),
        Output("play-btn", "style"),
        Output("sim-time", "data", allow_duplicate=True),
    ],
    [Input("play-btn", "n_clicks"), Input("reset-btn", "n_clicks")],
    [State("is-playing", "data"), State("sim-time", "data")],
    prevent_initial_call=True,
)
def handle_buttons(play_clicks, reset_clicks, playing, t):
    trigger = ctx.triggered_id

    if trigger == "reset-btn":
        return (
            False, True,
            "\u25b6  Play",
            {**btn_base, "backgroundColor": "#43A047", "color": "white"},
            0.0,
        )

    if trigger == "play-btn":
        new_playing = not playing
        if new_playing:
            start_t = 0.0 if t >= T_MAX - 0.01 else t
            return (
                True, False,
                "\u23f8  Pause",
                {**btn_base, "backgroundColor": "#EF6C00", "color": "white"},
                start_t,
            )
        else:
            return (
                False, True,
                "\u25b6  Play",
                {**btn_base, "backgroundColor": "#43A047", "color": "white"},
                no_update,
            )

    return no_update, no_update, no_update, no_update, no_update


@app.callback(
    Output("sim-time", "data"),
    Input("tick", "n_intervals"),
    [
        State("sim-time", "data"),
        State("speed", "value"),
        State("loop", "value"),
        State("is-playing", "data"),
    ],
    prevent_initial_call=True,
)
def advance_time(n, t, speed, loop_val, playing):
    if not playing:
        return no_update
    dt = speed * (TICK_MS / 1000.0) * 0.4  # scale: 1x takes ~2.5s
    t_new = t + dt
    if t_new >= T_MAX:
        if "loop" in (loop_val or []):
            return 0.0
        else:
            return T_MAX
    return t_new


# ── Helper: make bowl with optional opacity ────────────────────────

def _make_bowl(phi, t_meas, inverted, colorscale, name, opacity=0.82):
    power = np.cos(_TH - phi) ** 2
    if inverted:
        Z = t_meas - power * BOWL_H
    else:
        Z = t_meas + power * BOWL_H

    traces = []
    traces.append(
        go.Surface(
            x=_BX, y=_BY, z=Z,
            colorscale=colorscale,
            opacity=opacity,
            showscale=False,
            name=name,
            hoverinfo="skip",
        )
    )

    rim_x = np.cos(_bowl_theta)
    rim_y = np.sin(_bowl_theta)
    rim_power = np.cos(_bowl_theta - phi) ** 2
    rim_z = (t_meas - rim_power * BOWL_H) if inverted else (t_meas + rim_power * BOWL_H)

    traces.append(
        go.Scatter3d(
            x=rim_x, y=rim_y, z=rim_z,
            mode="lines",
            line=dict(color=colorscale[-1][1], width=5),
            showlegend=False, hoverinfo="skip",
        )
    )

    base_z = np.full_like(_bowl_theta, t_meas)
    traces.append(
        go.Scatter3d(
            x=np.cos(_bowl_theta) * 1.02,
            y=np.sin(_bowl_theta) * 1.02,
            z=base_z,
            mode="lines",
            line=dict(color="rgba(100,100,100,0.3)", width=2),
            showlegend=False, hoverinfo="skip",
        )
    )
    return traces


# ── Main render callback ───────────────────────────────────────────

@app.callback(
    [
        Output("main-plot", "figure"),
        Output("info-panel", "children"),
        Output("time-bar-fill", "style"),
        Output("time-label", "children"),
    ],
    [
        Input("sim-time", "data"),
        Input("phi-a", "value"),
        Input("phi-b", "value"),
        Input("a-on", "value"),
        Input("b-on", "value"),
        Input("t-a", "value"),
        Input("t-b", "value"),
        Input("show-opts", "value"),
    ],
)
def update(t_now, phi_a_deg, phi_b_deg, a_on, b_on, t_a, t_b, show_opts):
    phi_a = np.radians(phi_a_deg)
    phi_b = np.radians(phi_b_deg)
    a_enabled = "on" in (a_on or [])
    b_enabled = "on" in (b_on or [])
    show_super = "super" in (show_opts or [])
    show_planes = "planes" in (show_opts or [])
    show_axes = "axes" in (show_opts or [])

    fig = go.Figure()

    t_now = max(0.0, min(t_now, T_MAX))
    idx_cut = max(2, int(t_now / T_MAX * N_HELIX))

    # ── Helices (drawn up to current time) ─────────────────────────
    fig.add_scatter3d(
        x=_hx_pos[:idx_cut], y=_hy_pos[:idx_cut], z=_t_helix[:idx_cut],
        mode="lines",
        line=dict(color="#1976D2", width=3.5),
        name="+ seq (CCW)",
    )
    fig.add_scatter3d(
        x=_hx_neg[:idx_cut], y=_hy_neg[:idx_cut], z=_t_helix[:idx_cut],
        mode="lines",
        line=dict(color="#E53935", width=3.5),
        name="\u2212 seq (CW)",
    )

    # ── Wavefront dots at helix tips ───────────────────────────────
    tip = max(0, idx_cut - 1)
    fig.add_scatter3d(
        x=[_hx_pos[tip]], y=[_hy_pos[tip]], z=[_t_helix[tip]],
        mode="markers",
        marker=dict(size=7, color="#1976D2", symbol="diamond",
                    line=dict(width=1, color="white")),
        showlegend=False, hoverinfo="skip",
    )
    fig.add_scatter3d(
        x=[_hx_neg[tip]], y=[_hy_neg[tip]], z=[_t_helix[tip]],
        mode="markers",
        marker=dict(size=7, color="#E53935", symbol="diamond",
                    line=dict(width=1, color="white")),
        showlegend=False, hoverinfo="skip",
    )

    # ── Superposition trace ────────────────────────────────────────
    if show_super:
        fig.add_scatter3d(
            x=_sup_x[:idx_cut], y=_sup_y[:idx_cut], z=_t_helix[:idx_cut],
            mode="lines",
            line=dict(color="#43A047", width=2.5, dash="dot"),
            name="superposition",
        )

    # ── Analyzer bowls (appear & fade in when time reaches them) ───
    def bowl_opacity(t_meas):
        if t_now < t_meas:
            return 0.0
        frac = min(1.0, (t_now - t_meas) / FADE_DUR)
        return 0.15 + 0.67 * frac

    if a_enabled and t_now >= t_a:
        op = bowl_opacity(t_a)
        cs_a = [[0, "#BBDEFB"], [0.5, "#64B5F6"], [1, "#1565C0"]]
        for tr in _make_bowl(phi_a, t_a, inverted=False, colorscale=cs_a, name="A: cos\u00b2", opacity=op):
            fig.add_trace(tr)
        if show_axes:
            L = 1.15
            fig.add_scatter3d(
                x=[-L * np.cos(phi_a), L * np.cos(phi_a)],
                y=[-L * np.sin(phi_a), L * np.sin(phi_a)],
                z=[t_a, t_a],
                mode="lines+text",
                line=dict(color="#1565C0", width=5, dash="dash"),
                text=["", f"\u03c6_A={phi_a_deg}\u00b0"],
                textposition="top center",
                textfont=dict(size=11, color="#1565C0"),
                showlegend=False,
            )

    if b_enabled and t_now >= t_b:
        op = bowl_opacity(t_b)
        cs_b = [[0, "#FFCDD2"], [0.5, "#EF5350"], [1, "#B71C1C"]]
        for tr in _make_bowl(phi_b, t_b, inverted=True, colorscale=cs_b, name="B: cos\u00b2 (inv)", opacity=op):
            fig.add_trace(tr)
        if show_axes:
            L = 1.15
            fig.add_scatter3d(
                x=[-L * np.cos(phi_b), L * np.cos(phi_b)],
                y=[-L * np.sin(phi_b), L * np.sin(phi_b)],
                z=[t_b, t_b],
                mode="lines+text",
                line=dict(color="#B71C1C", width=5, dash="dash"),
                text=["", f"\u03c6_B={phi_b_deg}\u00b0"],
                textposition="bottom center",
                textfont=dict(size=11, color="#B71C1C"),
                showlegend=False,
            )

    # ── Conservation planes ────────────────────────────────────────
    if show_planes:
        px = np.array([[-1.3, 1.3], [-1.3, 1.3]])
        py = np.array([[-1.3, -1.3], [1.3, 1.3]])
        if a_enabled and t_now >= t_a:
            pz = np.full_like(px, t_a + BOWL_H)
            fig.add_surface(
                x=px, y=py, z=pz,
                colorscale=[[0, "#E3F2FD"], [1, "#E3F2FD"]],
                opacity=0.12, showscale=False, hoverinfo="skip",
            )
        if b_enabled and t_now >= t_b:
            pz = np.full_like(px, t_b)
            fig.add_surface(
                x=px, y=py, z=pz,
                colorscale=[[0, "#FFEBEE"], [1, "#FFEBEE"]],
                opacity=0.12, showscale=False, hoverinfo="skip",
            )

    # ── Title ──────────────────────────────────────────────────────
    delta_phi = abs(phi_a_deg - phi_b_deg)
    corr = np.cos(phi_a - phi_b) ** 2
    e_ab = -np.cos(2 * (phi_a - phi_b))
    title_text = (
        f"\u0394\u03c6 = {delta_phi}\u00b0  \u2502  "
        f"cos\u00b2(\u0394\u03c6) = {corr:.4f}  \u2502  "
        f"E(a,b) = {e_ab:.4f}"
    )

    # ── Phase label ────────────────────────────────────────────────
    a_measured = a_enabled and t_now >= t_a
    b_measured = b_enabled and t_now >= t_b
    both_measured = a_measured and b_measured
    if t_now < 0.01:
        phase = "ready"
    elif not a_measured and not b_measured:
        phase = "propagating"
    elif a_measured and not b_measured:
        phase = "A measured"
    elif not a_measured and b_measured:
        phase = "B measured"
    else:
        phase = "both measured"

    fig.update_layout(
        scene=dict(
            xaxis_title="\u03b1",
            yaxis_title="\u03b2",
            zaxis_title="time \u2192",
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
            bordercolor="#ddd", borderwidth=1,
            font=dict(size=11),
        ),
        title=dict(text=title_text, x=0.5, font=dict(size=14, family="monospace")),
        paper_bgcolor="white",
        uirevision="locked",  # preserve camera across animation frames
    )

    # ── Info panel ─────────────────────────────────────────────────
    phase_colors = {
        "ready": "#888",
        "propagating": "#43A047",
        "A measured": "#1565C0",
        "B measured": "#C62828",
        "both measured": "#6A1B9A",
    }
    info = []
    info.append(html.B("Bell correlation"))
    info.append(html.Br())
    info.append(f"E(a,b) = \u2212cos(2\u0394\u03c6) = {e_ab:.4f}")
    info.append(html.Br())
    info.append(html.Br())
    info.append(html.B("Phase: "))
    info.append(html.Span(phase, style={"color": phase_colors.get(phase, "#333"), "fontWeight": "bold"}))
    info.append(html.Br())
    info.append(html.Br())
    info.append(html.B("What you're seeing"))
    info.append(html.Br())
    if phase == "ready":
        info.append("Press Play to start the simulation.")
    elif phase == "propagating":
        info.append("Entangled pair propagating \u2014 two counter-rotating helices, no definite state yet.")
    elif phase == "A measured" :
        info.append("A has measured \u2014 bowl projects cos\u00b2(\u03b8\u2212\u03c6_A). B still propagating.")
    elif phase == "B measured":
        info.append("B has measured \u2014 inverted bowl projects cos\u00b2(\u03b8\u2212\u03c6_B). A still propagating.")
    elif delta_phi == 0:
        info.append("Analyzers aligned \u2192 perfect anti-correlation. A's peaks are B's valleys.")
    elif delta_phi == 90:
        info.append("Analyzers orthogonal \u2192 zero correlation. Bowls rotated 90\u00b0, independent.")
    elif delta_phi == 45:
        info.append("45\u00b0 \u2192 maximal CHSH violation angle. This is where S = 2\u221a2 comes from.")
    else:
        info.append(f"Bowls offset by {delta_phi}\u00b0. Overlap encodes correlation strength.")
    info.append(html.Br())
    info.append(html.Br())
    info.append(html.B("Conservation"))
    info.append(html.Br())
    info.append("cos\u00b2(\u03b8) + sin\u00b2(\u03b8) = 1 \u2192 bowl + flipped bowl = flat plane (constant total power).")

    # ── Time bar ───────────────────────────────────────────────────
    pct = min(100, t_now / T_MAX * 100)
    bar_color = phase_colors.get(phase, "#43A047")
    bar_style = {
        "width": f"{pct:.1f}%",
        "height": "6px",
        "backgroundColor": bar_color,
        "borderRadius": "3px",
        "transition": "width 0.04s linear",
    }
    time_label = f"t = {t_now:.3f} / {T_MAX:.1f}  [{phase}]"

    return fig, info, bar_style, time_label


# ── Entry point ────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n  \u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557")
    print("  \u2551   Entangled Sequences Visualizer         \u2551")
    print("  \u2551   Open http://localhost:8050              \u2551")
    print("  \u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d\n")
    app.run(debug=True, port=8050)
