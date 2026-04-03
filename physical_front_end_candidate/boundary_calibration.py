from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from detector_integration.detectors import validated_latch_arbiter_config

from .boundary_diagnosis import materialize_exported_trace, run_trace_handoff, scale_trace_power, selected_handoff_export_config, truncate_trace


@dataclass(frozen=True)
class CalibratedBoundaryConfig:
    export_mode: str = "piecewise:linear:20.0ms"
    gain: float = 4.0
    exposure_s: float = 5.0
    gain_sweep: tuple[float, ...] = (3.0, 3.5, 4.0, 4.5, 5.0)
    exposure_sweep_s: tuple[float, ...] = (3.0, 4.0, 5.0, 6.0, 7.0)


def resolved_calibrated_boundary_config(config: Mapping[str, Any] | None = None) -> CalibratedBoundaryConfig:
    if config is None:
        return CalibratedBoundaryConfig()
    return CalibratedBoundaryConfig(**dict(config))


def freeze_boundary_note_data(detector_spec: Mapping[str, Any]) -> dict[str, Any]:
    latch_config = validated_latch_arbiter_config(2)
    return {
        "export_config": asdict(selected_handoff_export_config()),
        "detector_family": str(detector_spec["family"]),
        "detector_model_params": dict(detector_spec["model_params"]),
        "latch_config": {
            "input_delay_s": float(latch_config.input_delay_s),
            "settle_time_s": float(latch_config.settle_time_s),
            "tie_window_s": float(latch_config.tie_window_s),
            "priority_order": tuple(int(value) for value in latch_config.priority_order),
        },
        "winner_semantics": {
            "winner_index": "Index of the first branch admitted by the latch; -1 indicates no branch fired before timeout.",
            "winner_valid": "True when a finite branch event reached the latch and won arbitration.",
        },
        "reset_semantics": "Reset and re-arm remain external trial-boundary operations; the latch and detector models are reinitialized between Monte Carlo trials.",
    }


def calibrated_trace(state: np.ndarray, analyzer, *, config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    resolved = resolved_calibrated_boundary_config(config)
    trace = materialize_exported_trace(state, analyzer, export_config=selected_handoff_export_config())
    return truncate_trace(scale_trace_power(trace, resolved.gain), resolved.exposure_s)


def run_calibrated_boundary_case(
    state: np.ndarray,
    analyzer,
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    n_trials: int,
    seed: int,
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    trace = calibrated_trace(state, analyzer, config=config)
    run = run_trace_handoff(trace, detector_spec, n_trials=n_trials, seed=seed)
    return {
        "trace": trace,
        "run": run,
        "errors": np.asarray(run["empirical_frequencies"], dtype=float) - np.asarray(run["exact_weights"], dtype=float),
    }
