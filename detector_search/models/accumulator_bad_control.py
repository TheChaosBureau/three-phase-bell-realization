from __future__ import annotations

from dataclasses import dataclass

from .base import DetectorModel, DetectorState, ParamGrid


@dataclass(frozen=True)
class AccumulatorBadControlModel(DetectorModel):
    sigma: float = 0.15
    threshold: float = 1.0
    reset_value: float = 0.0
    dead_time: float = 0.0
    name: str = "accumulator_bad_control"

    def reset(self, rng) -> DetectorState:
        return DetectorState({"energy": self.reset_value, "recovery_left": 0.0})

    def step(self, state: DetectorState, P_abs: float, dt: float, rng) -> tuple[DetectorState, bool]:
        recovery_left = max(float(state.data["recovery_left"]) - dt, 0.0)
        if recovery_left > 0.0:
            return DetectorState({"energy": self.reset_value, "recovery_left": recovery_left}), False

        energy = float(state.data["energy"])
        energy += max(P_abs, 0.0) * dt + self.sigma * (dt**0.5) * rng.normal()
        if energy >= self.threshold:
            return DetectorState({"energy": self.reset_value, "recovery_left": self.dead_time}), True
        return DetectorState({"energy": energy, "recovery_left": 0.0}), False

    def sample_click_time(self, P_abs: float, t_max: float, rng) -> float | None:
        drift = max(P_abs, 0.0)
        gap = self.threshold - self.reset_value
        if gap <= 0.0:
            return 0.0
        if drift <= 0.0:
            return None
        if self.sigma <= 0.0:
            click_time = gap / drift
            return click_time if click_time <= t_max else None

        mean = gap / drift
        scale = (gap**2) / (self.sigma**2)
        click_time = float(rng.wald(mean, scale))
        return click_time if click_time <= t_max else None

    def default_param_grid(self) -> ParamGrid:
        return {
            "sigma": (0.05, 0.5),
            "threshold": (0.5, 2.0),
            "reset_value": (-0.25, 0.25),
            "dead_time": (0.0, 0.1),
        }
