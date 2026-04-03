from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DetectorRigConfig:
    """Configuration for the two-cell detector characterization rig."""

    bias_scan_volts: tuple[float, ...] = (2.64, 2.68, 2.72, 2.74, 2.76, 2.78, 2.80, 2.82, 2.84, 2.86, 2.88)
    nominal_power_uw: float = 20.0
    rate_scan_powers_uw: tuple[float, ...] = (0.0, 2.5, 5.0, 10.0, 15.0, 20.0)
    total_race_power_uw: float = 20.0
    dark_window_s: float = 20.0
    n_dark_windows: int = 24
    rate_window_s: float = 2.5
    rate_repeats: int = 48
    pulse_events: int = 96
    pulse_overlay_count: int = 16
    pulse_window_ns: float = 28.0
    pulse_dt_ns: float = 0.1
    dead_time_intervals_us: tuple[float, ...] = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0)
    dead_time_repeats: int = 320
    race_splits: tuple[tuple[float, float], ...] = ((0.50, 0.50), (0.60, 0.40), (0.70, 0.30), (0.75, 0.25))
    race_trials: int = 5_000
    race_timeout_s: float = 1.0
    operating_target_signal_rate_hz: float = 30.0
    seed: int = 20260402


@dataclass(frozen=True)
class LatchRigConfig:
    """Configuration for the common-mode / zero-sequence latch bench rig."""

    input_threshold_v: float = 0.35
    min_input_pulse_width_ns: float = 6.0
    pickoff_delay_ns: float = 0.45
    propagation_delay_ns: float = 0.65
    inhibit_delay_ns: float = 0.20
    settle_time_ns: float = 1.10
    tie_window_ns: float = 0.25
    reset_pulse_ns: float = 8.0
    rearm_holdoff_us: float = 6.0
    synthetic_offsets_ns: tuple[float, ...] = (-12.0, -6.0, -1.0, -0.2, 0.0, 0.2, 1.0, 6.0, 12.0)
    synthetic_repeats: int = 256
    exclusivity_repeats: int = 192
    reset_cycles: int = 256
    input_load_amplitude_loss_rel: float = 0.012
    input_load_width_stretch_rel: float = 0.018
    input_load_added_jitter_ns: float = 0.015
    tie_break_priority: str = "A"
    seed: int = 20260402


DEFAULT_DETECTOR_RIG_CONFIG = DetectorRigConfig()
DEFAULT_LATCH_RIG_CONFIG = LatchRigConfig()
