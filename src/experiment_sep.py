from __future__ import annotations
import sys
from pathlib import Path

# Support running this file directly: `python src/experiment.py`.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "src"

import math
import random

from .config import SourceConfig, DetectorConfig, ExperimentConfig
from .source import build_antisymmetric_source
from .analyzer import (
    extract_local_modes_A,
    extract_local_modes_B,
    rotate_analyzer,
)
from .detector import branch_powers, step_detector
from .types import DetectorState


def local_click_from_outputs(
    p_plus: float,
    p_minus: float,
    det_cfg: DetectorConfig,
) -> int:
    """
    Purely local detector race.
    Returns +1 or -1.
    """
    d = DetectorState()
    t = 0.0

    while t < det_cfg.t_max and not d.clicked:
        d = step_detector(
            d,
            p_plus=p_plus,
            p_minus=p_minus,
            eta=det_cfg.eta,
            kappa=det_cfg.kappa,
            threshold=det_cfg.threshold,
            dt=det_cfg.dt,
            t_now=t,
        )
        t += det_cfg.dt

    if d.outcome is None:
        return +1 if p_plus >= p_minus else -1
    return d.outcome


def run_single_trial_local(
    a: float,
    b: float,
    source_cfg: SourceConfig,
    det_cfg: DetectorConfig,
    rng: random.Random,
) -> tuple[int, int]:
    """
    Local-click version:

    1. Source prepares programmable V±, I± state.
    2. Alice extracts only local modes, rotates by a, clicks locally.
    3. Bob extracts only local modes, rotates by b, clicks locally.
    4. Coincidence is recorded only after both local outcomes exist.

    This is the Bell-localized bench test.
    """
    state = build_antisymmetric_source(source_cfg)

    A_modes = extract_local_modes_A(state, source_cfg.G0)
    B_modes = extract_local_modes_B(state, source_cfg.G0)

    A_out = rotate_analyzer(A_modes, a)
    B_out = rotate_analyzer(B_modes, b)

    pA_plus, pA_minus = branch_powers(A_out)
    pB_plus, pB_minus = branch_powers(B_out)

    # Optional tiny local jitter to avoid pathological ties
    # while keeping everything local.
    eps = 1e-12
    pA_plus += eps * rng.random()
    pA_minus += eps * rng.random()
    pB_plus += eps * rng.random()
    pB_minus += eps * rng.random()

    A = local_click_from_outputs(pA_plus, pA_minus, det_cfg)
    B = local_click_from_outputs(pB_plus, pB_minus, det_cfg)
    return A, B


def estimate_E_local(
    a: float,
    b: float,
    source_cfg: SourceConfig,
    det_cfg: DetectorConfig,
    exp_cfg: ExperimentConfig,
) -> float:
    rng = random.Random(exp_cfg.rng_seed)
    counts = {"++": 0, "+-": 0, "-+": 0, "--": 0}

    for _ in range(exp_cfg.trials):
        A, B = run_single_trial_local(a, b, source_cfg, det_cfg, rng)
        label = ("+" if A > 0 else "-") + ("+" if B > 0 else "-")
        counts[label] += 1

    freqs = {k: counts[k] / exp_cfg.trials for k in counts}
    return freqs["++"] + freqs["--"] - freqs["+-"] - freqs["-+"]


def estimate_S_local(
    a: float,
    ap: float,
    b: float,
    bp: float,
    source_cfg: SourceConfig,
    det_cfg: DetectorConfig,
    exp_cfg: ExperimentConfig,
) -> float:
    Eab = estimate_E_local(a, b, source_cfg, det_cfg, ExperimentConfig(trials=exp_cfg.trials, rng_seed=exp_cfg.rng_seed + 1))
    Eabp = estimate_E_local(a, bp, source_cfg, det_cfg, ExperimentConfig(trials=exp_cfg.trials, rng_seed=exp_cfg.rng_seed + 2))
    Eapb = estimate_E_local(ap, b, source_cfg, det_cfg, ExperimentConfig(trials=exp_cfg.trials, rng_seed=exp_cfg.rng_seed + 3))
    Eapbp = estimate_E_local(ap, bp, source_cfg, det_cfg, ExperimentConfig(trials=exp_cfg.trials, rng_seed=exp_cfg.rng_seed + 4))
    return Eab - Eabp + Eapb + Eapbp


def exact_reference_E(a: float, b: float) -> float:
    return -math.cos(2.0 * (a - b))


def exact_reference_S(a: float, ap: float, b: float, bp: float) -> float:
    return (
        exact_reference_E(a, b)
        - exact_reference_E(a, bp)
        + exact_reference_E(ap, b)
        + exact_reference_E(ap, bp)
    )


def main() -> None:
    source_cfg = SourceConfig()
    det_cfg = DetectorConfig(mode="threshold_race")
    exp_cfg = ExperimentConfig(trials=50000, rng_seed=2026)

    a = math.radians(0.0)
    ap = math.radians(45.0)
    b = math.radians(22.5)
    bp = math.radians(67.5)

    print("Local-click programmable-source bench")
    print()

    for aa, bb in [(a, b), (a, bp), (ap, b), (ap, bp)]:
        E_hat = estimate_E_local(aa, bb, source_cfg, det_cfg, exp_cfg)
        E_ref = exact_reference_E(aa, bb)
        print(
            f"a={math.degrees(aa):6.1f}°, b={math.degrees(bb):6.1f}°  "
            f"E_local={E_hat:+.6f}, E_ref={E_ref:+.6f}"
        )

    S_hat = estimate_S_local(a, ap, b, bp, source_cfg, det_cfg, exp_cfg)
    S_ref = exact_reference_S(a, ap, b, bp)

    print()
    print(f"S_local = {S_hat:+.6f}")
    print(f"S_ref   = {S_ref:+.6f}")
    print(f"2       = {2.0:+.6f}")
    print(f"2*sqrt2 = {2.0 * math.sqrt(2.0):+.6f}")


if __name__ == "__main__":
    main()