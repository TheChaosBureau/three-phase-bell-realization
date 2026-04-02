from __future__ import annotations

import math
from dataclasses import dataclass

from .base import DetectorModel, DetectorState, ParamGrid


@dataclass(frozen=True)
class PoissonLinearModel(DetectorModel):
    lambda_dark: float = 0.02
    alpha: float = 0.8
    dead_time: float = 0.0
    name: str = "poisson_linear"

    def reset(self, rng) -> DetectorState:
        return DetectorState({"recovery_left": 0.0})

    def step(self, state: DetectorState, P_abs: float, dt: float, rng) -> tuple[DetectorState, bool]:
        recovery_left = max(float(state.data["recovery_left"]) - dt, 0.0)
        if recovery_left > 0.0:
            return DetectorState({"recovery_left": recovery_left}), False

        event_rate = max(self.lambda_dark + self.alpha * max(P_abs, 0.0), 0.0)
        event = bool(rng.random() < 1.0 - math.exp(-event_rate * dt))
        next_recovery = self.dead_time if event else 0.0
        return DetectorState({"recovery_left": next_recovery}), event

    def sample_click_time(self, P_abs: float, t_max: float, rng) -> float | None:
        event_rate = max(self.lambda_dark + self.alpha * max(P_abs, 0.0), 0.0)
        if event_rate <= 0.0:
            return None
        click_time = float(rng.exponential(1.0 / event_rate))
        return click_time if click_time <= t_max else None

    def default_param_grid(self) -> ParamGrid:
        return {
            "lambda_dark": (1e-4, 5e-2, "log"),
            "alpha": (0.1, 2.0),
            "dead_time": (0.0, 0.1),
        }
