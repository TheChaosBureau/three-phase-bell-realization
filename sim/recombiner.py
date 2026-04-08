from __future__ import annotations

import math

from .config import BRANCHES, RecombinerParams


def quadratic_bay_drives(alpha_a: float, beta_a: float, alpha_b: float, beta_b: float) -> tuple[float, float, float, float]:
    q1 = (alpha_a + alpha_b) ** 2 + (beta_a + beta_b) ** 2
    q2 = (alpha_a - alpha_b) ** 2 + (beta_a - beta_b) ** 2
    q3 = (alpha_a + beta_b) ** 2 + (beta_a - alpha_b) ** 2
    q4 = (alpha_a - beta_b) ** 2 + (beta_a + alpha_b) ** 2
    return q1, q2, q3, q4


def bay_outputs(
    q1: float,
    q2: float,
    q3: float,
    q4: float,
    params: RecombinerParams,
) -> tuple[complex, complex, complex, complex]:
    lambda2 = complex(params.lambda2_real, params.lambda2_imag)
    kappas = [
        params.kappa_bar * (1.0 + params.eps1),
        params.kappa_bar * (1.0 + params.eps2),
        params.kappa_bar * (1.0 + params.eps3),
        params.kappa_bar * (1.0 + params.eps4),
    ]
    qs = [q1, q2, q3, q4]
    return tuple((kappa / lambda2) * q for kappa, q in zip(kappas, qs, strict=True))


def pair_rails(
    r1: complex,
    r2: complex,
    r3: complex,
    r4: complex,
    params: RecombinerParams,
) -> tuple[complex, complex]:
    lambda2 = complex(params.lambda2_real, params.lambda2_imag)
    scale = lambda2 / (4.0 * params.kappa_bar)
    o = scale * (r1 - r2)
    s = scale * (r3 - r4)
    return o, s


def joint_channels_from_rails(o: complex, s: complex, quadrature_sign: int = +1) -> dict[str, complex]:
    phase = complex(0.0, quadrature_sign / math.sqrt(2.0))
    real_scale = 1.0 / math.sqrt(2.0)
    return {
        "pp": phase * s,
        "pm": -real_scale * o,
        "mp": real_scale * o,
        "mm": -phase * s,
    }


def recombination_snapshot(
    alpha_a: float,
    beta_a: float,
    alpha_b: float,
    beta_b: float,
    params: RecombinerParams,
) -> dict[str, float | complex]:
    q1, q2, q3, q4 = quadratic_bay_drives(alpha_a, beta_a, alpha_b, beta_b)
    r1, r2, r3, r4 = bay_outputs(q1, q2, q3, q4, params)
    o, s = pair_rails(r1, r2, r3, r4, params)
    z = joint_channels_from_rails(o, s, quadrature_sign=params.quadrature_sign)
    snapshot: dict[str, float | complex] = {
        "q1": q1,
        "q2": q2,
        "q3": q3,
        "q4": q4,
        "r1": r1,
        "r2": r2,
        "r3": r3,
        "r4": r4,
        "o": o,
        "s": s,
    }
    for branch in BRANCHES:
        snapshot[f"z_{branch}"] = z[branch]
    return snapshot


def recombine_joint_channels(
    alpha_a: float,
    beta_a: float,
    alpha_b: float,
    beta_b: float,
    params: RecombinerParams,
) -> dict[str, complex]:
    snapshot = recombination_snapshot(alpha_a, beta_a, alpha_b, beta_b, params)
    return {branch: snapshot[f"z_{branch}"] for branch in BRANCHES}
