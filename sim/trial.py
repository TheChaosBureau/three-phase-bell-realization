from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .analyzers import analyzer_pockets
from .closure import advance_closure_state, apply_post_click_attenuation, completion_window_satisfied
from .config import (
    BRANCHES,
    AnalyzerParams,
    DetectorParams,
    RecombinerParams,
    SharedCoreParams,
    WINNER_SIGNS,
)
from .detector import detector_step, initial_detector_state
from .metrics import target_joint_weights
from .recombiner import recombination_snapshot
from .shared_core import shared_state


def _preclick_snapshot(
    angle_a: float,
    angle_b: float,
    t: float,
    core_params: SharedCoreParams,
    analyzer_params: AnalyzerParams,
    recombiner_params: RecombinerParams,
) -> dict[str, Any]:
    c_x, c_y = shared_state(core_params, t)
    alpha_a, beta_a = analyzer_pockets(c_x, c_y, angle_a, analyzer_params.gain_a)
    alpha_b, beta_b = analyzer_pockets(c_x, c_y, angle_b, analyzer_params.gain_b)
    snapshot = recombination_snapshot(alpha_a, beta_a, alpha_b, beta_b, recombiner_params)
    snapshot.update(
        {
            "c_x": c_x,
            "c_y": c_y,
            "alpha_a": alpha_a,
            "beta_a": beta_a,
            "alpha_b": alpha_b,
            "beta_b": beta_b,
        }
    )
    return snapshot


def _timeseries_row(
    t: float,
    preclick: dict[str, Any],
    branch_amplitudes: dict[str, complex],
    detector_state: dict[str, Any],
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "t": t,
        "c_x": float(preclick["c_x"]),
        "c_y": float(preclick["c_y"]),
        "alpha_a": float(preclick["alpha_a"]),
        "beta_a": float(preclick["beta_a"]),
        "alpha_b": float(preclick["alpha_b"]),
        "beta_b": float(preclick["beta_b"]),
        "q1": float(preclick["q1"]),
        "q2": float(preclick["q2"]),
        "q3": float(preclick["q3"]),
        "q4": float(preclick["q4"]),
        "o_real": float(complex(preclick["o"]).real),
        "o_imag": float(complex(preclick["o"]).imag),
        "s_real": float(complex(preclick["s"]).real),
        "s_imag": float(complex(preclick["s"]).imag),
        "winner_so_far": detector_state["winner"],
    }
    for branch in BRANCHES:
        row[f"z_{branch}_abs2"] = float(abs(branch_amplitudes[branch]) ** 2)
        row[f"m_{branch}"] = float(detector_state[f"m_{branch}"])
        row[f"y_{branch}"] = int(detector_state[f"y_{branch}"])
        row[f"g_{branch}"] = float(detector_state[f"g_{branch}"])
        row[f"rfr_{branch}"] = float(detector_state[f"rfr_{branch}"])
    row["h"] = float(detector_state["h"])
    return row


def run_trial(
    angle_a: float,
    angle_b: float,
    core_params: SharedCoreParams,
    analyzer_params: AnalyzerParams,
    recombiner_params: RecombinerParams,
    detector_params: DetectorParams,
) -> dict[str, Any]:
    rng = np.random.default_rng(detector_params.seed)
    detector_state = initial_detector_state(detector_params)
    static_preclick = (
        _preclick_snapshot(
            angle_a=angle_a,
            angle_b=angle_b,
            t=0.0,
            core_params=core_params,
            analyzer_params=analyzer_params,
            recombiner_params=recombiner_params,
        )
        if core_params.use_static_envelope
        else None
    )

    timeseries_rows: list[dict[str, Any]] = []
    first_snapshot: dict[str, Any] | None = None
    trigger_time: float | None = None
    trigger_step_index: int | None = None

    step_index = 0
    while True:
        t = step_index * detector_params.dt
        if t > detector_params.t_max + 1e-12:
            break

        preclick = static_preclick or _preclick_snapshot(
            angle_a=angle_a,
            angle_b=angle_b,
            t=t,
            core_params=core_params,
            analyzer_params=analyzer_params,
            recombiner_params=recombiner_params,
        )
        if first_snapshot is None:
            first_snapshot = preclick

        branch_amplitudes = {
            branch: complex(preclick[f"z_{branch}"])
            for branch in BRANCHES
        }
        if detector_state["winner"] != "none":
            branch_amplitudes = apply_post_click_attenuation(branch_amplitudes, detector_state, detector_params)

        previous_winner = detector_state["winner"]
        detector_state, winner = detector_step(
            branch_amplitudes=branch_amplitudes,
            detector_state=detector_state,
            params=detector_params,
            rng=rng,
        )
        if previous_winner == "none" and winner is not None:
            trigger_time = t
            trigger_step_index = step_index

        detector_state, closure_deltas = advance_closure_state(detector_state, detector_params)
        timeseries_rows.append(_timeseries_row(t, preclick, branch_amplitudes, detector_state))

        if t >= detector_params.t_max - 1e-12:
            break

        steps_after_trigger = 0 if trigger_step_index is None else step_index - trigger_step_index
        if completion_window_satisfied(
            branch_amplitudes=branch_amplitudes,
            detector_state=detector_state,
            closure_deltas=closure_deltas,
            min_post_winner_steps=20,
            post_winner_steps=steps_after_trigger,
        ):
            break

        step_index += 1

    if first_snapshot is None:
        raise RuntimeError("trial produced no time-series rows")

    delta = angle_a - angle_b
    target = target_joint_weights(delta)
    winner = detector_state["winner"]
    winner_sign_a, winner_sign_b = WINNER_SIGNS[winner]
    summary: dict[str, Any] = {
        "seed": detector_params.seed,
        "detector_mode": detector_params.mode,
        "tie_broken": bool(detector_state["tie_broken"]),
        "angle_a": float(angle_a),
        "angle_b": float(angle_b),
        "delta": float(delta),
        "c_x": float(first_snapshot["c_x"]),
        "c_y": float(first_snapshot["c_y"]),
        "alpha_a": float(first_snapshot["alpha_a"]),
        "beta_a": float(first_snapshot["beta_a"]),
        "alpha_b": float(first_snapshot["alpha_b"]),
        "beta_b": float(first_snapshot["beta_b"]),
        "o_real": float(complex(first_snapshot["o"]).real),
        "o_imag": float(complex(first_snapshot["o"]).imag),
        "s_real": float(complex(first_snapshot["s"]).real),
        "s_imag": float(complex(first_snapshot["s"]).imag),
        "winner": winner,
        "winner_sign_a": int(winner_sign_a),
        "winner_sign_b": int(winner_sign_b),
        "trigger_time": float(trigger_time) if trigger_time is not None else float("nan"),
        "dark_triggered": bool(detector_state["dark_triggered"]),
        "decisive": winner != "none",
        "h_final": float(detector_state["h"]),
    }
    for branch in BRANCHES:
        summary[f"z_{branch}_abs2"] = float(abs(complex(first_snapshot[f"z_{branch}"])) ** 2)
        summary[f"w_{branch}_target"] = float(target[branch])
        summary[f"g_{branch}_final"] = float(detector_state[f"g_{branch}"])

    return {
        "summary": summary,
        "timeseries": pd.DataFrame(timeseries_rows),
    }
