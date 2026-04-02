from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from detector_rig.config import DetectorRigConfig
from detector_search.sim.metrics import fit_rate_vs_power, race_error_metric


@dataclass(frozen=True)
class DetectorCell:
    """Parameterized rare-event detector cell used by the virtual bench rig."""

    name: str
    bias_v: float
    alpha_hz_per_uw: float
    lambda_dark_hz: float
    dead_time_us: float
    reset_recovery_us: float
    pulse_amplitude_v: float
    pulse_width_ns: float
    pulse_rise_ns: float
    pulse_fall_ns: float
    timing_jitter_ns: float
    double_pulse_rate: float
    gain_trim: float = 1.0
    dark_trim: float = 1.0
    pulse_trim: float = 1.0
    timing_offset_ns: float = 0.0
    absorber_ohm: float = 50.0


def _logistic(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def _power_to_rate(alpha_hz_per_uw: float, lambda_dark_hz: float, power_uw: float) -> float:
    return max(lambda_dark_hz + alpha_hz_per_uw * max(power_uw, 0.0), 0.0)


def click_rate(cell: DetectorCell, power_uw: float) -> float:
    return _power_to_rate(cell.alpha_hz_per_uw, cell.lambda_dark_hz, power_uw)


def build_cell_candidate(
    name: str,
    bias_v: float,
    *,
    gain_trim: float = 1.0,
    dark_trim: float = 1.0,
    pulse_trim: float = 1.0,
    timing_offset_ns: float = 0.0,
) -> DetectorCell:
    """
    Map one bias point into a rare-event cell contract.

    The mapping is intentionally simple: higher bias raises both signal gain and
    dark rate, producing quiet, rare-event, and unstable regions across the scan.
    """
    slope = _logistic((bias_v - 2.75) / 0.025)
    alpha_hz_per_uw = 1.95 * (0.16 + 0.84 * slope) * gain_trim
    lambda_dark_hz = 0.01 * math.exp((bias_v - 2.70) / 0.024) * dark_trim
    dead_time_us = 1.7 + 2.4 * slope
    reset_recovery_us = dead_time_us + 0.9 + 0.25 * slope
    pulse_amplitude_v = 1.05 * pulse_trim
    pulse_width_ns = 11.5 + 5.0 * slope
    pulse_rise_ns = 1.7 + 0.55 * slope
    pulse_fall_ns = 2.6 + 0.7 * slope
    timing_jitter_ns = 0.22 + 0.18 * (1.0 - slope)
    double_pulse_rate = 0.0015 + 0.02 * max(bias_v - 2.84, 0.0) / 0.06
    return DetectorCell(
        name=name,
        bias_v=bias_v,
        alpha_hz_per_uw=alpha_hz_per_uw,
        lambda_dark_hz=lambda_dark_hz,
        dead_time_us=dead_time_us,
        reset_recovery_us=reset_recovery_us,
        pulse_amplitude_v=pulse_amplitude_v,
        pulse_width_ns=pulse_width_ns,
        pulse_rise_ns=pulse_rise_ns,
        pulse_fall_ns=pulse_fall_ns,
        timing_jitter_ns=timing_jitter_ns,
        double_pulse_rate=double_pulse_rate,
        gain_trim=gain_trim,
        dark_trim=dark_trim,
        pulse_trim=pulse_trim,
        timing_offset_ns=timing_offset_ns,
    )


def classify_operating_regime(cell: DetectorCell, nominal_power_uw: float) -> str:
    signal_rate_hz = click_rate(cell, nominal_power_uw)
    dark_fraction = cell.lambda_dark_hz / max(signal_rate_hz, 1e-12)
    if cell.lambda_dark_hz > 3.0 or cell.double_pulse_rate > 0.01:
        return "unstable"
    if signal_rate_hz < 10.0 or dark_fraction > 0.06:
        return "quiet"
    return "rare_event"


def summarize_bias_sweep(config: DetectorRigConfig) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bias_v in config.bias_scan_volts:
        cell = build_cell_candidate("cell_a", bias_v)
        signal_rate_hz = click_rate(cell, config.nominal_power_uw)
        dark_fraction = cell.lambda_dark_hz / max(signal_rate_hz, 1e-12)
        rows.append(
            {
                "bias_v": bias_v,
                "lambda_dark_hz": cell.lambda_dark_hz,
                "alpha_hz_per_uw": cell.alpha_hz_per_uw,
                "signal_rate_hz_at_nominal_power": signal_rate_hz,
                "dark_fraction_at_nominal_power": dark_fraction,
                "double_pulse_rate": cell.double_pulse_rate,
                "regime": classify_operating_regime(cell, config.nominal_power_uw),
            }
        )
    return rows


def select_operating_point(config: DetectorRigConfig) -> dict[str, Any]:
    rows = summarize_bias_sweep(config)
    candidates = [row for row in rows if row["regime"] == "rare_event"]
    if not candidates:
        raise ValueError("No rare-event operating point found in bias scan.")
    return min(
        candidates,
        key=lambda row: (
            abs(float(row["signal_rate_hz_at_nominal_power"]) - config.operating_target_signal_rate_hz),
            float(row["dark_fraction_at_nominal_power"]),
            float(row["double_pulse_rate"]),
        ),
    )


def build_single_cell_candidate(config: DetectorRigConfig) -> DetectorCell:
    operating_point = select_operating_point(config)
    return build_cell_candidate("cell_a", float(operating_point["bias_v"]))


def build_matched_cell_pair(config: DetectorRigConfig) -> tuple[DetectorCell, DetectorCell]:
    cell_a = build_single_cell_candidate(config)
    cell_b = build_cell_candidate(
        "cell_b",
        cell_a.bias_v,
        gain_trim=1.003,
        dark_trim=1.05,
        pulse_trim=0.992,
        timing_offset_ns=0.08,
    )
    return cell_a, cell_b


def simulate_dark_counts(
    cell: DetectorCell,
    *,
    window_s: float,
    n_windows: int,
    seed: int,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    counts = rng.poisson(cell.lambda_dark_hz * window_s, size=n_windows)
    rows: list[dict[str, Any]] = []
    for index, count in enumerate(counts, start=1):
        rows.append(
            {
                "window_index": index,
                "window_s": window_s,
                "count": int(count),
                "estimated_rate_hz": float(count) / window_s,
            }
        )
    rates = counts.astype(float) / window_s
    mean_rate = float(np.mean(rates))
    std_rate = float(np.std(rates, ddof=1)) if rates.size > 1 else 0.0
    mean_count = float(np.mean(counts))
    variance_count = float(np.var(counts, ddof=1)) if counts.size > 1 else 0.0
    return {
        "rows": rows,
        "mean_rate_hz": mean_rate,
        "std_rate_hz": std_rate,
        "fano_factor": variance_count / max(mean_count, 1e-12),
    }


def simulate_rate_scan(
    cell: DetectorCell,
    *,
    powers_uw: tuple[float, ...],
    window_s: float,
    repeats: int,
    seed: int,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    measured_rates: list[float] = []
    for power_uw in powers_uw:
        true_rate_hz = click_rate(cell, power_uw)
        counts = rng.poisson(true_rate_hz * window_s, size=repeats)
        observed_rate_hz = float(np.mean(counts) / window_s)
        rate_std_hz = float(np.std(counts / window_s, ddof=1)) if repeats > 1 else 0.0
        measured_rates.append(observed_rate_hz)
        rows.append(
            {
                "power_uw": float(power_uw),
                "window_s": window_s,
                "repeats": repeats,
                "observed_rate_hz": observed_rate_hz,
                "true_rate_hz": true_rate_hz,
                "rate_std_hz": rate_std_hz,
                "total_clicks": int(np.sum(counts)),
            }
        )

    fit = fit_rate_vs_power(powers_uw, measured_rates)
    for row, fit_value, residual, rel_residual in zip(
        rows,
        fit["fit_values"],
        fit["residuals"],
        fit["relative_residuals"],
        strict=True,
    ):
        row["fit_rate_hz"] = float(fit_value)
        row["residual_hz"] = float(residual)
        row["relative_residual"] = float(rel_residual)
    return {"rows": rows, "fit": fit}


def _pulse_waveform(
    time_axis_ns: np.ndarray,
    onset_ns: float,
    amplitude_v: float,
    rise_ns: float,
    width_ns: float,
    fall_ns: float,
) -> np.ndarray:
    shifted = time_axis_ns - onset_ns
    rising = np.where(shifted >= 0.0, amplitude_v * (1.0 - np.exp(-shifted / max(rise_ns, 1e-6))), 0.0)
    held = np.where(shifted <= width_ns, rising, amplitude_v)
    decaying = np.where(
        shifted > width_ns,
        amplitude_v * np.exp(-(shifted - width_ns) / max(fall_ns, 1e-6)),
        held,
    )
    return decaying


def simulate_pulses(
    cell: DetectorCell,
    *,
    n_events: int,
    window_ns: float,
    dt_ns: float,
    seed: int,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    time_axis_ns = np.arange(0.0, window_ns + dt_ns, dt_ns, dtype=float)
    rows: list[dict[str, Any]] = []
    waveforms: list[np.ndarray] = []

    for event_index in range(1, n_events + 1):
        amplitude_v = float(rng.normal(cell.pulse_amplitude_v, 0.02 * cell.pulse_amplitude_v))
        rise_ns = max(float(rng.normal(cell.pulse_rise_ns, 0.08)), 0.5)
        width_ns = max(float(rng.normal(cell.pulse_width_ns, 0.35)), rise_ns)
        fall_ns = max(float(rng.normal(cell.pulse_fall_ns, 0.10)), 0.6)
        latency_ns = float(rng.normal(cell.timing_offset_ns, cell.timing_jitter_ns))
        onset_ns = 4.5 + latency_ns
        double_pulse = bool(rng.random() < cell.double_pulse_rate)

        waveform = _pulse_waveform(time_axis_ns, onset_ns, amplitude_v, rise_ns, width_ns, fall_ns)
        if double_pulse:
            second_delay_ns = float(rng.uniform(3.5, 6.0))
            waveform += 0.42 * _pulse_waveform(
                time_axis_ns,
                onset_ns + second_delay_ns,
                amplitude_v,
                rise_ns,
                0.55 * width_ns,
                fall_ns,
            )

        waveforms.append(waveform)
        rows.append(
            {
                "event_index": event_index,
                "amplitude_v": amplitude_v,
                "rise_time_ns": rise_ns,
                "width_ns": width_ns,
                "fall_time_ns": fall_ns,
                "latency_ns": latency_ns,
                "double_pulse": int(double_pulse),
            }
        )

    waveform_matrix = np.asarray(waveforms, dtype=float)
    amplitude_values = waveform_matrix.max(axis=1)
    width_values = np.asarray([row["width_ns"] for row in rows], dtype=float)
    rise_values = np.asarray([row["rise_time_ns"] for row in rows], dtype=float)
    latency_values = np.asarray([row["latency_ns"] for row in rows], dtype=float)
    double_rate = float(np.mean([row["double_pulse"] for row in rows])) if rows else 0.0

    return {
        "rows": rows,
        "time_axis_ns": time_axis_ns,
        "waveforms": waveform_matrix,
        "summary": {
            "amplitude_mean_v": float(np.mean(amplitude_values)) if amplitude_values.size else 0.0,
            "amplitude_std_v": float(np.std(amplitude_values, ddof=1)) if amplitude_values.size > 1 else 0.0,
            "width_mean_ns": float(np.mean(width_values)) if width_values.size else 0.0,
            "width_std_ns": float(np.std(width_values, ddof=1)) if width_values.size > 1 else 0.0,
            "rise_mean_ns": float(np.mean(rise_values)) if rise_values.size else 0.0,
            "timing_jitter_ns": float(np.std(latency_values, ddof=1)) if latency_values.size > 1 else 0.0,
            "double_pulse_rate": double_rate,
        },
    }


def simulate_dead_time_scan(
    cell: DetectorCell,
    *,
    intervals_us: tuple[float, ...],
    repeats: int,
    seed: int,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    observed_dead_times = np.clip(
        rng.normal(cell.dead_time_us, 0.12, size=max(repeats, 4)),
        0.1,
        None,
    )
    tau_us = max(cell.reset_recovery_us - cell.dead_time_us, 0.2)

    for interval_us in intervals_us:
        available = max(interval_us - cell.dead_time_us, 0.0)
        rearm_probability = 0.0 if available <= 0.0 else 1.0 - math.exp(-available / tau_us)
        success_count = int(rng.binomial(repeats, rearm_probability))
        rows.append(
            {
                "interval_us": float(interval_us),
                "repeats": repeats,
                "rearm_fraction": success_count / max(repeats, 1),
                "success_count": success_count,
                "expected_rearm_probability": rearm_probability,
            }
        )

    recovery_90_candidates = [row["interval_us"] for row in rows if row["rearm_fraction"] >= 0.9]
    return {
        "rows": rows,
        "observed_dead_times_us": observed_dead_times,
        "summary": {
            "dead_time_mean_us": float(np.mean(observed_dead_times)),
            "dead_time_std_us": float(np.std(observed_dead_times, ddof=1)) if observed_dead_times.size > 1 else 0.0,
            "recovery_90_us": float(recovery_90_candidates[0]) if recovery_90_candidates else math.inf,
        },
    }


def summarize_matching(
    cell_a: DetectorCell,
    cell_b: DetectorCell,
    rate_fit_a: dict[str, Any],
    rate_fit_b: dict[str, Any],
    pulse_summary_a: dict[str, float],
    pulse_summary_b: dict[str, float],
    dead_time_summary_a: dict[str, float],
    dead_time_summary_b: dict[str, float],
) -> dict[str, Any]:
    alpha_a = float(rate_fit_a["alpha_fit"])
    alpha_b = float(rate_fit_b["alpha_fit"])
    dark_a = float(rate_fit_a["lambda_dark_fit"])
    dark_b = float(rate_fit_b["lambda_dark_fit"])
    alpha_mean = 0.5 * (alpha_a + alpha_b)
    pulse_width_mean = 0.5 * (pulse_summary_a["width_mean_ns"] + pulse_summary_b["width_mean_ns"])
    timing_mean = 0.5 * (pulse_summary_a["timing_jitter_ns"] + pulse_summary_b["timing_jitter_ns"])
    dead_time_mean = 0.5 * (dead_time_summary_a["dead_time_mean_us"] + dead_time_summary_b["dead_time_mean_us"])
    return {
        "rows": [
            {
                "cell": cell_a.name,
                "bias_v": cell_a.bias_v,
                "alpha_fit_hz_per_uw": alpha_a,
                "lambda_dark_fit_hz": dark_a,
                "pulse_amplitude_mean_v": pulse_summary_a["amplitude_mean_v"],
                "pulse_width_mean_ns": pulse_summary_a["width_mean_ns"],
                "timing_jitter_ns": pulse_summary_a["timing_jitter_ns"],
                "dead_time_mean_us": dead_time_summary_a["dead_time_mean_us"],
            },
            {
                "cell": cell_b.name,
                "bias_v": cell_b.bias_v,
                "alpha_fit_hz_per_uw": alpha_b,
                "lambda_dark_fit_hz": dark_b,
                "pulse_amplitude_mean_v": pulse_summary_b["amplitude_mean_v"],
                "pulse_width_mean_ns": pulse_summary_b["width_mean_ns"],
                "timing_jitter_ns": pulse_summary_b["timing_jitter_ns"],
                "dead_time_mean_us": dead_time_summary_b["dead_time_mean_us"],
            },
        ],
        "summary": {
            "alpha_mismatch_rel": abs(alpha_a - alpha_b) / max(alpha_mean, 1e-12),
            "dark_rate_mismatch_hz": abs(dark_a - dark_b),
            "pulse_width_mismatch_rel": abs(pulse_summary_a["width_mean_ns"] - pulse_summary_b["width_mean_ns"])
            / max(pulse_width_mean, 1e-12),
            "timing_jitter_mismatch_rel": abs(pulse_summary_a["timing_jitter_ns"] - pulse_summary_b["timing_jitter_ns"])
            / max(timing_mean, 1e-12),
            "dead_time_mismatch_rel": abs(dead_time_summary_a["dead_time_mean_us"] - dead_time_summary_b["dead_time_mean_us"])
            / max(dead_time_mean, 1e-12),
        },
    }


def _sample_click_time(rate_hz: float, timeout_s: float, rng) -> float | None:
    if rate_hz <= 0.0:
        return None
    sample = float(rng.exponential(1.0 / rate_hz))
    return sample if sample <= timeout_s else None


def simulate_race_summary(
    cell_a: DetectorCell,
    cell_b: DetectorCell,
    *,
    splits: tuple[tuple[float, float], ...],
    total_power_uw: float,
    n_trials: int,
    timeout_s: float,
    seed: int,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    raw_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    empirical_p1_values: list[float] = []
    target_p1_values: list[float] = []

    for split_index, (fraction_1, fraction_2) in enumerate(splits):
        power_1 = total_power_uw * fraction_1
        power_2 = total_power_uw * fraction_2
        rate_1 = click_rate(cell_a, power_1)
        rate_2 = click_rate(cell_b, power_2)
        winner_counts = {0: 0, 1: 0, 2: 0}

        for trial_index in range(1, n_trials + 1):
            t1 = _sample_click_time(rate_1, timeout_s, rng)
            t2 = _sample_click_time(rate_2, timeout_s, rng)
            winner = 0
            if t1 is None and t2 is None:
                winner = 0
            elif t1 is None:
                winner = 2
            elif t2 is None or t1 < t2:
                winner = 1
            elif t2 < t1:
                winner = 2
            winner_counts[winner] += 1
            raw_rows.append(
                {
                    "split_label": f"{fraction_1:.2f}/{fraction_2:.2f}",
                    "trial_index": trial_index,
                    "power_1_uw": power_1,
                    "power_2_uw": power_2,
                    "winner": winner,
                    "click_time_1_s": "" if t1 is None else t1,
                    "click_time_2_s": "" if t2 is None else t2,
                }
            )

        decisive = winner_counts[1] + winner_counts[2]
        empirical_p1 = winner_counts[1] / max(decisive, 1)
        target_p1 = fraction_1 / max(fraction_1 + fraction_2, 1e-12)
        empirical_p1_values.append(empirical_p1)
        target_p1_values.append(target_p1)
        summary_rows.append(
            {
                "split_label": f"{fraction_1:.2f}/{fraction_2:.2f}",
                "target_p1": target_p1,
                "empirical_p1": empirical_p1,
                "winner_1_count": winner_counts[1],
                "winner_2_count": winner_counts[2],
                "timeout_count": winner_counts[0],
                "decisive_fraction": decisive / max(n_trials, 1),
            }
        )

    metrics = race_error_metric(target_p1_values, empirical_p1_values)
    return {
        "raw_rows": raw_rows,
        "summary_rows": summary_rows,
        "metrics": {
            "race_rms_error": float(metrics["race_rms_error"]),
            "race_max_error": float(metrics["race_max_error"]),
        },
    }
