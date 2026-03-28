import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import hype_map_models as hype


@pytest.fixture(scope="session")
def result_bundle():
    results = hype.evaluate_mechanism_map()
    artifact = hype.write_result_map(results)
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    return {
        "results": results,
        "by_id": {result.id: result for result in results},
        "artifact": artifact,
        "payload": payload,
    }


def test_registry_covers_every_hype_map_subfamily():
    ids = tuple(spec.id for spec in hype.mechanism_registry())
    assert ids == hype.EXPECTED_MECHANISM_IDS


def test_result_artifact_is_written_with_expected_schema(result_bundle):
    artifact = result_bundle["artifact"]
    payload = result_bundle["payload"]

    assert artifact == hype.artifact_path()
    assert artifact.exists()
    assert payload["mechanism_ids"] == list(hype.EXPECTED_MECHANISM_IDS)
    assert payload["samples_per_setting"] == hype.DEFAULT_SAMPLES
    assert payload["delta_grid_size"] == len(hype.DELTA_GRID)
    assert payload["signal_grid_size"] == len(hype.SIGNAL_GRID)
    assert len(payload["results"]) == len(hype.EXPECTED_MECHANISM_IDS)


def test_every_mechanism_has_summary_and_tags(result_bundle):
    for result in result_bundle["results"]:
        assert result.summary
        assert result.tags


def test_a1_is_local_no_signaling_but_half_amplitude(result_bundle):
    result = result_bundle["by_id"]["A1"]

    assert result.flags.no_signaling
    assert result.metrics.chsh == pytest.approx(math.sqrt(2.0), abs=0.15)
    assert result.metrics.aligned_same_sign_mass > 0.15
    assert "boundary_only" in result.tags
    assert "misses_target_angle_law" in result.tags


def test_a2_hits_bell_boundary_with_exact_aligned_antisupport(result_bundle):
    result = result_bundle["by_id"]["A2"]

    assert result.flags.no_signaling
    assert result.flags.aligned_anti_support
    assert result.metrics.chsh == pytest.approx(2.0, abs=0.08)
    assert result.metrics.angle_law_rmse > 0.10
    assert "boundary_only" in result.tags


def test_a3_improves_coordination_without_crossing_classical_boundary(result_bundle):
    result = result_bundle["by_id"]["A3"]

    assert result.flags.no_signaling
    assert result.flags.aligned_anti_support
    assert result.metrics.chsh < 2.0
    assert result.metrics.angle_law_rmse > 0.20
    assert "boundary_only" in result.tags


def test_shared_source_dynamics_trade_correlation_for_signaling(result_bundle):
    weak = result_bundle["by_id"]["B1"]
    strong = result_bundle["by_id"]["B2"]

    assert weak.flags.no_signaling
    assert weak.metrics.chsh < 2.0
    assert strong.metrics.chsh > 2.0
    assert not strong.flags.no_signaling
    assert max(strong.metrics.alice_marginal_drift, strong.metrics.bob_marginal_drift) > 0.05
    assert max(strong.metrics.alice_marginal_drift, strong.metrics.bob_marginal_drift) > max(
        weak.metrics.alice_marginal_drift, weak.metrics.bob_marginal_drift
    )
    assert "signals" in strong.tags
    assert "correlation_via_signaling" in strong.tags


def test_generic_vs_projective_depletion_separates_residual_quality(result_bundle):
    generic = result_bundle["by_id"]["C1"]
    projective = result_bundle["by_id"]["C2"]

    assert generic.metrics.projectivity_score is not None
    assert projective.metrics.projectivity_score is not None
    assert generic.metrics.projectivity_score < 0.80
    assert projective.metrics.projectivity_score >= 0.99
    assert generic.metrics.angle_law_rmse > 0.10
    assert not generic.flags.no_signaling
    assert projective.flags.no_signaling
    assert projective.flags.matches_angle_law
    assert "nonprojective_residual" in generic.tags
    assert "projective_proxy" in projective.tags


def test_sequential_models_and_pair_selectors_hit_target_cleanly(result_bundle):
    for mechanism_id in ("D1", "D2", "E1", "E2", "F2"):
        result = result_bundle["by_id"][mechanism_id]
        assert result.flags.matches_angle_law
        assert result.flags.no_signaling
        assert result.flags.aligned_anti_support
        assert result.metrics.chsh == pytest.approx(hype.TSIRELSON, abs=0.08)
        assert "meets_target_constraints" in result.tags


def test_f1_is_joint_and_no_signaling_but_not_an_exact_fit(result_bundle):
    result = result_bundle["by_id"]["F1"]

    assert result.flags.no_signaling
    assert not result.flags.matches_angle_law
    assert result.metrics.chsh > 2.0
    assert result.metrics.angle_law_rmse > 0.10
    assert result.metrics.aligned_same_sign_mass > 0.05
    assert "misses_target_angle_law" in result.tags


def test_superdeterministic_proxy_is_explicitly_excluded(result_bundle):
    result = result_bundle["by_id"]["G"]

    assert result.flags.matches_angle_law
    assert result.flags.no_signaling
    assert not result.flags.measurement_independent
    assert "measurement_dependence_excluded" in result.tags
    assert "meets_target_constraints" in result.tags
