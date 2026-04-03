from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict
from typing import Any

import numpy as np

from detector_integration.detectors import latch_first_event, resolve_branch_detector_params, simulate_branch_nucleation, validated_latch_arbiter_config
from detector_integration.sim.metrics import two_branch_metrics, winner_frequency_summary

from .export_interface import HandoffExportConfig, build_detector_handoff_envelopes, render_envelope_traces, resolve_envelope_config
from .two_branch_candidate import simulate_two_branch_physical_candidate

BOUNDARY_GAIN_SWEEP = (0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0)
BOUNDARY_EXPOSURE_SWEEP_S = (0.25, 0.5, 1.0, 2.5, 5.0)


def selected_handoff_export_config() -> HandoffExportConfig:
    return HandoffExportConfig(mode="piecewise_envelope", piecewise_mode="linear", piecewise_bin_width_s=2e-2)


def materialize_exported_trace(
    state: np.ndarray,
    analyzer,
    *,
    export_config: Mapping[str, Any] | HandoffExportConfig | None = None,
    envelope_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    candidate = simulate_two_branch_physical_candidate(state, analyzer, envelope_config=envelope_config)
    resolved_export = selected_handoff_export_config() if export_config is None else (export_config if isinstance(export_config, HandoffExportConfig) else HandoffExportConfig(**dict(export_config)))
    branch_labels = list(candidate["branch_labels"])
    detector_envelopes = build_detector_handoff_envelopes(
        candidate["branch_power_w"],
        time_s=candidate["time_s"],
        branch_labels=branch_labels,
        envelope_config=resolve_envelope_config(candidate["envelope_config"]),
        export_config=resolved_export,
    )
    first_envelope = detector_envelopes[0]
    if first_envelope["kind"] in {"sampled", "sampled_linear"}:
        sample_time_s = np.asarray(first_envelope["time_s"], dtype=float)
    else:
        dt = max(float(first_envelope.get("dt", 1e-3)), 1e-3)
        t_max = float(first_envelope.get("t_max", resolve_envelope_config(candidate["envelope_config"]).duration_s))
        sample_time_s = np.arange(0.0, t_max + dt, dt, dtype=float)
    exported_branch_power = render_envelope_traces(detector_envelopes, sample_time_s=sample_time_s, branch_labels=branch_labels)
    return {
        "candidate": candidate,
        "branch_labels": branch_labels,
        "time_s": sample_time_s.tolist(),
        "export_config": asdict(resolved_export),
        "exported_branch_power": exported_branch_power,
    }


def scale_trace_power(trace: Mapping[str, Any], gain: float) -> dict[str, Any]:
    return {
        **dict(trace),
        "gain": float(gain),
        "exported_branch_power": {
            label: (float(gain) * np.asarray(values, dtype=float)).tolist()
            for label, values in trace["exported_branch_power"].items()
        },
    }


def truncate_trace(trace: Mapping[str, Any], exposure_s: float) -> dict[str, Any]:
    time_s = np.asarray(trace["time_s"], dtype=float)
    cutoff = float(exposure_s)
    if cutoff >= float(time_s[-1]):
        return {**dict(trace), "exposure_s": cutoff}
    mask = time_s <= cutoff
    kept_time = time_s[mask]
    if kept_time.size == 0:
        kept_time = np.array([float(time_s[0]), cutoff], dtype=float)
    elif kept_time[-1] < cutoff:
        kept_time = np.append(kept_time, cutoff)
    truncated_power: dict[str, list[float]] = {}
    for label, values in trace["exported_branch_power"].items():
        power = np.asarray(values, dtype=float)
        kept_power = np.interp(kept_time, time_s, power)
        truncated_power[label] = kept_power.tolist()
    return {
        **dict(trace),
        "time_s": kept_time.tolist(),
        "exported_branch_power": truncated_power,
        "exposure_s": cutoff,
    }


def synthetic_common_envelope_trace(trace: Mapping[str, Any]) -> dict[str, Any]:
    candidate = trace["candidate"]
    branch_labels = list(trace["branch_labels"])
    time_s = np.asarray(trace["time_s"], dtype=float)
    candidate_time_s = np.asarray(candidate["time_s"], dtype=float)
    exact_weight = {label: float(candidate["exact_weight"][label]) for label in branch_labels}
    gamma_rows = [
        np.interp(time_s, candidate_time_s, np.asarray(candidate["branch_power_w"][label], dtype=float) / exact_weight[label])
        for label in branch_labels
        if abs(exact_weight[label]) > 1e-12
    ]
    if not gamma_rows:
        gamma_mean = np.zeros_like(time_s)
    else:
        gamma_mean = np.mean(np.vstack(gamma_rows), axis=0)
    synthetic_power = {
        label: (gamma_mean * exact_weight[label]).tolist()
        for label in branch_labels
    }
    return {
        **dict(trace),
        "trace_kind": "synthetic_common_envelope",
        "exported_branch_power": synthetic_power,
    }


def trace_to_detector_envelopes(trace: Mapping[str, Any]) -> list[dict[str, Any]]:
    time_s = np.asarray(trace["time_s"], dtype=float)
    dt = float(time_s[1] - time_s[0]) if time_s.size > 1 else 1e-3
    return [
        {
            "kind": "sampled",
            "time_s": time_s.tolist(),
            "power_w": list(trace["exported_branch_power"][label]),
            "dt": dt,
            "t_max": float(time_s[-1]) if time_s.size else 0.0,
        }
        for label in trace["branch_labels"]
    ]


def expected_click_count(trace: Mapping[str, Any], detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    time_s = np.asarray(trace["time_s"], dtype=float)
    branch_mu: dict[str, float] = {}
    for branch_index, label in enumerate(trace["branch_labels"]):
        detector_params = resolve_branch_detector_params(detector_spec, branch_index)
        family = str(detector_params.get("family", "shot_trigger"))
        if family != "shot_trigger":
            raise ValueError(f"Expected-click-count diagnostic currently supports shot_trigger only, got {family}.")
        if "model_params" in detector_params:
            model_params = dict(detector_params["model_params"])
        else:
            model_params = dict(detector_params)
        eps_event = max(float(model_params["eps_event"]), 1e-12)
        p_trig = min(max(float(model_params["p_trig"]), 0.0), 1.0)
        lambda_dark = float(model_params["lambda_dark"])
        gain_scale = float(detector_params.get("gain_scale", 1.0))
        power = gain_scale * np.maximum(np.asarray(trace["exported_branch_power"][label], dtype=float), 0.0)
        hazard = lambda_dark + (power / eps_event) * p_trig
        branch_mu[label] = float(np.trapezoid(hazard, x=time_s))
    branch_values = np.asarray(list(branch_mu.values()), dtype=float)
    return {
        "branch_mu": branch_mu,
        "mean_mu": float(np.mean(branch_values)),
        "min_mu": float(np.min(branch_values)),
        "max_mu": float(np.max(branch_values)),
    }


def run_trace_handoff(
    trace: Mapping[str, Any],
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    n_trials: int,
    seed: int,
) -> dict[str, Any]:
    exact_weights = np.array([trace["candidate"]["exact_weight"][label] for label in trace["branch_labels"]], dtype=float)
    detector_envelopes = trace_to_detector_envelopes(trace)
    rng = np.random.default_rng(seed)
    latch_config = validated_latch_arbiter_config(len(trace["branch_labels"]))
    winners: list[int] = []
    event_time_rows: list[np.ndarray] = []
    for _ in range(n_trials):
        event_times = np.full(len(trace["branch_labels"]), np.inf, dtype=float)
        for branch_index in range(len(trace["branch_labels"])):
            branch_rng = np.random.default_rng(int(rng.integers(0, 2**32 - 1)))
            detector_params = resolve_branch_detector_params(detector_spec, branch_index)
            click_time = simulate_branch_nucleation(detector_params, 1.0, detector_envelopes[branch_index], branch_rng)
            if click_time is not None:
                event_times[branch_index] = click_time
        latch_result = latch_first_event(event_times, config=latch_config, rng=rng)
        winners.append(int(latch_result["winner_index"]))
        event_time_rows.append(event_times)
    frequency_summary = winner_frequency_summary(winners, n_branches=len(trace["branch_labels"]))
    return {
        "detector_envelopes": detector_envelopes,
        "exact_weights": exact_weights,
        "empirical_frequencies": frequency_summary["frequencies"],
        "winner_counts": frequency_summary["counts"],
        "decisive_fraction": frequency_summary["decisive_fraction"],
        "timeout_fraction": frequency_summary["timeout_fraction"],
        "metrics": two_branch_metrics(exact_weights, frequency_summary["frequencies"]),
        "event_times": np.asarray(event_time_rows, dtype=float),
    }


def classify_boundary_outcome(*, best_physical: Mapping[str, Any], best_synthetic: Mapping[str, Any]) -> dict[str, str]:
    physical_pass = float(best_physical["winner_rms_error"]) < 0.03 and float(best_physical["winner_max_error"]) < 0.05
    synthetic_pass = float(best_synthetic["winner_rms_error"]) < 0.03 and float(best_synthetic["winner_max_error"]) < 0.05
    if physical_pass:
        return {
            "classification": "regime mismatch",
            "next_ticket": "Calibrate the physical-front-end -> detector boundary to the recovered operating regime and re-run the handoff validation.",
        }
    if synthetic_pass:
        return {
            "classification": "adapter/export mismatch",
            "next_ticket": "Redesign the detector-facing export/adapter while preserving the physical front-end and frozen detector family.",
        }
    return {
        "classification": "deeper detector abstraction mismatch",
        "next_ticket": "Revisit frozen detector abstraction assumptions for physical front-end time-structured inputs before further SPICE scaling.",
    }
