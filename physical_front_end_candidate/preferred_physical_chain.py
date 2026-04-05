from __future__ import annotations

import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from detector_integration.detectors import (
    latch_first_event,
    resolve_branch_detector_params,
    simulate_branch_nucleation,
    validated_latch_arbiter_config,
)
from detector_integration.sim.metrics import four_branch_metrics, winner_frequency_summary

from .boundary_diagnosis import trace_to_detector_envelopes
from .integration import materialize_candidate_trace
from .physical_closure_drain_candidate import (
    PhysicalClosureDrainConfig,
    build_physical_closure_candidate_cache,
    default_physical_closure_drain_config,
    simulate_physical_closure_drain,
)
from .preferred_physical_chain_energy import build_trial_energy_accounting, summarize_energy_accounting_rows
from .preferred_physical_chain_metrics import (
    build_chsh_result,
    build_pre_click_comparison,
    build_summary_metrics,
    summarize_post_click_behavior,
)
from .resonant_four_branch_candidate import benchmark_resonant_four_branch_cases, simulate_resonant_four_branch_candidate


@dataclass
class _ProgressReporter:
    total_steps: int
    enabled: bool = False
    completed_steps: int = 0
    start_time_s: float = 0.0
    last_report_time_s: float = 0.0
    last_phase: str | None = None
    last_case_name: str | None = None

    def __post_init__(self) -> None:
        self.start_time_s = time.monotonic()
        self.last_report_time_s = self.start_time_s
        if self.enabled:
            self.report("starting", force=True)

    def report(self, phase: str, case_name: str | None = None, *, force: bool = False) -> None:
        if not self.enabled:
            return
        now = time.monotonic()
        phase_changed = phase != self.last_phase or case_name != self.last_case_name
        if not force and not phase_changed and (now - self.last_report_time_s) < 0.5:
            return
        elapsed_s = max(now - self.start_time_s, 0.0)
        completed = self.completed_steps
        rate = completed / elapsed_s if elapsed_s > 0.0 else 0.0
        remaining = max(self.total_steps - completed, 0)
        eta_s = remaining / rate if rate > 0.0 else None
        percent = 100.0 * completed / max(self.total_steps, 1)
        eta_text = "unknown" if eta_s is None else f"{eta_s:.1f}s"
        case_text = "" if case_name is None else f", case={case_name}"
        message = (
            f"[preferred-physical-chain] {completed}/{self.total_steps} steps "
            f"({percent:.1f}%), elapsed {elapsed_s:.1f}s, ETA {eta_text}, phase={phase}{case_text}"
        )
        print(message, file=sys.stderr, flush=True)
        self.last_report_time_s = now
        self.last_phase = phase
        self.last_case_name = case_name

    def advance(self, phase: str, case_name: str | None = None, *, steps: int = 1) -> None:
        self.completed_steps += int(steps)
        self.report(phase, case_name=case_name, force=self.completed_steps >= self.total_steps)


def preferred_physical_chain_benchmark_cases() -> list[dict[str, Any]]:
    return benchmark_resonant_four_branch_cases()


def _resolve_closure_config(
    config: PhysicalClosureDrainConfig | Mapping[str, Any] | None,
) -> PhysicalClosureDrainConfig:
    if config is None:
        return default_physical_closure_drain_config()
    if isinstance(config, PhysicalClosureDrainConfig):
        return config
    return PhysicalClosureDrainConfig(**dict(config))


def _run_pre_click_race(
    candidate: Mapping[str, Any],
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    n_trials: int,
    seed: int,
    boundary_config: Mapping[str, Any] | None = None,
    progress: _ProgressReporter | None = None,
    case_name: str | None = None,
) -> dict[str, Any]:
    trace = materialize_candidate_trace(candidate, boundary_config=boundary_config)
    detector_envelopes = trace_to_detector_envelopes(trace)
    exact_weights = np.asarray(
        [candidate["exact_weight"][label] for label in candidate["branch_labels"]],
        dtype=float,
    )
    rng = np.random.default_rng(seed)
    latch_config = validated_latch_arbiter_config(len(candidate["branch_labels"]))
    winners: list[int] = []
    event_time_rows: list[np.ndarray] = []
    pulse_time_rows: list[np.ndarray] = []
    latch_results: list[dict[str, Any]] = []
    tie_region_count = 0

    for _ in range(n_trials):
        event_times = np.full(len(candidate["branch_labels"]), np.inf, dtype=float)
        for branch_index in range(len(candidate["branch_labels"])):
            branch_rng = np.random.default_rng(int(rng.integers(0, 2**32 - 1)))
            detector_params = resolve_branch_detector_params(detector_spec, branch_index)
            click_time = simulate_branch_nucleation(detector_params, 1.0, detector_envelopes[branch_index], branch_rng)
            if click_time is not None:
                event_times[branch_index] = click_time
        latch_result = latch_first_event(event_times, config=latch_config, rng=rng)
        winners.append(int(latch_result["winner_index"]))
        event_time_rows.append(event_times)
        pulse_time_rows.append(np.asarray(latch_result["pulse_times"], dtype=float))
        tie_region_count += int(bool(latch_result["tie_region"]))
        latch_results.append(
            {
                "winner_index": int(latch_result["winner_index"]),
                "winner_valid": bool(latch_result["winner_valid"]),
                "settled_at_s": float(latch_result["settled_at_s"]),
                "tie_region": bool(latch_result["tie_region"]),
                "suppressed_indices": list(latch_result["suppressed_indices"]),
            }
        )
        if progress is not None:
            progress.advance("pre-click-race", case_name=case_name)

    frequency_summary = winner_frequency_summary(winners, n_branches=len(candidate["branch_labels"]))
    return {
        "trace": trace,
        "detector_envelopes": detector_envelopes,
        "exact_weights": exact_weights,
        "metrics": four_branch_metrics(exact_weights, frequency_summary["frequencies"]),
        "frequency_summary": frequency_summary,
        "event_times": np.asarray(event_time_rows, dtype=float),
        "pulse_times": np.asarray(pulse_time_rows, dtype=float),
        "latch_results": latch_results,
        "tie_region_fraction": tie_region_count / max(n_trials, 1),
    }


def run_preferred_physical_chain_candidate(
    candidate: Mapping[str, Any],
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    n_trials: int,
    seed: int,
    closure_config: PhysicalClosureDrainConfig | Mapping[str, Any] | None = None,
    boundary_config: Mapping[str, Any] | None = None,
    race_result: Mapping[str, Any] | None = None,
    candidate_cache: Mapping[str, Any] | None = None,
    progress: _ProgressReporter | None = None,
    case_name: str | None = None,
) -> dict[str, Any]:
    resolved_closure = _resolve_closure_config(closure_config)
    race = (
        _run_pre_click_race(
            candidate,
            detector_spec,
            n_trials=n_trials,
            seed=seed,
            boundary_config=boundary_config,
            progress=progress,
            case_name=case_name,
        )
        if race_result is None
        else dict(race_result)
    )
    frequency_summary = race["frequency_summary"]
    cache = build_physical_closure_candidate_cache(candidate) if candidate_cache is None else dict(candidate_cache)
    closure_rows: list[dict[str, Any]] = []
    energy_rows: list[dict[str, Any]] = []
    example_trial: dict[str, Any] | None = None

    for trial_index, latch_result in enumerate(race["latch_results"]):
        physical = simulate_physical_closure_drain(
            time_s=candidate["time_s"],
            branch_power_w=candidate["branch_power_w"],
            branch_labels=candidate["branch_labels"],
            winner_index=int(latch_result["winner_index"]),
            winner_valid=bool(latch_result["winner_valid"]),
            capture_time_s=float(latch_result["settled_at_s"]),
            config=resolved_closure,
            candidate_cache=cache,
            include_traces=False,
        )
        closure_rows.append(physical)
        energy_row = build_trial_energy_accounting(
            candidate,
            physical,
            capture_time_s=float(latch_result["settled_at_s"]),
            winner_valid=bool(latch_result["winner_valid"]),
            candidate_cache=cache,
        )
        energy_rows.append(
            {
                "trial_index": trial_index,
                **energy_row,
            }
        )
        if progress is not None:
            progress.advance("post-click-closure", case_name=case_name)
        if example_trial is None and bool(physical["closure_active"]):
            physical_trace = simulate_physical_closure_drain(
                time_s=candidate["time_s"],
                branch_power_w=candidate["branch_power_w"],
                branch_labels=candidate["branch_labels"],
                winner_index=int(latch_result["winner_index"]),
                winner_valid=bool(latch_result["winner_valid"]),
                capture_time_s=float(latch_result["settled_at_s"]),
                config=resolved_closure,
                candidate_cache=cache,
                include_traces=True,
            )
            example_trial = {
                "trial_index": trial_index,
                "latch_result": dict(latch_result),
                "event_times": race["event_times"][trial_index].tolist(),
                "pulse_times": race["pulse_times"][trial_index].tolist(),
                "physical": physical_trace,
                "energy_accounting": dict(energy_row),
            }

    pre_click_comparison = build_pre_click_comparison(
        exact_weights=race["exact_weights"],
        baseline_frequencies=frequency_summary["frequencies"],
        integrated_frequencies=frequency_summary["frequencies"],
        baseline_decisive_fraction=float(frequency_summary["decisive_fraction"]),
        integrated_decisive_fraction=float(frequency_summary["decisive_fraction"]),
        baseline_timeout_fraction=float(frequency_summary["timeout_fraction"]),
        integrated_timeout_fraction=float(frequency_summary["timeout_fraction"]),
    )
    post_click_summary = summarize_post_click_behavior(closure_rows, energy_rows)
    energy_summary = summarize_energy_accounting_rows(energy_rows)
    return {
        "candidate": candidate,
        "trace": race["trace"],
        "detector_envelopes": race["detector_envelopes"],
        "export_config": dict(race["trace"]["export_config"]),
        "boundary_config": dict(race["trace"]["boundary_config"]),
        "closure_config": asdict(resolved_closure),
        "pre_click_race": race,
        "exact_weights": race["exact_weights"],
        "empirical_frequencies": frequency_summary["frequencies"],
        "winner_counts": frequency_summary["counts"],
        "decisive_count": frequency_summary["decisive_count"],
        "timeout_count": frequency_summary["timeout_count"],
        "decisive_fraction": frequency_summary["decisive_fraction"],
        "timeout_fraction": frequency_summary["timeout_fraction"],
        "metrics": dict(race["metrics"]),
        "pre_click_comparison": pre_click_comparison,
        "post_click_summary": post_click_summary,
        "closure_rows": closure_rows,
        "energy_accounting_rows": energy_rows,
        "energy_accounting_summary": energy_summary,
        "example_trial": example_trial,
        "tie_region_fraction": float(race["tie_region_fraction"]),
    }


def run_preferred_physical_chain_case(
    state4: np.ndarray | None,
    *,
    a_deg: float,
    b_deg: float,
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    n_trials: int,
    seed: int,
    closure_config: PhysicalClosureDrainConfig | Mapping[str, Any] | None = None,
    boundary_config: Mapping[str, Any] | None = None,
    progress: _ProgressReporter | None = None,
    case_name: str | None = None,
) -> dict[str, Any]:
    candidate = simulate_resonant_four_branch_candidate(state4, a_deg=a_deg, b_deg=b_deg)
    return run_preferred_physical_chain_candidate(
        candidate,
        detector_spec,
        n_trials=n_trials,
        seed=seed,
        closure_config=closure_config,
        boundary_config=boundary_config,
        progress=progress,
        case_name=case_name,
    )


def run_preferred_physical_chain_benchmark(
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    n_trials: int,
    seed: int,
    case_names: Sequence[str] | None = None,
    closure_config: PhysicalClosureDrainConfig | Mapping[str, Any] | None = None,
    boundary_config: Mapping[str, Any] | None = None,
    verbose_progress: bool = False,
) -> dict[str, Any]:
    selected_case_names = None if case_names is None else set(case_names)
    cases = [
        case
        for case in preferred_physical_chain_benchmark_cases()
        if selected_case_names is None or case["case"] in selected_case_names
    ]
    if not cases:
        raise ValueError("No preferred physical-chain benchmark cases selected.")
    progress = _ProgressReporter(
        total_steps=max(len(cases) * max(2 * n_trials, 1), 1),
        enabled=verbose_progress,
    )

    case_results: list[dict[str, Any]] = []
    case_rows: list[dict[str, Any]] = []
    pre_click_rows: list[dict[str, Any]] = []
    post_click_rows: list[dict[str, Any]] = []
    energy_case_rows: list[dict[str, Any]] = []
    all_energy_rows: list[dict[str, Any]] = []
    example_trial: dict[str, Any] | None = None

    for case_index, case in enumerate(cases):
        progress.report("starting-case", case_name=str(case["case"]), force=True)
        candidate = simulate_resonant_four_branch_candidate(case["state4"], a_deg=case["a_deg"], b_deg=case["b_deg"])
        result = run_preferred_physical_chain_candidate(
            candidate,
            detector_spec,
            n_trials=n_trials,
            seed=seed + 1_003 * case_index,
            closure_config=closure_config,
            boundary_config=boundary_config,
            progress=progress,
            case_name=str(case["case"]),
        )
        case_results.append({"case": case, "result": result})
        case_rows.append(
            {
                "case": case["case"],
                "a_deg": float(case["a_deg"]),
                "b_deg": float(case["b_deg"]),
                "branch_labels": list(candidate["branch_labels"]),
                "exact_weights": list(result["exact_weights"]),
                "empirical_frequencies": list(result["empirical_frequencies"]),
                "winner_rms_error": float(result["metrics"]["rms_error"]),
                "winner_max_error": float(result["metrics"]["max_abs_error"]),
                "correlator_exact": float(result["metrics"]["correlator_exact"]),
                "correlator_empirical": float(result["metrics"]["correlator_empirical"]),
                "correlator_error": float(result["metrics"]["correlator_error"]),
                "decisive_fraction": float(result["decisive_fraction"]),
                "timeout_fraction": float(result["timeout_fraction"]),
                "tie_region_fraction": float(result["tie_region_fraction"]),
            }
        )
        pre_click_rows.append(
            {
                "case": case["case"],
                "a_deg": float(case["a_deg"]),
                "b_deg": float(case["b_deg"]),
                **result["pre_click_comparison"],
            }
        )
        post_click_rows.append(
            {
                "case": case["case"],
                "a_deg": float(case["a_deg"]),
                "b_deg": float(case["b_deg"]),
                **result["post_click_summary"],
            }
        )
        energy_case_summary = summarize_energy_accounting_rows(result["energy_accounting_rows"])
        energy_case_rows.append(
            {
                "case": case["case"],
                "a_deg": float(case["a_deg"]),
                "b_deg": float(case["b_deg"]),
                **energy_case_summary,
            }
        )
        all_energy_rows.extend(
            {
                "case": case["case"],
                "a_deg": float(case["a_deg"]),
                "b_deg": float(case["b_deg"]),
                **row,
            }
            for row in result["energy_accounting_rows"]
        )
        if example_trial is None and result["example_trial"] is not None:
            example_trial = {
                "case": case["case"],
                "a_deg": float(case["a_deg"]),
                "b_deg": float(case["b_deg"]),
                **result["example_trial"],
            }

    chsh_result = build_chsh_result(case_rows)
    energy_summary = summarize_energy_accounting_rows(all_energy_rows)
    summary_metrics = build_summary_metrics(
        case_rows,
        pre_click_rows,
        post_click_rows,
        energy_summary,
        chsh_result,
    )
    progress.report("benchmark-complete", force=True)
    return {
        "case_results": case_results,
        "case_rows": case_rows,
        "pre_click_rows": pre_click_rows,
        "post_click_rows": post_click_rows,
        "energy_case_rows": energy_case_rows,
        "energy_rows": all_energy_rows,
        "energy_summary": energy_summary,
        "chsh_result": chsh_result,
        "summary_metrics": summary_metrics,
        "example_trial": example_trial,
    }
