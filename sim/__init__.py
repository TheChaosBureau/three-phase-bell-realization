from .analyzers import analyzer_pockets
from .config import (
    BRANCHES,
    AnalyzerParams,
    DEFAULT_ANALYZER_PARAMS,
    DEFAULT_CHSH_SETTINGS,
    DEFAULT_DETECTOR_PARAMS_OU,
    DEFAULT_DETECTOR_PARAMS_POISSON,
    DEFAULT_RECOMBINER_PARAMS,
    DEFAULT_SHARED_CORE_PARAMS,
    DEFAULT_SWEEP_ANGLE_PAIRS,
    DetectorParams,
    RecombinerParams,
    SharedCoreParams,
)
from .detector import detector_step
from .metrics import (
    compute_chsh,
    correlator_from_probs,
    empirical_joint_probs,
    target_joint_weights,
    winner_law_errors,
)
from .recombiner import (
    bay_outputs,
    quadratic_bay_drives,
    recombine_joint_channels,
)
from .shared_core import shared_state
from .sweep import run_angle_sweep
from .trial import run_trial

__all__ = [
    "BRANCHES",
    "AnalyzerParams",
    "DEFAULT_ANALYZER_PARAMS",
    "DEFAULT_CHSH_SETTINGS",
    "DEFAULT_DETECTOR_PARAMS_OU",
    "DEFAULT_DETECTOR_PARAMS_POISSON",
    "DEFAULT_RECOMBINER_PARAMS",
    "DEFAULT_SHARED_CORE_PARAMS",
    "DEFAULT_SWEEP_ANGLE_PAIRS",
    "DetectorParams",
    "RecombinerParams",
    "SharedCoreParams",
    "analyzer_pockets",
    "bay_outputs",
    "compute_chsh",
    "correlator_from_probs",
    "detector_step",
    "empirical_joint_probs",
    "quadratic_bay_drives",
    "recombine_joint_channels",
    "run_angle_sweep",
    "run_trial",
    "shared_state",
    "target_joint_weights",
    "winner_law_errors",
]
