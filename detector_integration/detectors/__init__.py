"""Detector-side helpers."""

from .closure_latch import first_event_latch, post_click_closure_placeholder
from .shot_trigger_adapter import resolve_branch_detector_params, resolve_branch_envelope_params, simulate_branch_nucleation

__all__ = [
    "first_event_latch",
    "post_click_closure_placeholder",
    "resolve_branch_detector_params",
    "resolve_branch_envelope_params",
    "simulate_branch_nucleation",
]
