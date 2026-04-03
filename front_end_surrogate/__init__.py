"""SPICE-facing linear front-end surrogate package."""

from typing import Any

from .four_branch_surrogate import simulate_four_branch_surrogate
from .integration_adapter import run_four_branch_surrogate_handoff, run_surrogate_chsh_handoff, run_two_branch_surrogate_handoff
from .two_branch_surrogate import simulate_two_branch_surrogate


def build_front_end_surrogate_report(*args: Any, **kwargs: Any):
    from .experiments.build_summary_report import build_front_end_surrogate_report as _build_front_end_surrogate_report

    return _build_front_end_surrogate_report(*args, **kwargs)

__all__ = [
    "build_front_end_surrogate_report",
    "run_four_branch_surrogate_handoff",
    "run_surrogate_chsh_handoff",
    "run_two_branch_surrogate_handoff",
    "simulate_four_branch_surrogate",
    "simulate_two_branch_surrogate",
]
