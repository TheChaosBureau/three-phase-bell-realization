from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SearchConfig:
    """Configuration for rate, race, and robustness scans."""

    dt: float = 1e-4
    t_max: float = 50.0
    n_rate_trials: int = 2_000
    n_race_trials: int = 5_000
    p_scan: tuple[float, ...] = (0.0, 0.1, 0.2, 0.5, 1.0, 2.0)
    race_pairs: tuple[tuple[float, float], ...] = (
        (0.75, 0.25),
        (0.70, 0.30),
        (0.60, 0.40),
        (0.50, 0.50),
    )
    mismatch_levels: tuple[float, ...] = (0.01, 0.02, 0.05)
    waiting_time_powers: tuple[float, ...] = (0.2, 1.0, 2.0)
    seed: int = 1234
    score_weights: dict[str, float] = field(
        default_factory=lambda: {
            "linearity_rms_rel": 3.0,
            "race_rms_error": 4.0,
            "dark_penalty": 2.0,
            "waiting_time_penalty": 1.5,
            "mismatch_penalty": 3.0,
        }
    )


DEFAULT_SEARCH_CONFIG = SearchConfig()
