from __future__ import annotations

import json
from pathlib import Path

from physical_front_end_candidate.experiments.refresh_common_inhibit_tuning_summary import (
    refresh_common_inhibit_tuning_summary,
)


def test_refresh_common_inhibit_tuning_summary_reclassifies_existing_outputs(tmp_path: Path) -> None:
    outdir = tmp_path / "tuning"
    outdir.mkdir()
    payload = {
        "summary_metrics": {},
        "baseline": {
            "control_tau_s": 0.1,
            "clamp_reference_g_on_s": 1.0,
            "winner_drain_g_on_s": 2.0,
            "winner_drain_tau_s": 0.08,
            "pre_click_transparency_rms_shift": 0.0,
            "mean_winner_drain_fraction": 0.80,
            "mean_loser_fraction": 0.01,
            "completion_rate": 1.0,
            "mean_completion_time_s": 0.2,
            "monotonic_remaining_energy": True,
            "mean_terminal_loser_suppression": 0.95,
            "mean_winner_drain_path_count": 0.95,
            "reduced_winner_fraction_abs_diff": 0.01,
            "reduced_loser_fraction_abs_diff": 0.01,
            "reduced_completion_rate_abs_diff": 0.0,
            "reduced_completion_time_abs_diff": 0.0,
            "guardrail_pass": True,
            "winner_dominance_pass": False,
            "completion_pass": True,
            "reduced_consistency_pass": True,
            "proceed_to_next_phase": False,
            "improvement_vs_baseline": 0.0,
        },
        "best_tuned": {},
        "sweep_rows": {
            "winner_drain_g_on_s": [
                {
                    "control_tau_s": 0.06,
                    "clamp_reference_g_on_s": 1.4,
                    "winner_drain_g_on_s": 3.2,
                    "winner_drain_tau_s": 0.04,
                    "pre_click_transparency_rms_shift": 0.0,
                    "mean_winner_drain_fraction": 0.967831,
                    "mean_loser_fraction": 0.002279,
                    "completion_rate": 1.0,
                    "mean_completion_time_s": 0.1,
                    "monotonic_remaining_energy": True,
                    "mean_terminal_loser_suppression": 0.997972,
                    "mean_winner_drain_path_count": 0.9941666666666666,
                    "reduced_winner_fraction_abs_diff": 0.01,
                    "reduced_loser_fraction_abs_diff": 0.01,
                    "reduced_completion_rate_abs_diff": 0.0,
                    "reduced_completion_time_abs_diff": 0.0,
                    "guardrail_pass": True,
                    "winner_dominance_pass": False,
                    "completion_pass": True,
                    "reduced_consistency_pass": True,
                    "proceed_to_next_phase": False,
                    "improvement_vs_baseline": 0.167831,
                    "score": 1.0,
                }
            ]
        },
        "comparison_row": {},
        "top_candidates": [],
        "outputs": {
            "parameter_sweeps_dir": str(outdir / "parameter_sweeps"),
            "best_candidate_dir": str(outdir / "best_candidate"),
            "design_md": str(outdir / "tuned_candidate_design_note.md"),
            "progress_json": str(outdir / "progress.json"),
            "top_candidates_csv": str(outdir / "top_winner_drain_candidates.csv"),
        },
    }
    (outdir / "summary_metrics.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    outputs = refresh_common_inhibit_tuning_summary(outdir)

    refreshed = json.loads((outdir / "summary_metrics.json").read_text(encoding="utf-8"))
    summary_metrics = refreshed["summary_metrics"]
    assert summary_metrics["winner_dominance_pass"] is True
    assert summary_metrics["winner_path_activation_pass"] is True
    assert summary_metrics["proceed_to_next_phase"] is True
    assert abs(summary_metrics["winner_path_activation_rate"] - 0.9941666666666666) < 1e-12
    assert Path(outputs["summary_md"]).exists()
    assert Path(outputs["summary_csv"]).exists()
    assert Path(outputs["top_candidates_csv"]).exists()
