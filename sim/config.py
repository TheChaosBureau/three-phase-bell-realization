from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from typing import Any

DEFAULT_SEED = 7
DEFAULT_GAMMA_MINUS = 1.0
EPSILON = 1e-12
WINDOW_FRACTIONS_ALL = (1.0 / 6.0, 0.25, 1.0 / 3.0, 0.5, 1.0)
PRIMARY_WINDOW_FRACTIONS = (0.25, 0.5, 1.0)
KEY_ANGLES_DEG = (0.0, 22.5, 45.0, 67.5, 90.0)
DEFAULT_ANISOTROPY_RATIOS = (1.0, 1.5, 2.0, 4.0, 8.0, 16.0)
DEFAULT_READOUT_RULES = (
    "dominant_pre",
    "dominant_post",
    "dominance_shift",
    "extracted_energy",
    "residual_classifier",
)


def dense_angles_deg(count: int = 37) -> tuple[float, ...]:
    if count < 2:
        return KEY_ANGLES_DEG
    step = 90.0 / (count - 1)
    return tuple(round(index * step, 6) for index in range(count))


@dataclass(slots=True)
class SourceConfig:
    sample_count: int = 256
    seed: int = DEFAULT_SEED
    radius: float = 1.0
    amplitude_imbalance: float = 0.0
    noise_std: float = 0.0
    random_global_phase: bool = True
    random_relative_phase: bool = False
    relative_phase_rad: float = 0.0


@dataclass(slots=True)
class DampingConfig:
    gamma_plus: float
    gamma_minus: float = DEFAULT_GAMMA_MINUS
    window_fraction: float = 0.25
    base_period: float = 1.0

    @property
    def window_duration(self) -> float:
        return self.base_period * self.window_fraction

    @property
    def anisotropy_ratio(self) -> float:
        if abs(self.gamma_minus) <= EPSILON:
            return float("inf")
        return self.gamma_plus / self.gamma_minus


@dataclass(slots=True)
class SingleRunConfig:
    source: SourceConfig
    damping: DampingConfig
    analyzer_angles_deg: tuple[float, ...] = KEY_ANGLES_DEG
    include_dense_angles: bool = True
    dense_angle_count: int = 37

    def expanded_angles_deg(self) -> tuple[float, ...]:
        angle_set = set(self.analyzer_angles_deg)
        if self.include_dense_angles:
            angle_set.update(dense_angles_deg(self.dense_angle_count))
        return tuple(sorted(angle_set))


@dataclass(slots=True)
class SequentialRunConfig:
    source: SourceConfig
    damping: DampingConfig
    alice_angles_deg: tuple[float, ...] = KEY_ANGLES_DEG
    bob_angles_deg: tuple[float, ...] = KEY_ANGLES_DEG
    readout_rules: tuple[str, ...] = DEFAULT_READOUT_RULES


@dataclass(slots=True)
class SweepPreset:
    name: str
    description: str
    source: SourceConfig = field(default_factory=SourceConfig)
    single_sample_count: int = 256
    sequential_sample_count: int = 384
    gamma_minus: float = DEFAULT_GAMMA_MINUS
    anisotropy_ratios: tuple[float, ...] = DEFAULT_ANISOTROPY_RATIOS
    single_window_fractions: tuple[float, ...] = WINDOW_FRACTIONS_ALL
    sequential_window_fractions: tuple[float, ...] = PRIMARY_WINDOW_FRACTIONS
    single_angles_deg: tuple[float, ...] = KEY_ANGLES_DEG
    sequential_alice_angles_deg: tuple[float, ...] = KEY_ANGLES_DEG
    sequential_bob_angles_deg: tuple[float, ...] = KEY_ANGLES_DEG
    include_dense_single_angles: bool = True
    dense_single_angle_count: int = 37
    readout_rules: tuple[str, ...] = DEFAULT_READOUT_RULES

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def make_preset(
    name: str,
    *,
    seed: int = DEFAULT_SEED,
    single_sample_count: int | None = None,
    sequential_sample_count: int | None = None,
    dense_single_angle_count: int | None = None,
) -> SweepPreset:
    source = SourceConfig(seed=seed)
    match name:
        case "single":
            preset = SweepPreset(
                name=name,
                description="Single-analyzer characterization across all windows and anisotropy ratios.",
                source=source,
                single_sample_count=single_sample_count or 256,
                sequential_sample_count=sequential_sample_count or 384,
                sequential_window_fractions=(),
            )
        case "sequential":
            preset = SweepPreset(
                name=name,
                description="Sequential Alice-to-Bob sweeps with rule comparisons and marginal diagnostics.",
                source=source,
                single_sample_count=single_sample_count or 256,
                sequential_sample_count=sequential_sample_count or 384,
                single_window_fractions=(),
                include_dense_single_angles=False,
            )
        case "risk_first_full":
            preset = SweepPreset(
                name=name,
                description="Risk-first workflow: full single-analyzer characterization plus targeted sequential diagnostics.",
                source=source,
                single_sample_count=single_sample_count or 256,
                sequential_sample_count=sequential_sample_count or 384,
            )
        case _:
            raise ValueError(f"Unknown preset: {name}")
    if dense_single_angle_count is not None:
        preset = replace(preset, dense_single_angle_count=dense_single_angle_count)
    return preset


def build_single_run_configs(preset: SweepPreset) -> list[SingleRunConfig]:
    source = replace(preset.source, sample_count=preset.single_sample_count)
    runs: list[SingleRunConfig] = []
    for window_fraction in preset.single_window_fractions:
        for ratio in preset.anisotropy_ratios:
            damping = DampingConfig(
                gamma_plus=preset.gamma_minus * ratio,
                gamma_minus=preset.gamma_minus,
                window_fraction=window_fraction,
            )
            runs.append(
                SingleRunConfig(
                    source=source,
                    damping=damping,
                    analyzer_angles_deg=preset.single_angles_deg,
                    include_dense_angles=preset.include_dense_single_angles,
                    dense_angle_count=preset.dense_single_angle_count,
                )
            )
    return runs


def build_sequential_run_configs(preset: SweepPreset) -> list[SequentialRunConfig]:
    source = replace(preset.source, sample_count=preset.sequential_sample_count)
    runs: list[SequentialRunConfig] = []
    for window_fraction in preset.sequential_window_fractions:
        for ratio in preset.anisotropy_ratios:
            damping = DampingConfig(
                gamma_plus=preset.gamma_minus * ratio,
                gamma_minus=preset.gamma_minus,
                window_fraction=window_fraction,
            )
            runs.append(
                SequentialRunConfig(
                    source=source,
                    damping=damping,
                    alice_angles_deg=preset.sequential_alice_angles_deg,
                    bob_angles_deg=preset.sequential_bob_angles_deg,
                    readout_rules=preset.readout_rules,
                )
            )
    return runs
