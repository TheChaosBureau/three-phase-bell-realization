from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Literal

BRANCHES = ("pp", "pm", "mp", "mm")

DEFAULT_CHSH_SETTINGS = (0.0, math.pi / 4.0, math.pi / 8.0, -math.pi / 8.0)


def _dedupe_angle_pairs(angle_pairs: list[tuple[float, float]]) -> list[tuple[float, float]]:
    seen: set[tuple[float, float]] = set()
    ordered: list[tuple[float, float]] = []
    for pair in angle_pairs:
        if pair in seen:
            continue
        seen.add(pair)
        ordered.append(pair)
    return ordered


DEFAULT_SWEEP_ANGLE_PAIRS = _dedupe_angle_pairs(
    [
        (0.0, math.pi / 8.0),
        (0.0, -math.pi / 8.0),
        (math.pi / 4.0, math.pi / 8.0),
        (math.pi / 4.0, -math.pi / 8.0),
        (0.0, 0.0),
        (0.0, math.pi / 4.0),
        (0.0, 3.0 * math.pi / 8.0),
        (0.0, math.pi / 2.0),
        (0.0, 5.0 * math.pi / 8.0),
        (0.0, 3.0 * math.pi / 4.0),
        (0.0, 7.0 * math.pi / 8.0),
    ]
)

WINNER_SIGNS = {
    "pp": (+1, +1),
    "pm": (+1, -1),
    "mp": (-1, +1),
    "mm": (-1, -1),
    "none": (0, 0),
}


@dataclass(frozen=True)
class SharedCoreParams:
    amplitude_rho: float
    phase_omega: float
    damping_gamma: float
    use_static_envelope: bool


@dataclass(frozen=True)
class AnalyzerParams:
    gain_a: float
    gain_b: float


@dataclass(frozen=True)
class RecombinerParams:
    kappa_bar: float
    lambda2_real: float
    lambda2_imag: float
    eps1: float
    eps2: float
    eps3: float
    eps4: float
    quadrature_sign: int


@dataclass(frozen=True)
class DetectorParams:
    mode: Literal["ou_threshold", "poisson_linear"]
    dt: float
    t_max: float
    dark_rate: float
    seed: int
    m_bias: float
    threshold: float
    tau_m: float
    beta: float
    sigma: float
    alpha_poisson: float
    tau_h: float
    gain_h: float
    tau_g: float
    gain_g: float
    tau_r: float
    gain_r: float
    chi_h: float
    chi_r: float
    gamma_g: float
    gamma_h: float
    reset_value: float


DEFAULT_SHARED_CORE_PARAMS = SharedCoreParams(
    amplitude_rho=1.0,
    phase_omega=0.0,
    damping_gamma=0.0,
    use_static_envelope=True,
)

DEFAULT_ANALYZER_PARAMS = AnalyzerParams(
    gain_a=1.0,
    gain_b=1.0,
)

DEFAULT_RECOMBINER_PARAMS = RecombinerParams(
    kappa_bar=1.0,
    lambda2_real=1.0,
    lambda2_imag=0.0,
    eps1=0.0,
    eps2=0.0,
    eps3=0.0,
    eps4=0.0,
    quadrature_sign=+1,
)

DEFAULT_DETECTOR_PARAMS_OU = DetectorParams(
    mode="ou_threshold",
    dt=1e-3,
    t_max=10.0,
    dark_rate=1e-4,
    seed=7,
    m_bias=0.70,
    threshold=1.00,
    tau_m=0.10,
    beta=4.0,
    sigma=0.30,
    alpha_poisson=2.0,
    tau_h=0.01,
    gain_h=1.0,
    tau_g=0.01,
    gain_g=1.0,
    tau_r=0.20,
    gain_r=1.0,
    chi_h=4.0,
    chi_r=2.0,
    gamma_g=8.0,
    gamma_h=8.0,
    reset_value=0.0,
)

DEFAULT_DETECTOR_PARAMS_POISSON = DetectorParams(
    **{
        **asdict(DEFAULT_DETECTOR_PARAMS_OU),
        "mode": "poisson_linear",
        "alpha_poisson": 2.0,
    }
)


def params_to_dict(*params: Any) -> list[dict[str, Any]]:
    return [asdict(param) if hasattr(param, "__dataclass_fields__") else dict(param) for param in params]
