from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from detector_search.models import PoissonLinearModel, ShotTriggerModel
from detector_search.sim.single_branch import simulate_single_trial

MODEL_FACTORIES = {
    "poisson_linear": PoissonLinearModel,
    "shot_trigger": ShotTriggerModel,
}

DEFAULT_ENVELOPE_PARAMS = {
    "kind": "constant",
    "power_scale": 1.0,
    "dt": 1e-4,
    "t_max": 10.0,
}

_RESERVED_KEYS = {"family", "model_params", "gain_scale"}


def resolve_branch_detector_params(detector_params: Mapping[str, Any] | Sequence[Mapping[str, Any]], branch_index: int) -> dict[str, Any]:
    if isinstance(detector_params, Mapping):
        return dict(detector_params)
    return dict(detector_params[branch_index])


def resolve_branch_envelope_params(
    envelope_params: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None,
    branch_index: int,
) -> dict[str, Any]:
    if envelope_params is None:
        return dict(DEFAULT_ENVELOPE_PARAMS)
    if isinstance(envelope_params, Mapping):
        return {**DEFAULT_ENVELOPE_PARAMS, **dict(envelope_params)}
    return {**DEFAULT_ENVELOPE_PARAMS, **dict(envelope_params[branch_index])}


def _detector_family(detector_params: Mapping[str, Any]) -> str:
    return str(detector_params.get("family", "shot_trigger"))


def _model_params(detector_params: Mapping[str, Any]) -> dict[str, float]:
    if "model_params" in detector_params:
        return dict(detector_params["model_params"])
    return {name: value for name, value in detector_params.items() if name not in _RESERVED_KEYS}


def _effective_power(weight: float, detector_params: Mapping[str, Any], envelope_params: Mapping[str, Any]) -> float:
    gain_scale = float(detector_params.get("gain_scale", 1.0))
    power_scale = float(envelope_params.get("power_scale", 1.0))
    return max(float(weight) * gain_scale, 0.0) * power_scale


def _simulate_time_varying_branch(
    detector_params: Mapping[str, Any],
    weight: float,
    envelope_params: Mapping[str, Any],
    rng,
) -> float | None:
    family = _detector_family(detector_params)
    if family not in MODEL_FACTORIES:
        raise ValueError(f"Unsupported detector family: {family}")
    configured = MODEL_FACTORIES[family]().with_params(_model_params(detector_params))
    dt = float(envelope_params["dt"])
    t_max = float(envelope_params["t_max"])
    state = configured.reset(rng)
    if envelope_params["kind"] == "sampled":
        time_s = np.asarray(envelope_params["time_s"], dtype=float)
        power_w = np.asarray(envelope_params["power_w"], dtype=float)
        if time_s.ndim != 1 or power_w.ndim != 1 or time_s.size != power_w.size:
            raise ValueError("Sampled envelope requires matching 1D time_s and power_w arrays.")
        if time_s.size < 2:
            raise ValueError("Sampled envelope requires at least two sample points.")
        step_durations = np.diff(time_s, append=float(time_s[-1]) + dt)
        for step_index, (base_power, step_dt) in enumerate(zip(power_w, step_durations, strict=True)):
            P_abs = max(float(weight), 0.0) * float(detector_params.get("gain_scale", 1.0)) * max(float(base_power), 0.0)
            state, event = configured.step(state, P_abs=P_abs, dt=max(float(step_dt), 1e-12), rng=rng)
            if event:
                return float(time_s[step_index] + max(float(step_dt), 1e-12))
        return None
    if envelope_params["kind"] == "sampled_linear":
        time_s = np.asarray(envelope_params["time_s"], dtype=float)
        power_w = np.asarray(envelope_params["power_w"], dtype=float)
        if time_s.ndim != 1 or power_w.ndim != 1 or time_s.size != power_w.size:
            raise ValueError("Sampled linear envelope requires matching 1D time_s and power_w arrays.")
        if time_s.size < 2:
            raise ValueError("Sampled linear envelope requires at least two sample points.")
        target_dt = max(float(envelope_params.get("dt", dt)), 1e-12)
        for step_index in range(time_s.size - 1):
            start_t = float(time_s[step_index])
            end_t = float(time_s[step_index + 1])
            duration = max(end_t - start_t, 1e-12)
            n_substeps = max(int(np.ceil(duration / target_dt)), 1)
            sub_dt = duration / n_substeps
            start_power = float(power_w[step_index])
            end_power = float(power_w[step_index + 1])
            for substep_index in range(n_substeps):
                alpha = (substep_index + 0.5) / n_substeps
                base_power = (1.0 - alpha) * start_power + alpha * end_power
                P_abs = max(float(weight), 0.0) * float(detector_params.get("gain_scale", 1.0)) * max(base_power, 0.0)
                state, event = configured.step(state, P_abs=P_abs, dt=sub_dt, rng=rng)
                if event:
                    return start_t + (substep_index + 1) * sub_dt
        return None

    n_steps = int(np.ceil(t_max / dt))
    for step_index in range(n_steps):
        time = step_index * dt
        if envelope_params["kind"] == "exp_decay":
            tau = max(float(envelope_params.get("decay_tau", 1.0)), dt)
            base_power = float(envelope_params.get("power_scale", 1.0)) * np.exp(-time / tau)
        else:
            raise ValueError(f"Unsupported envelope kind: {envelope_params['kind']}")
        P_abs = max(float(weight), 0.0) * float(detector_params.get("gain_scale", 1.0)) * base_power
        state, event = configured.step(state, P_abs=P_abs, dt=dt, rng=rng)
        if event:
            return (step_index + 1) * dt
    return None


def simulate_branch_nucleation(
    detector_params: Mapping[str, Any],
    weight: float,
    envelope_params: Mapping[str, Any],
    rng,
) -> float | None:
    """
    Return the first nucleation time for one detector branch under a weight-driven envelope.
    """
    branch_weight = max(float(weight), 0.0)
    envelope = {**DEFAULT_ENVELOPE_PARAMS, **dict(envelope_params)}
    if envelope["kind"] == "constant":
        family = _detector_family(detector_params)
        if family not in MODEL_FACTORIES:
            raise ValueError(f"Unsupported detector family: {family}")
        return simulate_single_trial(
            MODEL_FACTORIES[family](),
            params=_model_params(detector_params),
            P_abs=_effective_power(branch_weight, detector_params, envelope),
            dt=float(envelope["dt"]),
            t_max=float(envelope["t_max"]),
            rng=rng,
        )
    return _simulate_time_varying_branch(detector_params, branch_weight, envelope, rng)
