from __future__ import annotations

import numpy as np

from src.analyzer_couplers import AnalyzerCouplers
from src.joint_readout import JointReadout

_NOMINAL_READOUT = JointReadout(analyzers=AnalyzerCouplers())


def four_branch_weights(state4: np.ndarray, a_deg: float, b_deg: float) -> np.ndarray:
    """Return normalized four-branch weights [++, +-, -+, --]."""
    return _NOMINAL_READOUT.measure(np.asarray(state4, dtype=np.complex128), a_deg=float(a_deg), b_deg=float(b_deg)).fractions
