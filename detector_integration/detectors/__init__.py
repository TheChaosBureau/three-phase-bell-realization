"""Detector-side helpers."""

from .closure_latch import (
    LatchArbiterConfig,
    first_event_latch,
    latch_first_event,
    post_click_closure_placeholder,
    validated_latch_arbiter_config,
)
from .shot_trigger_adapter import resolve_branch_detector_params, resolve_branch_envelope_params, simulate_branch_nucleation

__all__ = [
    "LatchArbiterConfig",
    "first_event_latch",
    "latch_first_event",
    "post_click_closure_placeholder",
    "resolve_branch_detector_params",
    "resolve_branch_envelope_params",
    "simulate_branch_nucleation",
    "validated_latch_arbiter_config",
]
