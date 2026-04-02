from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping


ParamGridValue = tuple[float, float] | tuple[float, float, str] | list[float] | tuple[float, ...]
ParamGrid = dict[str, ParamGridValue]


@dataclass
class DetectorState:
    data: Any


@dataclass(frozen=True)
class DetectorModel:
    """Abstract detector model family."""

    name: str

    def with_params(self, params: Mapping[str, float]) -> "DetectorModel":
        return replace(self, **params)

    def reset(self, rng) -> DetectorState:
        raise NotImplementedError

    def step(self, state: DetectorState, P_abs: float, dt: float, rng) -> tuple[DetectorState, bool]:
        """
        Advance one timestep and return a new state plus an event flag.
        """
        raise NotImplementedError

    def sample_click_time(self, P_abs: float, t_max: float, rng) -> float | None:
        """
        Optionally draw a first-click time directly for event-driven models.
        """
        return None

    def default_param_grid(self) -> ParamGrid:
        raise NotImplementedError
