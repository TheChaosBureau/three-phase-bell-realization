from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from physical_front_end_candidate.common_inhibit_tuning import _candidate_rank, _top_candidate_rank
from physical_front_end_candidate.experiments.build_common_inhibit_tuning_report import (
    _json_default,
    _summary_markdown,
    _write_csv,
)


def _derive_activation_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    derived = dict(metrics)
    activation_rate = float(derived.get("winner_path_activation_rate", derived.get("mean_winner_drain_path_count", 0.0)))
    derived["winner_path_activation_rate"] = activation_rate

    if "mean_activated_winner_drain_fraction" not in derived:
        derived["mean_activated_winner_drain_fraction"] = (
            float(derived.get("mean_winner_drain_fraction", 0.0)) / activation_rate if activation_rate > 0.0 else 0.0
        )
    if "mean_activated_loser_fraction" not in derived:
        derived["mean_activated_loser_fraction"] = (
            float(derived.get("mean_loser_fraction", 0.0)) / activation_rate if activation_rate > 0.0 else 0.0
        )
    if "mean_activated_terminal_loser_suppression" not in derived:
        derived["mean_activated_terminal_loser_suppression"] = float(
            derived.get("mean_terminal_loser_suppression", 0.0)
        )

    derived["pre_click_transparency_pass"] = float(derived.get("pre_click_transparency_rms_shift", 0.0)) < 0.01
    derived["winner_dominance_pass"] = (
        activation_rate > 0.0
        and float(derived["mean_activated_winner_drain_fraction"]) > 0.88
        and float(derived["mean_activated_loser_fraction"]) < 0.02
        and float(derived["mean_activated_terminal_loser_suppression"]) > 0.93
    )
    derived["winner_path_activation_pass"] = activation_rate >= 0.99
    derived["completion_pass"] = float(derived.get("completion_rate", 0.0)) > 0.9 and bool(
        derived.get("monotonic_remaining_energy", False)
    )
    derived["reduced_consistency_pass"] = (
        float(derived.get("reduced_winner_fraction_abs_diff", 0.0)) < 0.12
        and float(derived.get("reduced_loser_fraction_abs_diff", 0.0)) < 0.05
        and float(derived.get("reduced_completion_rate_abs_diff", 0.0)) < 0.1
    )
    derived["guardrail_pass"] = (
        bool(derived["pre_click_transparency_pass"])
        and bool(derived["completion_pass"])
        and bool(derived["reduced_consistency_pass"])
        and float(derived.get("mean_loser_fraction", 0.0)) < 0.02
        and float(derived.get("mean_terminal_loser_suppression", 0.0)) > 0.93
    )
    derived["proceed_to_next_phase"] = (
        bool(derived["guardrail_pass"])
        and bool(derived["winner_dominance_pass"])
        and bool(derived["winner_path_activation_pass"])
    )
    return derived


def _candidate_row_from_metrics(metrics: dict[str, Any], *, source: str) -> dict[str, Any]:
    row = {
        "source": source,
        "control_tau_s": float(metrics["control_tau_s"]),
        "clamp_reference_g_on_s": float(metrics["clamp_reference_g_on_s"]),
        "winner_drain_g_on_s": float(metrics["winner_drain_g_on_s"]),
        "winner_drain_tau_s": float(metrics["winner_drain_tau_s"]),
        "mean_winner_drain_fraction": float(metrics["mean_winner_drain_fraction"]),
        "mean_loser_fraction": float(metrics["mean_loser_fraction"]),
        "winner_path_activation_rate": float(metrics["winner_path_activation_rate"]),
        "mean_activated_winner_drain_fraction": float(metrics["mean_activated_winner_drain_fraction"]),
        "mean_activated_loser_fraction": float(metrics["mean_activated_loser_fraction"]),
        "mean_terminal_loser_suppression": float(metrics["mean_terminal_loser_suppression"]),
        "mean_activated_terminal_loser_suppression": float(metrics["mean_activated_terminal_loser_suppression"]),
        "completion_rate": float(metrics["completion_rate"]),
        "mean_completion_time_s": float(metrics["mean_completion_time_s"]),
        "pre_click_transparency_rms_shift": float(metrics["pre_click_transparency_rms_shift"]),
        "guardrail_pass": bool(metrics["guardrail_pass"]),
        "winner_dominance_pass": bool(metrics["winner_dominance_pass"]),
        "winner_path_activation_pass": bool(metrics["winner_path_activation_pass"]),
        "proceed_to_next_phase": bool(metrics["proceed_to_next_phase"]),
        "score": float(metrics.get("score", 0.0)),
    }
    return row


def _design_note_markdown(*, baseline_metrics: dict[str, Any], tuned_metrics: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Tuned Common Inhibit Candidate",
            "",
            "## Refresh Note",
            "",
            "- This note was regenerated from existing sweep outputs without rerunning the tuning search.",
            "- Dominance is now evaluated on activated trials only.",
            "- Winner path activation reliability is reported separately.",
            "",
            "## What Changed Relative To First Candidate",
            "",
            f"- Baseline winner drain fraction (all trials): {float(baseline_metrics['mean_winner_drain_fraction']):.6f}",
            f"- Tuned winner drain fraction (all trials): {float(tuned_metrics['mean_winner_drain_fraction']):.6f}",
            f"- Baseline winner drain fraction (activated trials): {float(baseline_metrics['mean_activated_winner_drain_fraction']):.6f}",
            f"- Tuned winner drain fraction (activated trials): {float(tuned_metrics['mean_activated_winner_drain_fraction']):.6f}",
            f"- Baseline winner path activation rate: {float(baseline_metrics['winner_path_activation_rate']):.6f}",
            f"- Tuned winner path activation rate: {float(tuned_metrics['winner_path_activation_rate']):.6f}",
            "",
            "## Best Tuned Configuration",
            "",
            f"- `control_tau_s = {float(tuned_metrics['control_tau_s']):.6f}`",
            f"- `clamp_reference_g_on_s = {float(tuned_metrics['clamp_reference_g_on_s']):.6f}`",
            f"- `winner_drain_g_on_s = {float(tuned_metrics['winner_drain_g_on_s']):.6f}`",
            f"- `winner_drain_tau_s = {float(tuned_metrics['winner_drain_tau_s']):.6f}`",
            "",
        ]
    )


def refresh_common_inhibit_tuning_summary(
    outdir: str | Path = "artifacts/physical_closure_drain_tuning",
) -> dict[str, str]:
    output_dir = Path(outdir)
    summary_json = output_dir / "summary_metrics.json"
    if not summary_json.exists():
        raise FileNotFoundError(f"Missing tuning summary JSON: {summary_json}")

    payload = json.loads(summary_json.read_text(encoding="utf-8"))
    outputs = dict(payload.get("outputs", {}))
    outputs.setdefault("parameter_sweeps_dir", str(output_dir / "parameter_sweeps"))
    outputs.setdefault("best_candidate_dir", str(output_dir / "best_candidate"))
    outputs.setdefault("design_md", str(output_dir / "tuned_candidate_design_note.md"))
    outputs.setdefault("progress_json", str(output_dir / "progress.json"))
    outputs.setdefault("top_candidates_csv", str(output_dir / "top_winner_drain_candidates.csv"))

    baseline_metrics = _derive_activation_metrics(dict(payload["baseline"]))
    candidate_entries: list[tuple[str, dict[str, Any]]] = [("baseline", baseline_metrics)]
    refreshed_sweep_rows: dict[str, list[dict[str, Any]]] = {}
    for source, rows in dict(payload.get("sweep_rows", {})).items():
        refreshed_rows: list[dict[str, Any]] = []
        for row in rows:
            refreshed_row = _derive_activation_metrics(dict(row))
            refreshed_rows.append(refreshed_row)
            candidate_entries.append((source, refreshed_row))
        refreshed_sweep_rows[source] = refreshed_rows

    tuned_source, tuned_metrics = max(candidate_entries, key=lambda item: _candidate_rank(item[1]))
    top_candidates = sorted(
        (_candidate_row_from_metrics(metrics, source=source) for source, metrics in candidate_entries),
        key=_top_candidate_rank,
        reverse=True,
    )[:10]

    comparison_row = {
        "winner_drain_fraction_delta": float(tuned_metrics["mean_winner_drain_fraction"])
        - float(baseline_metrics["mean_winner_drain_fraction"]),
        "activated_winner_drain_fraction_delta": float(tuned_metrics["mean_activated_winner_drain_fraction"])
        - float(baseline_metrics["mean_activated_winner_drain_fraction"]),
        "loser_fraction_delta": float(tuned_metrics["mean_loser_fraction"]) - float(baseline_metrics["mean_loser_fraction"]),
        "terminal_loser_suppression_delta": float(tuned_metrics["mean_terminal_loser_suppression"])
        - float(baseline_metrics["mean_terminal_loser_suppression"]),
        "winner_path_activation_rate_delta": float(tuned_metrics["winner_path_activation_rate"])
        - float(baseline_metrics["winner_path_activation_rate"]),
        "completion_rate_delta": float(tuned_metrics["completion_rate"]) - float(baseline_metrics["completion_rate"]),
        "mean_completion_time_delta_s": float(tuned_metrics["mean_completion_time_s"])
        - float(baseline_metrics["mean_completion_time_s"]),
        "pre_click_transparency_shift_delta": float(tuned_metrics["pre_click_transparency_rms_shift"])
        - float(baseline_metrics["pre_click_transparency_rms_shift"]),
    }

    summary_metrics = {
        **tuned_metrics,
        "baseline_mean_winner_drain_fraction": float(baseline_metrics["mean_winner_drain_fraction"]),
        "baseline_mean_activated_winner_drain_fraction": float(
            baseline_metrics["mean_activated_winner_drain_fraction"]
        ),
        "baseline_mean_loser_fraction": float(baseline_metrics["mean_loser_fraction"]),
        "baseline_mean_terminal_loser_suppression": float(baseline_metrics["mean_terminal_loser_suppression"]),
        "baseline_winner_path_activation_rate": float(baseline_metrics["winner_path_activation_rate"]),
        "baseline_completion_rate": float(baseline_metrics["completion_rate"]),
        "winner_drain_fraction_delta": comparison_row["winner_drain_fraction_delta"],
        "activated_winner_drain_fraction_delta": comparison_row["activated_winner_drain_fraction_delta"],
        "loser_fraction_delta": comparison_row["loser_fraction_delta"],
        "terminal_loser_suppression_delta": comparison_row["terminal_loser_suppression_delta"],
        "winner_path_activation_rate_delta": comparison_row["winner_path_activation_rate_delta"],
        "completion_rate_delta": comparison_row["completion_rate_delta"],
        "best_tuned_source": tuned_source,
    }

    top_candidates_csv = Path(outputs["top_candidates_csv"])
    _write_csv(top_candidates_csv, list(top_candidates))
    _write_csv(output_dir / "first_candidate_comparison.csv", [comparison_row])
    _write_csv(output_dir / "summary_metrics.csv", [{"metric": key, "value": value} for key, value in summary_metrics.items()])

    design_md = Path(outputs["design_md"])
    design_md.write_text(
        _design_note_markdown(baseline_metrics=baseline_metrics, tuned_metrics=tuned_metrics) + "\n",
        encoding="utf-8",
    )

    refreshed_payload = {
        "summary_metrics": summary_metrics,
        "baseline": baseline_metrics,
        "best_tuned": tuned_metrics,
        "sweep_rows": refreshed_sweep_rows,
        "comparison_row": comparison_row,
        "top_candidates": top_candidates,
        "outputs": outputs,
    }
    summary_json.write_text(json.dumps(refreshed_payload, indent=2, default=_json_default) + "\n", encoding="utf-8")

    summary_md = output_dir / "summary_report.md"
    summary_md.write_text(
        _summary_markdown(
            baseline={"summary_metrics": baseline_metrics},
            tuned={"summary_metrics": tuned_metrics, "source": tuned_source},
            comparison_row=comparison_row,
            outputs=outputs,
            top_candidates=top_candidates,
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
        "summary_csv": str(output_dir / "summary_metrics.csv"),
        "design_md": str(design_md),
        "top_candidates_csv": str(top_candidates_csv),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh a common-inhibit tuning summary from existing sweep outputs.")
    parser.add_argument("--outdir", default="artifacts/physical_closure_drain_tuning")
    args = parser.parse_args()
    refresh_common_inhibit_tuning_summary(args.outdir)


if __name__ == "__main__":
    main()
