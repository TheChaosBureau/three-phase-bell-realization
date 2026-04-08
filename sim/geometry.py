from __future__ import annotations

from dataclasses import dataclass

from .config import BRANCHES


@dataclass(frozen=True)
class CircularBasinGeometry:
    basin_radius: float
    analyzer_positions: dict[str, tuple[float, float]]
    bay_positions: dict[str, tuple[float, float]]
    detector_positions: dict[str, tuple[float, float]]
    analyzer_radius: float
    bay_radius: float
    detector_radius: float


def default_geometry() -> CircularBasinGeometry:
    return CircularBasinGeometry(
        basin_radius=1.0,
        analyzer_positions={
            "A": (-0.55, 0.35),
            "B": (0.55, 0.35),
        },
        bay_positions={
            "q1": (-0.22, 0.22),
            "q2": (0.22, 0.22),
            "q3": (0.22, -0.22),
            "q4": (-0.22, -0.22),
        },
        detector_positions=dict(
            zip(
                BRANCHES,
                (
                    (-0.72, 0.68),
                    (0.72, 0.68),
                    (-0.72, -0.68),
                    (0.72, -0.68),
                ),
                strict=True,
            )
        ),
        analyzer_radius=0.16,
        bay_radius=0.09,
        detector_radius=0.11,
    )
