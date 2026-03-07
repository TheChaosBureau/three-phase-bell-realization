from __future__ import annotations
from dataclasses import dataclass
import cmath
import math

from .types import SequenceState
from .config import SourceConfig


def build_path_state_pm(cfg: SourceConfig) -> SequenceState:
    """
    Path 1: A+ with B-
    """
    V0 = cfg.V0
    return SequenceState(
        VA_plus=V0,
        VA_minus=0.0j,
        IA_plus=cfg.YA_plus * V0,
        IA_minus=0.0j,
        VB_plus=0.0j,
        VB_minus=V0,
        IB_plus=0.0j,
        IB_minus=cfg.YB_minus * V0,
    )


def build_path_state_mp(cfg: SourceConfig) -> SequenceState:
    """
    Path 2: A- with B+
    """
    V0 = cfg.V0
    return SequenceState(
        VA_plus=0.0j,
        VA_minus=V0,
        IA_plus=0.0j,
        IA_minus=cfg.YA_minus * V0,
        VB_plus=V0,
        VB_minus=0.0j,
        IB_plus=cfg.YB_plus * V0,
        IB_minus=0.0j,
    )


def combine_states(s1: SequenceState, s2: SequenceState, c1: complex, c2: complex) -> SequenceState:
    return SequenceState(
        VA_plus=c1 * s1.VA_plus + c2 * s2.VA_plus,
        VA_minus=c1 * s1.VA_minus + c2 * s2.VA_minus,
        IA_plus=c1 * s1.IA_plus + c2 * s2.IA_plus,
        IA_minus=c1 * s1.IA_minus + c2 * s2.IA_minus,
        VB_plus=c1 * s1.VB_plus + c2 * s2.VB_plus,
        VB_minus=c1 * s1.VB_minus + c2 * s2.VB_minus,
        IB_plus=c1 * s1.IB_plus + c2 * s2.IB_plus,
        IB_minus=c1 * s1.IB_minus + c2 * s2.IB_minus,
    )


def build_antisymmetric_source(cfg: SourceConfig) -> SequenceState:
    """
    z* = ( z_(+-) - exp(j phi_s) z_(-+) ) / sqrt(2)
    """
    s_pm = build_path_state_pm(cfg)
    s_mp = build_path_state_mp(cfg)
    rel = cmath.exp(1j * cfg.phi_s)

    return combine_states(
        s_pm,
        s_mp,
        c1=1.0 / math.sqrt(2.0),
        c2=-rel / math.sqrt(2.0),
    )
