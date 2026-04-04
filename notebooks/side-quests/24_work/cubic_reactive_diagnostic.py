import argparse
import math
from dataclasses import dataclass
from typing import Dict, List

import mpmath as mp
import numpy as np

mp.mp.dps = 80

# ------------------------------------------------------------------
# 1. Cubic character mod 7
# ------------------------------------------------------------------

Q = 7
omega = mp.e ** (2j * mp.pi / 3)

CHI = [0, 1, omega**2, omega, omega, omega**2, 1]
CHI_BAR = [mp.conj(z) for z in CHI]

def gauss_sum(char_vals: List[complex], q: int) -> complex:
    return sum(char_vals[n] * mp.e ** (2j * mp.pi * n / q) for n in range(1, q))

TAU = gauss_sum(CHI, Q)
EPS = TAU / mp.sqrt(Q)
EPS_BAR = mp.conj(EPS)

EPS_INV_HALF = mp.e ** (-1j * mp.arg(EPS) / 2)
EPS_BAR_INV_HALF = mp.e ** (-1j * mp.arg(EPS_BAR) / 2)

# ------------------------------------------------------------------
# 2. Completed channels
# ------------------------------------------------------------------

def Lambda_dirichlet(s: complex, char_vals: List[complex], q: int = Q, parity: int = 0):
    return (q / mp.pi) ** ((s + parity) / 2) * mp.gamma((s + parity) / 2) * mp.dirichlet(s, char_vals)

def Xi_zeta(s: complex):
    return mp.pi ** (-s / 2) * mp.gamma(s / 2) * mp.zeta(s)

def Xi_chi(s: complex):
    return EPS_INV_HALF * Lambda_dirichlet(s, CHI)

def Xi_chibar(s: complex):
    return EPS_BAR_INV_HALF * Lambda_dirichlet(s, CHI_BAR)

def Xi_chi_real(t):
    return mp.re(Xi_chi(mp.mpf('0.5') + 1j * mp.mpf(t)))

def Xi_chibar_real(t):
    return mp.re(Xi_chibar(mp.mpf('0.5') + 1j * mp.mpf(t)))

# ------------------------------------------------------------------
# 3. Zero finding on the critical line
# ------------------------------------------------------------------

def bisect_root(real_function, a, b, max_iter=120, tol=mp.mpf("1e-30")):
    a = mp.mpf(a)
    b = mp.mpf(b)
    fa = real_function(a)
    fb = real_function(b)

    if fa == 0:
        return a
    if fb == 0:
        return b
    if fa * fb > 0:
        raise ValueError("bisect_root requires a sign change")

    for _ in range(max_iter):
        c = (a + b) / 2
        fc = real_function(c)

        if fc == 0 or abs(b - a) < tol:
            return c

        if fa * fc < 0:
            b, fb = c, fc
        else:
            a, fa = c, fc

    return (a + b) / 2

def refine_root(real_function, a, b):
    a = mp.mpf(a)
    b = mp.mpf(b)
    # First bracket safely by bisection, then polish with findroot.
    c = bisect_root(real_function, a, b, max_iter=80, tol=mp.mpf("1e-20"))
    try:
        r = mp.findroot(real_function, (a, b), tol=1e-20, verify=False, solver="secant", maxsteps=100)
        # Only trust it if it stayed inside the bracket and improved the residual.
        if min(a, b) <= r <= max(a, b):
            if abs(real_function(r)) <= abs(real_function(c)):
                return r
    except Exception:
        pass
    return c

def find_critical_line_zeros(real_function, t_min, t_max, dt, n_roots):
    roots = []
    t_prev = mp.mpf(t_min)
    f_prev = real_function(t_prev)
    t = t_prev + mp.mpf(dt)

    while t <= t_max and len(roots) < n_roots:
        f_cur = real_function(t)

        if f_prev == 0:
            root = t_prev
            if not roots or abs(root - roots[-1]) > mp.mpf("1e-8"):
                roots.append(root)
        elif f_prev * f_cur < 0:
            root = refine_root(real_function, t_prev, t)
            if not roots or abs(root - roots[-1]) > mp.mpf("1e-8"):
                roots.append(root)

        t_prev, f_prev = t, f_cur
        t += mp.mpf(dt)

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
    s = mp.mpf("0.5") + 1j * mp.mpf(t)
    v_phase = phase_vector(s)
    v_seq = sequence_vector_from_phase(v_phase)
    diag = sequence_diagnostics_from_sequence(v_seq)
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
    s_line = mp.mpf("0.5") + 1j * mp.mpf(t)
    s_off = mp.mpf(str(sigma)) + 1j * mp.mpf(t)

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
# 6. CLI
# ------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--sigma", type=float, default=0.75)
    p.add_argument("--which", choices=["chi", "chibar", "zeta", "all"], default="all")
    p.add_argument("--zero-index", type=int, default=0, help="0-based index into detected chi zeros")
    p.add_argument("--n-roots", type=int, default=5)
    p.add_argument("--t-min", type=float, default=0.1)
    p.add_argument("--t-max", type=float, default=60.0)
    p.add_argument("--dt", type=float, default=0.05)
    return p.parse_args()

def main():
    args = parse_args()

    print("=" * 80)
    print("CUBIC REACTIVE DIAGNOSTIC SETUP (PATCHED)")
    print("=" * 80)
    print(f"modulus q = {Q}")
    print(f"epsilon(chi) = {EPS}")
    print(f"|epsilon(chi)| = {abs(EPS)}")

    print(f"\nFinding first {args.n_roots} critical-line zeros of Xi_chi ...")
    roots = find_critical_line_zeros(
        Xi_chi_real,
        t_min=args.t_min,
        t_max=args.t_max,
        dt=args.dt,
        n_roots=args.n_roots,
    )
    for k, r in enumerate(roots, start=1):
        print(f"  zero {k}: t = {r}")

    if not roots:
        print("No roots found; try increasing --t-max or reducing --dt.")
        return

    if args.zero_index < 0 or args.zero_index >= len(roots):
        raise ValueError(f"--zero-index must be between 0 and {len(roots)-1}")

    t0 = roots[args.zero_index]

    print(f"\nCritical-line PSD sanity check at chi-zero index {args.zero_index} (t={t0}):")
    res = diagnostics_at_height(t0)
    print("  phase eigenvalues:", res["phase_eigs"])
    print("  seq eigenvalues:  ", res["seq_eigs"])
    d = res["diagnostics"]
    print(f"  P0={d.P0:.6e}, P+={d.Pp:.6e}, P-={d.Pm:.6e}, Q+-={d.Qpm:.6e}")

    print(f"\nSynthetic off-critical insertion at sigma={args.sigma}, t={t0}")
    which_list = ["chi", "chibar", "zeta"] if args.which == "all" else [args.which]
    for which in which_list:
        out = synthetic_offcritical_case(t0, sigma=args.sigma, which=which)
        dd = out["diagnostics"]
        print(
            f"  {which:>6s}: "
            f"P0={dd.P0:.6e}, P+={dd.Pp:.6e}, P-={dd.Pm:.6e}, "
            f"P+-={dd.Ppm:.6e}, Q+-={dd.Qpm:.6e}"
        )

if __name__ == "__main__":
    main()