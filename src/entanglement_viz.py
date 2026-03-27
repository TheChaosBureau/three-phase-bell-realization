"""
Rigorous Clarke-space entanglement view.

The app now keeps geometry and accounting separate:

- The 3D scene uses z only as a propagation coordinate.
- Detector planes are flat disks whose colors encode the literal analyzer response.
- A linked accounting plot shows the actual theta-dependent power profiles.

Because the paper currently uses two related but not identical constructions, the app
exposes them explicitly:

1. Sequence response (paper Sec. 4):
   P_A(theta) = cos^2(theta - phi_A)
   P_B(theta) = sin^2(theta - phi_B)

2. Three-party closure (paper Sec. 6):
   P_A(theta) = cos^2(theta - phi_A)
   P_B(theta) = cos^2(theta - phi_B)
   P_0(theta) = 1 - P_A(theta) - P_B(theta)

The Bell correlation readout E(a,b) = -cos(2Δφ) is retained as an analytic overlay
and is labeled as such in the UI.
"""

import numpy as np
import dash
from dash import dcc, html, ctx, no_update
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go

# ── Constants ──────────────────────────────────────────────────────
N_PATH = 600
N_DISK_TH = 160
N_DISK_R = 48
N_TURNS = 5
T_MAX = 1.0
HELIX_R = 0.85
DISK_R = 1.0
TICK_MS = 40

MODEL_SEQUENCE = "sequence"
MODEL_CLOSURE = "closure"

POSITIVE_COLOR = "#1565C0"
NEGATIVE_COLOR = "#C62828"
SUPER_COLOR = "#2E7D32"
A_COLOR = "#0D47A1"
B_COLOR = "#B71C1C"
CHANNEL_COLOR = "#FF8F00"
RESIDUAL_COLOR = "#616161"
PRIMARY_COLOR = A_COLOR
PARTNER_COLOR = B_COLOR

# Retained for compatibility with earlier helpers and tests; the rigorous scene does
# not use any breathing modulation.
BREATH_AMP = 0.0
BREATH_CYCLES = 0.0
HELIX_BREATH_GAIN = 0.0
SUPER_BREATH_GAIN = 0.0
SURFACE_BREATH_GAIN = 0.0
SURFACE_RIM_GAIN = 0.0
TIP_BREATH_GAIN = 0.0
BOWL_H = 0.10
FADE_DUR = 0.06

# ── Static grids ───────────────────────────────────────────────────
_path_t = np.linspace(0.0, T_MAX, N_PATH)
_profile_theta = np.linspace(0.0, 2.0 * np.pi, 721)
_disk_theta = np.linspace(0.0, 2.0 * np.pi, N_DISK_TH)
_disk_r = np.linspace(0.0, DISK_R, N_DISK_R)
_TH, _RR = np.meshgrid(_disk_theta, _disk_r)
_DISK_X = _RR * np.cos(_TH)
_DISK_Y = _RR * np.sin(_TH)


# ── Legacy-compatible helpers ──────────────────────────────────────
def phase_progression(time, handedness=1):
    """Phase angle as a function of normalized propagation coordinate."""
    time = np.asarray(time, dtype=float)
    return handedness * N_TURNS * 2.0 * np.pi * time / T_MAX


def breathing_envelope(sim_time):
    """Legacy helper; the rigorous view uses no non-physical breathing."""
    sim_time = np.asarray(sim_time, dtype=float)
    return np.ones_like(sim_time, dtype=float)


def breathing_scale(sim_time, gain=1.0):
    return np.ones_like(np.asarray(sim_time, dtype=float), dtype=float)


def helix_coords(time, handedness, branch_sign=1, radius_scale=1.0):
    """
    Legacy helper retained for continuity.

    branch_sign = -1 produces a pi azimuth shift at fixed handedness.
    """
    phase = phase_progression(time, handedness=handedness)
    radius = HELIX_R * np.asarray(radius_scale, dtype=float)
    x = branch_sign * radius * np.cos(phase)
    y = branch_sign * radius * np.sin(phase)
    return x, y


def superposition_coords(time, radius_scale=1.0):
    """Equal positive and negative sequences collapse to a fixed alpha-axis swing."""
    phase = phase_progression(time, handedness=1)
    radius = HELIX_R * np.asarray(radius_scale, dtype=float)
    x = radius * np.cos(phase)
    y = np.zeros_like(x)
    return x, y


def viewpoint_flipped_angle(phi):
    return (np.asarray(phi, dtype=float) + np.pi) % (2.0 * np.pi)


def handedness_label(handedness):
    return "positive-sequence / CCW" if handedness > 0 else "negative-sequence / CW"


def clarke_energy_profile(theta, phi):
    theta = np.asarray(theta, dtype=float)
    return np.cos(theta - phi) ** 2


def analyzer_surface_height(theta, phi, measurement_time, inverted=False, breathing=1.0, height_scale=1.0):
    """
    Legacy helper retained so the prior surface interpretation can still be inspected.

    The rigorous Dash scene no longer uses height as energy.
    """
    direction = -1.0 if inverted else 1.0
    return measurement_time + direction * BOWL_H * height_scale * breathing * clarke_energy_profile(theta, phi)


def analyzer_surface(phi, measurement_time, inverted=False, breathing=1.0, height_scale=1.0, radius_scale=1.0):
    x = radius_scale * _DISK_X
    y = radius_scale * _DISK_Y
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


def measurement_opacity(sim_time, measurement_time):
    if sim_time < measurement_time:
        return 0.0
    fade = min(1.0, (sim_time - measurement_time) / max(FADE_DUR, 1e-9))
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


# ── Rigorous model helpers ─────────────────────────────────────────
def positive_sequence_coords(time, radius_scale=1.0):
    phase = phase_progression(time, handedness=1)
    radius = HELIX_R * np.asarray(radius_scale, dtype=float)
    return radius * np.cos(phase), radius * np.sin(phase)


def negative_sequence_coords(time, radius_scale=1.0):
    phase = phase_progression(time, handedness=-1)
    radius = HELIX_R * np.asarray(radius_scale, dtype=float)
    return radius * np.cos(phase), radius * np.sin(phase)


def complementary_energy_profile(theta, phi):
    theta = np.asarray(theta, dtype=float)
    return np.sin(theta - phi) ** 2


def sequence_response_profiles(theta, phi_a, phi_b):
    p_a = clarke_energy_profile(theta, phi_a)
    p_b = complementary_energy_profile(theta, phi_b)
    residual = 1.0 - p_a - p_b
    return p_a, p_b, residual


def three_party_profiles(theta, phi_a, phi_b):
    p_a = clarke_energy_profile(theta, phi_a)
    p_b = clarke_energy_profile(theta, phi_b)
    p_0 = 1.0 - p_a - p_b
    return p_a, p_b, p_0


def current_hidden_phase(sim_time):
    return float(np.mod(phase_progression(sim_time, handedness=1), 2.0 * np.pi))


def periodic_value(theta_star, phi, complementary=False):
    if complementary:
        return float(complementary_energy_profile(theta_star, phi))
    return float(clarke_energy_profile(theta_star, phi))


def bell_metrics(phi_a, phi_b):
    delta = abs(np.degrees(phi_a - phi_b))
    corr = np.cos(phi_a - phi_b) ** 2
    e_ab = -np.cos(2.0 * (phi_a - phi_b))
    return delta, corr, e_ab


def clamp_time(sim_time):
    return max(0.0, min(float(sim_time), T_MAX))


def model_metadata(model_key):
    if model_key == MODEL_CLOSURE:
        return {
            "name": "Three-party closure",
            "formula": "P_A = cos²(θ-φ_A),  P_B = cos²(θ-φ_B),  P_0 = 1 - P_A - P_B",
            "extra_label": "P_0(θ)",
            "extra_name": "channel / P_0",
        }
    return {
        "name": "Sequence response",
        "formula": "P_A = cos²(θ-φ_A),  P_B = sin²(θ-φ_B)",
        "extra_label": "1 - P_A - P_B",
        "extra_name": "closure residual",
    }


def detector_plane_trace(z_plane, surfacecolor, name, colorscale, cmin, cmax, opacity=0.95):
    theta_deg = np.degrees(_TH) % 360.0
    return go.Surface(
        x=_DISK_X,
        y=_DISK_Y,
        z=np.full_like(_DISK_X, z_plane),
        surfacecolor=surfacecolor,
        colorscale=colorscale,
        cmin=cmin,
        cmax=cmax,
        opacity=opacity,
        showscale=False,
        name=name,
        customdata=theta_deg,
        hovertemplate=f"{name}<br>θ=%{{customdata:.1f}}°<br>value=%{{surfacecolor:.4f}}<extra></extra>",
    )


def disk_outline_trace(z_plane, color, name):
    theta = _disk_theta
    return go.Scatter3d(
        x=DISK_R * np.cos(theta),
        y=DISK_R * np.sin(theta),
        z=np.full_like(theta, z_plane),
        mode="lines",
        line=dict(color=color, width=4.0),
        name=name,
        hoverinfo="skip",
        showlegend=False,
    )


def detector_axis_trace(phi, z_plane, color, label):
    length = 1.12 * DISK_R
    return go.Scatter3d(
        x=[-length * np.cos(phi), length * np.cos(phi)],
        y=[-length * np.sin(phi), length * np.sin(phi)],
        z=[z_plane, z_plane],
        mode="lines+text",
        line=dict(color=color, width=6, dash="dash"),
        text=["", label],
        textposition="top center",
        textfont=dict(size=11, color=color),
        showlegend=False,
        hoverinfo="skip",
    )


def hidden_phase_marker(theta_star, z_plane, color, name):
    return go.Scatter3d(
        x=[DISK_R * np.cos(theta_star)],
        y=[DISK_R * np.sin(theta_star)],
        z=[z_plane],
        mode="markers",
        marker=dict(size=6, color=color, line=dict(width=1, color="white")),
        name=name,
        showlegend=False,
        hovertemplate=f"{name}<br>θ*={np.degrees(theta_star):.1f}°<extra></extra>",
    )


def build_scene_figure(sim_time, phi_a, phi_b, z_a, z_b, model_key, show_super, show_channel, show_axes):
    theta_star = current_hidden_phase(sim_time)
    model = model_metadata(model_key)

    fig = go.Figure()

    pos_x, pos_y = positive_sequence_coords(_path_t)
    neg_x, neg_y = negative_sequence_coords(_path_t)
    fig.add_scatter3d(
        x=pos_x,
        y=pos_y,
        z=_path_t,
        mode="lines",
        line=dict(color=POSITIVE_COLOR, width=4.0),
        name="positive sequence (+)",
    )
    fig.add_scatter3d(
        x=neg_x,
        y=neg_y,
        z=_path_t,
        mode="lines",
        line=dict(color=NEGATIVE_COLOR, width=4.0),
        name="negative sequence (-)",
    )

    if show_super:
        sup_x, sup_y = superposition_coords(_path_t)
        fig.add_scatter3d(
            x=sup_x,
            y=sup_y,
            z=_path_t,
            mode="lines",
            line=dict(color=SUPER_COLOR, width=3.0, dash="dot"),
            name="equal-sequence superposition",
        )

    sample_x_pos, sample_y_pos = positive_sequence_coords(np.array([sim_time]))
    sample_x_neg, sample_y_neg = negative_sequence_coords(np.array([sim_time]))
    fig.add_scatter3d(
        x=sample_x_pos,
        y=sample_y_pos,
        z=[sim_time],
        mode="markers",
        marker=dict(size=7, color=POSITIVE_COLOR, line=dict(width=1, color="white")),
        name="sample on + sequence",
        showlegend=False,
    )
    fig.add_scatter3d(
        x=sample_x_neg,
        y=sample_y_neg,
        z=[sim_time],
        mode="markers",
        marker=dict(size=7, color=NEGATIVE_COLOR, line=dict(width=1, color="white")),
        name="sample on - sequence",
        showlegend=False,
    )

    p_a_disk = clarke_energy_profile(_TH, phi_a)
    if model_key == MODEL_CLOSURE:
        p_b_disk = clarke_energy_profile(_TH, phi_b)
        p_extra_disk = 1.0 - p_a_disk - p_b_disk
    else:
        p_b_disk = complementary_energy_profile(_TH, phi_b)
        p_extra_disk = 1.0 - p_a_disk - p_b_disk

    fig.add_trace(
        detector_plane_trace(
            z_a,
            p_a_disk,
            "A plane: P_A",
            [[0.0, "#E3F2FD"], [0.6, "#64B5F6"], [1.0, A_COLOR]],
            0.0,
            1.0,
        )
    )
    fig.add_trace(disk_outline_trace(z_a, A_COLOR, "A outline"))
    fig.add_trace(hidden_phase_marker(theta_star, z_a, A_COLOR, "A θ*"))

    fig.add_trace(
        detector_plane_trace(
            z_b,
            p_b_disk,
            "B plane: P_B",
            [[0.0, "#FFEBEE"], [0.6, "#EF5350"], [1.0, B_COLOR]],
            0.0,
            1.0,
        )
    )
    fig.add_trace(disk_outline_trace(z_b, B_COLOR, "B outline"))
    fig.add_trace(hidden_phase_marker(theta_star, z_b, B_COLOR, "B θ*"))

    if show_channel and model_key == MODEL_CLOSURE:
        z_mid = 0.5 * (z_a + z_b)
        fig.add_trace(
            detector_plane_trace(
                z_mid,
                p_extra_disk,
                "channel plane: P_0",
                [[0.0, "#6D4C41"], [0.5, "#FFF3E0"], [1.0, "#1B5E20"]],
                -1.0,
                1.0,
                opacity=0.92,
            )
        )
        fig.add_trace(disk_outline_trace(z_mid, CHANNEL_COLOR, "channel outline"))
        fig.add_trace(hidden_phase_marker(theta_star, z_mid, CHANNEL_COLOR, "P_0 θ*"))

    if show_axes:
        fig.add_trace(detector_axis_trace(phi_a, z_a, A_COLOR, f"φ_A={np.degrees(phi_a):.0f}°"))
        fig.add_trace(detector_axis_trace(phi_b, z_b, B_COLOR, f"φ_B={np.degrees(phi_b):.0f}°"))

    title = (
        "Propagation in Clarke α-β space; detector disks encode response by color"
        if model_key == MODEL_SEQUENCE
        else "Propagation in Clarke α-β space with explicit three-party closure disk"
    )

    fig.update_layout(
        scene=dict(
            xaxis_title="α",
            yaxis_title="β",
            zaxis_title="propagation z",
            aspectmode="manual",
            aspectratio=dict(x=1, y=1, z=1.55),
            camera=dict(eye=dict(x=1.7, y=1.35, z=0.85), up=dict(x=0, y=0, z=1)),
            xaxis=dict(range=[-1.35, 1.35], showgrid=True, gridcolor="#ececec"),
            yaxis=dict(range=[-1.35, 1.35], showgrid=True, gridcolor="#ececec"),
            zaxis=dict(range=[0.0, T_MAX], showgrid=True, gridcolor="#ececec"),
            bgcolor="white",
        ),
        margin=dict(l=0, r=0, t=45, b=0),
        paper_bgcolor="white",
        title=dict(text=title, x=0.5, font=dict(size=14, family="monospace")),
        legend=dict(
            x=0.01,
            y=0.99,
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#ddd",
            borderwidth=1,
            font=dict(size=11),
        ),
        uirevision="locked",
    )
    return fig


def build_accounting_figure(sim_time, phi_a, phi_b, model_key):
    theta = _profile_theta
    theta_deg = np.degrees(theta)
    theta_star = current_hidden_phase(sim_time)
    theta_star_deg = np.degrees(theta_star)
    model = model_metadata(model_key)

    if model_key == MODEL_CLOSURE:
        p_a, p_b, p_extra = three_party_profiles(theta, phi_a, phi_b)
        extra_name = model["extra_label"]
        extra_color = CHANNEL_COLOR
    else:
        p_a, p_b, p_extra = sequence_response_profiles(theta, phi_a, phi_b)
        extra_name = model["extra_label"]
        extra_color = RESIDUAL_COLOR

    p_a_star = periodic_value(theta_star, phi_a, complementary=False)
    p_b_star = periodic_value(theta_star, phi_b, complementary=(model_key == MODEL_SEQUENCE))
    p_extra_star = float(1.0 - p_a_star - p_b_star)

    fig = go.Figure()
    fig.add_scatter(
        x=theta_deg,
        y=p_a,
        mode="lines",
        line=dict(color=A_COLOR, width=3),
        name="P_A(θ)",
    )
    fig.add_scatter(
        x=theta_deg,
        y=p_b,
        mode="lines",
        line=dict(color=B_COLOR, width=3),
        name="P_B(θ)",
    )
    fig.add_scatter(
        x=theta_deg,
        y=p_extra,
        mode="lines",
        line=dict(color=extra_color, width=2.5, dash="dash"),
        name=extra_name,
    )

    fig.add_vline(x=theta_star_deg, line_dash="dot", line_color="#424242", line_width=1.5)
    for y_val, color, name in (
        (p_a_star, A_COLOR, "P_A(θ*)"),
        (p_b_star, B_COLOR, "P_B(θ*)"),
        (p_extra_star, extra_color, f"{extra_name} at θ*"),
    ):
        fig.add_scatter(
            x=[theta_star_deg],
            y=[y_val],
            mode="markers",
            marker=dict(size=8, color=color, line=dict(width=1, color="white")),
            name=name,
            showlegend=False,
        )

    fig.add_hline(y=0.0, line_dash="dot", line_color="#bdbdbd", line_width=1)
    fig.add_hline(y=1.0, line_dash="dot", line_color="#bdbdbd", line_width=1)

    fig.update_layout(
        title=dict(text=model["formula"], x=0.5, font=dict(size=13, family="monospace")),
        margin=dict(l=55, r=20, t=48, b=45),
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis=dict(
            title="hidden phase θ (degrees)",
            range=[0, 360],
            dtick=45,
            showgrid=True,
            gridcolor="#efefef",
        ),
        yaxis=dict(
            title="normalized power / residual",
            range=[-1.1, 1.1],
            showgrid=True,
            gridcolor="#efefef",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0.0,
            bgcolor="rgba(255,255,255,0.9)",
        ),
    )
    return fig


def info_panel_children(sim_time, phi_a, phi_b, model_key):
    theta_star = current_hidden_phase(sim_time)
    delta_phi, corr, e_ab = bell_metrics(phi_a, phi_b)
    model = model_metadata(model_key)

    if model_key == MODEL_CLOSURE:
        p_a, p_b, p_extra = three_party_profiles(_profile_theta, phi_a, phi_b)
        extra_name = "P_0"
        closure_error = np.max(np.abs(p_a + p_b + p_extra - 1.0))
    else:
        p_a, p_b, p_extra = sequence_response_profiles(_profile_theta, phi_a, phi_b)
        extra_name = "1 - P_A - P_B"
        closure_error = np.max(np.abs((p_a + p_b + p_extra) - 1.0))

    p_a_star = periodic_value(theta_star, phi_a, complementary=False)
    p_b_star = periodic_value(theta_star, phi_b, complementary=(model_key == MODEL_SEQUENCE))
    p_extra_star = float(1.0 - p_a_star - p_b_star)

    return [
        html.B("Rigorous mapping"),
        html.Br(),
        f"Model: {model['name']}.",
        html.Br(),
        model["formula"],
        html.Br(),
        html.Br(),
        html.B("Current sample"),
        html.Br(),
        f"z = {sim_time:.3f}, θ* = {np.degrees(theta_star):.1f}°.",
        html.Br(),
        f"P_A(θ*) = {p_a_star:.4f}, P_B(θ*) = {p_b_star:.4f}, {extra_name}(θ*) = {p_extra_star:.4f}.",
        html.Br(),
        html.Br(),
        html.B("Averaged quantities"),
        html.Br(),
        f"⟨P_A⟩ = {np.mean(p_a):.4f}, ⟨P_B⟩ = {np.mean(p_b):.4f}.",
        html.Br(),
        f"{extra_name} range = [{np.min(p_extra):.4f}, {np.max(p_extra):.4f}].",
        html.Br(),
        f"Closure check max|P_A + P_B + extra - 1| = {closure_error:.2e}.",
        html.Br(),
        html.Br(),
        html.B("Analytic overlay"),
        html.Br(),
        f"Δφ = {delta_phi:.1f}°, cos²(Δφ) = {corr:.4f}.",
        html.Br(),
        f"E(a,b) = -cos(2Δφ) = {e_ab:.4f}.",
        html.Br(),
        "The Bell value is displayed as the paper's analytic quadratic-correlation law; this app does not simulate binary outcomes.",
    ]


# ── Dash app ───────────────────────────────────────────────────────
app = dash.Dash(__name__)
app.title = "Rigorous Clarke-Space Entanglement"

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
            "Rigorous Clarke-Space Entanglement",
            style={"textAlign": "center", "fontFamily": "monospace", "marginBottom": "4px"},
        ),
        html.P(
            "Propagation is shown in Clarke α-β-z geometry; detector planes encode literal analyzer response by color, and the lower plot shows the full θ-dependent accounting.",
            style={"textAlign": "center", "color": "#555", "fontSize": "14px", "marginTop": "0"},
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
                                html.Label("Propagation speed", style={"fontWeight": "bold", "fontSize": "13px"}),
                                dcc.Slider(
                                    id="speed",
                                    min=0.2,
                                    max=3.0,
                                    value=1.0,
                                    step=0.1,
                                    marks={0.2: "0.2×", 1: "1×", 2: "2×", 3: "3×"},
                                    tooltip={"placement": "bottom"},
                                ),
                                dcc.Checklist(
                                    id="loop",
                                    options=[{"label": " Loop propagation sample", "value": "loop"}],
                                    value=["loop"],
                                    inputStyle={"marginRight": "4px"},
                                    style={"marginTop": "6px"},
                                ),
                                html.Div(
                                    [html.Div(id="time-bar-fill", style={"width": "0%", "height": "6px", "backgroundColor": "#43A047", "borderRadius": "3px"})],
                                    style={"width": "100%", "height": "6px", "backgroundColor": "#e0e0e0", "borderRadius": "3px", "marginTop": "10px"},
                                ),
                                html.Div(
                                    id="time-label",
                                    style={"fontSize": "12px", "color": "#666", "marginTop": "4px", "textAlign": "center"},
                                ),
                            ],
                            style={**section_style, "backgroundColor": "#f0f7f0", "border": "1px solid #c8e6c9"},
                        ),
                        html.Div(
                            [
                                html.H4("Equation Set", style={"margin": "0 0 8px 0"}),
                                dcc.RadioItems(
                                    id="model-selector",
                                    options=[
                                        {
                                            "label": " Sequence response: P_A = cos²(θ-φ_A), P_B = sin²(θ-φ_B)",
                                            "value": MODEL_SEQUENCE,
                                        },
                                        {
                                            "label": " Three-party closure: P_A = cos²(θ-φ_A), P_B = cos²(θ-φ_B), P_0 = 1 - P_A - P_B",
                                            "value": MODEL_CLOSURE,
                                        },
                                    ],
                                    value=MODEL_CLOSURE,
                                    labelStyle={"display": "block", "marginBottom": "8px"},
                                    inputStyle={"marginRight": "6px"},
                                ),
                            ],
                            style=section_style,
                        ),
                        html.Div(
                            [
                                html.H4("Detector A", style={"color": A_COLOR, "margin": "0 0 10px 0"}),
                                html.Label("Analyzer angle φ_A", style={"fontWeight": "bold", "fontSize": "13px"}),
                                dcc.Slider(
                                    id="phi-a",
                                    min=0,
                                    max=180,
                                    value=0,
                                    step=5,
                                    marks={i: f"{i}°" for i in range(0, 181, 45)},
                                    tooltip={"placement": "bottom"},
                                ),
                                html.Label("Detector plane z_A", style={"fontWeight": "bold", "fontSize": "13px"}),
                                dcc.Slider(
                                    id="t-a",
                                    min=0.10,
                                    max=0.90,
                                    value=0.35,
                                    step=0.05,
                                    marks={0.1: "0.1", 0.5: "0.5", 0.9: "0.9"},
                                    tooltip={"placement": "bottom"},
                                ),
                            ],
                            style=section_style,
                        ),
                        html.Div(
                            [
                                html.H4("Detector B", style={"color": B_COLOR, "margin": "0 0 10px 0"}),
                                html.Label("Analyzer angle φ_B", style={"fontWeight": "bold", "fontSize": "13px"}),
                                dcc.Slider(
                                    id="phi-b",
                                    min=0,
                                    max=180,
                                    value=90,
                                    step=5,
                                    marks={i: f"{i}°" for i in range(0, 181, 45)},
                                    tooltip={"placement": "bottom"},
                                ),
                                html.Label("Detector plane z_B", style={"fontWeight": "bold", "fontSize": "13px"}),
                                dcc.Slider(
                                    id="t-b",
                                    min=0.10,
                                    max=0.90,
                                    value=0.70,
                                    step=0.05,
                                    marks={0.1: "0.1", 0.5: "0.5", 0.9: "0.9"},
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
                                        {"label": " Equal-sequence superposition trace", "value": "super"},
                                        {"label": " Explicit channel / P_0 plane when available", "value": "channel"},
                                        {"label": " Detector axis lines", "value": "axes"},
                                    ],
                                    value=["super", "channel", "axes"],
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
                                "backgroundColor": "#fff8e1",
                                "borderRadius": "8px",
                                "fontSize": "13px",
                                "lineHeight": "1.5",
                                "border": "1px solid #ffe082",
                            },
                        ),
                    ],
                    style={"width": "360px", "padding": "12px", "flexShrink": "0", "overflowY": "auto", "maxHeight": "95vh"},
                ),
                html.Div(
                    [
                        dcc.Graph(id="main-plot", style={"height": "56vh"}, config={"displayModeBar": True}),
                        dcc.Graph(id="accounting-plot", style={"height": "31vh"}, config={"displayModeBar": True}),
                    ],
                    style={"flexGrow": "1", "minWidth": "0"},
                ),
            ],
            style={"display": "flex", "gap": "12px", "padding": "8px 16px"},
        ),
    ],
    style={"fontFamily": "system-ui, sans-serif", "maxWidth": "1600px", "margin": "auto"},
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
        return False, True, "\u25b6  Play", {**btn_base, "backgroundColor": "#43A047", "color": "white"}, 0.0

    if trigger == "play-btn":
        new_playing = not playing
        if new_playing:
            start_t = 0.0 if sim_time >= T_MAX - 0.01 else sim_time
            return True, False, "\u23f8  Pause", {**btn_base, "backgroundColor": "#EF6C00", "color": "white"}, start_t
        return False, True, "\u25b6  Play", {**btn_base, "backgroundColor": "#43A047", "color": "white"}, no_update

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
        Output("accounting-plot", "figure"),
        Output("info-panel", "children"),
        Output("time-bar-fill", "style"),
        Output("time-label", "children"),
    ],
    [
        Input("sim-time", "data"),
        Input("model-selector", "value"),
        Input("phi-a", "value"),
        Input("phi-b", "value"),
        Input("t-a", "value"),
        Input("t-b", "value"),
        Input("show-opts", "value"),
    ],
)
def update(sim_time, model_key, phi_a_deg, phi_b_deg, z_a, z_b, show_opts):
    sim_time = clamp_time(sim_time)
    phi_a = np.radians(phi_a_deg)
    phi_b = np.radians(phi_b_deg)
    show_super = "super" in (show_opts or [])
    show_channel = "channel" in (show_opts or [])
    show_axes = "axes" in (show_opts or [])

    if z_a > z_b:
        z_a, z_b = z_b, z_a

    scene_fig = build_scene_figure(sim_time, phi_a, phi_b, z_a, z_b, model_key, show_super, show_channel, show_axes)
    accounting_fig = build_accounting_figure(sim_time, phi_a, phi_b, model_key)
    info = info_panel_children(sim_time, phi_a, phi_b, model_key)

    pct = min(100.0, sim_time / T_MAX * 100.0)
    bar_style = {
        "width": f"{pct:.1f}%",
        "height": "6px",
        "backgroundColor": "#43A047",
        "borderRadius": "3px",
        "transition": "width 0.04s linear",
    }
    time_label = f"Propagation sample z = {sim_time:.3f} / {T_MAX:.1f}   [θ* = {np.degrees(current_hidden_phase(sim_time)):.1f}°]"
    return scene_fig, accounting_fig, info, bar_style, time_label


# ── Entry point ────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n  ╔══════════════════════════════════════════╗")
    print("  ║   Rigorous Clarke-Space Entanglement    ║")
    print("  ║   Open http://localhost:8050            ║")
    print("  ╚══════════════════════════════════════════╝\n")
    app.run(debug=True, port=8050)
