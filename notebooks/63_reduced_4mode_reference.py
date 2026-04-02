#!/usr/bin/env python3
from __future__ import annotations
import argparse, math
from dataclasses import dataclass
import numpy as np

def normalize(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=np.complex128).reshape(-1)
    n = np.linalg.norm(v)
    if n == 0:
        raise ValueError("Vector must be nonzero.")
    return v / n

def singlet_state() -> np.ndarray:
    return normalize(np.array([0.0, 1.0, -1.0, 0.0], dtype=np.complex128))

def projector_hamiltonian(omega0: float = 1.0, delta: float = 0.5,
                          psi_ref: np.ndarray | None = None) -> np.ndarray:
    if psi_ref is None:
        psi_ref = singlet_state()
    psi_ref = normalize(psi_ref)
    proj = np.outer(psi_ref, np.conjugate(psi_ref))
    return omega0 * np.eye(4, dtype=np.complex128) + delta * proj

def evolve_state(H: np.ndarray, psi0: np.ndarray, t: float) -> np.ndarray:
    evals, evecs = np.linalg.eigh(H)
    phases = np.exp(-1j * evals * t)
    return evecs @ (phases * (np.conjugate(evecs).T @ psi0))

def R(theta_rad: float) -> np.ndarray:
    c = math.cos(theta_rad); s = math.sin(theta_rad)
    return np.array([[c, s], [-s, c]], dtype=np.complex128)

def joint_rotation(a_rad: float, b_rad: float) -> np.ndarray:
    return np.kron(R(a_rad), R(b_rad))

def rotate_state(psi: np.ndarray, a_rad: float, b_rad: float) -> np.ndarray:
    return joint_rotation(a_rad, b_rad) @ psi

BASIS_LABELS = ["++", "+-", "-+", "--"]

def joint_amplitudes(psi_rot: np.ndarray) -> np.ndarray:
    return np.asarray(psi_rot, dtype=np.complex128).reshape(4).copy()

def joint_weights(psi_rot: np.ndarray) -> np.ndarray:
    amps = joint_amplitudes(psi_rot)
    w = np.abs(amps) ** 2
    s = np.sum(w)
    if s <= 0:
        raise ValueError("State has zero total weight.")
    return w / s

def same_diff_probs(weights: np.ndarray) -> tuple[float, float]:
    w = np.asarray(weights, dtype=float).reshape(4)
    return float(w[0] + w[3]), float(w[1] + w[2])

def correlator(weights: np.ndarray) -> float:
    w = np.asarray(weights, dtype=float).reshape(4)
    return float(w[0] - w[1] - w[2] + w[3])

def singlet_closed_form_weights(delta_rad: float) -> np.ndarray:
    s2 = math.sin(delta_rad) ** 2
    c2 = math.cos(delta_rad) ** 2
    return np.array([0.5 * s2, 0.5 * c2, 0.5 * c2, 0.5 * s2], dtype=float)

def sample_joint_outcomes(weights: np.ndarray, n_trials: int,
                          rng: np.random.Generator) -> np.ndarray:
    w = np.asarray(weights, dtype=float).reshape(4)
    outcomes = rng.choice(4, size=n_trials, p=w)
    counts = np.bincount(outcomes, minlength=4)
    return counts / n_trials

def E_for_angles(psi0: np.ndarray, a_deg: float, b_deg: float) -> float:
    a = math.radians(a_deg); b = math.radians(b_deg)
    psi_rot = rotate_state(psi0, a, b)
    return correlator(joint_weights(psi_rot))

def chsh_S(psi0: np.ndarray, a0_deg: float, a1_deg: float,
           b0_deg: float, b1_deg: float) -> float:
    e_a0b0 = E_for_angles(psi0, a0_deg, b0_deg)
    e_a0b1 = E_for_angles(psi0, a0_deg, b1_deg)
    e_a1b0 = E_for_angles(psi0, a1_deg, b0_deg)
    e_a1b1 = E_for_angles(psi0, a1_deg, b1_deg)
    return e_a0b0 + e_a0b1 + e_a1b0 - e_a1b1

@dataclass
class OneCaseResult:
    a_deg: float
    b_deg: float
    amplitudes: np.ndarray
    weights: np.ndarray
    p_same: float
    p_diff: float
    correlator: float

def one_case(psi0: np.ndarray, a_deg: float, b_deg: float) -> OneCaseResult:
    psi_rot = rotate_state(psi0, math.radians(a_deg), math.radians(b_deg))
    amps = joint_amplitudes(psi_rot)
    weights = joint_weights(psi_rot)
    p_same, p_diff = same_diff_probs(weights)
    E = correlator(weights)
    return OneCaseResult(a_deg=a_deg, b_deg=b_deg, amplitudes=amps,
                         weights=weights, p_same=p_same, p_diff=p_diff, correlator=E)

def print_one_case(result: OneCaseResult) -> None:
    print(f"a = {result.a_deg:.3f} deg, b = {result.b_deg:.3f} deg, delta = {result.a_deg - result.b_deg:.3f} deg")
    print("amplitudes [++, +-, -+, --] =", np.round(result.amplitudes, 6))
    print("weights    [++, +-, -+, --] =", np.round(result.weights, 6))
    print(f"P_same = {result.p_same:.6f}")
    print(f"P_diff = {result.p_diff:.6f}")
    print(f"E      = {result.correlator:.6f}")

def assert_close(x, y, tol: float = 1e-9, msg: str = "") -> None:
    if not np.allclose(x, y, atol=tol, rtol=0.0):
        raise AssertionError(msg or f"Not close:\n{x}\n!=\n{y}")

def run_tests(verbose: bool = True) -> None:
    psi0 = singlet_state()
    assert_close(np.linalg.norm(psi0), 1.0, tol=1e-12, msg="Singlet not normalized.")
    for deg in [0.0, 17.0, 33.3, 45.0]:
        U = joint_rotation(math.radians(deg), math.radians(-deg / 2))
        assert_close(np.conjugate(U).T @ U, np.eye(4), tol=1e-12, msg="Joint rotation not unitary.")
    for a_deg, b_deg in [(0.0, 0.0), (45.0, 22.5), (0.0, 45.0), (10.0, -20.0)]:
        w = joint_weights(rotate_state(psi0, math.radians(a_deg), math.radians(b_deg)))
        assert_close(np.sum(w), 1.0, tol=1e-12, msg="Weights do not sum to 1.")
    for a_deg, b_deg in [(0.0, 0.0), (45.0, 22.5), (0.0, 45.0), (12.0, -7.0)]:
        delta = math.radians(a_deg - b_deg)
        w_exact = singlet_closed_form_weights(delta)
        w_num = joint_weights(rotate_state(psi0, math.radians(a_deg), math.radians(b_deg)))
        assert_close(w_num, w_exact, tol=1e-12, msg=f"Closed-form weights mismatch at ({a_deg}, {b_deg}).")
    for a_deg, b_deg in [(0.0, 0.0), (45.0, 22.5), (0.0, 45.0), (12.0, -7.0)]:
        delta = math.radians(a_deg - b_deg)
        e_num = E_for_angles(psi0, a_deg, b_deg)
        e_exact = -math.cos(2 * delta)
        assert_close(e_num, e_exact, tol=1e-12, msg=f"Correlator mismatch at ({a_deg}, {b_deg}).")
    S = chsh_S(psi0, 0.0, 45.0, 22.5, -22.5)
    assert_close(abs(S), 2 * math.sqrt(2), tol=1e-12, msg="CHSH |S| mismatch.")
    rng = np.random.default_rng(1234)
    w = joint_weights(rotate_state(psi0, math.radians(45.0), math.radians(22.5)))
    w_emp = sample_joint_outcomes(w, 50000, rng)
    if np.max(np.abs(w_emp - w)) > 0.01:
        raise AssertionError(f"Monte Carlo frequencies too far from exact weights:\n exact={w}\n emp={w_emp}")
    H = projector_hamiltonian(omega0=1.0, delta=0.5, psi_ref=psi0)
    evals, evecs = np.linalg.eigh(H)
    overlaps = np.abs(np.conjugate(evecs).T @ psi0) ** 2
    best_idx = int(np.argmax(overlaps))
    assert_close(overlaps[best_idx], 1.0, tol=1e-12, msg="Singlet is not an eigenvector.")
    assert_close(evals[best_idx], 1.5, tol=1e-12, msg="Singlet eigenvalue incorrect.")
    if verbose:
        print("All tests passed.")

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Reduced 4-mode shared-state simulator.")
    p.add_argument("--run-tests", action="store_true")
    p.add_argument("--one-case", action="store_true")
    p.add_argument("--mc", action="store_true")
    p.add_argument("--chsh", action="store_true")
    p.add_argument("--a", type=float, default=45.0)
    p.add_argument("--b", type=float, default=22.5)
    p.add_argument("--trials", type=int, default=20000)
    p.add_argument("--seed", type=int, default=1234)
    return p

def main() -> None:
    args = build_parser().parse_args()
    psi0 = singlet_state()
    if args.run_tests:
        run_tests(verbose=True); return
    if args.one_case:
        print_one_case(one_case(psi0, args.a, args.b))
    if args.mc:
        rng = np.random.default_rng(args.seed)
        psi_rot = rotate_state(psi0, math.radians(args.a), math.radians(args.b))
        w = joint_weights(psi_rot)
        w_emp = sample_joint_outcomes(w, args.trials, rng)
        print(f"a = {args.a:.3f} deg, b = {args.b:.3f} deg")
        print("weights exact     [++, +-, -+, --] =", np.round(w, 6))
        print("weights empirical [++, +-, -+, --] =", np.round(w_emp, 6))
        print(f"E exact = {correlator(w):.6f}")
        print(f"E emp   = {correlator(w_emp):.6f}")
    if args.chsh:
        a0,a1,b0,b1 = 0.0,45.0,22.5,-22.5
        e_a0b0 = E_for_angles(psi0, a0, b0)
        e_a0b1 = E_for_angles(psi0, a0, b1)
        e_a1b0 = E_for_angles(psi0, a1, b0)
        e_a1b1 = E_for_angles(psi0, a1, b1)
        S = e_a0b0 + e_a0b1 + e_a1b0 - e_a1b1
        print("CHSH settings:")
        print(f"E({a0:5.1f},{b0:5.1f}) = {e_a0b0:.6f}")
        print(f"E({a0:5.1f},{b1:5.1f}) = {e_a0b1:.6f}")
        print(f"E({a1:5.1f},{b0:5.1f}) = {e_a1b0:.6f}")
        print(f"E({a1:5.1f},{b1:5.1f}) = {e_a1b1:.6f}")
        print(f"S = {S:.6f}")
    if not (args.one_case or args.mc or args.chsh or args.run_tests):
        print("Nothing selected. Try --run-tests, --one-case, --mc, or --chsh.")

if __name__ == "__main__":
    main()
