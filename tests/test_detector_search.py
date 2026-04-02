from __future__ import annotations

from pathlib import Path

from detector_search.config import SearchConfig
from detector_search.experiments.run_global_search import _save_global_search_plots
from detector_search.models import AccumulatorBadControlModel, PoissonLinearModel, ShotTriggerModel
from detector_search.sim.search import evaluate_candidate, rank_candidates, save_results_csv, save_results_jsonl


TEST_CONFIG = SearchConfig(
    dt=5e-4,
    t_max=12.0,
    n_rate_trials=350,
    n_race_trials=700,
    p_scan=(0.0, 0.25, 0.5, 1.0, 1.5),
    race_pairs=((0.75, 0.25), (0.6, 0.4), (0.5, 0.5)),
    mismatch_levels=(0.01, 0.03),
    waiting_time_powers=(0.25, 1.0, 1.5),
    seed=20260402,
)


def test_poisson_benchmark_has_low_race_and_linearity_error() -> None:
    result = evaluate_candidate(
        PoissonLinearModel(),
        params={"lambda_dark": 0.02, "alpha": 0.8, "dead_time": 0.0},
        config=TEST_CONFIG,
    )

    assert result["metrics"]["linearity_rms_rel"] < 0.12
    assert result["metrics"]["race_rms_error"] < 0.06
    assert result["metrics"]["waiting_time_penalty"] < 0.25


def test_bad_control_is_ranked_worse_than_linear_models() -> None:
    poisson = evaluate_candidate(
        PoissonLinearModel(),
        params={"lambda_dark": 0.02, "alpha": 0.8, "dead_time": 0.0},
        config=TEST_CONFIG,
    )
    shot = evaluate_candidate(
        ShotTriggerModel(),
        params={"eps_event": 1.25, "p_trig": 0.9, "lambda_dark": 0.02, "dead_time": 0.0},
        config=TEST_CONFIG,
    )
    bad = evaluate_candidate(
        AccumulatorBadControlModel(),
        params={"sigma": 0.08, "threshold": 1.0, "reset_value": 0.0, "dead_time": 0.0},
        config=TEST_CONFIG,
    )

    ranked = rank_candidates([bad, shot, poisson])

    assert ranked[0]["model"] in {"poisson_linear", "shot_trigger"}
    assert ranked[-1]["model"] == "accumulator_bad_control"
    assert bad["metrics"]["race_rms_error"] > poisson["metrics"]["race_rms_error"]
    assert bad["metrics"]["score"] > poisson["metrics"]["score"]


def test_result_export_writes_jsonl_and_csv(tmp_path: Path) -> None:
    result = evaluate_candidate(
        PoissonLinearModel(),
        params={"lambda_dark": 0.02, "alpha": 0.8, "dead_time": 0.0},
        config=TEST_CONFIG,
    )
    jsonl_path = tmp_path / "results.jsonl"
    csv_path = tmp_path / "results.csv"

    save_results_jsonl([result], jsonl_path)
    save_results_csv([result], csv_path)

    assert jsonl_path.exists()
    assert csv_path.exists()
    assert "poisson_linear" in jsonl_path.read_text(encoding="utf-8")
    assert "score" in csv_path.read_text(encoding="utf-8")


def test_global_search_plot_export_writes_expected_artifacts(tmp_path: Path) -> None:
    model = PoissonLinearModel()
    result = evaluate_candidate(
        model,
        params={"lambda_dark": 0.02, "alpha": 0.8, "dead_time": 0.0},
        config=TEST_CONFIG,
    )

    written = _save_global_search_plots(
        model_name="poisson_linear",
        model=model,
        results=[result],
        outdir=str(tmp_path),
        config=TEST_CONFIG,
    )

    expected_names = {
        "poisson_linear_score_histogram.png",
        "poisson_linear_top_rate_scan.png",
        "poisson_linear_top_rate_residuals.png",
        "poisson_linear_top_race_law.png",
        "poisson_linear_top_robustness.png",
        "poisson_linear_top_waiting_time_hist.png",
        "poisson_linear_top_candidate.txt",
    }

    assert {Path(path).name for path in written} == expected_names
    assert all((tmp_path / name).exists() for name in expected_names)
