
"""
Numerical setup for the cubic-field reactive diagnostic.

What this script does
---------------------
1. Builds the primitive cubic character mod 7.
2. Computes the completed, root-number-normalized channels
       Xi_0(s), Xi_chi(s), Xi_chibar(s)
   so Xi_chi(1/2+it) and Xi_chibar(1/2+it) are real on the critical line.
3. Finds the first N critical-line zeros of Xi_chi by sign-scan + root find.
4. Forms the phase vector and Fortescue/sequence components.
5. Computes the sequence diagnostics
       P0, P+, P-, P+-, Q+-, P0+, Q0+, P0-, Q0-
6. Runs a synthetic "off-critical insertion" experiment by replacing one channel
   with its value at sigma + i t while leaving the other channels on the line.

Caveat
------
The off-critical insertion is synthetic. It is a numerical probe for the
conjectural diagnostic Q_{+-}; it is NOT a theorem-level model of GRH violation.
"""

import cmath
import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

import mpmath as mp
import numpy as np

mp.mp.dps = 80

# ------------------------------------------------------------------
# 1. Cubic character mod 7
# ------------------------------------------------------------------

Q = 7
omega = mp.e ** (2j * mp.pi / 3)

# Primitive cubic character mod 7:
# 1 -> 1
# 3,4 -> omega
# 2,5 -> omega^2
# 6=-1 -> 1
CHI = [0, 1, omega**2, omega, omega, omega**2, 1]
CHI_BAR = [mp.conj(z) for z in CHI]

def gauss_sum(char_vals: List[complex], q: int) -> complex:
    return sum(char_vals[n] * mp.e ** (2j * mp.pi * n / q) for n in range(1, q))

TAU = gauss_sum(CHI, Q)
EPS = TAU / mp.sqrt(Q)          # even character: epsilon = tau / sqrt(q)
EPS_BAR = mp.conj(EPS)

# Choose square roots so the completed functions are real on the line.
EPS_INV_HALF = mp.e ** (-1j * mp.arg(EPS) / 2)
EPS_BAR_INV_HALF = mp.e ** (-1j * mp.arg(EPS_BAR) / 2)

# ------------------------------------------------------------------
# 2. Completed channels
# ------------------------------------------------------------------

def Lambda_dirichlet(s: complex, char_vals: List[complex], q: int = Q, parity: int = 0):
    """Completed Dirichlet L-function for an even primitive character."""
    return (q / mp.pi) ** ((s + parity) / 2) * mp.gamma((s + parity) / 2) * mp.dirichlet(s, char_vals)

def Xi_zeta(s: complex):
    """Completed zeta channel, normalized to be real on Re(s)=1/2."""
    return mp.pi ** (-s / 2) * mp.gamma(s / 2) * mp.zeta(s)

def Xi_chi(s: complex):
    """Root-number-normalized completed cubic character channel."""
    return EPS_INV_HALF * Lambda_dirichlet(s, CHI)

def Xi_chibar(s: complex):
    """Root-number-normalized completed conjugate cubic character channel."""
    return EPS_BAR_INV_HALF * Lambda_dirichlet(s, CHI_BAR)

def Xi_chi_real(t: float) -> float:
    return float(mp.re(Xi_chi(mp.mpf('0.5') + 1j * t)))

def Xi_chibar_real(t: float) -> float:
    return float(mp.re(Xi_chibar(mp.mpf('0.5') + 1j * t)))

# ------------------------------------------------------------------
# 3. Zero finding on the critical line
# ------------------------------------------------------------------

def find_critical_line_zeros(real_function, t_min: float, t_max: float, dt: float, n_roots: int) -> List[mp.mpf]:
    roots = []
    t_prev = t_min
    f_prev = real_function(t_prev)
    t = t_prev + dt
    while t <= t_max and len(roots) < n_roots:
        f_cur = real_function(t)
        if f_prev == 0:
            roots.append(mp.mpf(t_prev))
        elif f_prev * f_cur < 0:
            root = mp.findroot(lambda x: real_function(float(x)), (t_prev, t))
            if not roots or abs(root - roots[-1]) > mp.mpf("1e-8"):
                roots.append(root)
        t_prev, f_prev = t, f_cur
        t += dt
    return roots

# ------------------------------------------------------------------
# 4. Fortescue transform and diagnostics
# ------------------------------------------------------------------

a = complex(-0.5, math.sqrt(3) / 2.0)

T_INV = np.array([
    [1, 1, 1],
    [1, a, a * a],
    [1, a * a, a],
], dtype=complex) / 3.0

@dataclass
class SequenceDiagnostics:
    G0: complex
    Gp: complex
    Gm: complex
    P0: float
    Pp: float
    Pm: float
    Ppm: float
    Qpm: float
    P0p: float
    Q0p: float
    P0m: float
    Q0m: float

def phase_vector(s: complex) -> np.ndarray:
    return np.array([
        complex(Xi_zeta(s)),
        complex(Xi_chi(s)),
        complex(Xi_chibar(s)),
    ], dtype=complex)

def sequence_vector_from_phase(v_phase: np.ndarray) -> np.ndarray:
    return T_INV @ v_phase

def sequence_diagnostics_from_sequence(v_seq: np.ndarray) -> SequenceDiagnostics:
    G0, Gp, Gm = v_seq
    return SequenceDiagnostics(
        G0=G0,
        Gp=Gp,
        Gm=Gm,
        P0=float(abs(G0) ** 2),
        Pp=float(abs(Gp) ** 2),
        Pm=float(abs(Gm) ** 2),
        Ppm=float(np.real(Gp * np.conj(Gm))),
        Qpm=float(np.imag(Gp * np.conj(Gm))),
        P0p=float(np.real(G0 * np.conj(Gp))),
        Q0p=float(np.imag(G0 * np.conj(Gp))),
        P0m=float(np.real(G0 * np.conj(Gm))),
        Q0m=float(np.imag(G0 * np.conj(Gm))),
    )

def diagnostics_at_height(t: float) -> Dict[str, object]:
    s = mp.mpf("0.5") + 1j * t
    v_phase = phase_vector(s)
    v_seq = sequence_vector_from_phase(v_phase)
    diag = sequence_diagnostics_from_sequence(v_seq)
    # PSD sanity check on the critical line:
    S_phase = np.outer(v_phase, np.conj(v_phase))
    S_seq = np.outer(v_seq, np.conj(v_seq))
    eigs_phase = np.linalg.eigvalsh(S_phase)
    eigs_seq = np.linalg.eigvalsh(S_seq)
    return {
        "t": t,
        "s": s,
        "phase_vector": v_phase,
        "sequence_vector": v_seq,
        "diagnostics": diag,
        "phase_eigs": eigs_phase,
        "seq_eigs": eigs_seq,
    }

# ------------------------------------------------------------------
# 5. Synthetic off-critical insertion
# ------------------------------------------------------------------

def synthetic_offcritical_case(t: float, sigma: float, which: str = "chi") -> Dict[str, object]:
    """
    Replace one completed channel value by its value at sigma + i t,
    while leaving the other channels on the critical line.
    """
    s_line = mp.mpf("0.5") + 1j * t
    s_off = mp.mpf(str(sigma)) + 1j * t

    v = phase_vector(s_line).copy()
    if which == "chi":
        v[1] = complex(Xi_chi(s_off))
    elif which == "chibar":
        v[2] = complex(Xi_chibar(s_off))
    elif which == "zeta":
        v[0] = complex(Xi_zeta(s_off))
    else:
        raise ValueError("which must be one of: zeta, chi, chibar")

    v_seq = sequence_vector_from_phase(v)
    diag = sequence_diagnostics_from_sequence(v_seq)
    return {
        "t": t,
        "sigma": sigma,
        "which": which,
        "phase_vector": v,
        "sequence_vector": v_seq,
        "diagnostics": diag,
    }

# ------------------------------------------------------------------
# 6. Minimal runner
# ------------------------------------------------------------------

def main():
    print("=" * 80)
    print("CUBIC REACTIVE DIAGNOSTIC SETUP")
    print("=" * 80)
    print(f"modulus q = {Q}")
    print(f"epsilon(chi) = {EPS}")
    print(f"|epsilon(chi)| = {abs(EPS)}")

    print("\nFinding first 5 critical-line zeros of Xi_chi ...")
    roots = find_critical_line_zeros(Xi_chi_real, t_min=0.1, t_max=60.0, dt=0.05, n_roots=5)
    for k, r in enumerate(roots, start=1):
        print(f"  zero {k}: t = {r}")

    if not roots:
        print("No roots found; stopping.")
        return

    t0 = float(roots[0])

    print("\nCritical-line PSD sanity check at the first chi-zero height:")
    res = diagnostics_at_height(t0)
    print("  phase eigenvalues:", res["phase_eigs"])
    print("  seq eigenvalues:  ", res["seq_eigs"])
    d = res["diagnostics"]
    print(f"  P0={d.P0:.6e}, P+={d.Pp:.6e}, P-={d.Pm:.6e}, Q+-={d.Qpm:.6e}")

    sigma = 0.75
    print(f"\nSynthetic off-critical insertion at sigma={sigma}, t={t0:.6f}")
    for which in ["chi", "chibar", "zeta"]:
        out = synthetic_offcritical_case(t0, sigma=sigma, which=which)
        dd = out["diagnostics"]
        print(
            f"  {which:>6s}: "
            f"P0={dd.P0:.6e}, P+={dd.Pp:.6e}, P-={dd.Pm:.6e}, "
            f"P+-={dd.Ppm:.6e}, Q+-={dd.Qpm:.6e}"
        )

if __name__ == "__main__":
    main()
