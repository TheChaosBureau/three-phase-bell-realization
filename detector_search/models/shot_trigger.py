from __future__ import annotations

import math
from dataclasses import dataclass

from .base import DetectorModel, DetectorState, ParamGrid


@dataclass(frozen=True)
class ShotTriggerModel(DetectorModel):
    eps_event: float = 1.0
    p_trig: float = 0.8
    lambda_dark: float = 0.01
    dead_time: float = 0.0
    name: str = "shot_trigger"

    def reset(self, rng) -> DetectorState:
        return DetectorState({"recovery_left": 0.0})

    def step(self, state: DetectorState, P_abs: float, dt: float, rng) -> tuple[DetectorState, bool]:
        recovery_left = max(float(state.data["recovery_left"]) - dt, 0.0)
        if recovery_left > 0.0:
            return DetectorState({"recovery_left": recovery_left}), False

        arrival_rate = max(P_abs, 0.0) / max(self.eps_event, 1e-12)
        success_rate = self.lambda_dark + arrival_rate * min(max(self.p_trig, 0.0), 1.0)
        event = bool(rng.random() < 1.0 - math.exp(-success_rate * dt))
        next_recovery = self.dead_time if event else 0.0
        return DetectorState({"recovery_left": next_recovery}), event

    def sample_click_time(self, P_abs: float, t_max: float, rng) -> float | None:
        arrival_rate = max(P_abs, 0.0) / max(self.eps_event, 1e-12)
        success_rate = self.lambda_dark + arrival_rate * min(max(self.p_trig, 0.0), 1.0)
        if success_rate <= 0.0:
            return None
        click_time = float(rng.exponential(1.0 / success_rate))
        return click_time if click_time <= t_max else None

    def default_param_grid(self) -> ParamGrid:
        return {
            "eps_event": (0.2, 5.0, "log"),
            "p_trig": (0.05, 0.99),
            "lambda_dark": (1e-4, 5e-2, "log"),
            "dead_time": (0.0, 0.1),
        }
