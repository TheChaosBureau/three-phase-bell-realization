from __future__ import annotations

import sys
import time
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

import numpy as np

from .preferred_chain_device_physicalization import (
    run_preferred_chain_device_physicalization_case,
)
from .spice_driven_preferred_chain import (
    SpiceDrivenPreferredChainConfig,
    run_spice_driven_preferred_chain_summary,
    spice_driven_preferred_chain_benchmark_cases,
)

FRONT_END_TOLERANCES_KEY = "front_end_tolerances"
COUPLING_MISMATCH_KEY = "coupling_mismatch"
LOAD_MISMATCH_KEY = "load_mismatch"
LEAKAGE_VARIATION_KEY = "leakage_variation"
BOUNDARY_VARIATION_KEY = "boundary_variation"
CLOSURE_VARIATION_KEY = "closure_variation"

CLASS_DISPLAY_NAMES = {
    FRONT_END_TOLERANCES_KEY: "Front-End Component Tolerances",
    COUPLING_MISMATCH_KEY: "Coupling Mismatch",
    LOAD_MISMATCH_KEY: "Load Mismatch",
    LEAKAGE_VARIATION_KEY: "Leakage / Parasitic Variation",
    BOUNDARY_VARIATION_KEY: "Detector-Boundary Variation",
    CLOSURE_VARIATION_KEY: "Closure / Drain Strength Variation",
}


@dataclass
class _ProgressReporter:
    total_steps: int
    enabled: bool = False
    label: str = "spice-driven-robustness"
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
class SpiceDrivenRobustnessConfig:
    baseline_spice_driven_config: SpiceDrivenPreferredChainConfig = field(default_factory=SpiceDrivenPreferredChainConfig)
    front_end_tolerance_levels: tuple[float, ...] = (-0.05, -0.02, -0.01, 0.01, 0.02, 0.05)
    coupling_mismatch_levels: tuple[float, ...] = (-0.05, -0.02, -0.01, 0.01, 0.02, 0.05)
    load_mismatch_levels: tuple[float, ...] = (-0.05, -0.02, -0.01, 0.01, 0.02, 0.05)
    leakage_severity_levels: tuple[float, ...] = (0.05, 0.10, 0.20)
    boundary_gains: tuple[float, ...] = (3.5, 4.0, 4.5)
    boundary_exposures_s: tuple[float, ...] = (4.0, 5.0, 6.0)
    closure_variation_levels: tuple[float, ...] = (-0.20, -0.10, 0.10, 0.20)
    decisive_fraction_threshold: float = 0.95


def _stable_case_seed(base_seed: int, case_name: str) -> int:
    del case_name
    return int(base_seed)


def _scale_tuple(values: Sequence[float], factor: float) -> tuple[float, ...]:
    return tuple(float(value) * float(factor) for value in values)


def _pattern_scale_tuple(values: Sequence[float], delta: float, pattern: Sequence[float]) -> tuple[float, ...]:
    return tuple(
        float(value) * (1.0 + float(delta) * float(pattern[index]))
        for index, value in enumerate(values)
    )


def _percent_label(level: float) -> str:
    return f"{level * 100.0:+.1f}%"


def _replace_front_end_config(
    base: SpiceDrivenPreferredChainConfig,
    *,
    front_end_config: Any,
) -> SpiceDrivenPreferredChainConfig:
    codesign_config = replace(base.physicalization_config.codesign_config, front_end_config=front_end_config)
    physicalization_config = replace(base.physicalization_config, codesign_config=codesign_config)
    actual_spice_config = replace(base.actual_spice_config, front_end_config=front_end_config)
    return replace(
        base,
        actual_spice_config=actual_spice_config,
        physicalization_config=physicalization_config,
    )


def _replace_codesign_closure_config(
    base: SpiceDrivenPreferredChainConfig,
    *,
    closure_config: Any,
) -> SpiceDrivenPreferredChainConfig:
    codesign_config = replace(base.physicalization_config.codesign_config, closure_config=closure_config)
    physicalization_config = replace(base.physicalization_config, codesign_config=codesign_config)
    return replace(base, physicalization_config=physicalization_config)


def _front_end_tolerance_point(
    base: SpiceDrivenPreferredChainConfig,
    level: float,
) -> dict[str, Any]:
    factor = 1.0 + float(level)
    front_end = base.actual_spice_config.front_end_config
    perturbed = replace(
        front_end,
        source_resistance_ohm=_scale_tuple(front_end.source_resistance_ohm, factor),
        source_inductance_h=_scale_tuple(front_end.source_inductance_h, factor),
        tank_inductance_h=float(front_end.tank_inductance_h) * factor,
        tank_capacitance_f=float(front_end.tank_capacitance_f) * factor,
        bridge_resistance_ohm=float(front_end.bridge_resistance_ohm) * factor,
        bridge_capacitance_f=float(front_end.bridge_capacitance_f) * factor,
    )
    return {
        "class_key": FRONT_END_TOLERANCES_KEY,
        "class_display": CLASS_DISPLAY_NAMES[FRONT_END_TOLERANCES_KEY],
        "parameter_name": "front_end_rlc_tolerance",
        "level": float(level),
        "severity": abs(float(level)),
        "label": f"front_end_{_percent_label(level)}",
        "boundary_config": None,
        "spice_driven_config": _replace_front_end_config(base, front_end_config=perturbed),
        "notes": "Uniform scaling of explicit front-end R/L/C elements excluding asymmetric load terms.",
    }


def _coupling_mismatch_point(
    base: SpiceDrivenPreferredChainConfig,
    level: float,
) -> dict[str, Any]:
    factor = 1.0 + float(level)
    front_end = base.actual_spice_config.front_end_config
    core_imperfections = replace(
        front_end.core_imperfections,
        coupling_scale=float(front_end.core_imperfections.coupling_scale) * factor,
    )
    perturbed = replace(
        front_end,
        kappa=float(front_end.kappa) * factor,
        side_coupling_capacitance_f=float(front_end.side_coupling_capacitance_f) * factor,
        return_coupling_capacitance_f=float(front_end.return_coupling_capacitance_f) * factor,
        core_imperfections=core_imperfections,
    )
    return {
        "class_key": COUPLING_MISMATCH_KEY,
        "class_display": CLASS_DISPLAY_NAMES[COUPLING_MISMATCH_KEY],
        "parameter_name": "coupling_scale",
        "level": float(level),
        "severity": abs(float(level)),
        "label": f"coupling_{_percent_label(level)}",
        "boundary_config": None,
        "spice_driven_config": _replace_front_end_config(base, front_end_config=perturbed),
        "notes": "Shared-core and inter-branch coupling terms shifted together around the frozen baseline.",
    }


def _load_mismatch_point(
    base: SpiceDrivenPreferredChainConfig,
    level: float,
) -> dict[str, Any]:
    front_end = base.actual_spice_config.front_end_config
    pattern = (1.0, -1.0, -1.0, 1.0)
    perturbed = replace(
        front_end,
        load_resistance_ohm=_pattern_scale_tuple(front_end.load_resistance_ohm, float(level), pattern),
        readout_shunt_capacitance_f=_pattern_scale_tuple(front_end.readout_shunt_capacitance_f, -float(level), pattern),
    )
    return {
        "class_key": LOAD_MISMATCH_KEY,
        "class_display": CLASS_DISPLAY_NAMES[LOAD_MISMATCH_KEY],
        "parameter_name": "asymmetric_load_mismatch",
        "level": float(level),
        "severity": abs(float(level)),
        "label": f"load_{_percent_label(level)}",
        "boundary_config": None,
        "spice_driven_config": _replace_front_end_config(base, front_end_config=perturbed),
        "notes": "Asymmetric branch loading mismatch on resistive readout loads and shunt caps.",
    }


def _leakage_variation_point(
    base: SpiceDrivenPreferredChainConfig,
    severity: float,
) -> dict[str, Any]:
    front_end = base.actual_spice_config.front_end_config
    leak_factor = 1.0 + float(severity)
    cross_coupling = float(front_end.readout_cross_coupling) + 0.03 * float(severity) / 0.20
    perturbed = replace(
        front_end,
        internal_loss_resistance_ohm=_scale_tuple(front_end.internal_loss_resistance_ohm, 1.0 / leak_factor),
        readout_cross_coupling=float(cross_coupling),
    )
    return {
        "class_key": LEAKAGE_VARIATION_KEY,
        "class_display": CLASS_DISPLAY_NAMES[LEAKAGE_VARIATION_KEY],
        "parameter_name": "leakage_parasitic_severity",
        "level": float(severity),
        "severity": float(severity),
        "label": f"leakage_{severity * 100.0:.1f}%",
        "boundary_config": None,
        "spice_driven_config": _replace_front_end_config(base, front_end_config=perturbed),
        "notes": "Increased internal loss plus readout parasitic cross-coupling relative to the frozen front-end.",
    }


def _boundary_variation_point(
    base: SpiceDrivenPreferredChainConfig,
    *,
    gain: float,
    exposure_s: float,
) -> dict[str, Any]:
    severity = max(abs(float(gain) - 4.0) / 4.0, abs(float(exposure_s) - 5.0) / 5.0)
    return {
        "class_key": BOUNDARY_VARIATION_KEY,
        "class_display": CLASS_DISPLAY_NAMES[BOUNDARY_VARIATION_KEY],
        "parameter_name": "boundary_gain_exposure",
        "level": float(severity),
        "severity": float(severity),
        "label": f"gain_{gain:.1f}x_exposure_{exposure_s:.1f}s",
        "boundary_config": {"gain": float(gain), "exposure_s": float(exposure_s)},
        "spice_driven_config": base,
        "gain": float(gain),
        "exposure_s": float(exposure_s),
        "notes": "Local frozen-boundary sweep around the validated nominal gain and exposure.",
    }


def _closure_variation_points(
    base: SpiceDrivenPreferredChainConfig,
    level: float,
) -> list[dict[str, Any]]:
    factor = 1.0 + float(level)
    physicalization = base.physicalization_config
    closure = physicalization.codesign_config.closure_config
    points: list[dict[str, Any]] = []

    inhibit_config = replace(
        physicalization,
        sense_resistance_ohm=float(physicalization.sense_resistance_ohm) * factor,
        inhibit_charge_resistance_ohm=float(physicalization.inhibit_charge_resistance_ohm) * factor,
        gate_driver_resistance_ohm=float(physicalization.gate_driver_resistance_ohm) * factor,
    )
    points.append(
        {
            "class_key": CLOSURE_VARIATION_KEY,
            "class_display": CLASS_DISPLAY_NAMES[CLOSURE_VARIATION_KEY],
            "parameter_name": "inhibit_rise_tau",
            "level": float(level),
            "severity": abs(float(level)),
            "label": f"inhibit_rise_{_percent_label(level)}",
            "boundary_config": None,
            "spice_driven_config": replace(base, physicalization_config=inhibit_config),
            "notes": "Local variation of the sense/store/gate RC rise constants without re-optimization.",
        }
    )

    winner_strength = max(factor, 1e-6)
    winner_config = replace(
        physicalization,
        switch_on_resistance_ohm=float(physicalization.switch_on_resistance_ohm) / winner_strength,
        drain_dump_resistance_ohm=float(physicalization.drain_dump_resistance_ohm) / winner_strength,
    )
    points.append(
        {
            "class_key": CLOSURE_VARIATION_KEY,
            "class_display": CLASS_DISPLAY_NAMES[CLOSURE_VARIATION_KEY],
            "parameter_name": "winner_drain_strength",
            "level": float(level),
            "severity": abs(float(level)),
            "label": f"winner_drain_{_percent_label(level)}",
            "boundary_config": None,
            "spice_driven_config": replace(base, physicalization_config=winner_config),
            "notes": "Winner-drain channel and dump-path strength variation around the tuned nominal.",
        }
    )

    clamp_strength = max(factor, 1e-6)
    clamp_closure = replace(
        closure,
        clamp_resistance_ohm=float(closure.clamp_resistance_ohm) / clamp_strength,
        clamp_coupling_strength=float(closure.clamp_coupling_strength) * clamp_strength,
    )
    clamp_config = _replace_codesign_closure_config(base, closure_config=clamp_closure)
    points.append(
        {
            "class_key": CLOSURE_VARIATION_KEY,
            "class_display": CLASS_DISPLAY_NAMES[CLOSURE_VARIATION_KEY],
            "parameter_name": "loser_clamp_strength",
            "level": float(level),
            "severity": abs(float(level)),
            "label": f"loser_clamp_{_percent_label(level)}",
            "boundary_config": None,
            "spice_driven_config": clamp_config,
            "notes": "Loser-clamp resistance/coupling strength variation around the tuned nominal.",
        }
    )
    return points


def spice_driven_robustness_points(
    robustness_config: SpiceDrivenRobustnessConfig | Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    resolved = (
        SpiceDrivenRobustnessConfig()
        if robustness_config is None
        else robustness_config
        if isinstance(robustness_config, SpiceDrivenRobustnessConfig)
        else SpiceDrivenRobustnessConfig(**dict(robustness_config))
    )
    base = resolved.baseline_spice_driven_config
    points: list[dict[str, Any]] = []
    points.extend(_front_end_tolerance_point(base, level) for level in resolved.front_end_tolerance_levels)
    points.extend(_coupling_mismatch_point(base, level) for level in resolved.coupling_mismatch_levels)
    points.extend(_load_mismatch_point(base, level) for level in resolved.load_mismatch_levels)
    points.extend(_leakage_variation_point(base, severity) for severity in resolved.leakage_severity_levels)
    points.extend(
        _boundary_variation_point(base, gain=gain, exposure_s=exposure_s)
        for gain in resolved.boundary_gains
        for exposure_s in resolved.boundary_exposures_s
    )
    for level in resolved.closure_variation_levels:
        points.extend(_closure_variation_points(base, level))
    return points


def _boundary_valid(boundary_rows: Sequence[Mapping[str, Any]]) -> bool:
    return bool(
        boundary_rows
        and all(
            row["export_mode"] == "piecewise_envelope"
            and row["piecewise_mode"] == "linear"
            and abs(float(row["piecewise_bin_width_s"]) - 0.02) < 1e-12
            and float(row["boundary_gain"]) > 0.0
            and float(row["boundary_exposure_s"]) > 0.0
            for row in boundary_rows
        )
    )


def _damage_score(metrics: Mapping[str, Any], *, decisive_fraction_threshold: float) -> float:
    return float(
        max(
            float(metrics["winner_law_rms_error"]) / 0.03,
            float(metrics["winner_law_max_error"]) / 0.05,
            float(metrics["correlator_rms_error"]) / 0.05,
            float(metrics["chsh_abs_error"]) / 0.10,
            float(metrics["pre_click_transparency_rms_shift"]) / 0.01,
            float(metrics["pre_click_transparency_max_shift"]) / 0.01,
            float(decisive_fraction_threshold) / max(float(metrics["mean_decisive_fraction"]), 1e-12),
            0.99 / max(float(metrics["winner_drain_dominance_rate"]), 1e-12),
            float(metrics["mean_loser_fraction_of_post_click"]) / 0.05,
            0.90 / max(float(metrics["completion_rate"]), 1e-12),
            float(metrics["max_energy_balance_abs_fraction"]) / 1e-6,
        )
    )


def _robustness_pass(
    metrics: Mapping[str, Any],
    *,
    boundary_valid_pass: bool,
    decisive_fraction_threshold: float,
) -> bool:
    return bool(
        metrics["winner_law_pass"]
        and metrics["correlator_pass"]
        and metrics["chsh_pass"]
        and metrics["pre_click_transparency_pass"]
        and metrics["winner_drain_dominance_pass"]
        and metrics["loser_residual_pass"]
        and metrics["monotonic_shared_energy_decay_pass"]
        and metrics["completion_pass"]
        and metrics["energy_accounting_pass"]
        and metrics["front_end_fraction_pass"]
        and metrics["actual_spice_execution_pass"]
        and metrics["spice_trace_ingestion_pass"]
        and metrics["spice_driven_alignment_pass"]
        and boundary_valid_pass
        and float(metrics["mean_decisive_fraction"]) >= float(decisive_fraction_threshold)
    )


def _build_frozen_baseline_case_map(
    *,
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    n_trials: int,
    seed: int,
    case_names: Sequence[str] | None,
    spice_driven_config: SpiceDrivenPreferredChainConfig,
    compact: bool = False,
) -> dict[str, dict[str, Any]]:
    selected_case_names = None if case_names is None else set(case_names)
    case_map: dict[str, dict[str, Any]] = {}
    for case in spice_driven_preferred_chain_benchmark_cases():
        case_name = str(case["case"])
        if selected_case_names is not None and case_name not in selected_case_names:
            continue
        result = run_preferred_chain_device_physicalization_case(
            case["state4"],
            a_deg=float(case["a_deg"]),
            b_deg=float(case["b_deg"]),
            detector_spec=detector_spec,
            n_trials=n_trials,
            seed=_stable_case_seed(seed, case_name),
            physicalization_config=spice_driven_config.physicalization_config,
        )
        case_map[case_name] = (
            {
                "empirical_frequencies": list(result["empirical_frequencies"]),
                "decisive_fraction": float(result["decisive_fraction"]),
                "timeout_fraction": float(result["timeout_fraction"]),
            }
            if compact
            else result
        )
    return case_map


def _metric_delta_rows(
    baseline_metrics: Mapping[str, Any],
    metrics: Mapping[str, Any],
) -> dict[str, float]:
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
    return {
        f"{key}_delta": float(metrics[key]) - float(baseline_metrics[key])
        for key in keys
    }


def _class_rows_from_points(
    perturbation_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in perturbation_rows:
        grouped[str(row["class_key"])].append(row)
    rows: list[dict[str, Any]] = []
    for class_key, class_rows in grouped.items():
        worst_row = max(class_rows, key=lambda row: (float(row["damage_score"]), float(row["severity"])))
        pass_count = sum(bool(row["robustness_pass"]) for row in class_rows)
        rows.append(
            {
                "class_key": class_key,
                "class_display": CLASS_DISPLAY_NAMES[class_key],
                "configuration_count": len(class_rows),
                "pass_count": int(pass_count),
                "pass_rate": float(pass_count / max(len(class_rows), 1)),
                "worst_damage_score": float(max(float(row["damage_score"]) for row in class_rows)),
                "mean_damage_score": float(np.mean([float(row["damage_score"]) for row in class_rows])),
                "worst_configuration": str(worst_row["label"]),
                "worst_parameter_name": str(worst_row["parameter_name"]),
                "worst_severity": float(worst_row["severity"]),
                "worst_winner_law_rms_error": float(worst_row["winner_law_rms_error"]),
                "worst_pre_click_transparency_max_shift": float(worst_row["pre_click_transparency_max_shift"]),
                "worst_chsh_abs_error": float(worst_row["chsh_abs_error"]),
            }
        )
    return rows


def _sensitivity_ranking_rows(class_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(
        class_rows,
        key=lambda row: (
            -float(row["worst_damage_score"]),
            float(row["pass_rate"]),
            -float(row["mean_damage_score"]),
        ),
    )
    return [
        {
            "rank": index + 1,
            **dict(row),
        }
        for index, row in enumerate(ordered)
    ]


def _safe_window_rows(perturbation_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in perturbation_rows:
        grouped[(str(row["class_key"]), str(row["parameter_name"]))].append(row)

    safe_rows: list[dict[str, Any]] = []
    for (class_key, parameter_name), rows in grouped.items():
        passing = [row for row in rows if bool(row["robustness_pass"])]
        if class_key == BOUNDARY_VARIATION_KEY:
            gains = [float(row["gain"]) for row in passing]
            exposures = [float(row["exposure_s"]) for row in passing]
            safe_rows.append(
                {
                    "class_key": class_key,
                    "class_display": CLASS_DISPLAY_NAMES[class_key],
                    "parameter_name": parameter_name,
                    "pass_count": len(passing),
                    "configuration_count": len(rows),
                    "safe_min_gain": float(min(gains)) if gains else float("nan"),
                    "safe_max_gain": float(max(gains)) if gains else float("nan"),
                    "safe_min_exposure_s": float(min(exposures)) if exposures else float("nan"),
                    "safe_max_exposure_s": float(max(exposures)) if exposures else float("nan"),
                    "safe_window_label": (
                        f"gain [{min(gains):.1f}, {max(gains):.1f}] x, exposure [{min(exposures):.1f}, {max(exposures):.1f}] s"
                        if gains and exposures
                        else "no passing operating window"
                    ),
                }
            )
            continue

        levels = [float(row["level"]) for row in passing]
        safe_rows.append(
            {
                "class_key": class_key,
                "class_display": CLASS_DISPLAY_NAMES[class_key],
                "parameter_name": parameter_name,
                "pass_count": len(passing),
                "configuration_count": len(rows),
                "safe_min_level": float(min(levels)) if levels else float("nan"),
                "safe_max_level": float(max(levels)) if levels else float("nan"),
                "safe_window_label": (
                    f"level [{min(levels):+.3f}, {max(levels):+.3f}]"
                    if levels
                    else "no passing operating window"
                ),
            }
        )
    return safe_rows


def run_spice_driven_robustness_sweep(
    detector_spec: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    n_trials: int,
    seed: int,
    case_names: Sequence[str] | None = None,
    robustness_config: SpiceDrivenRobustnessConfig | Mapping[str, Any] | None = None,
    verbose_progress: bool = False,
) -> dict[str, Any]:
    resolved = (
        SpiceDrivenRobustnessConfig()
        if robustness_config is None
        else robustness_config
        if isinstance(robustness_config, SpiceDrivenRobustnessConfig)
        else SpiceDrivenRobustnessConfig(**dict(robustness_config))
    )
    perturbation_points = spice_driven_robustness_points(resolved)
    progress = _ProgressReporter(total_steps=max(len(perturbation_points) + 1, 1), enabled=verbose_progress)

    baseline_case_map = _build_frozen_baseline_case_map(
        detector_spec=detector_spec,
        n_trials=n_trials,
        seed=seed,
        case_names=case_names,
        spice_driven_config=resolved.baseline_spice_driven_config,
        compact=True,
    )
    baseline_summary = run_spice_driven_preferred_chain_summary(
        detector_spec,
        n_trials=n_trials,
        seed=seed,
        case_names=case_names,
        spice_driven_config=resolved.baseline_spice_driven_config,
        baseline_case_map=baseline_case_map,
        verbose_progress=False,
    )
    progress.advance("baseline-complete")

    perturbation_rows: list[dict[str, Any]] = []
    class_case_rows: list[dict[str, Any]] = []
    for point in perturbation_points:
        summary = run_spice_driven_preferred_chain_summary(
            detector_spec,
            n_trials=n_trials,
            seed=seed,
            case_names=case_names,
            spice_driven_config=point["spice_driven_config"],
            boundary_config=point["boundary_config"],
            baseline_case_map=baseline_case_map,
            verbose_progress=False,
        )
        metrics = summary["summary_metrics"]
        boundary_valid_pass = _boundary_valid(summary["boundary_export_rows"])
        row = {
            "class_key": str(point["class_key"]),
            "class_display": str(point["class_display"]),
            "parameter_name": str(point["parameter_name"]),
            "label": str(point["label"]),
            "level": float(point["level"]),
            "severity": float(point["severity"]),
            "notes": str(point["notes"]),
            "gain": float(point.get("gain", float("nan"))),
            "exposure_s": float(point.get("exposure_s", float("nan"))),
            **{key: float(metrics[key]) if isinstance(metrics[key], (int, float, np.floating)) else bool(metrics[key]) for key in (
                "winner_law_rms_error",
                "winner_law_max_error",
                "correlator_rms_error",
                "chsh_abs_error",
                "mean_decisive_fraction",
                "pre_click_transparency_rms_shift",
                "pre_click_transparency_max_shift",
                "winner_drain_dominance_rate",
                "mean_loser_fraction_of_post_click",
                "completion_rate",
                "max_energy_balance_abs_fraction",
                "front_end_fraction_rms_error",
                "front_end_fraction_max_error",
            )},
            "winner_law_pass": bool(metrics["winner_law_pass"]),
            "correlator_pass": bool(metrics["correlator_pass"]),
            "chsh_pass": bool(metrics["chsh_pass"]),
            "pre_click_transparency_pass": bool(metrics["pre_click_transparency_pass"]),
            "winner_drain_dominance_pass": bool(metrics["winner_drain_dominance_pass"]),
            "loser_residual_pass": bool(metrics["loser_residual_pass"]),
            "monotonic_shared_energy_decay_pass": bool(metrics["monotonic_shared_energy_decay_pass"]),
            "completion_pass": bool(metrics["completion_pass"]),
            "energy_accounting_pass": bool(metrics["energy_accounting_pass"]),
            "front_end_fraction_pass": bool(metrics["front_end_fraction_pass"]),
            "actual_spice_execution_pass": bool(metrics["actual_spice_execution_pass"]),
            "spice_trace_ingestion_pass": bool(metrics["spice_trace_ingestion_pass"]),
            "spice_driven_alignment_pass": bool(metrics["spice_driven_alignment_pass"]),
            "boundary_valid_pass": bool(boundary_valid_pass),
            "damage_score": _damage_score(metrics, decisive_fraction_threshold=resolved.decisive_fraction_threshold),
            "robustness_pass": _robustness_pass(
                metrics,
                boundary_valid_pass=boundary_valid_pass,
                decisive_fraction_threshold=resolved.decisive_fraction_threshold,
            ),
            **_metric_delta_rows(baseline_summary["summary_metrics"], metrics),
        }
        perturbation_rows.append(row)

        for case_row in summary["case_rows"]:
            class_case_rows.append(
                {
                    "class_key": str(point["class_key"]),
                    "parameter_name": str(point["parameter_name"]),
                    "label": str(point["label"]),
                    "case": str(case_row["case"]),
                    "winner_rms_error": float(case_row["winner_rms_error"]),
                    "winner_max_error": float(case_row["winner_max_error"]),
                    "correlator_error": float(case_row["correlator_error"]),
                    "decisive_fraction": float(case_row["decisive_fraction"]),
                }
            )
        progress.advance("perturbation-complete", case_name=str(point["label"]))

    class_rows = _class_rows_from_points(perturbation_rows)
    ranking_rows = _sensitivity_ranking_rows(class_rows)
    safe_window_rows = _safe_window_rows(perturbation_rows)
    passing_rows = [row for row in perturbation_rows if bool(row["robustness_pass"])]
    summary_metrics = {
        "n_trials": int(n_trials),
        "seed": int(seed),
        "baseline_winner_law_rms_error": float(baseline_summary["summary_metrics"]["winner_law_rms_error"]),
        "baseline_correlator_rms_error": float(baseline_summary["summary_metrics"]["correlator_rms_error"]),
        "baseline_chsh_abs_error": float(baseline_summary["summary_metrics"]["chsh_abs_error"]),
        "baseline_pre_click_transparency_rms_shift": float(
            baseline_summary["summary_metrics"]["pre_click_transparency_rms_shift"]
        ),
        "configuration_count": int(len(perturbation_rows)),
        "passing_configuration_count": int(len(passing_rows)),
        "pass_rate": float(len(passing_rows) / max(len(perturbation_rows), 1)),
        "class_count": int(len(class_rows)),
        "classes_with_passing_window": int(sum(row["pass_count"] > 0 for row in class_rows)),
        "most_dangerous_class": str(ranking_rows[0]["class_key"]) if ranking_rows else "",
        "most_dangerous_configuration": str(
            max(perturbation_rows, key=lambda row: float(row["damage_score"]))["label"]
        )
        if perturbation_rows
        else "",
        "worst_damage_score": float(max(float(row["damage_score"]) for row in perturbation_rows)) if perturbation_rows else 0.0,
        "mean_damage_score": float(np.mean([float(row["damage_score"]) for row in perturbation_rows])) if perturbation_rows else 0.0,
        "safe_window_available": bool(any(row["pass_count"] > 0 for row in safe_window_rows)),
        "decisive_fraction_threshold": float(resolved.decisive_fraction_threshold),
    }
    return {
        "baseline_summary": baseline_summary,
        "baseline_summary_metrics": baseline_summary["summary_metrics"],
        "perturbation_rows": perturbation_rows,
        "class_rows": class_rows,
        "class_case_rows": class_case_rows,
        "sensitivity_ranking_rows": ranking_rows,
        "safe_window_rows": safe_window_rows,
        "summary_metrics": summary_metrics,
    }


__all__ = [
    "BOUNDARY_VARIATION_KEY",
    "CLASS_DISPLAY_NAMES",
    "CLOSURE_VARIATION_KEY",
    "COUPLING_MISMATCH_KEY",
    "FRONT_END_TOLERANCES_KEY",
    "LEAKAGE_VARIATION_KEY",
    "LOAD_MISMATCH_KEY",
    "SpiceDrivenRobustnessConfig",
    "run_spice_driven_robustness_sweep",
    "spice_driven_robustness_points",
]
