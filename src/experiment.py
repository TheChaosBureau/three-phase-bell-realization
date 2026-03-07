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
    power_wave_amplitude,
)
from .detector import sample_from_joint_probs


def local_analyzer_coeff(theta: float, branch: str, seq: str) -> complex:
    """
    Coefficient from one local sequence component seq in {"+","-"}
    to one analyzer output branch in {"u","v"}.

    u(theta) = (e^{-j theta} (+) + e^{+j theta} (-)) / sqrt(2)
    v(theta) = (-e^{-j theta} (+) + e^{+j theta} (-)) / sqrt(2)
    """
    if branch not in ("u", "v"):
        raise ValueError(f"Unknown branch {branch}")
    if seq not in ("+", "-"):
        raise ValueError(f"Unknown sequence {seq}")

    e_minus = math.cos(theta) - 1j * math.sin(theta)
    e_plus = math.cos(theta) + 1j * math.sin(theta)

    if branch == "u" and seq == "+":
        return e_minus / math.sqrt(2.0)
    if branch == "u" and seq == "-":
        return e_plus / math.sqrt(2.0)
    if branch == "v" and seq == "+":
        return -e_minus / math.sqrt(2.0)
    if branch == "v" and seq == "-":
        return e_plus / math.sqrt(2.0)

    raise RuntimeError("Unreachable")


def build_local_mode_amplitudes(state, G0: float) -> dict[str, complex]:
    """
    Build the local sequence-mode amplitudes from the programmable source state.
    """
    return {
        "A+": power_wave_amplitude(state.VA_plus, state.IA_plus, G0),
        "A-": power_wave_amplitude(state.VA_minus, state.IA_minus, G0),
        "B+": power_wave_amplitude(state.VB_plus, state.IB_plus, G0),
        "B-": power_wave_amplitude(state.VB_minus, state.IB_minus, G0),
    }


def joint_coincidence_amplitudes(
    a: float,
    b: float,
    source_cfg: SourceConfig,
) -> dict[str, complex]:
    """
    Build joint coincidence amplitudes directly from the two coherent source paths.

    This preserves the antisymmetric pair structure:
        (A+ B- - exp(j phi_s) A- B+) / sqrt(2)

    For each coincidence channel ij:
        d_ij = ( c_i^(A+) c_j^(B-) - exp(j phi_s) c_i^(A-) c_j^(B+) ) / sqrt(2)
    """
    state = build_antisymmetric_source(source_cfg)
    modes = build_local_mode_amplitudes(state, source_cfg.G0)

    rel = math.cos(source_cfg.phi_s) + 1j * math.sin(source_cfg.phi_s)

    amps: dict[str, complex] = {}

    for a_branch, a_label in (("u", "+"), ("v", "-")):
        for b_branch, b_label in (("u", "+"), ("v", "-")):
            key = a_label + b_label

            # Path 1: A+ with B-
            path1 = (
                local_analyzer_coeff(a, a_branch, "+") * modes["A+"]
                * local_analyzer_coeff(b, b_branch, "-") * modes["B-"]
            )

            # Path 2: A- with B+
            path2 = (
                local_analyzer_coeff(a, a_branch, "-") * modes["A-"]
                * local_analyzer_coeff(b, b_branch, "+") * modes["B+"]
            )

            amps[key] = (path1 - rel * path2) / math.sqrt(2.0)

    return amps


def joint_coincidence_probabilities(
    a: float,
    b: float,
    source_cfg: SourceConfig,
) -> dict[str, float]:
    amps = joint_coincidence_amplitudes(a, b, source_cfg)
    raw = {k: abs(v) ** 2 for k, v in amps.items()}
    total = sum(raw.values())
    if total <= 0:
        raise ValueError("Non-positive total probability.")
    return {k: v / total for k, v in raw.items()}


def run_single_trial_joint(
    a: float,
    b: float,
    source_cfg: SourceConfig,
    det_cfg: DetectorConfig,
    rng: random.Random,
) -> tuple[int, int]:
    """
    Trial using the joint coincidence-amplitude builder.

    For now both detector modes reduce to sampling from the joint channel weights.
    That is appropriate here because the important thing is preserving the pair
    interference before squaring.
    """
    probs = joint_coincidence_probabilities(a, b, source_cfg)
    return sample_from_joint_probs(probs, rng)


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
        A, B = run_single_trial_joint(a, b, source_cfg, det_cfg, rng)
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
    det_cfg = DetectorConfig(mode="categorical")
    exp_cfg = ExperimentConfig(trials=50000, rng_seed=2026)

    a = math.radians(0.0)
    ap = math.radians(45.0)
    b = math.radians(22.5)
    bp = math.radians(67.5)

    print("Joint programmable-source bench")
    print()

    for aa, bb in [(a, b), (a, bp), (ap, b), (ap, bp)]:
        probs = joint_coincidence_probabilities(aa, bb, source_cfg)
        E_hat = estimate_E(aa, bb, source_cfg, det_cfg, exp_cfg)
        E_ref = exact_reference_E(aa, bb)

        print(
            f"a={math.degrees(aa):6.1f}°, b={math.degrees(bb):6.1f}°  "
            f"E_hat={E_hat:+.6f}, E_ref={E_ref:+.6f}"
        )
        print(
            f"    P++={probs['++']:.6f}  P+-={probs['+-']:.6f}  "
            f"P-+={probs['-+']:.6f}  P--={probs['--']:.6f}"
        )

    S_hat = estimate_S(a, ap, b, bp, source_cfg, det_cfg, exp_cfg)
    S_ref = exact_reference_S(a, ap, b, bp)

    print()
    print(f"S_hat = {S_hat:+.6f}")
    print(f"S_ref = {S_ref:+.6f}")
    print(f"2*sqrt(2) = {2.0 * math.sqrt(2.0):+.6f}")


if __name__ == "__main__":
    main()