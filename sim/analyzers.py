from __future__ import annotations

import math


def analyzer_pockets(
    c_x: float,
    c_y: float,
    angle: float,
    gain: float,
) -> tuple[float, float]:
    alpha = gain * (c_x * math.cos(angle) + c_y * math.sin(angle))
    beta = gain * (-c_x * math.sin(angle) + c_y * math.cos(angle))
    return alpha, beta
