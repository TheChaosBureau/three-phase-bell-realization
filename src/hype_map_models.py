from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable

import numpy as np

TSIRELSON = 2.0 * math.sqrt(2.0)
DEFAULT_SAMPLES = 50_000
DELTA_GRID = np.linspace(0.0, math.pi / 2.0, 17)
SIGNAL_GRID = np.linspace(0.0, math.pi / 2.0, 5)
CHSH_SETTINGS = (0.0, math.pi / 4.0, math.pi / 8.0, 3.0 * math.pi / 8.0)
EXPECTED_MECHANISM_IDS = (
    "A1",
    "A2",
    "A3",
    "B1",
    "B2",
    "C1",
    "C2",
    "D1",
    "D2",
    "E1",
    "E2",
    "F1",
    "F2",
    "G",
)
SEED_TABLE = {
    "A1": 1_001,
    "A2": 1_002,
    "A3": 1_003,
    "B1": 1_004,
    "B2": 1_005,
    "C1": 1_006,
    "C2": 1_007,
    "D1": 1_008,
    "D2": 1_009,
    "E1": 1_010,
    "E2": 1_011,
    "F1": 1_012,
    "F2": 1_013,
    "G": 1_014,
}
ANGLE_LAW_RMSE_THRESHOLD = 0.025
TSIRELSON_TOLERANCE = 0.05
NO_SIGNALING_DRIFT_THRESHOLD = 0.02
ALIGNED_SAME_SIGN_THRESHOLD = 0.01
PROJECTIVITY_THRESHOLD = 0.95

SampleFn = Callable[[float, float, int, np.random.Generator], "SampleBatch"]


@dataclass(frozen=True)
class SampleBatch:
    alice: np.ndarray
    bob: np.ndarray
    projectivity: np.ndarray | None = None


@dataclass(frozen=True)
class MechanismSpec:
    id: str
    family: str
    label: str
    selection_mode: str
    physical_proxy: bool
    uses_measurement_dependence: bool
    bell_local_structure: bool
    joint_pair_selector: bool
    sampler: SampleFn


@dataclass(frozen=True)
class MechanismMetrics:
    angle_law_rmse: float
    chsh: float
    alice_marginal_drift: float
    bob_marginal_drift: float
    aligned_same_sign_mass: float
    aligned_anti_mass: float
    projectivity_score: float | None


@dataclass(frozen=True)
class MechanismFlags:
    matches_angle_law: bool
    no_signaling: bool
    aligned_anti_support: bool
    measurement_independent: bool
    bell_local_structure: bool
    joint_pair_selector: bool
    physical_proxy: bool


@dataclass(frozen=True)
class MechanismResult:
    id: str
    family: str
    label: str
    selection_mode: str
    metrics: MechanismMetrics
    flags: MechanismFlags
    tags: list[str]
    summary: str


def _canonical_delta(phi_a: float, phi_b: float) -> float:
    delta = abs((phi_a - phi_b) % math.pi)
    return min(delta, math.pi - delta)


def _hidden_phase(rng: np.random.Generator, n: int) -> np.ndarray:
    return rng.uniform(0.0, math.pi, size=n)


def _sign_nonzero(values: np.ndarray) -> np.ndarray:
    return np.where(values >= 0.0, 1, -1).astype(np.int8)


def _sample_binary(prob_plus: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    return np.where(rng.random(prob_plus.shape) < prob_plus, 1, -1).astype(np.int8)


def _sample_from_pair_probs(probabilities: np.ndarray, rng: np.random.Generator, n: int) -> SampleBatch:
    probs = probabilities / probabilities.sum()
    cuts = np.cumsum(probs)
    u = rng.random(n)
    alice = np.empty(n, dtype=np.int8)
    bob = np.empty(n, dtype=np.int8)

    mask0 = u < cuts[0]
    mask1 = (u >= cuts[0]) & (u < cuts[1])
    mask2 = (u >= cuts[1]) & (u < cuts[2])
    mask3 = u >= cuts[2]

    alice[mask0], bob[mask0] = 1, 1
    alice[mask1], bob[mask1] = 1, -1
    alice[mask2], bob[mask2] = -1, 1
    alice[mask3], bob[mask3] = -1, -1
    return SampleBatch(alice=alice, bob=bob)


def _exact_pair_probabilities(delta: float) -> np.ndarray:
    same = math.sin(delta) ** 2 / 2.0
    different = math.cos(delta) ** 2 / 2.0
    return np.array([same, different, different, same], dtype=float)


def _stochastic_local_sampler(phi_a: float, phi_b: float, n: int, rng: np.random.Generator) -> SampleBatch:
    theta = _hidden_phase(rng, n)
    p_a = np.cos(theta - phi_a) ** 2
    p_b = np.sin(theta - phi_b) ** 2
    return SampleBatch(alice=_sample_binary(p_a, rng), bob=_sample_binary(p_b, rng))


def _deterministic_threshold_sampler(phi_a: float, phi_b: float, n: int, rng: np.random.Generator) -> SampleBatch:
    theta = _hidden_phase(rng, n)
    alice = _sign_nonzero(np.cos(2.0 * (theta - phi_a)))
    bob = -_sign_nonzero(np.cos(2.0 * (theta - phi_b)))
    return SampleBatch(alice=alice, bob=bob.astype(np.int8))


def _shared_threshold_sampler(phi_a: float, phi_b: float, n: int, rng: np.random.Generator) -> SampleBatch:
    theta = _hidden_phase(rng, n)
    u = rng.random(n)
    p_a = np.cos(theta - phi_a) ** 2
    complement_b = np.cos(theta - phi_b) ** 2
    alice = np.where(u < p_a, 1, -1).astype(np.int8)
    bob = np.where(u > complement_b, 1, -1).astype(np.int8)
    return SampleBatch(alice=alice, bob=bob)


def _shared_source_sampler(reserve: float) -> SampleFn:
    def sample(phi_a: float, phi_b: float, n: int, rng: np.random.Generator) -> SampleBatch:
        theta = _hidden_phase(rng, n)
        demand_a = np.cos(theta - phi_a) ** 2
        demand_b = np.sin(theta - phi_b) ** 2
        total = demand_a + demand_b + reserve
        p_a = np.clip((demand_a / total) * (1.0 + reserve), 0.0, 1.0)
        p_b = np.clip((demand_b / total) * (1.0 + reserve), 0.0, 1.0)
        u = rng.random(n)
        alice = np.where(u < p_a, 1, -1).astype(np.int8)
        bob = np.where(u > 1.0 - p_b, 1, -1).astype(np.int8)
        return SampleBatch(alice=alice, bob=bob)

    return sample


def _projective_clean_probabilities(alice: np.ndarray, delta: float) -> np.ndarray:
    return np.where(alice == 1, math.sin(delta) ** 2, math.cos(delta) ** 2)


def _generic_depletion_sampler(phi_a: float, phi_b: float, n: int, rng: np.random.Generator) -> SampleBatch:
    theta = _hidden_phase(rng, n)
    p_a = np.cos(theta - phi_a) ** 2
    alice = _sample_binary(p_a, rng)
    delta = _canonical_delta(phi_a, phi_b)
    clean = _projective_clean_probabilities(alice, delta)
    local = np.sin(theta - phi_b) ** 2
    absolute_bias = 0.5 + 0.5 * math.cos(2.0 * (phi_a + phi_b))
    p_b = np.clip(0.55 * clean + 0.30 * local + 0.15 * absolute_bias, 0.0, 1.0)
    bob = _sample_binary(p_b, rng)
    projectivity = np.clip(0.58 + 0.22 * np.cos(theta - phi_a) ** 2, 0.0, 1.0)
    return SampleBatch(alice=alice, bob=bob, projectivity=projectivity)


def _projective_depletion_sampler(phi_a: float, phi_b: float, n: int, rng: np.random.Generator) -> SampleBatch:
    theta = _hidden_phase(rng, n)
    p_a = np.cos(theta - phi_a) ** 2
    alice = _sample_binary(p_a, rng)
    delta = _canonical_delta(phi_a, phi_b)
    p_b = _projective_clean_probabilities(alice, delta)
    bob = _sample_binary(p_b, rng)
    return SampleBatch(alice=alice, bob=bob, projectivity=np.ones(n, dtype=float))


def _sequential_joint_update_sampler(phi_a: float, phi_b: float, n: int, rng: np.random.Generator) -> SampleBatch:
    alice = np.where(rng.random(n) < 0.5, 1, -1).astype(np.int8)
    delta = _canonical_delta(phi_a, phi_b)
    same = rng.random(n) < math.sin(delta) ** 2
    bob = np.where(same, alice, -alice).astype(np.int8)
    return SampleBatch(alice=alice, bob=bob)


def _hardware_bridge_sampler(phi_a: float, phi_b: float, n: int, rng: np.random.Generator) -> SampleBatch:
    alice = np.where(rng.random(n) < 0.5, 1, -1).astype(np.int8)
    delta = _canonical_delta(phi_a, phi_b)
    same = rng.random(n) < math.sin(delta) ** 2
    bob = np.where(same, alice, -alice).astype(np.int8)
    projectivity = np.full(n, 0.99, dtype=float)
    return SampleBatch(alice=alice, bob=bob, projectivity=projectivity)


def _exact_joint_law_sampler(phi_a: float, phi_b: float, n: int, rng: np.random.Generator) -> SampleBatch:
    return _sample_from_pair_probs(_exact_pair_probabilities(_canonical_delta(phi_a, phi_b)), rng, n)


def _pair_space_selector_sampler(phi_a: float, phi_b: float, n: int, rng: np.random.Generator) -> SampleBatch:
    delta = _canonical_delta(phi_a, phi_b)
    scores = np.array(
        [
            math.sin(delta) ** 2,
            math.cos(delta) ** 2,
            math.cos(delta) ** 2,
            math.sin(delta) ** 2,
        ],
        dtype=float,
    )
    return _sample_from_pair_probs(scores, rng, n)


def _global_variational_sampler(phi_a: float, phi_b: float, n: int, rng: np.random.Generator) -> SampleBatch:
    delta = _canonical_delta(phi_a, phi_b)
    closure = math.cos(2.0 * delta)
    beta = 1.0
    same = math.exp(-beta * closure)
    different = math.exp(beta * closure)
    probabilities = np.array([same, different, different, same], dtype=float)
    return _sample_from_pair_probs(probabilities, rng, n)


def _two_boundary_sampler(phi_a: float, phi_b: float, n: int, rng: np.random.Generator) -> SampleBatch:
    return _sample_from_pair_probs(_exact_pair_probabilities(_canonical_delta(phi_a, phi_b)), rng, n)


def _superdeterministic_sampler(phi_a: float, phi_b: float, n: int, rng: np.random.Generator) -> SampleBatch:
    # The hidden state is assumed to already encode the chosen settings; the observable
    # output is still local given that enriched hidden state.
    return _sample_from_pair_probs(_exact_pair_probabilities(_canonical_delta(phi_a, phi_b)), rng, n)


def mechanism_registry() -> tuple[MechanismSpec, ...]:
    return (
        MechanismSpec(
            id="A1",
            family="A",
            label="Independent local randomness",
            selection_mode="local_independent",
            physical_proxy=False,
            uses_measurement_dependence=False,
            bell_local_structure=True,
            joint_pair_selector=False,
            sampler=_stochastic_local_sampler,
        ),
        MechanismSpec(
            id="A2",
            family="A",
            label="Deterministic local threshold",
            selection_mode="local_independent",
            physical_proxy=False,
            uses_measurement_dependence=False,
            bell_local_structure=True,
            joint_pair_selector=False,
            sampler=_deterministic_threshold_sampler,
        ),
        MechanismSpec(
            id="A3",
            family="A",
            label="Shared classical threshold carrier",
            selection_mode="local_shared_hidden",
            physical_proxy=False,
            uses_measurement_dependence=False,
            bell_local_structure=True,
            joint_pair_selector=False,
            sampler=_shared_threshold_sampler,
        ),
        MechanismSpec(
            id="B1",
            family="B",
            label="Weak-coupling shared-source dynamics",
            selection_mode="shared_source_dynamic",
            physical_proxy=True,
            uses_measurement_dependence=False,
            bell_local_structure=False,
            joint_pair_selector=False,
            sampler=_shared_source_sampler(reserve=20.0),
        ),
        MechanismSpec(
            id="B2",
            family="B",
            label="Strong-coupling shared-source dynamics",
            selection_mode="shared_source_dynamic",
            physical_proxy=True,
            uses_measurement_dependence=False,
            bell_local_structure=False,
            joint_pair_selector=False,
            sampler=_shared_source_sampler(reserve=0.2),
        ),
        MechanismSpec(
            id="C1",
            family="C",
            label="Generic modal depletion",
            selection_mode="projective_depletion",
            physical_proxy=True,
            uses_measurement_dependence=False,
            bell_local_structure=False,
            joint_pair_selector=False,
            sampler=_generic_depletion_sampler,
        ),
        MechanismSpec(
            id="C2",
            family="C",
            label="Projective modal depletion",
            selection_mode="projective_depletion",
            physical_proxy=True,
            uses_measurement_dependence=False,
            bell_local_structure=False,
            joint_pair_selector=False,
            sampler=_projective_depletion_sampler,
        ),
        MechanismSpec(
            id="D1",
            family="D",
            label="Sequential joint-state update toy model",
            selection_mode="sequential_update",
            physical_proxy=False,
            uses_measurement_dependence=False,
            bell_local_structure=False,
            joint_pair_selector=False,
            sampler=_sequential_joint_update_sampler,
        ),
        MechanismSpec(
            id="D2",
            family="D",
            label="Sequential update hardware bridge",
            selection_mode="sequential_update",
            physical_proxy=True,
            uses_measurement_dependence=False,
            bell_local_structure=False,
            joint_pair_selector=False,
            sampler=_hardware_bridge_sampler,
        ),
        MechanismSpec(
            id="E1",
            family="E",
            label="Exact-fit joint rule",
            selection_mode="pair_selector",
            physical_proxy=False,
            uses_measurement_dependence=False,
            bell_local_structure=False,
            joint_pair_selector=True,
            sampler=_exact_joint_law_sampler,
        ),
        MechanismSpec(
            id="E2",
            family="E",
            label="Central pair-space selector",
            selection_mode="pair_selector",
            physical_proxy=False,
            uses_measurement_dependence=False,
            bell_local_structure=False,
            joint_pair_selector=True,
            sampler=_pair_space_selector_sampler,
        ),
        MechanismSpec(
            id="F1",
            family="F",
            label="Global variational closure",
            selection_mode="global_constraint",
            physical_proxy=False,
            uses_measurement_dependence=False,
            bell_local_structure=False,
            joint_pair_selector=True,
            sampler=_global_variational_sampler,
        ),
        MechanismSpec(
            id="F2",
            family="F",
            label="Two-boundary global selector",
            selection_mode="global_constraint",
            physical_proxy=False,
            uses_measurement_dependence=False,
            bell_local_structure=False,
            joint_pair_selector=True,
            sampler=_two_boundary_sampler,
        ),
        MechanismSpec(
            id="G",
            family="G",
            label="Superdeterministic anti-pattern",
            selection_mode="measurement_dependent",
            physical_proxy=False,
            uses_measurement_dependence=True,
            bell_local_structure=True,
            joint_pair_selector=False,
            sampler=_superdeterministic_sampler,
        ),
    )


def _estimate_expectation(spec: MechanismSpec, phi_a: float, phi_b: float, n: int, seed_offset: int = 0) -> tuple[float, float, float]:
    rng = np.random.default_rng(SEED_TABLE[spec.id] + seed_offset)
    batch = spec.sampler(phi_a, phi_b, n, rng)
    return (
        float(np.mean(batch.alice * batch.bob)),
        float(np.mean(batch.alice == 1)),
        float(np.mean(batch.bob == 1)),
    )


def _compute_chsh(spec: MechanismSpec) -> float:
    phi_a, phi_a_prime, phi_b, phi_b_prime = CHSH_SETTINGS
    e_ab = _estimate_expectation(spec, phi_a, phi_b, DEFAULT_SAMPLES, seed_offset=10)[0]
    e_ab_prime = _estimate_expectation(spec, phi_a, phi_b_prime, DEFAULT_SAMPLES, seed_offset=11)[0]
    e_a_prime_b = _estimate_expectation(spec, phi_a_prime, phi_b, DEFAULT_SAMPLES, seed_offset=12)[0]
    e_a_prime_b_prime = _estimate_expectation(spec, phi_a_prime, phi_b_prime, DEFAULT_SAMPLES, seed_offset=13)[0]
    return abs(e_ab - e_ab_prime + e_a_prime_b + e_a_prime_b_prime)


def _compute_angle_law_rmse(spec: MechanismSpec) -> float:
    residuals = []
    for index, delta in enumerate(DELTA_GRID):
        expectation = _estimate_expectation(spec, 0.0, float(delta), DEFAULT_SAMPLES, seed_offset=100 + index)[0]
        residuals.append(expectation + math.cos(2.0 * float(delta)))
    return float(np.sqrt(np.mean(np.square(residuals))))


def _compute_marginal_drifts(spec: MechanismSpec) -> tuple[float, float]:
    alice_drift = 0.0
    bob_drift = 0.0
    for a_index, phi_a in enumerate(SIGNAL_GRID):
        marginals = []
        for b_index, phi_b in enumerate(SIGNAL_GRID):
            marginals.append(
                _estimate_expectation(spec, float(phi_a), float(phi_b), DEFAULT_SAMPLES, seed_offset=200 + a_index * 10 + b_index)[1]
            )
        alice_drift = max(alice_drift, max(marginals) - min(marginals))
    for b_index, phi_b in enumerate(SIGNAL_GRID):
        marginals = []
        for a_index, phi_a in enumerate(SIGNAL_GRID):
            marginals.append(
                _estimate_expectation(spec, float(phi_a), float(phi_b), DEFAULT_SAMPLES, seed_offset=300 + b_index * 10 + a_index)[2]
            )
        bob_drift = max(bob_drift, max(marginals) - min(marginals))
    return float(alice_drift), float(bob_drift)


def _compute_aligned_support(spec: MechanismSpec) -> tuple[float, float]:
    same_sign_mass = 0.0
    anti_mass = 0.0
    for index, phi in enumerate(SIGNAL_GRID):
        rng = np.random.default_rng(SEED_TABLE[spec.id] + 400 + index)
        batch = spec.sampler(float(phi), float(phi), DEFAULT_SAMPLES, rng)
        aligned_same = float(np.mean(batch.alice == batch.bob))
        same_sign_mass = max(same_sign_mass, aligned_same)
        anti_mass = max(anti_mass, float(np.mean(batch.alice != batch.bob)))
    return same_sign_mass, anti_mass


def _compute_projectivity(spec: MechanismSpec) -> float | None:
    scores = []
    for index, delta in enumerate(DELTA_GRID):
        rng = np.random.default_rng(SEED_TABLE[spec.id] + 500 + index)
        batch = spec.sampler(0.0, float(delta), DEFAULT_SAMPLES, rng)
        if batch.projectivity is not None:
            scores.append(float(np.mean(batch.projectivity)))
    if not scores:
        return None
    return float(np.mean(scores))


def _make_tags(spec: MechanismSpec, metrics: MechanismMetrics, flags: MechanismFlags) -> list[str]:
    tags: list[str] = []
    if not flags.measurement_independent:
        tags.append("measurement_dependence_excluded")
    if flags.matches_angle_law and flags.no_signaling and flags.aligned_anti_support:
        tags.append("meets_target_constraints")
        if flags.physical_proxy:
            tags.append("projective_proxy")
        elif spec.selection_mode in {"pair_selector", "global_constraint", "sequential_update"}:
            tags.append("exact_formal_match")
    else:
        if not flags.matches_angle_law:
            tags.append("misses_target_angle_law")
        if not flags.no_signaling:
            tags.append("signals")
        if not flags.aligned_anti_support:
            tags.append("leaks_aligned_same_sign_support")
    if flags.bell_local_structure and metrics.chsh <= 2.05 and flags.no_signaling:
        tags.append("boundary_only")
    if not flags.bell_local_structure and metrics.chsh > 2.0 and not flags.no_signaling:
        tags.append("correlation_via_signaling")
    if metrics.projectivity_score is not None and metrics.projectivity_score < PROJECTIVITY_THRESHOLD:
        tags.append("nonprojective_residual")
    if metrics.projectivity_score is not None and metrics.projectivity_score >= PROJECTIVITY_THRESHOLD:
        tags.append("high_projectivity")
    return tags


def _make_summary(spec: MechanismSpec, metrics: MechanismMetrics, tags: list[str]) -> str:
    parts = [
        f"CHSH={metrics.chsh:.3f}",
        f"rmse={metrics.angle_law_rmse:.3f}",
        f"drift={max(metrics.alice_marginal_drift, metrics.bob_marginal_drift):.3f}",
        f"aligned_same={metrics.aligned_same_sign_mass:.3f}",
    ]
    if metrics.projectivity_score is not None:
        parts.append(f"projectivity={metrics.projectivity_score:.3f}")
    if tags:
        parts.append("tags=" + ",".join(tags))
    return f"{spec.label}: " + "; ".join(parts)


def evaluate_mechanism(spec: MechanismSpec) -> MechanismResult:
    alice_drift, bob_drift = _compute_marginal_drifts(spec)
    aligned_same, aligned_anti = _compute_aligned_support(spec)
    projectivity = _compute_projectivity(spec)
    metrics = MechanismMetrics(
        angle_law_rmse=_compute_angle_law_rmse(spec),
        chsh=_compute_chsh(spec),
        alice_marginal_drift=alice_drift,
        bob_marginal_drift=bob_drift,
        aligned_same_sign_mass=aligned_same,
        aligned_anti_mass=aligned_anti,
        projectivity_score=projectivity,
    )
    flags = MechanismFlags(
        matches_angle_law=metrics.angle_law_rmse <= ANGLE_LAW_RMSE_THRESHOLD
        and abs(metrics.chsh - TSIRELSON) <= TSIRELSON_TOLERANCE,
        no_signaling=max(metrics.alice_marginal_drift, metrics.bob_marginal_drift) <= NO_SIGNALING_DRIFT_THRESHOLD,
        aligned_anti_support=metrics.aligned_same_sign_mass <= ALIGNED_SAME_SIGN_THRESHOLD,
        measurement_independent=not spec.uses_measurement_dependence,
        bell_local_structure=spec.bell_local_structure,
        joint_pair_selector=spec.joint_pair_selector,
        physical_proxy=spec.physical_proxy,
    )
    tags = _make_tags(spec, metrics, flags)
    return MechanismResult(
        id=spec.id,
        family=spec.family,
        label=spec.label,
        selection_mode=spec.selection_mode,
        metrics=metrics,
        flags=flags,
        tags=tags,
        summary=_make_summary(spec, metrics, tags),
    )


@lru_cache(maxsize=1)
def evaluate_mechanism_map() -> tuple[MechanismResult, ...]:
    return tuple(evaluate_mechanism(spec) for spec in mechanism_registry())


def artifact_path() -> Path:
    return Path(__file__).resolve().parents[1] / "artifacts" / "hype_map_results.json"


def write_result_map(results: tuple[MechanismResult, ...] | None = None, path: Path | None = None) -> Path:
    artifact = path or artifact_path()
    artifact.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "samples_per_setting": DEFAULT_SAMPLES,
        "delta_grid_size": int(len(DELTA_GRID)),
        "signal_grid_size": int(len(SIGNAL_GRID)),
        "tsirelson": TSIRELSON,
        "mechanism_ids": list(EXPECTED_MECHANISM_IDS),
        "results": [asdict(result) for result in (results or evaluate_mechanism_map())],
    }
    artifact.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return artifact
