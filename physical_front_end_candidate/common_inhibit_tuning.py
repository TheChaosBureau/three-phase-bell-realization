from __future__ import annotations

import json
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np

from .physical_closure_drain_candidate import (
    PhysicalClosureDrainConfig,
    build_physical_closure_candidate_cache,
    default_physical_closure_drain_config,
    preferred_common_mode_interpretation,
    run_four_branch_candidate_with_physical_closure,
)
from .resonant_four_branch_candidate import benchmark_resonant_four_branch_cases, simulate_resonant_four_branch_candidate


@dataclass(frozen=True)
class CommonInhibitTuningSweepConfig:
    inhibit_tau_values_s: tuple[float, ...] = (0.05, 0.08, 0.10, 0.14, 0.20)
    clamp_strength_values_s: tuple[float, ...] = (0.4, 0.7, 1.0, 1.4, 2.0)
    drain_strength_values_s: tuple[float, ...] = (1.6, 2.0, 2.6, 3.2, 4.0)


@dataclass
class _ProgressReporter:
    total_steps: int
    enabled: bool = False
    path: Path | None = None
    completed_steps: int = 0
    start_time_s: float = 0.0

    def __post_init__(self) -> None:
        self.start_time_s = time.monotonic()
        if self.enabled:
            self._emit("starting", initial=True)

    def advance(self, phase: str, *, case_name: str | None = None) -> None:
        self.completed_steps += 1
        self._emit(phase, case_name=case_name)

    def _emit(self, phase: str, *, case_name: str | None = None, initial: bool = False) -> None:
        elapsed_s = max(time.monotonic() - self.start_time_s, 0.0)
        completed = self.completed_steps
        rate = completed / elapsed_s if elapsed_s > 0.0 else 0.0
        remaining = max(self.total_steps - completed, 0)
        eta_s = remaining / rate if rate > 0.0 else None
        percent = 100.0 * completed / max(self.total_steps, 1)
        payload = {
            "phase": phase,
            "case_name": case_name,
            "completed_steps": completed,
            "total_steps": self.total_steps,
            "percent": percent,
            "elapsed_s": elapsed_s,
            "eta_s": eta_s,
        }
        if self.path is not None:
            self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        if not self.enabled:
            return
        if initial:
            message = f"[common-inhibit-tuning] 0/{self.total_steps} steps, elapsed 0.0s, ETA unknown, phase=starting"
        else:
            eta_text = "unknown" if eta_s is None else f"{eta_s:.1f}s"
            case_text = "" if case_name is None else f", case={case_name}"
            message = (
                f"[common-inhibit-tuning] {completed}/{self.total_steps} steps "
                f"({percent:.1f}%), elapsed {elapsed_s:.1f}s, ETA {eta_text}, phase={phase}{case_text}"
            )
        print(message, file=sys.stderr, flush=True)


def default_common_inhibit_tuning_sweep_config() -> CommonInhibitTuningSweepConfig:
    base = default_physical_closure_drain_config()
    return CommonInhibitTuningSweepConfig(
        inhibit_tau_values_s=(
            round(base.control_tau_s * 0.6, 6),
            round(base.control_tau_s * 0.8, 6),
            round(base.control_tau_s, 6),
            round(base.control_tau_s * 1.25, 6),
            round(base.control_tau_s * 1.6, 6),
        ),
        clamp_strength_values_s=(0.4, 0.7, 1.0, 1.4, 2.0),
        drain_strength_values_s=(1.6, 2.0, 2.6, 3.2, 4.0),
    )


def benchmark_tuning_case_runs(
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    n_trials: int,
    seed: int,
    case_names: Sequence[str] | None = None,
    progress: _ProgressReporter | None = None,
) -> list[dict[str, Any]]:
    from .closure_path import simulate_four_branch_candidate_pre_click_race

    selected_case_names = None if case_names is None else set(case_names)
    cases = [
        case
        for case in benchmark_resonant_four_branch_cases()
        if selected_case_names is None or case["case"] in selected_case_names
    ]
    runs: list[dict[str, Any]] = []
    for case_index, case in enumerate(cases):
        candidate = simulate_resonant_four_branch_candidate(case["state4"], a_deg=case["a_deg"], b_deg=case["b_deg"])
        race = simulate_four_branch_candidate_pre_click_race(candidate, detector_spec, n_trials=n_trials, seed=seed + 1_003 * case_index)
        runs.append(
            {
                "case": case,
                "candidate": candidate,
                "candidate_cache": build_physical_closure_candidate_cache(candidate),
                "race": race,
            }
        )
        if progress is not None:
            progress.advance("precompute-race", case_name=str(case["case"]))
    return runs


def _aggregate_case_results(
    case_results: list[dict[str, Any]],
    *,
    config: PhysicalClosureDrainConfig,
    baseline_summary: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    integration_rows = [
        {
            "case": result["case"],
            "a_deg": result["a_deg"],
            "b_deg": result["b_deg"],
            "winner_rms_error": float(result["metrics"]["rms_error"]),
            "winner_max_error": float(result["metrics"]["max_abs_error"]),
            "correlator_error": float(result["metrics"]["correlator_error"]),
            "decisive_fraction": float(result["decisive_fraction"]),
            "pre_click_transparency_rms_shift": float(result["closure_metrics"]["pre_click_transparency_rms_shift"]),
            "winner_drain_fraction": float(result["closure_metrics"]["mean_winner_drain_fraction"]),
            "loser_fraction": float(result["closure_metrics"]["mean_loser_fraction"]),
            "completion_rate": float(result["closure_metrics"]["completion_rate"]),
            "mean_completion_time_s": float(result["closure_metrics"]["mean_completion_time_s"]),
            "monotonic_remaining_energy": bool(result["closure_metrics"]["monotonic_remaining_energy"]),
            "mean_terminal_loser_suppression": float(result["closure_metrics"]["mean_terminal_loser_suppression"]),
            "winner_drain_path_count": float(result["closure_metrics"]["mean_winner_drain_path_count"]),
        }
        for result in case_results
    ]
    comparison_rows = [
        {
            "case": result["case"],
            "winner_fraction_abs_diff": float(result["comparison_metrics"]["winner_fraction_abs_diff"]),
            "loser_fraction_abs_diff": float(result["comparison_metrics"]["loser_fraction_abs_diff"]),
            "completion_rate_abs_diff": float(result["comparison_metrics"]["completion_rate_abs_diff"]),
            "completion_time_abs_diff": float(result["comparison_metrics"]["completion_time_abs_diff"]),
        }
        for result in case_results
    ]
    summary_metrics = {
        "control_tau_s": float(config.control_tau_s),
        "clamp_reference_g_on_s": float(config.clamp_reference_g_on_s),
        "winner_drain_g_on_s": float(config.winner_drain_g_on_s),
        "winner_drain_tau_s": float(config.winner_drain_tau_s),
        "pre_click_transparency_rms_shift": float(np.sqrt(np.mean(np.square([row["pre_click_transparency_rms_shift"] for row in integration_rows])))),
        "mean_winner_drain_fraction": float(np.mean([row["winner_drain_fraction"] for row in integration_rows])),
        "mean_loser_fraction": float(np.mean([row["loser_fraction"] for row in integration_rows])),
        "completion_rate": float(np.mean([row["completion_rate"] for row in integration_rows])),
        "mean_completion_time_s": float(np.mean([row["mean_completion_time_s"] for row in integration_rows])),
        "monotonic_remaining_energy": bool(all(bool(row["monotonic_remaining_energy"]) for row in integration_rows)),
        "mean_terminal_loser_suppression": float(np.mean([row["mean_terminal_loser_suppression"] for row in integration_rows])),
        "mean_winner_drain_path_count": float(np.mean([row["winner_drain_path_count"] for row in integration_rows])),
        "reduced_winner_fraction_abs_diff": float(np.mean([row["winner_fraction_abs_diff"] for row in comparison_rows])),
        "reduced_loser_fraction_abs_diff": float(np.mean([row["loser_fraction_abs_diff"] for row in comparison_rows])),
        "reduced_completion_rate_abs_diff": float(np.mean([row["completion_rate_abs_diff"] for row in comparison_rows])),
        "reduced_completion_time_abs_diff": float(np.mean([row["completion_time_abs_diff"] for row in comparison_rows])),
    }
    summary_metrics["pre_click_transparency_pass"] = float(summary_metrics["pre_click_transparency_rms_shift"]) < 0.01
    summary_metrics["winner_dominance_pass"] = (
        float(summary_metrics["mean_winner_drain_fraction"]) > 0.88
        and float(summary_metrics["mean_loser_fraction"]) < 0.02
        and float(summary_metrics["mean_terminal_loser_suppression"]) > 0.93
        and abs(float(summary_metrics["mean_winner_drain_path_count"]) - 1.0) < 1e-9
    )
    summary_metrics["completion_pass"] = float(summary_metrics["completion_rate"]) > 0.9 and bool(summary_metrics["monotonic_remaining_energy"])
    summary_metrics["reduced_consistency_pass"] = (
        float(summary_metrics["reduced_winner_fraction_abs_diff"]) < 0.12
        and float(summary_metrics["reduced_loser_fraction_abs_diff"]) < 0.05
        and float(summary_metrics["reduced_completion_rate_abs_diff"]) < 0.1
    )
    if baseline_summary is None:
        summary_metrics["improvement_vs_baseline"] = 0.0
    else:
        summary_metrics["improvement_vs_baseline"] = (
            float(summary_metrics["mean_winner_drain_fraction"]) - float(baseline_summary["mean_winner_drain_fraction"])
        )
    return {
        "integration_rows": integration_rows,
        "comparison_rows": comparison_rows,
        "summary_metrics": summary_metrics,
    }


def score_tuned_candidate(summary_metrics: Mapping[str, float | bool]) -> float:
    penalty = 0.0
    if float(summary_metrics["pre_click_transparency_rms_shift"]) >= 0.01:
        penalty += 10.0
    if not bool(summary_metrics["monotonic_remaining_energy"]):
        penalty += 10.0
    if float(summary_metrics["completion_rate"]) < 0.9:
        penalty += 5.0
    return (
        8.0 * float(summary_metrics["mean_winner_drain_fraction"])
        - 8.0 * float(summary_metrics["mean_loser_fraction"])
        + 2.0 * float(summary_metrics["mean_terminal_loser_suppression"])
        + 2.0 * float(summary_metrics["completion_rate"])
        - 4.0 * float(summary_metrics["reduced_winner_fraction_abs_diff"])
        - 2.0 * float(summary_metrics["pre_click_transparency_rms_shift"])
        + 3.0 * float(summary_metrics["improvement_vs_baseline"])
        - penalty
    )


def evaluate_tuned_closure_config(
    case_runs: Sequence[Mapping[str, Any]],
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    config: PhysicalClosureDrainConfig,
    seed: int = 20260403,
    baseline_summary: Mapping[str, float] | None = None,
    progress: _ProgressReporter | None = None,
    progress_phase: str = "evaluate",
) -> dict[str, Any]:
    reduced = preferred_common_mode_interpretation()
    case_results: list[dict[str, Any]] = []
    example_trial: dict[str, Any] | None = None
    for case_index, case_run in enumerate(case_runs):
        result = run_four_branch_candidate_with_physical_closure(
            case_run["candidate"],
            detector_spec,
            n_trials=int(case_run["race"]["frequency_summary"]["decisive_count"] + case_run["race"]["frequency_summary"]["timeout_count"]),
            seed=seed + 1_003 * case_index,
            config=config,
            reduced_interpretation=reduced,
            race_result=case_run["race"],
            candidate_cache=case_run.get("candidate_cache"),
        )
        case_results.append(
            {
                "case": case_run["case"]["case"],
                "a_deg": float(case_run["case"]["a_deg"]),
                "b_deg": float(case_run["case"]["b_deg"]),
                "metrics": result["metrics"],
                "decisive_fraction": result["decisive_fraction"],
                "closure_metrics": result["closure_metrics"],
                "comparison_metrics": result["comparison_metrics"],
            }
        )
        if example_trial is None and result["example_trial"] is not None:
            example_trial = {
                "case": case_run["case"]["case"],
                **result["example_trial"],
            }
        if progress is not None:
            progress.advance(progress_phase, case_name=str(case_run["case"]["case"]))
    aggregate = _aggregate_case_results(case_results, config=config, baseline_summary=baseline_summary)
    return {
        "config": asdict(config),
        "case_results": case_results,
        "summary_metrics": aggregate["summary_metrics"],
        "integration_rows": aggregate["integration_rows"],
        "comparison_rows": aggregate["comparison_rows"],
        "score": score_tuned_candidate(aggregate["summary_metrics"]),
        "example_trial": example_trial,
    }


def run_common_inhibit_parameter_sweeps(
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    n_trials: int,
    seed: int = 20260403,
    case_names: Sequence[str] | None = None,
    sweep_config: CommonInhibitTuningSweepConfig | None = None,
    verbose_progress: bool = False,
    progress_path: str | Path | None = None,
) -> dict[str, Any]:
    base_config = default_physical_closure_drain_config()
    sweeps = default_common_inhibit_tuning_sweep_config() if sweep_config is None else sweep_config
    selected_case_names = None if case_names is None else set(case_names)
    case_count = sum(
        1
        for case in benchmark_resonant_four_branch_cases()
        if selected_case_names is None or case["case"] in selected_case_names
    )
    total_eval_count = 1 + len(sweeps.drain_strength_values_s) + len(sweeps.clamp_strength_values_s) + len(sweeps.inhibit_tau_values_s) + 1
    progress = _ProgressReporter(
        total_steps=case_count * (1 + total_eval_count),
        enabled=verbose_progress,
        path=None if progress_path is None else Path(progress_path),
    )
    case_runs = benchmark_tuning_case_runs(
        detector_spec,
        n_trials=n_trials,
        seed=seed,
        case_names=case_names,
        progress=progress,
    )
    baseline = evaluate_tuned_closure_config(
        case_runs,
        detector_spec,
        config=base_config,
        seed=seed,
        progress=progress,
        progress_phase="baseline",
    )

    sweep_rows: dict[str, list[dict[str, Any]]] = {
        "winner_drain_g_on_s": [],
        "clamp_reference_g_on_s": [],
        "control_tau_s": [],
    }
    best_values = {
        "winner_drain_g_on_s": base_config.winner_drain_g_on_s,
        "clamp_reference_g_on_s": base_config.clamp_reference_g_on_s,
        "control_tau_s": base_config.control_tau_s,
    }

    for value in sweeps.drain_strength_values_s:
        config = replace(base_config, winner_drain_g_on_s=float(value))
        evaluation = evaluate_tuned_closure_config(
            case_runs,
            detector_spec,
            config=config,
            seed=seed,
            baseline_summary=baseline["summary_metrics"],
            progress=progress,
            progress_phase=f"drain-strength={float(value):.6g}",
        )
        row = {"winner_drain_g_on_s": float(value), **evaluation["summary_metrics"], "score": float(evaluation["score"])}
        sweep_rows["winner_drain_g_on_s"].append(row)

    for value in sweeps.clamp_strength_values_s:
        config = replace(base_config, clamp_reference_g_on_s=float(value))
        evaluation = evaluate_tuned_closure_config(
            case_runs,
            detector_spec,
            config=config,
            seed=seed,
            baseline_summary=baseline["summary_metrics"],
            progress=progress,
            progress_phase=f"clamp-strength={float(value):.6g}",
        )
        row = {"clamp_reference_g_on_s": float(value), **evaluation["summary_metrics"], "score": float(evaluation["score"])}
        sweep_rows["clamp_reference_g_on_s"].append(row)

    for value in sweeps.inhibit_tau_values_s:
        config = replace(
            base_config,
            control_tau_s=float(value),
            winner_drain_tau_s=min(base_config.winner_drain_tau_s, float(value)),
        )
        evaluation = evaluate_tuned_closure_config(
            case_runs,
            detector_spec,
            config=config,
            seed=seed,
            baseline_summary=baseline["summary_metrics"],
            progress=progress,
            progress_phase=f"inhibit-tau={float(value):.6g}",
        )
        row = {"control_tau_s": float(value), **evaluation["summary_metrics"], "score": float(evaluation["score"])}
        sweep_rows["control_tau_s"].append(row)

    for key, rows in sweep_rows.items():
        best_values[key] = max(rows, key=lambda row: float(row["score"]))[key]

    tuned_config = replace(
        base_config,
        winner_drain_g_on_s=float(best_values["winner_drain_g_on_s"]),
        clamp_reference_g_on_s=float(best_values["clamp_reference_g_on_s"]),
        control_tau_s=float(best_values["control_tau_s"]),
        winner_drain_tau_s=min(base_config.winner_drain_tau_s, float(best_values["control_tau_s"])),
    )
    tuned = evaluate_tuned_closure_config(
        case_runs,
        detector_spec,
        config=tuned_config,
        seed=seed,
        baseline_summary=baseline["summary_metrics"],
        progress=progress,
        progress_phase="best-tuned",
    )
    return {
        "base_config": asdict(base_config),
        "baseline": baseline,
        "sweep_rows": sweep_rows,
        "best_values": best_values,
        "best_tuned": tuned,
        "case_runs": case_runs,
    }
