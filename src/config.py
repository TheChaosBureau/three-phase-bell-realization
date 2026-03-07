from __future__ import annotations
from dataclasses import dataclass


@dataclass
class SourceConfig:
    V0: float = 1.0
    phi_s: float = 0.0
    YA_plus: complex = 1j
    YA_minus: complex = -1j
    YB_plus: complex = 1j
    YB_minus: complex = -1j
    G0: float = 1.0


@dataclass
class DetectorConfig:
    eta: float = 1.0
    kappa: float = 0.0
    threshold: float = 0.05
    dt: float = 1e-3
    t_max: float = 1.0
    mode: str = "threshold_race"  # or "categorical"


@dataclass
class ExperimentConfig:
    trials: int = 10000
    rng_seed: int = 1234