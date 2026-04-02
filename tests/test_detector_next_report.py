from __future__ import annotations

from pathlib import Path

from detector_search.config import SearchConfig
from detector_search.experiments.run_next_steps_report import build_next_steps_report, reduced_two_branch_weights


SMOKE_REPORT_CONFIG = SearchConfig(
    dt=5e-3,
    t_max=2.5,
    n_rate_trials=12,
    n_race_trials=24,
    p_scan=(0.0, 0.5, 1.0),
    race_pairs=((0.75, 0.25), (0.5, 0.5)),
    mismatch_levels=(0.02,),
    waiting_time_powers=(0.5,),
    seed=20260403,
)


def test_reduced_two_branch_weights_match_expected_rotation_slice() -> None:
    weights = reduced_two_branch_weights(30.0)
    assert abs(float(weights[0]) - 0.75) < 1e-12
    assert abs(float(weights[1]) - 0.25) < 1e-12


def test_build_next_steps_report_writes_artifact_folder(tmp_path: Path) -> None:
    outputs = build_next_steps_report(
        tmp_path,
        samples_per_model=2,
        top_k=1,
        grid_size=3,
        config=SMOKE_REPORT_CONFIG,
    )

    expected_files = {
        "results_summary.csv",
        "report.md",
        "poisson_linear_comparison.png",
        "shot_trigger_comparison.png",
        "metastable_escape_comparison.png",
        "shot_trigger_winner_region.csv",
        "shot_trigger_winner_region.png",
        "shot_trigger_integration.csv",
        "shot_trigger_integration.png",
    }

    assert expected_files.issubset({path.name for path in tmp_path.iterdir()})
    assert Path(outputs["summary_csv"]).exists()
    assert "Benchmark Triangle" in (tmp_path / "report.md").read_text(encoding="utf-8")
