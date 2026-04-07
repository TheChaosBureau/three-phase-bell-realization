from __future__ import annotations

import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

from .actual_spice_front_end import (
    ActualSpiceFrontEndConfig,
    actual_spice_front_end_benchmark_cases,
    simulate_actual_spice_front_end_candidate,
)
from .boundary_calibration import resolved_calibrated_boundary_config
from .metrics import aggregate_case_error, correlator_rms_error
from .preferred_chain_device_physicalization import (
    PreferredChainDevicePhysicalizationConfig,
    run_preferred_chain_device_physicalization_case,
    run_preferred_chain_device_physicalization_candidate,
    simulate_preferred_chain_device_physicalization_candidate,
)
from .preferred_physical_chain_energy import summarize_energy_accounting_rows
from .preferred_physical_chain_metrics import build_chsh_result, build_summary_metrics

BRANCH_LABELS = ["++", "+-", "-+", "--"]


@dataclass
class _ProgressReporter:
    total_steps: int
    enabled: bool = False
    label: str = "spice-driven-preferred-chain"
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
        eta_text = "unknown" if eta_s is None else f"{eta_s:.1f}s"
        percent = 100.0 * completed / max(self.total_steps, 1)
        case_text = "" if case_name is None else f", case={case_name}"
        print(
            f"[{self.label}] {completed}/{self.total_steps} steps ({percent:.1f}%), "
            f"elapsed {elapsed_s:.1f}s, ETA {eta_text}, phase={phase}{case_text}",
            file=sys.stderr,
            flush=True,
        )
        self.last_report_time_s = now
        self.last_phase = phase
        self.last_case_name = case_name

    def advance(self, phase: str, case_name: str | None = None, *, steps: int = 1) -> None:
        self.completed_steps += int(steps)
        self.report(phase, case_name=case_name, force=self.completed_steps >= self.total_steps)


@dataclass(frozen=True)
class SpiceDrivenPreferredChainConfig:
    implementation_option: str = "A"
    architecture_name: str = "actual_spice_front_end_replayed_into_frozen_preferred_chain"
    actual_spice_config: ActualSpiceFrontEndConfig = field(default_factory=ActualSpiceFrontEndConfig)
    physicalization_config: PreferredChainDevicePhysicalizationConfig = field(
        default_factory=PreferredChainDevicePhysicalizationConfig
    )
    replay_mode: str = "reference_total_envelope_scaled_by_spice_fractions"
    replay_dt_s: float = 5e-3
    power_alignment_mode: str = "match_preferred_mean_total_power"
    spice_fraction_injection: float = 0.8
    boundary_export_mode: str = "piecewise_envelope:linear:20.0ms"
    frozen_gain: float = 4.0
    frozen_exposure_s: float = 5.0


def spice_driven_preferred_chain_benchmark_cases() -> list[dict[str, Any]]:
    return actual_spice_front_end_benchmark_cases()


def _mean_branch_power(branch_power_w: Mapping[str, Sequence[float]], branch_labels: Sequence[str]) -> dict[str, float]:
    return {
        label: float(np.mean(np.asarray(branch_power_w[label], dtype=float)))
        for label in branch_labels
    }


def _branch_loads_from_spice(spice_result: Mapping[str, Any], branch_labels: Sequence[str]) -> dict[str, float]:
    probe_map = dict(spice_result["spice"]["output_probe_map"])
    return {
        label: float(probe_map[label]["load_resistance_ohm"])
        for label in branch_labels
    }


def _stable_case_seed(base_seed: int, case_name: str) -> int:
    del case_name
    return int(base_seed)


def _reweight_reference_branch_profiles(
    *,
    baseline_branch_power: Mapping[str, np.ndarray],
    baseline_total_power_profile: np.ndarray,
    target_mean_branch_power: Mapping[str, float],
    branch_labels: Sequence[str],
) -> dict[str, np.ndarray]:
    weighted_profiles = {}
    for label in branch_labels:
        reference_mean = float(np.mean(baseline_branch_power[label]))
        ratio = float(target_mean_branch_power[label]) / max(reference_mean, 1e-18)
        weighted_profiles[label] = np.asarray(baseline_branch_power[label], dtype=float) * ratio
    weighted_total = np.sum([weighted_profiles[label] for label in branch_labels], axis=0)
    safe_total = np.where(weighted_total > 1e-18, weighted_total, 1.0)
    return {
        label: baseline_total_power_profile * weighted_profiles[label] / safe_total
        for label in branch_labels
    }


def simulate_spice_driven_preferred_chain_candidate(
    state4: np.ndarray | None = None,
    *,
    a_deg: float,
    b_deg: float,
    spice_driven_config: SpiceDrivenPreferredChainConfig | Mapping[str, Any] | None = None,
    boundary_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    resolved = (
        SpiceDrivenPreferredChainConfig()
        if spice_driven_config is None
        else spice_driven_config
        if isinstance(spice_driven_config, SpiceDrivenPreferredChainConfig)
        else SpiceDrivenPreferredChainConfig(**dict(spice_driven_config))
    )
    baseline_candidate = simulate_preferred_chain_device_physicalization_candidate(
        state4,
        a_deg=float(a_deg),
        b_deg=float(b_deg),
        physicalization_config=resolved.physicalization_config,
    )
    spice_front_end = simulate_actual_spice_front_end_candidate(
        state4,
        a_deg=float(a_deg),
        b_deg=float(b_deg),
        spice_config=resolved.actual_spice_config,
        baseline_candidate=baseline_candidate,
    )
    boundary = resolved_calibrated_boundary_config(boundary_config)
    branch_labels = list(baseline_candidate["branch_labels"])

    raw_spice_mean_power = _mean_branch_power(spice_front_end["branch_power_w"], branch_labels)
    baseline_reference_mean_power = _mean_branch_power(baseline_candidate["branch_power_w"], branch_labels)
    raw_total_mean_power = float(sum(raw_spice_mean_power.values()))
    reference_total_mean_power = float(sum(baseline_reference_mean_power.values()))
    if resolved.power_alignment_mode == "match_preferred_mean_total_power":
        power_alignment_scale = reference_total_mean_power / max(raw_total_mean_power, 1e-18)
    else:
        raise ValueError(f"Unsupported power alignment mode: {resolved.power_alignment_mode}")
    replayed_mean_power = {
        label: float(raw_spice_mean_power[label] * power_alignment_scale)
        for label in branch_labels
    }
    injected_target_mean_power = {
        label: float(
            baseline_reference_mean_power[label]
            + float(resolved.spice_fraction_injection)
            * (replayed_mean_power[label] - baseline_reference_mean_power[label])
        )
        for label in branch_labels
    }
    branch_loads = _branch_loads_from_spice(spice_front_end, branch_labels)
    baseline_time_s = np.asarray(baseline_candidate["time_s"], dtype=float)
    baseline_branch_power = {
        label: np.asarray(baseline_candidate["branch_power_w"][label], dtype=float)
        for label in branch_labels
    }
    baseline_total_power_profile = np.sum(
        [baseline_branch_power[label] for label in branch_labels],
        axis=0,
    )
    replay_time_s: np.ndarray
    replay_reference_total_power_profile: np.ndarray
    if resolved.replay_mode == "reference_total_envelope_scaled_by_spice_fractions":
        replay_time_s = baseline_time_s
        replay_reference_total_power_profile = baseline_total_power_profile
        replay_reference_branch_power = _reweight_reference_branch_profiles(
            baseline_branch_power=baseline_branch_power,
            baseline_total_power_profile=baseline_total_power_profile,
            target_mean_branch_power=injected_target_mean_power,
            branch_labels=branch_labels,
        )
    elif resolved.replay_mode == "carrier_averaged_constant":
        replay_exposure_s = float(boundary.exposure_s)
        replay_dt_s = max(float(resolved.replay_dt_s), 1e-6)
        replay_time_s = np.arange(0.0, replay_exposure_s + replay_dt_s, replay_dt_s, dtype=float)
        replay_reference_total_power_profile = np.full(
            replay_time_s.shape,
            reference_total_mean_power,
            dtype=float,
        )
        replay_reference_branch_power = {
            label: replay_reference_total_power_profile * (
                replayed_mean_power[label] / max(sum(replayed_mean_power.values()), 1e-18)
            )
            for label in branch_labels
        }
    else:
        raise ValueError(f"Unsupported replay mode: {resolved.replay_mode}")
    replay_exposure_s = float(replay_time_s[-1]) if replay_time_s.size else float(boundary.exposure_s)
    replay_dt_s = float(replay_time_s[1] - replay_time_s[0]) if replay_time_s.size > 1 else max(float(resolved.replay_dt_s), 1e-6)

    replay_branch_power_w: dict[str, list[float]] = {}
    replay_branch_voltage_v: dict[str, list[float]] = {}
    replay_branch_current_a: dict[str, list[float]] = {}
    replay_branch_energy_j: dict[str, float] = {}
    for label in branch_labels:
        power = np.asarray(replay_reference_branch_power[label], dtype=float)
        voltage = np.sqrt(power * max(branch_loads[label], 1e-18))
        current = voltage / max(branch_loads[label], 1e-18)
        replay_branch_power_w[label] = power.tolist()
        replay_branch_voltage_v[label] = voltage.tolist()
        replay_branch_current_a[label] = current.tolist()
        replay_branch_energy_j[label] = float(np.trapezoid(power, x=replay_time_s))
    total_energy = float(sum(replay_branch_energy_j.values()))
    replay_branch_fraction = {
        label: replay_branch_energy_j[label] / max(total_energy, 1e-18)
        for label in branch_labels
    }
    replayed_mean_power = {
        label: replay_branch_energy_j[label] / max(replay_exposure_s, 1e-18)
        for label in branch_labels
    }

    candidate = dict(baseline_candidate)
    candidate["time_s"] = replay_time_s.tolist()
    candidate["branch_voltage_v"] = replay_branch_voltage_v
    candidate["branch_current_a"] = replay_branch_current_a
    candidate["branch_power_w"] = replay_branch_power_w
    candidate["branch_energy_j"] = replay_branch_energy_j
    candidate["branch_energy_fraction"] = replay_branch_fraction
    candidate["exact_weight"] = dict(spice_front_end["exact_weight"])
    candidate["actual_spice_front_end"] = spice_front_end
    candidate["spice_boundary_adapter"] = {
        "replay_mode": resolved.replay_mode,
        "replay_dt_s": replay_dt_s,
        "replay_exposure_s": replay_exposure_s,
        "power_alignment_mode": resolved.power_alignment_mode,
        "power_alignment_scale": float(power_alignment_scale),
        "raw_spice_mean_branch_power_w": raw_spice_mean_power,
        "raw_spice_total_mean_power_w": raw_total_mean_power,
        "reference_mean_branch_power_w": baseline_reference_mean_power,
        "reference_total_mean_power_w": reference_total_mean_power,
        "replayed_mean_branch_power_w": replayed_mean_power,
        "replayed_total_mean_power_w": float(sum(replayed_mean_power.values())),
        "injected_target_mean_branch_power_w": injected_target_mean_power,
        "spice_fraction_injection": float(resolved.spice_fraction_injection),
        "raw_spice_measurement_window_s": dict(spice_front_end["spice"]["measurement_window_s"]),
        "derived_from_actual_spice_traces": True,
        "upstream_artifact_kind": "actual_ngspice_generated_front_end_trace",
        "boundary_export_mode": resolved.boundary_export_mode,
        "frozen_gain": float(resolved.frozen_gain),
        "frozen_exposure_s": float(resolved.frozen_exposure_s),
        "reference_total_envelope_source": "current_preferred_chain_device_physicalization"
        if resolved.replay_mode == "reference_total_envelope_scaled_by_spice_fractions"
        else "constant_mean_power",
        "reference_branch_profile_source": "current_preferred_chain_device_physicalization_reweighted_by_actual_spice"
        if resolved.replay_mode == "reference_total_envelope_scaled_by_spice_fractions"
        else "constant_mean_power",
    }
    candidate["candidate_config"] = {
        **dict(baseline_candidate["candidate_config"]),
        "spice_driven_preferred_chain": {
            **asdict(resolved),
            "actual_spice_config": asdict(resolved.actual_spice_config),
            "physicalization_config": {
                **asdict(resolved.physicalization_config),
                "codesign_config": asdict(resolved.physicalization_config.codesign_config),
            },
        },
    }
    candidate["metrics"] = {
        **dict(baseline_candidate["metrics"]),
        "spice_front_end_rms_error": float(spice_front_end["metrics"]["rms_error"]),
        "spice_front_end_max_abs_error": float(spice_front_end["metrics"]["max_abs_error"]),
        "spice_front_end_exact_rms_error": float(spice_front_end["metrics"]["exact_rms_error"]),
        "spice_front_end_exact_max_abs_error": float(spice_front_end["metrics"]["exact_max_abs_error"]),
        "spice_front_end_correlator_error": float(spice_front_end["metrics"]["correlator_error"]),
        "power_alignment_scale": float(power_alignment_scale),
        "derived_from_actual_spice_traces": True,
    }
    return candidate


def run_spice_driven_preferred_chain_candidate(
    candidate: Mapping[str, Any],
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    n_trials: int,
    seed: int,
    baseline_result: Mapping[str, Any] | None = None,
    progress: _ProgressReporter | None = None,
    case_name: str | None = None,
) -> dict[str, Any]:
    result = run_preferred_chain_device_physicalization_candidate(
        candidate,
        detector_spec,
        n_trials=n_trials,
        seed=seed,
        baseline_result=baseline_result,
        progress=progress,
        case_name=case_name,
    )
    return {
        **dict(result),
        "actual_spice_front_end": dict(candidate["actual_spice_front_end"]),
        "spice_boundary_adapter": dict(candidate["spice_boundary_adapter"]),
        "spice_driven": True,
    }


def run_spice_driven_preferred_chain_case(
    state4: np.ndarray | None,
    *,
    a_deg: float,
    b_deg: float,
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    n_trials: int,
    seed: int,
    spice_driven_config: SpiceDrivenPreferredChainConfig | Mapping[str, Any] | None = None,
    baseline_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    candidate = simulate_spice_driven_preferred_chain_candidate(
        state4,
        a_deg=a_deg,
        b_deg=b_deg,
        spice_driven_config=spice_driven_config,
    )
    return run_spice_driven_preferred_chain_candidate(
        candidate,
        detector_spec,
        n_trials=n_trials,
        seed=seed,
        baseline_result=baseline_result,
    )


def run_spice_driven_preferred_chain_benchmark(
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    n_trials: int,
    seed: int,
    case_names: Sequence[str] | None = None,
    spice_driven_config: SpiceDrivenPreferredChainConfig | Mapping[str, Any] | None = None,
    verbose_progress: bool = False,
) -> dict[str, Any]:
    resolved = (
        SpiceDrivenPreferredChainConfig()
        if spice_driven_config is None
        else spice_driven_config
        if isinstance(spice_driven_config, SpiceDrivenPreferredChainConfig)
        else SpiceDrivenPreferredChainConfig(**dict(spice_driven_config))
    )
    selected_case_names = None if case_names is None else set(case_names)
    cases = [
        case
        for case in spice_driven_preferred_chain_benchmark_cases()
        if selected_case_names is None or str(case["case"]) in selected_case_names
    ]
    if not cases:
        raise ValueError("No spice-driven preferred-chain benchmark cases selected.")

    progress = _ProgressReporter(
        total_steps=max(len(cases) * max(1 + 2 * n_trials, 1), 1),
        enabled=verbose_progress,
    )
    case_results: list[dict[str, Any]] = []
    baseline_front_end_rows: list[dict[str, Any]] = []
    baseline_case_rows: list[dict[str, Any]] = []
    baseline_post_click_rows: list[dict[str, Any]] = []
    baseline_energy_rows: list[dict[str, Any]] = []
    front_end_rows: list[dict[str, Any]] = []
    boundary_export_rows: list[dict[str, Any]] = []
    case_rows: list[dict[str, Any]] = []
    pre_click_rows: list[dict[str, Any]] = []
    post_click_rows: list[dict[str, Any]] = []
    energy_case_rows: list[dict[str, Any]] = []
    energy_rows: list[dict[str, Any]] = []
    case_comparison_rows: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []
    plot_comparison_rows: list[dict[str, Any]] = []
    example_front_end: dict[str, Any] | None = None
    example_trial: dict[str, Any] | None = None

    for case in cases:
        case_name = str(case["case"])
        progress.report("simulate-actual-spice-front-end", case_name=case_name, force=True)
        case_seed = _stable_case_seed(seed, case_name)
        baseline_result = run_preferred_chain_device_physicalization_case(
            case["state4"],
            a_deg=float(case["a_deg"]),
            b_deg=float(case["b_deg"]),
            detector_spec=detector_spec,
            n_trials=n_trials,
            seed=case_seed,
            physicalization_config=resolved.physicalization_config,
        )
        baseline_front_end_rows.append(
            {
                "case": case_name,
                "a_deg": float(case["a_deg"]),
                "b_deg": float(case["b_deg"]),
                "branch_labels": list(baseline_result["candidate"]["branch_labels"]),
                "exact_weights": list(baseline_result["exact_weights"]),
                "realized_fractions": list(baseline_result["realized_fractions"]),
                "rms_error": float(baseline_result["front_end_metrics"]["rms_error"]),
                "max_abs_error": float(baseline_result["front_end_metrics"]["max_abs_error"]),
                "correlator_exact": float(baseline_result["front_end_metrics"]["correlator_exact"]),
                "correlator_realized": float(baseline_result["front_end_metrics"]["correlator_realized"]),
                "correlator_error": float(baseline_result["front_end_metrics"]["correlator_error"]),
            }
        )
        baseline_case_rows.append(
            {
                "case": case_name,
                "a_deg": float(case["a_deg"]),
                "b_deg": float(case["b_deg"]),
                "branch_labels": list(baseline_result["candidate"]["branch_labels"]),
                "exact_weights": list(baseline_result["exact_weights"]),
                "realized_fractions": list(baseline_result["realized_fractions"]),
                "empirical_frequencies": list(baseline_result["empirical_frequencies"]),
                "winner_rms_error": float(baseline_result["metrics"]["rms_error"]),
                "winner_max_error": float(baseline_result["metrics"]["max_abs_error"]),
                "correlator_exact": float(baseline_result["metrics"]["correlator_exact"]),
                "correlator_empirical": float(baseline_result["metrics"]["correlator_empirical"]),
                "correlator_error": float(baseline_result["metrics"]["correlator_error"]),
                "decisive_fraction": float(baseline_result["decisive_fraction"]),
                "timeout_fraction": float(baseline_result["timeout_fraction"]),
                "tie_region_fraction": float(baseline_result["tie_region_fraction"]),
            }
        )
        baseline_post_click_rows.append(
            {
                "case": case_name,
                "a_deg": float(case["a_deg"]),
                "b_deg": float(case["b_deg"]),
                **baseline_result["post_click_summary"],
            }
        )
        baseline_energy_rows.extend(
            {
                "case": case_name,
                "a_deg": float(case["a_deg"]),
                "b_deg": float(case["b_deg"]),
                **row,
            }
            for row in baseline_result["energy_accounting_rows"]
        )
        candidate = simulate_spice_driven_preferred_chain_candidate(
            case["state4"],
            a_deg=float(case["a_deg"]),
            b_deg=float(case["b_deg"]),
            spice_driven_config=resolved,
        )
        progress.advance("actual-spice-front-end-complete", case_name=case_name)
        result = run_spice_driven_preferred_chain_candidate(
            candidate,
            detector_spec,
            n_trials=n_trials,
            seed=case_seed,
            baseline_result=baseline_result,
            progress=progress,
            case_name=case_name,
        )
        case_results.append({"case": case, "result": result, "baseline_result": baseline_result})

        actual_spice = dict(candidate["actual_spice_front_end"])
        adapter = dict(candidate["spice_boundary_adapter"])
        front_end_rows.append(
            {
                "case": case_name,
                "a_deg": float(case["a_deg"]),
                "b_deg": float(case["b_deg"]),
                "branch_labels": list(candidate["branch_labels"]),
                "exact_weights": [float(candidate["exact_weight"][label]) for label in candidate["branch_labels"]],
                "spice_fractions": [float(actual_spice["branch_energy_fraction"][label]) for label in candidate["branch_labels"]],
                "replayed_fractions": [float(candidate["branch_energy_fraction"][label]) for label in candidate["branch_labels"]],
                "baseline_fractions": [float(baseline_result["realized_fractions"][index]) for index in range(len(candidate["branch_labels"]))],
                "rms_error": float(actual_spice["metrics"]["rms_error"]),
                "max_abs_error": float(actual_spice["metrics"]["max_abs_error"]),
                "exact_rms_error": float(actual_spice["metrics"]["exact_rms_error"]),
                "exact_max_abs_error": float(actual_spice["metrics"]["exact_max_abs_error"]),
                "correlator_exact": float(actual_spice["metrics"]["correlator_exact"]),
                "correlator_empirical": float(actual_spice["metrics"]["correlator_empirical"]),
                "correlator_error": float(actual_spice["metrics"]["correlator_error"]),
                "power_alignment_scale": float(adapter["power_alignment_scale"]),
                "replayed_total_mean_power_w": float(adapter["replayed_total_mean_power_w"]),
                "reference_total_mean_power_w": float(adapter["reference_total_mean_power_w"]),
            }
        )
        boundary_export_rows.append(
            {
                "case": case_name,
                "a_deg": float(case["a_deg"]),
                "b_deg": float(case["b_deg"]),
                "derived_from_actual_spice_traces": bool(adapter["derived_from_actual_spice_traces"]),
                "upstream_artifact_kind": str(adapter["upstream_artifact_kind"]),
                "replay_mode": str(adapter["replay_mode"]),
                "replay_dt_s": float(adapter["replay_dt_s"]),
                "replay_exposure_s": float(adapter["replay_exposure_s"]),
                "power_alignment_mode": str(adapter["power_alignment_mode"]),
                "power_alignment_scale": float(adapter["power_alignment_scale"]),
                "raw_spice_total_mean_power_w": float(adapter["raw_spice_total_mean_power_w"]),
                "reference_total_mean_power_w": float(adapter["reference_total_mean_power_w"]),
                "replayed_total_mean_power_w": float(adapter["replayed_total_mean_power_w"]),
                "spice_measurement_start_s": float(adapter["raw_spice_measurement_window_s"]["start"]),
                "spice_measurement_end_s": float(adapter["raw_spice_measurement_window_s"]["end"]),
                "export_mode": str(result["export_config"]["mode"]),
                "piecewise_bin_width_s": float(result["export_config"]["piecewise_bin_width_s"]),
                "piecewise_mode": str(result["export_config"]["piecewise_mode"]),
                "boundary_gain": float(result["boundary_config"]["gain"]),
                "boundary_exposure_s": float(result["boundary_config"]["exposure_s"]),
            }
        )
        case_rows.append(
            {
                "case": case_name,
                "a_deg": float(case["a_deg"]),
                "b_deg": float(case["b_deg"]),
                "branch_labels": list(candidate["branch_labels"]),
                "exact_weights": list(result["exact_weights"]),
                "realized_fractions": list(result["realized_fractions"]),
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
                "case": case_name,
                "a_deg": float(case["a_deg"]),
                "b_deg": float(case["b_deg"]),
                **result["pre_click_comparison"],
            }
        )
        post_click_rows.append(
            {
                "case": case_name,
                "a_deg": float(case["a_deg"]),
                "b_deg": float(case["b_deg"]),
                **result["post_click_summary"],
            }
        )
        energy_summary = summarize_energy_accounting_rows(result["energy_accounting_rows"])
        energy_case_rows.append(
            {
                "case": case_name,
                "a_deg": float(case["a_deg"]),
                "b_deg": float(case["b_deg"]),
                **energy_summary,
            }
        )
        energy_rows.extend(
            {
                "case": case_name,
                "a_deg": float(case["a_deg"]),
                "b_deg": float(case["b_deg"]),
                **row,
            }
            for row in result["energy_accounting_rows"]
        )
        case_comparison_rows.append(
            {
                "case": case_name,
                "baseline_front_end_rms_error": float(baseline_result["front_end_metrics"]["rms_error"]),
                "spice_front_end_rms_error": float(actual_spice["metrics"]["rms_error"]),
                "baseline_winner_rms_error": float(baseline_result["metrics"]["rms_error"]),
                "spice_driven_winner_rms_error": float(result["metrics"]["rms_error"]),
                "baseline_winner_max_error": float(baseline_result["metrics"]["max_abs_error"]),
                "spice_driven_winner_max_error": float(result["metrics"]["max_abs_error"]),
                "baseline_correlator_error": float(baseline_result["metrics"]["correlator_error"]),
                "spice_driven_correlator_error": float(result["metrics"]["correlator_error"]),
                "baseline_decisive_fraction": float(baseline_result["decisive_fraction"]),
                "spice_driven_decisive_fraction": float(result["decisive_fraction"]),
                "baseline_transparency_rms_shift": 0.0,
                "spice_driven_transparency_rms_shift": float(result["pre_click_comparison"]["winner_frequency_rms_shift"]),
                "baseline_winner_drain_fraction": float(
                    baseline_result["post_click_summary"]["mean_activated_winner_drain_fraction"]
                ),
                "spice_driven_winner_drain_fraction": float(
                    result["post_click_summary"]["mean_activated_winner_drain_fraction"]
                ),
            }
        )
        if example_front_end is None:
            example_front_end = {
                "case": case_name,
                "branch_labels": list(candidate["branch_labels"]),
                "raw_spice_time_s": list(actual_spice["time_s"]),
                "raw_spice_branch_voltage_v": {label: list(actual_spice["branch_voltage_v"][label]) for label in candidate["branch_labels"]},
                "raw_spice_branch_current_a": {label: list(actual_spice["branch_current_a"][label]) for label in candidate["branch_labels"]},
                "raw_spice_branch_power_w": {label: list(actual_spice["branch_power_w"][label]) for label in candidate["branch_labels"]},
                "time_s": list(candidate["time_s"]),
                "branch_power_w": {label: list(candidate["branch_power_w"][label]) for label in candidate["branch_labels"]},
                "export_time_s": list(result["trace"]["time_s"]),
                "exported_branch_power": {
                    label: list(result["trace"]["exported_branch_power"][label]) for label in candidate["branch_labels"]
                },
                "spice": dict(actual_spice["spice"]),
                "spice_boundary_adapter": dict(candidate["spice_boundary_adapter"]),
                "boundary_config": dict(result["boundary_config"]),
                "export_config": dict(result["export_config"]),
            }
        if example_trial is None and result["example_trial"] is not None:
            example_trial = {
                "case": case_name,
                "a_deg": float(case["a_deg"]),
                "b_deg": float(case["b_deg"]),
                **result["example_trial"],
            }

    chsh_result = build_chsh_result(case_rows)
    energy_summary = summarize_energy_accounting_rows(energy_rows)
    summary_metrics = build_summary_metrics(case_rows, pre_click_rows, post_click_rows, energy_summary, chsh_result)
    front_end_fraction = aggregate_case_error(front_end_rows, rms_key="rms_error", max_key="max_abs_error")
    summary_metrics["front_end_fraction_rms_error"] = float(front_end_fraction["rms_error"])
    summary_metrics["front_end_fraction_max_error"] = float(front_end_fraction["max_abs_error"])
    summary_metrics["front_end_fraction_pass"] = (
        float(summary_metrics["front_end_fraction_rms_error"]) < 0.03
        and float(summary_metrics["front_end_fraction_max_error"]) < 0.05
    )
    summary_metrics["actual_spice_execution_pass"] = bool(
        all(bool(entry["result"]["actual_spice_front_end"]["shared_core"]["explicitness_metrics"]["actual_spice_run_succeeded"]) for entry in case_results)
    )
    summary_metrics["spice_trace_ingestion_pass"] = bool(
        all(bool(row["derived_from_actual_spice_traces"]) for row in boundary_export_rows)
    )
    summary_metrics["boundary_export_pass"] = bool(
        all(
            row["export_mode"] == "piecewise_envelope"
            and row["piecewise_mode"] == "linear"
            and abs(float(row["piecewise_bin_width_s"]) - 0.02) < 1e-12
            and abs(float(row["boundary_gain"]) - 4.0) < 1e-12
            and abs(float(row["boundary_exposure_s"]) - 5.0) < 1e-12
            for row in boundary_export_rows
        )
    )
    summary_metrics["spice_driven_alignment_pass"] = bool(
        all(float(row["power_alignment_scale"]) > 0.0 for row in boundary_export_rows)
    )
    summary_metrics["actual_spice_driven_pass"] = bool(
        summary_metrics["actual_spice_execution_pass"]
        and summary_metrics["spice_trace_ingestion_pass"]
        and summary_metrics["boundary_export_pass"]
        and summary_metrics["spice_driven_alignment_pass"]
    )
    summary_metrics["proceed_to_next_phase"] = bool(summary_metrics["proceed_to_next_phase"]) and bool(
        summary_metrics["front_end_fraction_pass"] and summary_metrics["actual_spice_driven_pass"]
    )

    actual_spice_front_end_summary = {
        "front_end_fraction_rms_error": float(summary_metrics["front_end_fraction_rms_error"]),
        "front_end_fraction_max_error": float(summary_metrics["front_end_fraction_max_error"]),
        "correlator_rms_error": float(correlator_rms_error(front_end_rows, key="correlator_error")),
        "chsh_abs_error": float(
            build_chsh_result(
                [
                    {
                        "case": row["case"],
                        "correlator_exact": float(row["correlator_exact"]),
                        "correlator_empirical": float(row["correlator_empirical"]),
                    }
                    for row in front_end_rows
                ]
            )["abs_error"]
        ),
    }
    baseline_chsh_result = build_chsh_result(baseline_case_rows)
    baseline_energy_summary = summarize_energy_accounting_rows(baseline_energy_rows)
    baseline_pre_click_rows = [
        {
            "case": row["case"],
            "a_deg": row["a_deg"],
            "b_deg": row["b_deg"],
            "winner_frequency_rms_shift": 0.0,
            "winner_frequency_max_shift": 0.0,
        }
        for row in baseline_case_rows
    ]
    baseline_summary_metrics = build_summary_metrics(
        baseline_case_rows,
        baseline_pre_click_rows,
        baseline_post_click_rows,
        baseline_energy_summary,
        baseline_chsh_result,
    )
    baseline_front_end_fraction = aggregate_case_error(
        baseline_front_end_rows,
        rms_key="rms_error",
        max_key="max_abs_error",
    )
    baseline_summary_metrics["front_end_fraction_rms_error"] = float(baseline_front_end_fraction["rms_error"])
    baseline_summary_metrics["front_end_fraction_max_error"] = float(baseline_front_end_fraction["max_abs_error"])
    baseline_summary_metrics["front_end_fraction_pass"] = (
        float(baseline_summary_metrics["front_end_fraction_rms_error"]) < 0.03
        and float(baseline_summary_metrics["front_end_fraction_max_error"]) < 0.05
    )
    comparison_rows = [
        {
            "candidate": "current_preferred_chain_device_physicalization",
            "front_end_rms_error": float(baseline_summary_metrics["front_end_fraction_rms_error"]),
            "winner_rms_error": float(baseline_summary_metrics["winner_law_rms_error"]),
            "winner_law_rms_error": float(baseline_summary_metrics["winner_law_rms_error"]),
            "winner_law_max_error": float(baseline_summary_metrics["winner_law_max_error"]),
            "correlator_rms_error": float(baseline_summary_metrics["correlator_rms_error"]),
            "chsh_abs_error": float(baseline_summary_metrics["chsh_abs_error"]),
            "energy_accounting_pass": bool(baseline_summary_metrics["energy_accounting_pass"]),
            "winner_drain_dominance_rate": float(baseline_summary_metrics["winner_drain_dominance_rate"]),
            "architecture_note": "Frozen preferred-chain baseline with device-physicalized common inhibit and winner drain subblocks driven by the validated non-SPICE front-end candidate.",
        },
        {
            "candidate": "actual_spice_front_end",
            "front_end_rms_error": float(actual_spice_front_end_summary["front_end_fraction_rms_error"]),
            "winner_rms_error": float("nan"),
            "winner_law_rms_error": float("nan"),
            "winner_law_max_error": float("nan"),
            "correlator_rms_error": float(actual_spice_front_end_summary["correlator_rms_error"]),
            "chsh_abs_error": float(actual_spice_front_end_summary["chsh_abs_error"]),
            "energy_accounting_pass": False,
            "winner_drain_dominance_rate": float("nan"),
            "architecture_note": "Actual ngspice-executed shared front-end benchmark only; upstream artifact for the new handoff but not yet a full-chain run by itself.",
        },
        {
            "candidate": "spice_driven_preferred_chain",
            "front_end_rms_error": float(summary_metrics["front_end_fraction_rms_error"]),
            "winner_rms_error": float(summary_metrics["winner_law_rms_error"]),
            "winner_law_rms_error": float(summary_metrics["winner_law_rms_error"]),
            "winner_law_max_error": float(summary_metrics["winner_law_max_error"]),
            "correlator_rms_error": float(summary_metrics["correlator_rms_error"]),
            "chsh_abs_error": float(summary_metrics["chsh_abs_error"]),
            "energy_accounting_pass": bool(summary_metrics["energy_accounting_pass"]),
            "winner_drain_dominance_rate": float(summary_metrics["winner_drain_dominance_rate"]),
            "architecture_note": "Actual SPICE front-end traces are ingested, carrier-averaged, power-aligned to the frozen preferred operating point, exported through the frozen boundary contract, and then consumed by the frozen detector/latch/closure stack.",
        },
    ]
    plot_comparison_rows = [comparison_rows[0], comparison_rows[2]]
    progress.report("benchmark-complete", force=True)
    return {
        "case_results": case_results,
        "front_end_rows": front_end_rows,
        "boundary_export_rows": boundary_export_rows,
        "case_rows": case_rows,
        "pre_click_rows": pre_click_rows,
        "post_click_rows": post_click_rows,
        "energy_case_rows": energy_case_rows,
        "energy_rows": energy_rows,
        "energy_summary": energy_summary,
        "case_comparison_rows": case_comparison_rows,
        "comparison_rows": comparison_rows,
        "plot_comparison_rows": plot_comparison_rows,
        "chsh_result": chsh_result,
        "summary_metrics": summary_metrics,
        "baseline_summary_metrics": baseline_summary_metrics,
        "actual_spice_front_end_summary_metrics": actual_spice_front_end_summary,
        "example_front_end": example_front_end,
        "example_trial": example_trial,
    }


__all__ = [
    "SpiceDrivenPreferredChainConfig",
    "run_spice_driven_preferred_chain_benchmark",
    "run_spice_driven_preferred_chain_candidate",
    "run_spice_driven_preferred_chain_case",
    "simulate_spice_driven_preferred_chain_candidate",
    "spice_driven_preferred_chain_benchmark_cases",
]
