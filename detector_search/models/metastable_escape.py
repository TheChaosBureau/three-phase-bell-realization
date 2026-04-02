from __future__ import annotations

from dataclasses import dataclass

from .base import DetectorModel, DetectorState, ParamGrid


@dataclass(frozen=True)
class MetastableEscapeModel(DetectorModel):
    bias: float = 0.0
    gain_P: float = 0.9
    leak: float = 1.0
    sigma: float = 0.7
    threshold: float = 1.0
    reset_value: float = 0.0
    dead_time: float = 0.0
    name: str = "metastable_escape"

    def reset(self, rng) -> DetectorState:
        return DetectorState({"x": self.reset_value, "recovery_left": 0.0})

    def step(self, state: DetectorState, P_abs: float, dt: float, rng) -> tuple[DetectorState, bool]:
        recovery_left = max(float(state.data["recovery_left"]) - dt, 0.0)
        if recovery_left > 0.0:
            return DetectorState({"x": self.reset_value, "recovery_left": recovery_left}), False

        x_value = float(state.data["x"])
        drift = self.bias + self.gain_P * max(P_abs, 0.0) - self.leak * x_value
        noise = self.sigma * (dt**0.5) * rng.normal()
        x_next = x_value + drift * dt + noise
        if x_next >= self.threshold:
            return DetectorState({"x": self.reset_value, "recovery_left": self.dead_time}), True
        return DetectorState({"x": x_next, "recovery_left": 0.0}), False

    def default_param_grid(self) -> ParamGrid:
        return {
            "bias": (-0.2, 0.2),
            "gain_P": (0.2, 2.0),
            "leak": (0.1, 3.0),
            "sigma": (0.05, 1.0),
            "threshold": (0.5, 2.0),
            "reset_value": (-0.5, 0.5),
            "dead_time": (0.0, 0.1),
        }
