from typing import Any

from .config import DEFAULT_DETECTOR_RIG_CONFIG, DetectorRigConfig
from .sim import build_matched_cell_pair, build_single_cell_candidate, simulate_race_summary


def build_two_cell_detector_rig_report(*args: Any, **kwargs: Any):
    from .report import build_two_cell_detector_rig_report as _build_two_cell_detector_rig_report

    return _build_two_cell_detector_rig_report(*args, **kwargs)

__all__ = [
    "DEFAULT_DETECTOR_RIG_CONFIG",
    "DetectorRigConfig",
    "build_matched_cell_pair",
    "build_single_cell_candidate",
    "build_two_cell_detector_rig_report",
    "simulate_race_summary",
]
