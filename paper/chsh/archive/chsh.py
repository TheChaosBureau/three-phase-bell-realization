"""
Implementation-ready skeleton for the 3-phase Transmission-Line CHSH program.

Design goals:
- Fully specified numerics (no "choose later" placeholders)
- Energy-auditable, causal, and deterministic dynamics
- Explicit detector physics via conductance matrices parameterized by angle θ
- Two runs: loophole-free (all trials counted) and realistic detection (threshold + coincidence)

Numerical choices (fixed):
- Spatial discretization: LC ladder, M segments, N=M+1 nodes
- Time integration: staggered leapfrog (symplectic), fixed dt = CFL * dx / c with CFL=0.2
- Line parameters: L', C' identical per phase, no mutual coupling (baseline)
- Source: midline current injection at node mid, Gaussian-envelope sinusoid
- Detectors: shunt conductance matrix G_abc(θ) applied at boundary nodes
- CHSH: standard angles (0, 45) and (22.5, 67.5)

Dependencies: numpy only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import sys
import time
import numpy as np


# -----------------------------
# Utilities: Clarke transform
# -----------------------------

def clarke_power_invariant_T() -> np.ndarray:
    """
    Power-invariant Clarke transform T_C mapping abc -> alpha beta 0

    [vα]   √(2/3) [ 1    -1/2    -1/2 ] [va]
    [vβ] = √(2/3) [ 0   √3/2   -√3/2 ] [vb]
    [v0]   1/√3   [ 1     1       1  ] [vc]

    Returns:
        T_C: (3,3) matrix
    """
    k = np.sqrt(2.0 / 3.0)
    T = np.array(
        [
            [k * 1.0, k * (-0.5), k * (-0.5)],
            [k * 0.0, k * (np.sqrt(3) / 2), k * (-np.sqrt(3) / 2)],
            [1.0 / np.sqrt(3), 1.0 / np.sqrt(3), 1.0 / np.sqrt(3)],
        ],
        dtype=float,
    )
    return T


def rotation_ab(theta: float) -> np.ndarray:
    """Rotation matrix in αβ plane (3x3 acting on [α β 0])."""
    c, s = np.cos(theta), np.sin(theta)
    R2 = np.array([[c, s], [-s, c]], dtype=float)
    R = np.eye(3, dtype=float)
    R[:2, :2] = R2
    return R


def G_abc_from_detector_params(theta: float, g_par: float, g_perp: float, g0: float = 0.0) -> np.ndarray:
    """
    Build phase-domain conductance matrix G_abc(θ) implementing dissipation in rotated α'β'0 basis.

    Steps:
    - Define G in rotated basis diag(g_par, g_perp, g0)
    - Rotate back to αβ0 basis via R(θ)^T G R(θ)
    - Convert to abc: G_abc = T_C^T * G_ab0 * T_C
    """
    T = clarke_power_invariant_T()
    R = rotation_ab(theta)

    G_rot = np.diag([g_par, g_perp, g0]).astype(float)  # in α'β'0
    G_ab0 = R.T @ G_rot @ R  # back to αβ0

    Gabc = T.T @ G_ab0 @ T
    # Numerical symmetry enforcement
    Gabc = 0.5 * (Gabc + Gabc.T)
    return Gabc


# -----------------------------
# Source model
# -----------------------------

@dataclass(frozen=True)
class Source:
    """
    Midline current injection source: i_inj(t) into abc phases at a specified node.

    Current injection is applied in parallel with shunt capacitors at a node:
    C dv/dt = ... - i_shunt + i_inj(t)

    We inject a balanced 3-phase packet derived from an αβ complex packet:
        z(t) = A exp(-(t/σ)^2) cos(ωt + φ) + i A exp(-(t/σ)^2) sin(ωt + φ)
    which means:
        vα ~ Re(z), vβ ~ Im(z)   -> mapped to abc

    But injection is current; we choose i_inj proportional to the same abc waveform.
    """
    node_index: int
    A: float               # current amplitude (A)
    sigma: float           # seconds
    f0: float              # Hz
    phase: float           # radians
    t_center: float = 0.0  # seconds (center of Gaussian)

    def i_inj_abc(self, t: float) -> np.ndarray:
        w0 = 2.0 * np.pi * self.f0
        tau = (t - self.t_center)
        env = np.exp(-(tau / self.sigma) ** 2)

        # Build αβ0 waveform for "polarization"
        v_alpha = env * np.cos(w0 * tau + self.phase)
        v_beta  = env * np.sin(w0 * tau + self.phase)
        v0 = 0.0

        # Convert to abc using inverse of Clarke transform.
        # With power-invariant T, inverse is not exactly T^T, so compute explicitly once.
        T = clarke_power_invariant_T()
        Tinv = np.linalg.inv(T)
        v_abc = Tinv @ np.array([v_alpha, v_beta, v0], dtype=float)

        # Current injection follows same shape, scaled by A.
        return self.A * v_abc


# -----------------------------
# Detector model
# -----------------------------

@dataclass(frozen=True)
class Detector:
    """
    Angle-selective dissipative boundary detector at a boundary node (0 or N-1).

    Implements shunt load:
        i_load = G_abc(θ) v

    Additionally provides two channel powers in αβ (parallel/perp) for outcomes:
        P_par = g_par * (vα')^2
        P_per = g_per * (vβ')^2
    """
    node_index: int
    theta: float
    g_par: float
    g_perp: float
    g0: float = 0.0

    @property
    def Gabc(self) -> np.ndarray:
        return G_abc_from_detector_params(self.theta, self.g_par, self.g_perp, self.g0)

    def channel_powers(self, v_abc: np.ndarray) -> Tuple[float, float, float]:
        """
        Returns (P_par, P_per, P_total) at this node given v_abc.
        """
        T = clarke_power_invariant_T()
        v_ab0 = T @ v_abc
        R = rotation_ab(self.theta)
        v_rot = R @ v_ab0
        v_ap, v_bp, v0 = v_rot[0], v_rot[1], v_rot[2]
        P_par = self.g_par * (v_ap ** 2)
        P_per = self.g_perp * (v_bp ** 2)
        P0 = self.g0 * (v0 ** 2)
        return P_par, P_per, (P_par + P_per + P0)


# -----------------------------
# Transmission line (LC ladder)
# -----------------------------

class TransmissionLine:
    """
    3-phase lossless TL implemented as an LC ladder:

    - N nodes (indexed 0..N-1), M segments where M = N-1
    - Each segment has series inductors per phase: L_seg = L' * dx
      Currents i_seg[j] flows from node j -> j+1 (vector length 3)
    - Each node has shunt capacitors per phase: C_node = C' * dx
      Node voltages v_node[j] (vector length 3)

    Dynamics:
      dv_j/dt = (1/C_node) * (i_seg[j-1] - i_seg[j] - i_load_j + i_inj_j)
      di_seg[j]/dt = (1/L_seg) * (v_j - v_{j+1})

    with boundary conventions:
      i_seg[-1] = 0, i_seg[M] = 0  (handled by indexing)
    """
    def __init__(
        self,
        length_m: float,
        M: int,
        L_prime_H_per_m: float,
        C_prime_F_per_m: float,
        cfl: float = 0.2,
    ):
        assert M >= 4, "Use M>=4 for meaningful propagation."
        self.length = float(length_m)
        self.M = int(M)
        self.N = self.M + 1
        self.dx = self.length / self.M

        self.Lp = float(L_prime_H_per_m)
        self.Cp = float(C_prime_F_per_m)
        self.c = 1.0 / np.sqrt(self.Lp * self.Cp)
        self.Z0 = np.sqrt(self.Lp / self.Cp)

        self.L_seg = self.Lp * self.dx
        self.C_node = self.Cp * self.dx

        # Fixed timestep from CFL
        self.dt = float(cfl * self.dx / self.c)

        # State arrays
        self.v = np.zeros((self.N, 3), dtype=float)    # node voltages
        self.i = np.zeros((self.M, 3), dtype=float)    # segment currents (j->j+1)

        # For leapfrog
        self._i_half = np.zeros_like(self.i)           # currents at half-steps

        # Boundary shunt conductances per node (3x3 each)
        self.G_node = np.zeros((self.N, 3, 3), dtype=float)

        # Current injection per node (time-varying): we handle via Source list
        self.sources: List[Source] = []

    def reset(self) -> None:
        self.v.fill(0.0)
        self.i.fill(0.0)
        self._i_half.fill(0.0)
        self.G_node.fill(0.0)
        self.sources = []

    def set_detector(self, det: Detector) -> None:
        self.G_node[det.node_index] = det.Gabc

    def add_source(self, src: Source) -> None:
        self.sources.append(src)

    def _i_injection_node(self, t: float) -> np.ndarray:
        """Returns node-wise injection currents shape (N,3)."""
        Iinj = np.zeros((self.N, 3), dtype=float)
        for s in self.sources:
            Iinj[s.node_index] += s.i_inj_abc(t)
        return Iinj

    def step(self, t: float) -> None:
        """
        One leapfrog step:
        - Update segment currents at half step using node voltages at time t
        - Update node voltages at next time using segment currents at half step and shunt loads and injections
        """
        # 1) Update i at half-step: i^{n+1/2} = i^{n-1/2} + (dt/L_seg)*(v_j^n - v_{j+1}^n)
        dv_seg = self.v[:-1] - self.v[1:]  # shape (M,3)
        self._i_half += (self.dt / self.L_seg) * dv_seg

        # 2) Compute load currents at nodes: i_load = G v
        i_load = np.einsum("nij,nj->ni", self.G_node, self.v)  # (N,3)

        # 3) Compute net current into each node from segments
        # incoming from left segment: i_half[j-1], outgoing to right: i_half[j]
        net_from_segments = np.zeros((self.N, 3), dtype=float)
        net_from_segments[0] += -self._i_half[0]
        net_from_segments[1:-1] += self._i_half[:-1] - self._i_half[1:]
        net_from_segments[-1] += self._i_half[-1]

        # 4) Injection
        i_inj = self._i_injection_node(t)

        # 5) Update v: v^{n+1} = v^n + (dt/C_node)*(net_from_segments - i_load + i_inj)
        dv_node = (self.dt / self.C_node) * (net_from_segments - i_load + i_inj)
        self.v += dv_node

        # 6) Store full-step segment currents for convenience (optional)
        # i^n approximated as i^{n+1/2} (staggered)
        self.i[:] = self._i_half

    def energy(self) -> float:
        """Total stored energy in the line (J)."""
        # Capacitors: 1/2 C v^2 per node per phase
        Ec = 0.5 * self.C_node * float(np.sum(self.v ** 2))
        # Inductors: 1/2 L i^2 per segment per phase
        El = 0.5 * self.L_seg * float(np.sum(self.i ** 2))
        return Ec + El

    def absorbed_power_nodes(self) -> np.ndarray:
        """Instantaneous absorbed power at each node due to shunt loads, P = v^T G v."""
        # Pn = sum over phases: v_n^T G_n v_n
        P = np.einsum("ni,nij,nj->n", self.v, self.G_node, self.v)
        return P


# -----------------------------
# CHSH Experiment
# -----------------------------

@dataclass(frozen=True)
class CHSHSettings:
    theta_A: float
    theta_Ap: float
    theta_B: float
    theta_Bp: float


@dataclass
class TrialResult:
    theta_A: float
    theta_B: float
    A: int
    B: int
    # Optional diagnostics
    Epar_A: float
    Eper_A: float
    Epar_B: float
    Eper_B: float
    clicks_used: bool


class CHSHExperiment:
    """
    Runs trials on a TransmissionLine + Detector + Source model and computes CHSH S.

    Two modes:
    - loophole_free=True: all trials counted; outcome sign(Epar-Eper)
    - loophole_free=False: threshold/click + optional coincidence window
    """
    def __init__(
        self,
        tl: TransmissionLine,
        length_m: float,
        # Detector parameters
        g_par: float,
        g_perp: float,
        # Energy integration
        T_window_s: float,
        # Simulation time
        t_pre_s: float,
        t_post_s: float,
        # Detection (realistic) parameters
        threshold_J: float = 0.0,
        coincidence_window_s: float = 0.0,
        # CHSH settings
        settings: Optional[CHSHSettings] = None,
        rng_seed: int = 0,
    ):
        self.tl = tl
        self.length_m = length_m
        self.g_par = float(g_par)
        self.g_perp = float(g_perp)
        self.Tw = float(T_window_s)
        self.t_pre = float(t_pre_s)
        self.t_post = float(t_post_s)
        self.threshold = float(threshold_J)
        self.coincidence = float(coincidence_window_s)
        self.rng = np.random.default_rng(rng_seed)

        if settings is None:
            # Standard CHSH angles: A: 0, 45; B: 22.5, 67.5 degrees
            settings = CHSHSettings(
                theta_A=0.0,
                theta_Ap=np.pi / 4,
                theta_B=np.pi / 8,
                theta_Bp=3 * np.pi / 8,
            )
        self.settings = settings

        # Node indices for ports and source
        self.node_A = 0
        self.node_B = self.tl.N - 1
        self.node_src = self.tl.N // 2

    def _make_trial_source(self, A_current: float, sigma: float, f0: float, phase: float, t_center: float) -> Source:
        return Source(
            node_index=self.node_src,
            A=A_current,
            sigma=sigma,
            f0=f0,
            phase=phase,
            t_center=t_center,
        )

    def _simulate_trial(
        self,
        theta_A: float,
        theta_B: float,
        src: Source,
        loophole_free: bool,
    ) -> TrialResult:
        # Reset TL, set detectors, add source
        self.tl.reset()

        detA = Detector(node_index=self.node_A, theta=theta_A, g_par=self.g_par, g_perp=self.g_perp, g0=0.0)
        detB = Detector(node_index=self.node_B, theta=theta_B, g_par=self.g_par, g_perp=self.g_perp, g0=0.0)
        self.tl.set_detector(detA)
        self.tl.set_detector(detB)
        self.tl.add_source(src)

        # Time plan
        # We start at t = -t_pre so the packet can be centered at 0 if desired
        dt = self.tl.dt
        t0 = -self.t_pre
        t_end = self.t_post

        # We'll measure energies in a fixed window aligned to expected arrival at each port.
        # Arrival time from midline ~ (ℓ/2)/c
        Td = (self.length_m / 2.0) / self.tl.c
        # Start windows after arrival + small margin (fixed, angle-independent)
        # Fixed margin: 3 sigma
        margin = 3.0 * src.sigma
        win_A_start = Td + margin
        win_B_start = Td + margin

        # Integrate channel powers over windows
        Epar_A = Eper_A = 0.0
        Epar_B = Eper_B = 0.0

        # For realistic detection: track click times when cumulative energy crosses threshold
        clickA_t: Optional[float] = None
        clickB_t: Optional[float] = None
        cumA = 0.0
        cumB = 0.0

        # Energy audit (optional, but cheap)
        # Track absorbed energy at ports by integrating P_abs at those nodes
        Wabs_A = 0.0
        Wabs_B = 0.0

        t = t0
        steps = int(np.ceil((t_end - t0) / dt))
        for _ in range(steps):
            # step dynamics
            self.tl.step(t)

            # absorbed power at nodes from loads
            Pnodes = self.tl.absorbed_power_nodes()
            Wabs_A += Pnodes[self.node_A] * dt
            Wabs_B += Pnodes[self.node_B] * dt

            # channel powers from detectors (computed from node voltages)
            vA = self.tl.v[self.node_A]
            vB = self.tl.v[self.node_B]
            Ppar_A, Pper_A, Ptot_A = detA.channel_powers(vA)
            Ppar_B, Pper_B, Ptot_B = detB.channel_powers(vB)

            # integrate in fixed windows
            if win_A_start <= t < win_A_start + self.Tw:
                Epar_A += Ppar_A * dt
                Eper_A += Pper_A * dt
            if win_B_start <= t < win_B_start + self.Tw:
                Epar_B += Ppar_B * dt
                Eper_B += Pper_B * dt

            # realistic detection: cumulative energy and click times (angle-independent threshold)
            if not loophole_free and self.threshold > 0.0:
                cumA += Ptot_A * dt
                cumB += Ptot_B * dt
                if clickA_t is None and cumA >= self.threshold:
                    clickA_t = t
                if clickB_t is None and cumB >= self.threshold:
                    clickB_t = t

            t += dt

        # Outcomes
        def sgn(x: float) -> int:
            return 1 if x >= 0.0 else -1

        clicks_used = False
        if loophole_free:
            A = sgn(Epar_A - Eper_A)
            B = sgn(Epar_B - Eper_B)
        else:
            # Realistic: require clicks, optionally coincidence
            clicks_used = True
            if self.threshold <= 0.0:
                raise ValueError("Realistic mode requires threshold_J > 0.0")
            if clickA_t is None or clickB_t is None:
                # No-click: assign 0 outcomes by convention (and treat as discarded by CHSH accumulator)
                A = 0
                B = 0
            else:
                if self.coincidence > 0.0 and abs(clickA_t - clickB_t) > self.coincidence:
                    A = 0
                    B = 0
                else:
                    A = sgn(Epar_A - Eper_A)
                    B = sgn(Epar_B - Eper_B)

        return TrialResult(
            theta_A=theta_A,
            theta_B=theta_B,
            A=A,
            B=B,
            Epar_A=Epar_A,
            Eper_A=Eper_A,
            Epar_B=Epar_B,
            Eper_B=Eper_B,
            clicks_used=clicks_used,
        )

    def run(
        self,
        N_trials_per_setting: int,
        loophole_free: bool = True,
        # Source numeric parameters (fixed, fully specified defaults)
        src_A_current: float = 5.0,          # A
        src_sigma: float = 2e-4,             # s (0.2 ms)
        src_f0: float = 2_000.0,             # Hz
        src_t_center: float = 0.0,           # s
    ) -> Dict[str, object]:
        """
        Runs CHSH trials and returns:
          - correlations E(a,b), E(a,b'), E(a',b), E(a',b')
          - CHSH S
          - trial list for diagnostics
          - detection efficiency stats (if realistic mode)
        """
        # Settings list
        a, ap, b, bp = self.settings.theta_A, self.settings.theta_Ap, self.settings.theta_B, self.settings.theta_Bp
        setting_pairs = [(a, b), (a, bp), (ap, b), (ap, bp)]
        pair_labels = ["(a,b)", "(a,b')", "(a',b)", "(a',b')"]

        total_trials = 4 * N_trials_per_setting
        completed = 0
        t_start = time.monotonic()

        # Accumulate results per pair
        results: Dict[Tuple[float, float], List[TrialResult]] = {p: [] for p in setting_pairs}

        for pair_idx, (thA, thB) in enumerate(setting_pairs):
            for trial_num in range(N_trials_per_setting):
                # Hidden variable: random global phase independent of angles (Run 1 requirement)
                phase = float(self.rng.uniform(0.0, 2.0 * np.pi))
                src = self._make_trial_source(
                    A_current=src_A_current,
                    sigma=src_sigma,
                    f0=src_f0,
                    phase=phase,
                    t_center=src_t_center,
                )
                tr = self._simulate_trial(thA, thB, src, loophole_free=loophole_free)
                results[(thA, thB)].append(tr)

                completed += 1
                elapsed = time.monotonic() - t_start
                rate = completed / elapsed if elapsed > 0 else 0
                eta = (total_trials - completed) / rate if rate > 0 else 0
                sys.stdout.write(
                    f"\r  {pair_labels[pair_idx]} trial {trial_num+1}/{N_trials_per_setting}"
                    f"  [{completed}/{total_trials} total, {rate:.1f} trial/s, ETA {eta:.0f}s]"
                    "    "
                )
                sys.stdout.flush()
        sys.stdout.write("\r" + " " * 80 + "\r")
        sys.stdout.flush()

        # Compute correlations
        def corr(trials: List[TrialResult]) -> Tuple[float, int, int]:
            # returns (E, used, total)
            vals = []
            for tr in trials:
                if tr.A == 0 or tr.B == 0:
                    continue
                vals.append(tr.A * tr.B)
            used = len(vals)
            total = len(trials)
            E = float(np.mean(vals)) if used > 0 else float("nan")
            return E, used, total

        E_ab, used_ab, tot_ab = corr(results[(a, b)])
        E_abp, used_abp, tot_abp = corr(results[(a, bp)])
        E_apb, used_apb, tot_apb = corr(results[(ap, b)])
        E_apbp, used_apbp, tot_apbp = corr(results[(ap, bp)])

        S = abs(E_ab + E_abp + E_apb - E_apbp)

        # Efficiency stats
        eff = {
            "ab": used_ab / tot_ab,
            "abp": used_abp / tot_abp,
            "apb": used_apb / tot_apb,
            "apbp": used_apbp / tot_apbp,
        }

        return {
            "E": {
                "ab": E_ab,
                "abp": E_abp,
                "apb": E_apb,
                "apbp": E_apbp,
            },
            "S": S,
            "efficiency": eff,
            "results_by_pair": results,
            "settings": self.settings,
            "numerics": {
                "dt": self.tl.dt,
                "dx": self.tl.dx,
                "c": self.tl.c,
                "Z0": self.tl.Z0,
                "M": self.tl.M,
                "N": self.tl.N,
            },
        }


# -----------------------------
# Example usage (fully specified)
# -----------------------------

def main() -> None:
    # Fully specified TL
    length = 1000.0          # meters
    M = 200                  # segments -> dx = 5 m
    Lp = 1e-6                # H/m
    Cp = 1e-9                # F/m
    tl = TransmissionLine(length_m=length, M=M, L_prime_H_per_m=Lp, C_prime_F_per_m=Cp, cfl=0.2)

    # Detectors: equal channels for loophole-free run (no angle-dependent efficiency)
    g = 1.0 / tl.Z0          # Siemens ~ matched-ish per phase basis scale
    g_par = g
    g_perp = g

    # Window and sim time (fully specified)
    Tw = 5e-3                # 5 ms integration
    t_pre = 5e-3             # simulate from -5 ms
    # Need enough time for packet to reach ends and be absorbed.
    # Midline to end time: (ℓ/2)/c
    Td = (length / 2.0) / tl.c
    t_post = Td + 30e-3      # margin 30 ms

    exp = CHSHExperiment(
        tl=tl,
        length_m=length,
        g_par=g_par,
        g_perp=g_perp,
        T_window_s=Tw,
        t_pre_s=t_pre,
        t_post_s=t_post,
        threshold_J=0.0,             # not used in loophole-free
        coincidence_window_s=0.0,    # not used in loophole-free
        rng_seed=123,
    )

    # Run 1: loophole-free (expect S <= 2)
    print("Run 1 (loophole-free): 200 trials/setting, 800 total")
    out1 = exp.run(N_trials_per_setting=200, loophole_free=True)
    print("Run 1 (loophole-free):")
    print("E:", out1["E"])
    print("S:", out1["S"])
    print("eff:", out1["efficiency"])
    print("numerics:", out1["numerics"])

    # Run 2: realistic detection (threshold + coincidence)
    # Here we allow discards; apparent S>2 can occur via selection bias.
    exp2 = CHSHExperiment(
        tl=tl,
        length_m=length,
        g_par=g_par,
        g_perp=g_perp,
        T_window_s=Tw,
        t_pre_s=t_pre,
        t_post_s=t_post,
        threshold_J=1e-5,            # J
        coincidence_window_s=2e-3,   # 2 ms
        rng_seed=123,
    )
    print("\nRun 2 (realistic detection): 500 trials/setting, 2000 total")
    out2 = exp2.run(N_trials_per_setting=500, loophole_free=False)
    print("Run 2 (realistic detection):")
    print("E:", out2["E"])
    print("S:", out2["S"])
    print("eff:", out2["efficiency"])


if __name__ == "__main__":
    main()
