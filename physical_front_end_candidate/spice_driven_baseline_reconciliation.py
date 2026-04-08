from __future__ import annotations

import json
import math
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

from detector_integration.detectors import validated_latch_arbiter_config

from .spice_driven_robustness import SpiceDrivenRobustnessConfig, run_spice_driven_robustness_sweep
from .spice_driven_preferred_chain import (
    SpiceDrivenPreferredChainConfig,
    run_spice_driven_preferred_chain_benchmark,
    spice_driven_preferred_chain_benchmark_cases,
)


@dataclass
class _ProgressReporter:
    total_steps: int
    enabled: bool = False
    label: str = "spice-driven-baseline-reconciliation"
    completed_steps: int = 0
    start_time_s: float = 0.0
    last_report_time_s: float = 0.0
    last_phase: str | None = None

    def __post_init__(self) -> None:
        self.start_time_s = time.monotonic()
        self.last_report_time_s = self.start_time_s
        if self.enabled:
            self.report("starting", force=True)

    def report(self, phase: str, *, force: bool = False) -> None:
        if not self.enabled:
            return
        now = time.monotonic()
        if not force and phase == self.last_phase and (now - self.last_report_time_s) < 0.5:
            return
        elapsed_s = max(now - self.start_time_s, 0.0)
        completed = self.completed_steps
        rate = completed / elapsed_s if elapsed_s > 0.0 else 0.0
        remaining = max(self.total_steps - completed, 0)
        eta_s = remaining / rate if rate > 0.0 else None
        eta_text = "unknown" if eta_s is None else f"{eta_s:.1f}s"
        percent = 100.0 * completed / max(self.total_steps, 1)
        print(
            f"[{self.label}] {completed}/{self.total_steps} steps ({percent:.1f}%), "
            f"elapsed {elapsed_s:.1f}s, ETA {eta_text}, phase={phase}",
            file=sys.stderr,
            flush=True,
        )
        self.last_report_time_s = now
        self.last_phase = phase

    def advance(self, phase: str, *, steps: int = 1) -> None:
        self.completed_steps += int(steps)
        self.report(phase, force=self.completed_steps >= self.total_steps)


@dataclass(frozen=True)
class BaselineRunSpec:
    label: str
    source_kind: str
    n_trials: int
    seed: int
    case_names: tuple[str, ...] | None = None
    spice_driven_config: SpiceDrivenPreferredChainConfig = field(default_factory=SpiceDrivenPreferredChainConfig)


VALIDATED_SPICE_DRIVEN_BASELINE = BaselineRunSpec(
    label="validated_spice_driven_preferred_chain",
    source_kind="preferred_chain",
    n_trials=1_200,
    seed=20260411,
)

ROBUSTNESS_NOMINAL_BASELINE = BaselineRunSpec(
    label="robustness_nominal_baseline",
    source_kind="robustness_baseline_only",
    n_trials=180,
    seed=20260412,
)


def _empty_robustness_config(
    *,
    baseline_spice_driven_config: SpiceDrivenPreferredChainConfig,
) -> SpiceDrivenRobustnessConfig:
    return SpiceDrivenRobustnessConfig(
        baseline_spice_driven_config=baseline_spice_driven_config,
        front_end_tolerance_levels=(),
        coupling_mismatch_levels=(),
        load_mismatch_levels=(),
        leakage_severity_levels=(),
        boundary_gains=(),
        boundary_exposures_s=(),
        closure_variation_levels=(),
    )


def _run_spec(
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    spec: BaselineRunSpec,
) -> dict[str, Any]:
    if spec.source_kind == "preferred_chain":
        summary = run_spice_driven_preferred_chain_benchmark(
            detector_spec,
            n_trials=int(spec.n_trials),
            seed=int(spec.seed),
            case_names=spec.case_names,
            spice_driven_config=spec.spice_driven_config,
            verbose_progress=False,
        )
        return {
            "spec": spec,
            "driver": "run_spice_driven_preferred_chain_benchmark",
            "summary": summary,
            "summary_metrics": summary["summary_metrics"],
        }
    if spec.source_kind == "robustness_baseline_only":
        summary = run_spice_driven_robustness_sweep(
            detector_spec,
            n_trials=int(spec.n_trials),
            seed=int(spec.seed),
            case_names=spec.case_names,
            robustness_config=_empty_robustness_config(baseline_spice_driven_config=spec.spice_driven_config),
            verbose_progress=False,
        )
        return {
            "spec": spec,
            "driver": "run_spice_driven_robustness_sweep.baseline_summary",
            "summary": summary["baseline_summary"],
            "summary_metrics": summary["baseline_summary_metrics"],
            "signature": build_signature_from_spec(
                spec,
                detector_spec,
                driver="run_spice_driven_robustness_sweep.baseline_summary",
            ),
            "robustness_wrapper_summary": summary,
        }
    raise ValueError(f"Unsupported baseline source kind: {spec.source_kind}")


def _jsonable(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, dict):
        return {str(key): _jsonable(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "__dict__") and not isinstance(value, type):
        return _jsonable(asdict(value))
    return value


def _resolved_case_names(spec: BaselineRunSpec) -> list[str]:
    if spec.case_names is not None:
        return [str(name) for name in spec.case_names]
    return [str(case["case"]) for case in spice_driven_preferred_chain_benchmark_cases()]


def build_signature_from_spec(
    spec: BaselineRunSpec,
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    driver: str,
) -> dict[str, Any]:
    latch_config = validated_latch_arbiter_config(4)
    config = spec.spice_driven_config
    boundary_export_mode = str(config.boundary_export_mode)
    export_mode, _, mode_tail = boundary_export_mode.partition(":")
    piecewise_mode, _, bin_tail = mode_tail.partition(":")
    piecewise_bin_width_s = float(bin_tail.removesuffix("ms")) / 1000.0 if bin_tail.endswith("ms") else float("nan")
    return {
        "label": spec.label,
        "source_kind": spec.source_kind,
        "driver": driver,
        "benchmark_cases": _resolved_case_names(spec),
        "n_trials": int(spec.n_trials),
        "seed": int(spec.seed),
        "spice_front_end_artifact_identity": {
            "solver": "ngspice-via-pyspice",
            "module": "physical_front_end_candidate.actual_spice_front_end",
            "config": _jsonable(asdict(config.actual_spice_config)),
        },
        "trace_ingestion_path": "actual ngspice front-end -> carrier averaging -> calibrated replay -> frozen boundary export",
        "trace_preprocessing": {
            "replay_mode": str(config.replay_mode),
            "power_alignment_mode": str(config.power_alignment_mode),
            "spice_fraction_injection": float(config.spice_fraction_injection),
            "reference_total_envelope_source": "current_preferred_chain_device_physicalization"
            if config.replay_mode == "reference_total_envelope_scaled_by_spice_fractions"
            else "constant_mean_power",
            "reference_branch_profile_source": "current_preferred_chain_device_physicalization_reweighted_by_actual_spice"
            if config.replay_mode == "reference_total_envelope_scaled_by_spice_fractions"
            else "constant_mean_power",
        },
        "boundary_settings": {
            "export_mode": export_mode,
            "piecewise_mode": piecewise_mode,
            "piecewise_bin_width_s": piecewise_bin_width_s,
            "gain": float(config.frozen_gain),
            "exposure_s": float(config.frozen_exposure_s),
        },
        "detector_spec": _jsonable(detector_spec),
        "latch_settings": {
            "input_delay_s": float(latch_config.input_delay_s),
            "settle_time_s": float(latch_config.settle_time_s),
            "tie_window_s": float(latch_config.tie_window_s),
            "priority_order": [int(value) for value in latch_config.priority_order],
        },
        "spice_front_end_config": _jsonable(asdict(config.actual_spice_config)),
        "closure_drain_config": {
            "physicalization_config": _jsonable(
                {
                    **asdict(config.physicalization_config),
                    "codesign_config": asdict(config.physicalization_config.codesign_config),
                }
            ),
        },
        "metric_aggregation_logic": {
            "summary_metrics_function": "build_summary_metrics",
            "chsh_function": "build_chsh_result",
            "pre_click_comparison_function": "build_pre_click_comparison",
            "case_metric_source": "run_spice_driven_preferred_chain_benchmark.case_rows",
        },
    }


def _signature_from_run(
    run: Mapping[str, Any],
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if "signature" in run:
        return dict(run["signature"])
    summary = run["summary"]
    case_results = list(summary["case_results"])
    first_result = case_results[0]["result"]
    first_candidate = first_result["candidate"]
    case_names = [str(entry["case"]["case"]) for entry in case_results]
    latch_config = validated_latch_arbiter_config(4)
    candidate_cfg = dict(first_candidate["candidate_config"]["spice_driven_preferred_chain"])
    boundary_cfg = dict(first_result["boundary_config"])
    export_cfg = dict(first_result["export_config"])
    adapter = dict(first_candidate["spice_boundary_adapter"])
    return {
        "label": run["spec"].label,
        "source_kind": run["spec"].source_kind,
        "driver": run["driver"],
        "benchmark_cases": case_names,
        "n_trials": int(run["spec"].n_trials),
        "seed": int(run["spec"].seed),
        "spice_front_end_artifact_identity": {
            "solver": "ngspice-via-pyspice",
            "module": "physical_front_end_candidate.actual_spice_front_end",
            "config": _jsonable(candidate_cfg["actual_spice_config"]),
        },
        "trace_ingestion_path": "actual ngspice front-end -> carrier averaging -> calibrated replay -> frozen boundary export",
        "trace_preprocessing": {
            "replay_mode": adapter["replay_mode"],
            "power_alignment_mode": adapter["power_alignment_mode"],
            "spice_fraction_injection": candidate_cfg["spice_fraction_injection"],
            "reference_total_envelope_source": adapter["reference_total_envelope_source"],
            "reference_branch_profile_source": adapter["reference_branch_profile_source"],
        },
        "boundary_settings": {
            "export_mode": export_cfg["mode"],
            "piecewise_mode": export_cfg["piecewise_mode"],
            "piecewise_bin_width_s": export_cfg["piecewise_bin_width_s"],
            "gain": boundary_cfg["gain"],
            "exposure_s": boundary_cfg["exposure_s"],
        },
        "detector_spec": _jsonable(detector_spec),
        "latch_settings": {
            "input_delay_s": float(latch_config.input_delay_s),
            "settle_time_s": float(latch_config.settle_time_s),
            "tie_window_s": float(latch_config.tie_window_s),
            "priority_order": [int(value) for value in latch_config.priority_order],
        },
        "spice_front_end_config": _jsonable(candidate_cfg["actual_spice_config"]),
        "closure_drain_config": {
            "physicalization_config": _jsonable(candidate_cfg["physicalization_config"]),
        },
        "metric_aggregation_logic": {
            "summary_metrics_function": "build_summary_metrics",
            "chsh_function": "build_chsh_result",
            "pre_click_comparison_function": "build_pre_click_comparison",
            "case_metric_source": "run_spice_driven_preferred_chain_benchmark.case_rows",
        },
        "summary_metrics": _jsonable(run["summary_metrics"]),
    }


def build_baseline_comparison_rows(
    reference_signature: Mapping[str, Any],
    nominal_signature: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    fields = (
        ("benchmark_cases", "benchmark_definition"),
        ("n_trials", "sampling"),
        ("seed", "sampling"),
        ("source_kind", "harness"),
        ("driver", "harness"),
        ("trace_ingestion_path", "preprocessing"),
        ("trace_preprocessing", "preprocessing"),
        ("boundary_settings", "boundary"),
        ("detector_spec", "detector"),
        ("latch_settings", "latch"),
        ("spice_front_end_artifact_identity", "front_end"),
        ("spice_front_end_config", "front_end"),
        ("closure_drain_config", "closure"),
        ("metric_aggregation_logic", "aggregation"),
    )
    for field_name, category in fields:
        ref_value = reference_signature[field_name]
        nominal_value = nominal_signature[field_name]
        ref_json = json.dumps(_jsonable(ref_value), sort_keys=True)
        nominal_json = json.dumps(_jsonable(nominal_value), sort_keys=True)
        rows.append(
            {
                "setting_key": field_name,
                "category": category,
                "reference_value_json": ref_json,
                "nominal_value_json": nominal_json,
                "matches": bool(ref_json == nominal_json),
            }
        )
    return rows


def build_metric_comparison_rows(
    reference_metrics: Mapping[str, Any],
    nominal_metrics: Mapping[str, Any],
    reproduction_metrics: Mapping[str, Any],
) -> list[dict[str, Any]]:
    keys = (
        "winner_law_rms_error",
        "winner_law_max_error",
        "correlator_rms_error",
        "chsh_abs_error",
        "mean_decisive_fraction",
        "pre_click_transparency_rms_shift",
        "winner_drain_dominance_rate",
        "mean_loser_fraction_of_post_click",
        "completion_rate",
        "max_energy_balance_abs_fraction",
    )
    def _metric_value(metrics: Mapping[str, Any], key: str) -> float:
        value = metrics.get(key, float("nan"))
        return float(value)

    return [
        {
            "metric": key,
            "reference_value": _metric_value(reference_metrics, key),
            "nominal_value": _metric_value(nominal_metrics, key),
            "reproduction_value": _metric_value(reproduction_metrics, key),
            "nominal_minus_reference": _metric_value(nominal_metrics, key) - _metric_value(reference_metrics, key),
            "reproduction_minus_reference": _metric_value(reproduction_metrics, key) - _metric_value(reference_metrics, key),
        }
        for key in keys
    ]


def reproduction_within_tolerance(metric_rows: Sequence[Mapping[str, Any]]) -> bool:
    tolerances = {
        "winner_law_rms_error": 1e-9,
        "winner_law_max_error": 1e-9,
        "correlator_rms_error": 1e-9,
        "chsh_abs_error": 1e-9,
        "mean_decisive_fraction": 1e-9,
        "pre_click_transparency_rms_shift": 1e-9,
        "winner_drain_dominance_rate": 1e-9,
        "mean_loser_fraction_of_post_click": 1e-9,
        "completion_rate": 1e-9,
        "max_energy_balance_abs_fraction": 1e-9,
    }
    for row in metric_rows:
        reproduction_value = float(row["reproduction_value"])
        reference_value = float(row["reference_value"])
        if math.isnan(reproduction_value) and math.isnan(reference_value):
            continue
        if abs(float(row["reproduction_minus_reference"])) > float(tolerances[str(row["metric"])]):
            return False
    return True


def classify_root_cause(
    comparison_rows: Sequence[Mapping[str, Any]],
    *,
    reproduction_matches_reference: bool,
) -> dict[str, str]:
    mismatches = {str(row["setting_key"]) for row in comparison_rows if not bool(row["matches"])}
    if reproduction_matches_reference:
        if mismatches <= {"n_trials", "seed", "source_kind", "driver"} and mismatches:
            return {
                "classification": "configuration mismatch",
                "reason": "The robustness nominal baseline used different run settings from the validated SPICE-driven preferred-chain baseline. With matched settings, the robustness harness reproduces the validated baseline exactly.",
                "recommendation": "re-run with corrected nominal settings",
            }
        if {"trace_ingestion_path", "trace_preprocessing"} & mismatches:
            return {
                "classification": "preprocessing mismatch",
                "reason": "The robustness nominal baseline differs in preprocessing or boundary handoff logic, but the matched-settings reproduction restores the earlier baseline.",
                "recommendation": "re-run with corrected nominal settings",
            }
        if {"metric_aggregation_logic"} & mismatches:
            return {
                "classification": "aggregation mismatch",
                "reason": "The nominal robustness baseline is using different summary aggregation than the validated preferred-chain run.",
                "recommendation": "re-run with corrected nominal settings",
            }
        return {
            "classification": "other documented cause",
            "reason": "The robustness harness reproduces the validated baseline, but the nominal baseline still differs in documented settings outside the primary categories.",
            "recommendation": "re-run with corrected nominal settings",
        }
    if mismatches <= {"n_trials", "seed", "source_kind", "driver"} and mismatches:
        return {
            "classification": "random/statistical mismatch",
            "reason": "The nominal robustness baseline differs mainly in sampling settings, and the matched-settings reproduction did not fully restore the earlier baseline within tolerance.",
            "recommendation": "re-run with corrected nominal settings",
        }
    return {
        "classification": "true chain instability",
        "reason": "The robustness harness could not reproduce the earlier baseline even after matching nominal settings.",
        "recommendation": "replaced by a smaller reconciliation-first sweep",
    }


def _compact_run_record(run: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "label": str(run["spec"].label),
        "source_kind": str(run["spec"].source_kind),
        "driver": str(run["driver"]),
        "n_trials": int(run["spec"].n_trials),
        "seed": int(run["spec"].seed),
        "case_names": None if run["spec"].case_names is None else [str(name) for name in run["spec"].case_names],
        "summary_metrics": _jsonable(run["summary_metrics"]),
    }


def run_spice_driven_baseline_reconciliation(
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    reference_spec: BaselineRunSpec = VALIDATED_SPICE_DRIVEN_BASELINE,
    nominal_spec: BaselineRunSpec = ROBUSTNESS_NOMINAL_BASELINE,
    reference_run_override: Mapping[str, Any] | None = None,
    nominal_run_override: Mapping[str, Any] | None = None,
    verbose_progress: bool = False,
) -> dict[str, Any]:
    progress = _ProgressReporter(total_steps=3, enabled=verbose_progress)
    reference_run = dict(reference_run_override) if reference_run_override is not None else _run_spec(detector_spec, reference_spec)
    progress.advance("reference-complete")
    nominal_run = dict(nominal_run_override) if nominal_run_override is not None else _run_spec(detector_spec, nominal_spec)
    progress.advance("nominal-complete")
    reproduction_spec = BaselineRunSpec(
        label="robustness_harness_reproduction_of_reference",
        source_kind="robustness_baseline_only",
        n_trials=int(reference_spec.n_trials),
        seed=int(reference_spec.seed),
        case_names=reference_spec.case_names,
        spice_driven_config=reference_spec.spice_driven_config,
    )
    reproduction_run = _run_spec(detector_spec, reproduction_spec)
    progress.advance("reproduction-complete")

    reference_signature = _signature_from_run(reference_run, detector_spec)
    nominal_signature = _signature_from_run(nominal_run, detector_spec)
    reproduction_signature = _signature_from_run(reproduction_run, detector_spec)
    comparison_rows = build_baseline_comparison_rows(reference_signature, nominal_signature)
    metric_rows = build_metric_comparison_rows(
        reference_run["summary_metrics"],
        nominal_run["summary_metrics"],
        reproduction_run["summary_metrics"],
    )
    reproduction_matches_reference = reproduction_within_tolerance(metric_rows)
    classification = classify_root_cause(
        comparison_rows,
        reproduction_matches_reference=reproduction_matches_reference,
    )
    summary_metrics = {
        "reference_winner_law_rms_error": float(reference_run["summary_metrics"]["winner_law_rms_error"]),
        "nominal_winner_law_rms_error": float(nominal_run["summary_metrics"]["winner_law_rms_error"]),
        "reproduction_winner_law_rms_error": float(reproduction_run["summary_metrics"]["winner_law_rms_error"]),
        "reference_correlator_rms_error": float(reference_run["summary_metrics"]["correlator_rms_error"]),
        "nominal_correlator_rms_error": float(nominal_run["summary_metrics"]["correlator_rms_error"]),
        "reproduction_correlator_rms_error": float(reproduction_run["summary_metrics"]["correlator_rms_error"]),
        "reference_chsh_abs_error": float(reference_run["summary_metrics"]["chsh_abs_error"]),
        "nominal_chsh_abs_error": float(nominal_run["summary_metrics"]["chsh_abs_error"]),
        "reproduction_chsh_abs_error": float(reproduction_run["summary_metrics"]["chsh_abs_error"]),
        "nominal_vs_reference_winner_rms_delta": float(
            nominal_run["summary_metrics"]["winner_law_rms_error"] - reference_run["summary_metrics"]["winner_law_rms_error"]
        ),
        "nominal_vs_reference_correlator_delta": float(
            nominal_run["summary_metrics"]["correlator_rms_error"] - reference_run["summary_metrics"]["correlator_rms_error"]
        ),
        "nominal_vs_reference_chsh_delta": float(
            nominal_run["summary_metrics"]["chsh_abs_error"] - reference_run["summary_metrics"]["chsh_abs_error"]
        ),
        "reproduction_matches_reference": bool(reproduction_matches_reference),
        "matched_setting_count": int(sum(bool(row["matches"]) for row in comparison_rows)),
        "different_setting_count": int(sum(not bool(row["matches"]) for row in comparison_rows)),
        "root_cause_classification": classification["classification"],
        "recommendation": classification["recommendation"],
    }
    return {
        "reference_run": _compact_run_record(reference_run),
        "nominal_run": _compact_run_record(nominal_run),
        "reproduction_run": _compact_run_record(reproduction_run),
        "reference_signature": reference_signature,
        "nominal_signature": nominal_signature,
        "reproduction_signature": reproduction_signature,
        "comparison_rows": comparison_rows,
        "metric_rows": metric_rows,
        "summary_metrics": summary_metrics,
        "root_cause": classification,
    }


__all__ = [
    "BaselineRunSpec",
    "ROBUSTNESS_NOMINAL_BASELINE",
    "VALIDATED_SPICE_DRIVEN_BASELINE",
    "build_baseline_comparison_rows",
    "build_metric_comparison_rows",
    "classify_root_cause",
    "reproduction_within_tolerance",
    "run_spice_driven_baseline_reconciliation",
]
