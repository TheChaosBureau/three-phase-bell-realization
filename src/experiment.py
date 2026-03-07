from __future__ import annotations
import math
import random
import sys
from pathlib import Path

# Support running this file directly: `python src/experiment.py`.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "src"

from .config import SourceConfig, DetectorConfig, ExperimentConfig
from .source import build_antisymmetric_source
from .analyzer import extract_local_modes_A, extract_local_modes_B, rotate_analyzer, coincidence_probabilities
from .detector import branch_powers, step_detector, sample_from_joint_probs
from .types import DetectorState


def run_single_trial_bench(
    a: float,
    b: float,
    source_cfg: SourceConfig,
    det_cfg: DetectorConfig,
    rng: random.Random,
) -> tuple[int, int]:
    """
    Bench-model trial.
    """
    state = build_antisymmetric_source(source_cfg)

    if det_cfg.mode == "categorical":
        probs = coincidence_probabilities(state, a, b, source_cfg.G0)
        return sample_from_joint_probs(probs, rng)

    # threshold-race mode
    A_modes = extract_local_modes_A(state, source_cfg.G0)
    B_modes = extract_local_modes_B(state, source_cfg.G0)

    A_out = rotate_analyzer(A_modes, a)
    B_out = rotate_analyzer(B_modes, b)

    pA_plus, pA_minus = branch_powers(A_out)
    pB_plus, pB_minus = branch_powers(B_out)

    dA = DetectorState()
    dB = DetectorState()

    t = 0.0
    while t < det_cfg.t_max and not (dA.clicked and dB.clicked):
        if not dA.clicked:
            dA = step_detector(
                dA, pA_plus, pA_minus,
                eta=det_cfg.eta,
                kappa=det_cfg.kappa,
                threshold=det_cfg.threshold,
                dt=det_cfg.dt,
                t_now=t,
            )
        if not dB.clicked:
            dB = step_detector(
                dB, pB_plus, pB_minus,
                eta=det_cfg.eta,
                kappa=det_cfg.kappa,
                threshold=det_cfg.threshold,
                dt=det_cfg.dt,
                t_now=t,
            )
        t += det_cfg.dt

    # fallback if no threshold hit
    if dA.outcome is None:
        dA.outcome = +1 if pA_plus >= pA_minus else -1
    if dB.outcome is None:
        dB.outcome = +1 if pB_plus >= pB_minus else -1

    return (dA.outcome, dB.outcome)


def estimate_E(
    a: float,
    b: float,
    source_cfg: SourceConfig,
    det_cfg: DetectorConfig,
    exp_cfg: ExperimentConfig,
) -> float:
    rng = random.Random(exp_cfg.rng_seed)
    counts = {"++": 0, "+-": 0, "-+": 0, "--": 0}

    for _ in range(exp_cfg.trials):
        A, B = run_single_trial_bench(a, b, source_cfg, det_cfg, rng)
        label = ("+" if A > 0 else "-") + ("+" if B > 0 else "-")
        counts[label] += 1

    freqs = {k: counts[k] / exp_cfg.trials for k in counts}
    return freqs["++"] + freqs["--"] - freqs["+-"] - freqs["-+"]


def estimate_S(
    a: float,
    ap: float,
    b: float,
    bp: float,
    source_cfg: SourceConfig,
    det_cfg: DetectorConfig,
    exp_cfg: ExperimentConfig,
) -> float:
    Eab = estimate_E(a, b, source_cfg, det_cfg, ExperimentConfig(trials=exp_cfg.trials, rng_seed=exp_cfg.rng_seed + 1))
    Eabp = estimate_E(a, bp, source_cfg, det_cfg, ExperimentConfig(trials=exp_cfg.trials, rng_seed=exp_cfg.rng_seed + 2))
    Eapb = estimate_E(ap, b, source_cfg, det_cfg, ExperimentConfig(trials=exp_cfg.trials, rng_seed=exp_cfg.rng_seed + 3))
    Eapbp = estimate_E(ap, bp, source_cfg, det_cfg, ExperimentConfig(trials=exp_cfg.trials, rng_seed=exp_cfg.rng_seed + 4))

    return Eab - Eabp + Eapb + Eapbp


def main() -> None:
    source_cfg = SourceConfig()
    det_cfg = DetectorConfig(mode="threshold_race")
    exp_cfg = ExperimentConfig(trials=10000, rng_seed=2026)

    a = math.radians(0.0)
    ap = math.radians(45.0)
    b = math.radians(22.5)
    bp = math.radians(67.5)

    S = estimate_S(a, ap, b, bp, source_cfg, det_cfg, exp_cfg)
    print(f"S_bench = {S:+.6f}")


if __name__ == "__main__":
    main()
