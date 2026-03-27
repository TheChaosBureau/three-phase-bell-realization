"""
Notebook-grounded Clarke-surface model:
v_abc(θ) = [2V cos θ, -V cos θ, -V cos θ] is the balanced equal-sequence
construction used in the notebook. The Clarke map sends v_abc -> (v_α, v_β, v_0),
and with resistive normalization i_α = v_α / R, i_β = v_β / R the normalized
surface height is p_αβ(θ) = v_α i_α + v_β i_β ∝ cos²(θ - φ). The Dash scene treats
that Clarke-space energy as vertical relief, so integrated relief reads as volume.
A 180° azimuth flip, φ -> φ + π, preserves the same surface and can be read as the
partner viewpoint, while the helix handedness sign selects positive-sequence (CCW)
versus negative-sequence (CW) convention for the whole pair.
"""

import numpy as np
import dash
from dash import dcc, html, ctx, no_update
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go

# ── Constants ──────────────────────────────────────────────────────
N_HELIX = 600
N_BOWL_TH = 120
N_BOWL_R = 40
N_TURNS = 5
T_MAX = 1.0
BOWL_H = 0.10
HELIX_R = 0.85
FADE_DUR = 0.06
TICK_MS = 40

BREATH_AMP = 0.08
BREATH_CYCLES = 3.0
HELIX_BREATH_GAIN = 0.45
SUPER_BREATH_GAIN = 0.65
SURFACE_BREATH_GAIN = 1.75
SURFACE_RIM_GAIN = 0.35
TIP_BREATH_GAIN = 1.25

PRIMARY_COLOR = "#1565C0"
PARTNER_COLOR = "#C62828"
SUPER_COLOR = "#2E7D32"

# ── Static grids ───────────────────────────────────────────────────
_t_helix = np.linspace(0.0, T_MAX, N_HELIX)
_bowl_theta = np.linspace(0.0, 2.0 * np.pi, N_BOWL_TH)
_bowl_r = np.linspace(0.0, 1.0, N_BOWL_R)
_TH, _RR = np.meshgrid(_bowl_theta, _bowl_r)
_BX = _RR * np.cos(_TH)
_BY = _RR * np.sin(_TH)


# ── Model helpers ──────────────────────────────────────────────────
def phase_progression(time, handedness=1):
    """Helix phase as a function of propagation time and sequence sign."""
    time = np.asarray(time, dtype=float)
    return handedness * N_TURNS * 2.0 * np.pi * time / T_MAX


def breathing_envelope(sim_time):
    """Global positive breathing factor used throughout the animation."""
    sim_time = np.asarray(sim_time, dtype=float)
    return 1.0 + BREATH_AMP * np.sin(2.0 * np.pi * BREATH_CYCLES * sim_time / T_MAX)


def breathing_scale(sim_time, gain=1.0):
    """Convert the shared envelope into a gain-specific scale."""
    return 1.0 + gain * (breathing_envelope(sim_time) - 1.0)


def helix_coords(time, handedness, branch_sign=1, radius_scale=1.0):
    """Partner helices are the same winding seen with a 180° azimuth flip."""
    phase = phase_progression(time, handedness=handedness)
    radius = HELIX_R * np.asarray(radius_scale, dtype=float)
    x = branch_sign * radius * np.cos(phase)
    y = branch_sign * radius * np.sin(phase)
    return x, y


def superposition_coords(time, radius_scale=1.0):
    """The notebook's balanced Clarke trace stays on the α axis."""
    phase = phase_progression(time, handedness=1)
    radius = HELIX_R * np.asarray(radius_scale, dtype=float)
    x = radius * np.cos(phase)
    y = np.zeros_like(x)
    return x, y


def viewpoint_flipped_angle(phi):
    return (np.asarray(phi, dtype=float) + np.pi) % (2.0 * np.pi)


def clarke_energy_profile(theta, phi):
    """Normalized p_αβ profile from the equal-sequence Clarke construction."""
    theta = np.asarray(theta, dtype=float)
    return np.cos(theta - phi) ** 2


def analyzer_surface_height(theta, phi, measurement_time, inverted=False, breathing=1.0, height_scale=1.0):
    """Energy height at analyzer azimuth φ, offset around the measurement plane."""
    direction = -1.0 if inverted else 1.0
    return measurement_time + direction * BOWL_H * height_scale * breathing * clarke_energy_profile(theta, phi)


def analyzer_surface(phi, measurement_time, inverted=False, breathing=1.0, height_scale=1.0, radius_scale=1.0):
    x = radius_scale * _BX
    y = radius_scale * _BY
    z = analyzer_surface_height(
        _TH,
        phi,
        measurement_time,
        inverted=inverted,
        breathing=breathing,
        height_scale=height_scale,
    )
    return x, y, z


def complementary_surface_sum(theta, phi, measurement_time=0.5, breathing=1.0, height_scale=1.0):
    return analyzer_surface_height(
        theta,
        phi,
        measurement_time,
        inverted=False,
        breathing=breathing,
        height_scale=height_scale,
    ) + analyzer_surface_height(
        theta,
        phi,
        measurement_time,
        inverted=True,
        breathing=breathing,
        height_scale=height_scale,
    )


def handedness_label(handedness):
    return "positive-sequence / CCW" if handedness > 0 else "negative-sequence / CW"


def measurement_opacity(sim_time, measurement_time):
    if sim_time < measurement_time:
        return 0.0
    fade = min(1.0, (sim_time - measurement_time) / FADE_DUR)
    return 0.18 + 0.66 * fade


def simulation_phase(sim_time, t_a, t_b, a_enabled, b_enabled):
    a_measured = a_enabled and sim_time >= t_a
    b_measured = b_enabled and sim_time >= t_b
    if sim_time < 0.01:
        return "ready", a_measured, b_measured
    if not a_measured and not b_measured:
        return "propagating", a_measured, b_measured
    if a_measured and not b_measured:
        return "A measured", a_measured, b_measured
    if not a_measured and b_measured:
        return "B measured", a_measured, b_measured
    return "both measured", a_measured, b_measured


def bell_metrics(phi_a, phi_b):
    delta = abs(np.degrees(phi_a - phi_b))
    corr = np.cos(phi_a - phi_b) ** 2
    e_ab = -np.cos(2.0 * (phi_a - phi_b))
    return delta, corr, e_ab


def clamp_time(sim_time):
    return max(0.0, min(float(sim_time), T_MAX))


def surface_trace_bundle(phi, t_meas, inverted, colorscale, name, sim_time, surface_scale):
    opacity = measurement_opacity(sim_time, t_meas)
    if opacity <= 0.0:
        return []

    radius_scale = 1.0 + SURFACE_RIM_GAIN * (surface_scale - 1.0)
    x, y, z = analyzer_surface(
        phi,
        t_meas,
        inverted=inverted,
        breathing=1.0,
        height_scale=surface_scale,
        radius_scale=radius_scale,
    )
    theta = _bowl_theta
    rim_energy = analyzer_surface_height(
        theta,
        phi,
        t_meas,
        inverted=inverted,
        breathing=1.0,
        height_scale=surface_scale,
    )
    rim_x = radius_scale * np.cos(theta)
    rim_y = radius_scale * np.sin(theta)
    rim_width = 4.5 + 12.0 * abs(surface_scale - 1.0) / max(BREATH_AMP * SURFACE_BREATH_GAIN, 1e-9)
    traces = [
        go.Surface(
            x=x,
            y=y,
            z=z,
            surfacecolor=clarke_energy_profile(_TH, phi),
            colorscale=colorscale,
            opacity=opacity,
            showscale=False,
            name=name,
            hoverinfo="skip",
        ),
        go.Scatter3d(
            x=rim_x,
            y=rim_y,
            z=rim_energy,
            mode="lines",
            line=dict(color=colorscale[-1][1], width=rim_width),
            showlegend=False,
            hoverinfo="skip",
        ),
        go.Scatter3d(
            x=1.02 * np.cos(theta),
            y=1.02 * np.sin(theta),
            z=np.full_like(theta, t_meas),
            mode="lines",
            line=dict(color="rgba(90,90,90,0.28)", width=2.0),
            showlegend=False,
            hoverinfo="skip",
        ),
    ]
    return traces


def info_panel_children(phase, delta_phi, e_ab, handedness, breathing_value, surface_scale):
    phase_colors = {
        "ready": "#888",
        "propagating": "#43A047",
        "A measured": PRIMARY_COLOR,
        "B measured": PARTNER_COLOR,
        "both measured": "#6A1B9A",
    }

    children = [
        html.B("Clarke-space model"),
        html.Br(),
        f"Handedness: {handedness_label(handedness)}.",
        html.Br(),
        "The partner read is the same rim after a 180° azimuth flip.",
        html.Br(),
        html.Br(),
        html.B("Bell correlation"),
        html.Br(),
        f"E(a,b) = -cos(2Δφ) = {e_ab:.4f}",
        html.Br(),
        html.Br(),
        html.B("Phase: "),
        html.Span(phase, style={"color": phase_colors.get(phase, "#333"), "fontWeight": "bold"}),
        html.Br(),
        html.Br(),
        html.B("Breathing envelope"),
        html.Br(),
        f"Global pulse = {breathing_value:.3f}×, energy surfaces = {surface_scale:.3f}× height.",
        html.Br(),
        html.Br(),
        html.B("What you're seeing"),
        html.Br(),
    ]

    if phase == "ready":
        children.append("Press Play to launch the Clarke-space pair and its shared breathing envelope.")
    elif phase == "propagating":
        children.append(
            "Pre-measurement geometry is a propagating entangled pair in Clarke space; the dotted α trace is the balanced three-phase superposition."
        )
    elif phase == "A measured":
        children.append("Analyzer A has projected a Clarke-energy surface. Height tracks instantaneous pαβ and its bowl volume reads the accumulated energy.")
    elif phase == "B measured":
        children.append("Analyzer B has projected the partner energy surface. The inverted relief keeps the conservation read secondary to the energy volume.")
    elif delta_phi == 0:
        children.append("Aligned analyzers preserve the same energy ridge, so the partner view is a pure inversion about the measurement plane.")
    elif delta_phi == 90:
        children.append("Orthogonal analyzers rotate the Clarke energy ridge by 90°, flattening the Bell correlation.")
    elif delta_phi == 45:
        children.append("At 45° the paired surfaces are offset by the CHSH-optimal angle while still sharing the same Clarke-space volume story.")
    else:
        children.append(f"The analyzer rims are offset by {delta_phi:.0f}°, so the rotated energy surfaces encode the current correlation.")

    children.extend(
        [
            html.Br(),
            html.Br(),
            html.B("Conservation"),
            html.Br(),
            "Upright and inverted surfaces are complementary around the measurement plane, so the flat-sum reference remains a secondary conservation cue.",
        ]
    )
    return children


# ── Dash app ───────────────────────────────────────────────────────
app = dash.Dash(__name__)
app.title = "Clarke-Space Entanglement"

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
        dcc.Store(id="sim-time", data=0.0),
        dcc.Store(id="is-playing", data=False),
        dcc.Interval(id="tick", interval=TICK_MS, n_intervals=0, disabled=True),
        html.H2(
            "Clarke-Space Entanglement Surface",
            style={"textAlign": "center", "fontFamily": "monospace", "marginBottom": "4px"},
        ),
        html.P(
            "The propagating pair lives in Clarke α-β space; analyzer bowls are pαβ energy projections, and a 180° azimuth flip reads the partner view.",
            style={"textAlign": "center", "color": "#666", "fontSize": "14px", "marginTop": "0"},
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.H4("Simulation", style={"margin": "0 0 10px 0"}),
                                html.Div(
                                    [
                                        html.Button(
                                            "\u25b6  Play",
                                            id="play-btn",
                                            style={**btn_base, "backgroundColor": "#43A047", "color": "white"},
                                        ),
                                        html.Button(
                                            "\u27f2  Reset",
                                            id="reset-btn",
                                            style={**btn_base, "backgroundColor": "#757575", "color": "white"},
                                        ),
                                    ],
                                    style={"marginBottom": "12px"},
                                ),
                                html.Label("Helix convention", style={"fontWeight": "bold", "fontSize": "13px"}),
                                dcc.Checklist(
                                    id="handedness-toggle",
                                    options=[{"label": " Negative handedness (CW / negative sequence)", "value": "negative"}],
                                    value=[],
                                    inputStyle={"marginRight": "4px"},
                                    labelStyle={"display": "block", "marginBottom": "8px", "marginTop": "4px"},
                                ),
                                html.Label("Speed", style={"fontWeight": "bold", "fontSize": "13px"}),
                                dcc.Slider(
                                    id="speed",
                                    min=0.2,
                                    max=3.0,
                                    value=1.0,
                                    step=0.1,
                                    marks={0.2: "0.2×", 1: "1×", 2: "2×", 3: "3×"},
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
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.H4("Analyzer A", style={"color": PRIMARY_COLOR, "margin": "0", "display": "inline-block"}),
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
                                html.Label("Angle φ_A", style={"fontWeight": "bold", "fontSize": "13px"}),
                                dcc.Slider(
                                    id="phi-a",
                                    min=0,
                                    max=180,
                                    value=0,
                                    step=5,
                                    marks={i: f"{i}°" for i in range(0, 181, 45)},
                                    tooltip={"placement": "bottom", "always_visible": False},
                                ),
                                html.Label("Measurement time", style={"fontWeight": "bold", "fontSize": "13px"}),
                                dcc.Slider(
                                    id="t-a",
                                    min=0.10,
                                    max=0.90,
                                    value=0.45,
                                    step=0.05,
                                    marks={0.1: "early", 0.5: "mid", 0.9: "late"},
                                    tooltip={"placement": "bottom"},
                                ),
                            ],
                            style=section_style,
                        ),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.H4("Analyzer B", style={"color": PARTNER_COLOR, "margin": "0", "display": "inline-block"}),
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
                                html.Label("Angle φ_B", style={"fontWeight": "bold", "fontSize": "13px"}),
                                dcc.Slider(
                                    id="phi-b",
                                    min=0,
                                    max=180,
                                    value=90,
                                    step=5,
                                    marks={i: f"{i}°" for i in range(0, 181, 45)},
                                    tooltip={"placement": "bottom"},
                                ),
                                html.Label("Measurement time", style={"fontWeight": "bold", "fontSize": "13px"}),
                                dcc.Slider(
                                    id="t-b",
                                    min=0.10,
                                    max=0.90,
                                    value=0.65,
                                    step=0.05,
                                    marks={0.1: "early", 0.5: "mid", 0.9: "late"},
                                    tooltip={"placement": "bottom"},
                                ),
                            ],
                            style=section_style,
                        ),
                        html.Div(
                            [
                                html.H4("Display", style={"margin": "0 0 8px 0"}),
                                dcc.Checklist(
                                    id="show-opts",
                                    options=[
                                        {"label": " Clarke superposition trace", "value": "super"},
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
def handle_buttons(play_clicks, reset_clicks, playing, sim_time):
    trigger = ctx.triggered_id

    if trigger == "reset-btn":
        return (
            False,
            True,
            "\u25b6  Play",
            {**btn_base, "backgroundColor": "#43A047", "color": "white"},
            0.0,
        )

    if trigger == "play-btn":
        new_playing = not playing
        if new_playing:
            start_t = 0.0 if sim_time >= T_MAX - 0.01 else sim_time
            return (
                True,
                False,
                "\u23f8  Pause",
                {**btn_base, "backgroundColor": "#EF6C00", "color": "white"},
                start_t,
            )
        return (
            False,
            True,
            "\u25b6  Play",
            {**btn_base, "backgroundColor": "#43A047", "color": "white"},
            no_update,
        )

    return no_update, no_update, no_update, no_update, no_update


@app.callback(
    Output("sim-time", "data"),
    Input("tick", "n_intervals"),
    [State("sim-time", "data"), State("speed", "value"), State("loop", "value"), State("is-playing", "data")],
    prevent_initial_call=True,
)
def advance_time(n_intervals, sim_time, speed, loop_val, playing):
    if not playing:
        return no_update

    dt = speed * (TICK_MS / 1000.0) * 0.4
    new_time = sim_time + dt
    if new_time >= T_MAX:
        return 0.0 if "loop" in (loop_val or []) else T_MAX
    return new_time


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
        Input("handedness-toggle", "value"),
    ],
)
def update(sim_time, phi_a_deg, phi_b_deg, a_on, b_on, t_a, t_b, show_opts, handedness_toggle):
    sim_time = clamp_time(sim_time)
    phi_a = np.radians(phi_a_deg)
    phi_b = np.radians(phi_b_deg)
    handedness = -1 if "negative" in (handedness_toggle or []) else 1
    a_enabled = "on" in (a_on or [])
    b_enabled = "on" in (b_on or [])
    show_super = "super" in (show_opts or [])
    show_planes = "planes" in (show_opts or [])
    show_axes = "axes" in (show_opts or [])

    idx_cut = max(2, int(sim_time / T_MAX * N_HELIX))
    visible_time = _t_helix[:idx_cut]
    breathing_value = float(breathing_envelope(sim_time))
    helix_scale = float(breathing_scale(sim_time, HELIX_BREATH_GAIN))
    super_scale = float(breathing_scale(sim_time, SUPER_BREATH_GAIN))
    surface_scale = float(breathing_scale(sim_time, SURFACE_BREATH_GAIN))
    tip_size = 7.0 * float(breathing_scale(sim_time, TIP_BREATH_GAIN))
    phase, a_measured, b_measured = simulation_phase(sim_time, t_a, t_b, a_enabled, b_enabled)
    delta_phi, corr, e_ab = bell_metrics(phi_a, phi_b)

    fig = go.Figure()

    primary_x, primary_y = helix_coords(visible_time, handedness=handedness, branch_sign=1, radius_scale=helix_scale)
    partner_x, partner_y = helix_coords(visible_time, handedness=handedness, branch_sign=-1, radius_scale=helix_scale)

    fig.add_scatter3d(
        x=primary_x,
        y=primary_y,
        z=visible_time,
        mode="lines",
        line=dict(color=PRIMARY_COLOR, width=4.0),
        name=f"reference helix ({handedness_label(handedness)})",
    )
    fig.add_scatter3d(
        x=partner_x,
        y=partner_y,
        z=visible_time,
        mode="lines",
        line=dict(color=PARTNER_COLOR, width=4.0),
        name="partner helix (φ + 180°)",
    )

    tip = max(0, idx_cut - 1)
    for x_val, y_val, color in (
        (primary_x[tip], primary_y[tip], PRIMARY_COLOR),
        (partner_x[tip], partner_y[tip], PARTNER_COLOR),
    ):
        fig.add_scatter3d(
            x=[x_val],
            y=[y_val],
            z=[visible_time[tip]],
            mode="markers",
            marker=dict(size=tip_size, color=color, symbol="diamond", line=dict(width=1, color="white")),
            showlegend=False,
            hoverinfo="skip",
        )

    if show_super:
        super_x, super_y = superposition_coords(visible_time, radius_scale=super_scale)
        fig.add_scatter3d(
            x=super_x,
            y=super_y,
            z=visible_time,
            mode="lines",
            line=dict(color=SUPER_COLOR, width=3.0, dash="dot"),
            name="balanced Clarke trace",
        )

    if a_enabled:
        colorscale_a = [[0, "#E3F2FD"], [0.55, "#64B5F6"], [1, PRIMARY_COLOR]]
        for trace in surface_trace_bundle(
            phi_a,
            t_a,
            inverted=False,
            colorscale=colorscale_a,
            name="A energy surface",
            sim_time=sim_time,
            surface_scale=surface_scale,
        ):
            fig.add_trace(trace)
        if show_axes and a_measured:
            length = 1.15
            fig.add_scatter3d(
                x=[-length * np.cos(phi_a), length * np.cos(phi_a)],
                y=[-length * np.sin(phi_a), length * np.sin(phi_a)],
                z=[t_a, t_a],
                mode="lines+text",
                line=dict(color=PRIMARY_COLOR, width=5, dash="dash"),
                text=["", f"φ_A={phi_a_deg}°"],
                textposition="top center",
                textfont=dict(size=11, color=PRIMARY_COLOR),
                showlegend=False,
            )

    if b_enabled:
        colorscale_b = [[0, "#FFEBEE"], [0.55, "#EF5350"], [1, PARTNER_COLOR]]
        for trace in surface_trace_bundle(
            phi_b,
            t_b,
            inverted=True,
            colorscale=colorscale_b,
            name="B energy surface",
            sim_time=sim_time,
            surface_scale=surface_scale,
        ):
            fig.add_trace(trace)
        if show_axes and b_measured:
            length = 1.15
            fig.add_scatter3d(
                x=[-length * np.cos(phi_b), length * np.cos(phi_b)],
                y=[-length * np.sin(phi_b), length * np.sin(phi_b)],
                z=[t_b, t_b],
                mode="lines+text",
                line=dict(color=PARTNER_COLOR, width=5, dash="dash"),
                text=["", f"φ_B={phi_b_deg}°"],
                textposition="bottom center",
                textfont=dict(size=11, color=PARTNER_COLOR),
                showlegend=False,
            )

    if show_planes:
        px = np.array([[-1.3, 1.3], [-1.3, 1.3]])
        py = np.array([[-1.3, -1.3], [1.3, 1.3]])
        if a_measured:
            fig.add_surface(
                x=px,
                y=py,
                z=np.full_like(px, t_a),
                colorscale=[[0, "#E3F2FD"], [1, "#E3F2FD"]],
                opacity=0.08,
                showscale=False,
                hoverinfo="skip",
            )
        if b_measured:
            fig.add_surface(
                x=px,
                y=py,
                z=np.full_like(px, t_b),
                colorscale=[[0, "#FFEBEE"], [1, "#FFEBEE"]],
                opacity=0.08,
                showscale=False,
                hoverinfo="skip",
            )

    title_text = f"Δφ = {delta_phi:.0f}°  │  cos²(Δφ) = {corr:.4f}  │  E(a,b) = {e_ab:.4f}"
    fig.update_layout(
        scene=dict(
            xaxis_title="α",
            yaxis_title="β",
            zaxis_title="propagation / pαβ height",
            aspectmode="manual",
            aspectratio=dict(x=1, y=1, z=1.6),
            camera=dict(eye=dict(x=1.7, y=1.3, z=0.7), up=dict(x=0, y=0, z=1)),
            xaxis=dict(range=[-1.5, 1.5], showgrid=True, gridcolor="#eee"),
            yaxis=dict(range=[-1.5, 1.5], showgrid=True, gridcolor="#eee"),
            zaxis=dict(range=[0, T_MAX], showgrid=True, gridcolor="#eee"),
            bgcolor="white",
        ),
        margin=dict(l=0, r=0, t=50, b=0),
        legend=dict(
            x=0.01,
            y=0.99,
            bgcolor="rgba(255,255,255,0.88)",
            bordercolor="#ddd",
            borderwidth=1,
            font=dict(size=11),
        ),
        title=dict(text=title_text, x=0.5, font=dict(size=14, family="monospace")),
        paper_bgcolor="white",
        uirevision="locked",
    )

    info = info_panel_children(phase, delta_phi, e_ab, handedness, breathing_value, surface_scale)
    pct = min(100.0, sim_time / T_MAX * 100.0)
    phase_colors = {
        "ready": "#888",
        "propagating": "#43A047",
        "A measured": PRIMARY_COLOR,
        "B measured": PARTNER_COLOR,
        "both measured": "#6A1B9A",
    }
    bar_style = {
        "width": f"{pct:.1f}%",
        "height": "6px",
        "backgroundColor": phase_colors.get(phase, "#43A047"),
        "borderRadius": "3px",
        "transition": "width 0.04s linear",
    }
    time_label = f"t = {sim_time:.3f} / {T_MAX:.1f}  [{phase}, {handedness_label(handedness)}]"

    return fig, info, bar_style, time_label


# ── Entry point ────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n  ╔══════════════════════════════════════════╗")
    print("  ║   Clarke-Space Entanglement Surface     ║")
    print("  ║   Open http://localhost:8050            ║")
    print("  ╚══════════════════════════════════════════╝\n")
    app.run(debug=True, port=8050)
