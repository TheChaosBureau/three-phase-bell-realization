"""First physical/SPICE front-end candidate package."""

from typing import Any

from .boundary_diagnosis import classify_boundary_outcome, selected_handoff_export_config
from .integration import run_two_branch_physical_handoff
from .metrics import common_envelope_fidelity_metrics, energy_preservation_metrics, finite_export_metrics, fraction_error_metrics
from .two_branch_candidate import PhysicalFrontEndConfig, simulate_two_branch_physical_candidate


def build_physical_front_end_candidate_report(*args: Any, **kwargs: Any):
    from .experiments.build_summary_report import build_physical_front_end_candidate_report as _build

    return _build(*args, **kwargs)


def build_physical_front_end_handoff_report(*args: Any, **kwargs: Any):
    from .experiments.build_handoff_report import build_physical_front_end_handoff_report as _build

    return _build(*args, **kwargs)


def build_physical_front_end_boundary_diagnosis_report(*args: Any, **kwargs: Any):
    from .experiments.build_boundary_diagnosis_report import build_physical_front_end_boundary_diagnosis_report as _build

    return _build(*args, **kwargs)


__all__ = [
    "PhysicalFrontEndConfig",
    "build_physical_front_end_boundary_diagnosis_report",
    "build_physical_front_end_candidate_report",
    "build_physical_front_end_handoff_report",
    "classify_boundary_outcome",
    "common_envelope_fidelity_metrics",
    "energy_preservation_metrics",
    "finite_export_metrics",
    "fraction_error_metrics",
    "run_two_branch_physical_handoff",
    "selected_handoff_export_config",
    "simulate_two_branch_physical_candidate",
]
