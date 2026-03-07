"""
Minimal Python simulator for the sequence-mode Bell-style toy model.

What it does
------------
1. Builds the antisymmetric source state in sequence variables:
       Phi = (A+ B- - A- B+) / sqrt(2)

2. Applies local analyzer mixing at Alice angle a and Bob angle b:
       u(theta) = (exp(-j theta) * (+) + exp(+j theta) * (-)) / sqrt(2)
       v(theta) = (-exp(-j theta) * (+) + exp(+j theta) * (-)) / sqrt(2)

3. Computes coincidence amplitudes and probabilities.

4. Supports two detector models:
   - categorical: exact Born-style sampling from P++, P+-, P-+, P--
   - threshold_race: integrated-energy / hazard-race approximation

5. Estimates E(a,b) and CHSH S over many trials.

This is a compact experiment simulator for conceptual exploration.
It is not claiming a classical Bell-violation mechanism in hardware.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Literal, Tuple
import math
import cmath
import random


Outcome = Tuple[int, int]  # (Alice, Bob), each in {+1, -1}
DetectorMode = Literal["categorical", "threshold_race"]


@dataclass
class ExperimentConfig:
    trials: int = 10000
    detector_mode: DetectorMode = "categorical"
    rng_seed: int = 1234
    threshold_gamma: float = 1.0  # used by threshold_race
    source_phase: float = 0.0     # relative phase between the two source paths
    verbose: bool = False


# ---------------------------------------------------------------------
# Core model: source, analyzer mixing, coincidence amplitudes
# ---------------------------------------------------------------------

def analyzer_plus_coeff(theta: float, mode: Literal["plus", "minus"]) -> complex:
    """
    Local analyzer output coefficients in sequence basis.

    For a local input basis (+, -), the analyzer outputs are:
        u(theta) = (exp(-j theta)*(+) + exp(+j theta)*(-)) / sqrt(2)
        v(theta) = (-exp(-j theta)*(+) + exp(+j theta)*(-)) / sqrt(2)

    Returns coefficient for the requested local output branch.
    """
    if mode == "plus":
        return cmath.exp(-1j * theta) / math.sqrt(2)
    return -cmath.exp(-1j * theta) / math.sqrt(2)


def analyzer_minus_coeff(theta: float, mode: Literal["plus", "minus"]) -> complex:
    """
    Coefficient multiplying the local '-' sequence component.
    """
    if mode == "plus":
        return cmath.exp(+1j * theta) / math.sqrt(2)
    return cmath.exp(+1j * theta) / math.sqrt(2)


def local_branch_amplitude(theta: float, branch: Literal["plus", "minus"], seq: Literal["plus", "minus"]) -> complex:
    """
    Coefficient from one local sequence input seq in {+, -} to one local analyzer branch.
    """
    if seq == "plus":
        return analyzer_plus_coeff(theta, branch)
    return analyzer_minus_coeff(theta, branch)


def coincidence_amplitudes(a: float, b: float, source_phase: float = 0.0) -> Dict[str, complex]:
    """
    Coincidence amplitudes for the antisymmetric source

        Phi = ( |A+ B-> - exp(j*source_phase) |A- B+> ) / sqrt(2)

    Branch labels:
        ++, +-, -+, --

    Returns dict with complex amplitudes d_{ij}.
    """
    rel_phase = cmath.exp(1j * source_phase)

    amps: Dict[str, complex] = {}

    # Path 1: A+ B-
    # Path 2: A- B+ with a relative minus sign and optional phase
    for a_branch in ("plus", "minus"):
        for b_branch in ("plus", "minus"):
            key = ("+" if a_branch == "plus" else "-") + ("+" if b_branch == "plus" else "-")

            path1 = (
                local_branch_amplitude(a, a_branch, "plus")
                * local_branch_amplitude(b, b_branch, "minus")
            )

            path2 = (
                local_branch_amplitude(a, a_branch, "minus")
                * local_branch_amplitude(b, b_branch, "plus")
            )

            amps[key] = (path1 - rel_phase * path2) / math.sqrt(2)

    return amps


def coincidence_probabilities(a: float, b: float, source_phase: float = 0.0) -> Dict[str, float]:
    """
    Probabilities P_{ij} = |d_{ij}|^2, normalized.
    """
    amps = coincidence_amplitudes(a, b, source_phase=source_phase)
    probs = {k: abs(v) ** 2 for k, v in amps.items()}
    total = sum(probs.values())
    if total <= 0:
        raise ValueError("Total probability is non-positive.")
    return {k: v / total for k, v in probs.items()}


# ---------------------------------------------------------------------
# Theory helpers
# ---------------------------------------------------------------------

def correlator_theory(a: float, b: float) -> float:
    """
    Closed-form correlator for the antisymmetric state in this polarization-like model:
        E(a,b) = -cos(2(a-b))
    """
    return -math.cos(2.0 * (a - b))


def chsh_theory(a: float, ap: float, b: float, bp: float) -> float:
    """
    User's exact sign convention:
        S = E(a,b) - E(a,b') + E(a',b) + E(a',b')
    """
    return (
        correlator_theory(a, b)
        - correlator_theory(a, bp)
        + correlator_theory(ap, b)
        + correlator_theory(ap, bp)
    )


# ---------------------------------------------------------------------
# Detector models
# ---------------------------------------------------------------------

def sample_categorical(probs: Dict[str, float], rng: random.Random) -> Outcome:
    """
    Exact sampling from the coincidence distribution.
    """
    keys = ["++", "+-", "-+", "--"]
    weights = [probs[k] for k in keys]
    outcome = rng.choices(keys, weights=weights, k=1)[0]
    return decode_outcome(outcome)


def sample_threshold_race(
    probs: Dict[str, float],
    rng: random.Random,
    gamma: float = 1.0,
) -> Outcome:
    """
    Integrated-energy / threshold-race-inspired sampling.

    Interpretation:
    - Each coincidence channel ij gets an integrated energy weight W_ij proportional to probs[ij].
    - A memoryless first-click race with rate lambda_ij = gamma * W_ij yields
      selection probability proportional to W_ij.
    - Sampling from exponential arrival times realizes that race explicitly.

    This preserves the same normalized channel statistics in the ideal limit.
    """
    keys = ["++", "+-", "-+", "--"]
    arrival_times = []

    for key in keys:
        rate = max(gamma * probs[key], 1e-15)
        t = rng.expovariate(rate)
        arrival_times.append((t, key))

    _, winner = min(arrival_times, key=lambda item: item[0])
    return decode_outcome(winner)


def decode_outcome(label: str) -> Outcome:
    """
    '++' -> (+1, +1), '+-' -> (+1, -1), etc.
    """
    if label == "++":
        return (+1, +1)
    if label == "+-":
        return (+1, -1)
    if label == "-+":
        return (-1, +1)
    if label == "--":
        return (-1, -1)
    raise ValueError(f"Unknown outcome label: {label}")


# ---------------------------------------------------------------------
# Experiment execution
# ---------------------------------------------------------------------

def run_setting(a: float, b: float, cfg: ExperimentConfig) -> Dict[str, float]:
    """
    Run many trials at one analyzer setting pair (a,b).
    Returns counts, probabilities, and estimated correlator.
    """
    rng = random.Random(cfg.rng_seed)

    counts = {"++": 0, "+-": 0, "-+": 0, "--": 0}
    probs = coincidence_probabilities(a, b, source_phase=cfg.source_phase)

    sampler = sample_categorical if cfg.detector_mode == "categorical" else (
        lambda p, r: sample_threshold_race(p, r, gamma=cfg.threshold_gamma)
    )

    for _ in range(cfg.trials):
        A, B = sampler(probs, rng)
        label = encode_outcome(A, B)
        counts[label] += 1

    freqs = {k: counts[k] / cfg.trials for k in counts}
    E_hat = freqs["++"] + freqs["--"] - freqs["+-"] - freqs["-+"]
    E_exact = correlator_theory(a, b)

    result = {
        "P++": freqs["++"],
        "P+-": freqs["+-"],
        "P-+": freqs["-+"],
        "P--": freqs["--"],
        "E_hat": E_hat,
        "E_exact": E_exact,
    }

    if cfg.verbose:
        print(
            f"a={math.degrees(a):6.2f}°, b={math.degrees(b):6.2f}°  "
            f"E_hat={E_hat:+.6f}, E_exact={E_exact:+.6f}"
        )

    return result


def encode_outcome(A: int, B: int) -> str:
    """
    (+1, -1) -> '+-' etc.
    """
    return ("+" if A > 0 else "-") + ("+" if B > 0 else "-")


def estimate_chsh(a: float, ap: float, b: float, bp: float, cfg: ExperimentConfig) -> Dict[str, float]:
    """
    Estimate CHSH using the user's exact sign convention:
        S = E(a,b) - E(a,b') + E(a',b) + E(a',b')
    """
    # use distinct seeds per setting to avoid accidental coupling in Monte Carlo
    cfg1 = ExperimentConfig(**{**cfg.__dict__, "rng_seed": cfg.rng_seed + 1})
    cfg2 = ExperimentConfig(**{**cfg.__dict__, "rng_seed": cfg.rng_seed + 2})
    cfg3 = ExperimentConfig(**{**cfg.__dict__, "rng_seed": cfg.rng_seed + 3})
    cfg4 = ExperimentConfig(**{**cfg.__dict__, "rng_seed": cfg.rng_seed + 4})

    r_ab = run_setting(a, b, cfg1)
    r_abp = run_setting(a, bp, cfg2)
    r_apb = run_setting(ap, b, cfg3)
    r_apbp = run_setting(ap, bp, cfg4)

    S_hat = r_ab["E_hat"] - r_abp["E_hat"] + r_apb["E_hat"] + r_apbp["E_hat"]
    S_exact = chsh_theory(a, ap, b, bp)

    return {
        "E(a,b)": r_ab["E_hat"],
        "E(a,b')": r_abp["E_hat"],
        "E(a',b)": r_apb["E_hat"],
        "E(a',b')": r_apbp["E_hat"],
        "S_hat": S_hat,
        "S_exact": S_exact,
    }


# ---------------------------------------------------------------------
# Utility: scan over a small angle grid
# ---------------------------------------------------------------------

def scan_chsh(
    a: float,
    a_primes: Iterable[float],
    b_vals: Iterable[float],
    bp_vals: Iterable[float],
    cfg: ExperimentConfig,
) -> Tuple[Tuple[float, float, float], float]:
    """
    Scan |S| over a grid, fixing a and varying (a', b, b').
    Returns best (a', b, b') and best |S_exact|.
    """
    best_tuple = None
    best_abs_s = -1.0

    for ap in a_primes:
        for b in b_vals:
            for bp in bp_vals:
                s = abs(chsh_theory(a, ap, b, bp))
                if s > best_abs_s:
                    best_abs_s = s
                    best_tuple = (ap, b, bp)

    if best_tuple is None:
        raise RuntimeError("No grid points scanned.")

    return best_tuple, best_abs_s


# ---------------------------------------------------------------------
# Demo / main
# ---------------------------------------------------------------------

def deg(x: float) -> float:
    return math.radians(x)


def main() -> None:
    print("\n=== Minimal sequence-mode Bell-style simulator ===\n")

    cfg = ExperimentConfig(
        trials=50000,
        # detector_mode="threshold_race",  # try "categorical" too
        detector_mode="catagorical",  # try "categorical" too
        rng_seed=2026,
        threshold_gamma=1.0,
        source_phase=0.0,
        verbose=False,
    )
    print("Detector Mode: " + cfg.detector_mode + "\n")

    # Standard near-optimal angles for this polarization-like model
    a = deg(0.0)
    ap = deg(45.0)
    b = deg(22.5)
    bp = deg(67.5)

    print("Single-setting sanity checks:")
    for aa, bb in [(a, b), (a, bp), (ap, b), (ap, bp)]:
        result = run_setting(aa, bb, cfg)
        print(
            f"  a={math.degrees(aa):6.1f}°, b={math.degrees(bb):6.1f}°  "
            f"E_hat={result['E_hat']:+.5f}, E_exact={result['E_exact']:+.5f}"
        )

    print("\nCHSH estimate:")
    chsh = estimate_chsh(a, ap, b, bp, cfg)
    for k, v in chsh.items():
        print(f"  {k:8s} = {v:+.6f}")

    print(f"\n  Tsirelson bound = {2 * math.sqrt(2):+.6f}")

    # Probability sanity check at one setting
    print("\nCoincidence probabilities at a=0°, b=22.5°:")
    probs = coincidence_probabilities(a, b)
    for key in ["++", "+-", "-+", "--"]:
        print(f"  P{key} = {probs[key]:.6f}")

    # Small exact scan
    print("\nExact theory scan over a coarse grid:")
    grid_deg = [0, 22.5, 45, 67.5, 90, 112.5, 135, 157.5]
    best_tuple, best_abs_s = scan_chsh(
        a=deg(0.0),
        a_primes=[deg(x) for x in grid_deg],
        b_vals=[deg(x) for x in grid_deg],
        bp_vals=[deg(x) for x in grid_deg],
        cfg=cfg,
    )
    ap_best, b_best, bp_best = best_tuple
    print(
        f"  best coarse-grid angles: a'= {math.degrees(ap_best):.1f}°, "
        f"b= {math.degrees(b_best):.1f}°, b'= {math.degrees(bp_best):.1f}°"
    )
    print(f"  best |S_exact| = {best_abs_s:.6f}")

    print("\nDone.")


if __name__ == "__main__":
    main()