"""First physical/SPICE front-end candidate package."""

from typing import Any

from .integration import run_two_branch_physical_handoff
from .metrics import common_envelope_fidelity_metrics, energy_preservation_metrics, finite_export_metrics, fraction_error_metrics
from .two_branch_candidate import PhysicalFrontEndConfig, simulate_two_branch_physical_candidate


def build_physical_front_end_candidate_report(*args: Any, **kwargs: Any):
    from .experiments.build_summary_report import build_physical_front_end_candidate_report as _build

    return _build(*args, **kwargs)


def build_physical_front_end_handoff_report(*args: Any, **kwargs: Any):
    from .experiments.build_handoff_report import build_physical_front_end_handoff_report as _build

    return _build(*args, **kwargs)


__all__ = [
    "PhysicalFrontEndConfig",
    "build_physical_front_end_candidate_report",
    "build_physical_front_end_handoff_report",
    "common_envelope_fidelity_metrics",
    "energy_preservation_metrics",
    "finite_export_metrics",
    "fraction_error_metrics",
    "run_two_branch_physical_handoff",
    "simulate_two_branch_physical_candidate",
]
