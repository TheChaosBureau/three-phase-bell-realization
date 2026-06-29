from __future__ import annotations

import math

from .config import SharedCoreParams


def shared_state(params: SharedCoreParams, t: float) -> tuple[float, float]:
    if params.use_static_envelope:
        return params.amplitude_rho, 0.0

    envelope = params.amplitude_rho * math.exp(-params.damping_gamma * t)
    phase = params.phase_omega * t
    return envelope * math.cos(phase), envelope * math.sin(phase)
