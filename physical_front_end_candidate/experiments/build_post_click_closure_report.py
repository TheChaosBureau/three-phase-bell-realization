from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any
from collections.abc import Sequence

import numpy as np

from detector_integration.experiments.run_summary_report import load_top_shot_trigger_spec

from physical_front_end_candidate.closure_path import (
    closure_interpretations,
    run_four_branch_candidate_with_closure,
    simulate_four_branch_candidate_pre_click_race,
)
from physical_front_end_candidate.plots import (
    plot_closure_variable,
    plot_loser_suppression,
    plot_post_click_energy_partition,
    plot_remaining_shared_energy,
    plot_winner_drain_accumulation,
)
from physical_front_end_candidate.resonant_four_branch_candidate import benchmark_resonant_four_branch_cases, simulate_resonant_four_branch_candidate


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _json_default(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _interpretation_score(row: dict[str, Any]) -> float:
    return (
        4.0 * float(row["mean_winner_drain_fraction"])
        - 6.0 * float(row["mean_loser_fraction"])
        - 4.0 * float(row["pre_click_transparency_rms_shift"])
        + 1.5 * float(row["completion_rate"])
    )


def _summary_markdown(
    *,
    preferred: dict[str, Any],
    summary_metrics: dict[str, float | str | bool],
    outputs: dict[str, str],
) -> str:
    preferred_note = preferred["description"]
    return "\n".join(
        [
            "# Post-Click Closure / Drain Summary",
            "",
            "## Preferred Interpretation",
            "",
            f"- Preferred candidate: `{preferred['label']}`",
            f"- Closure variable: `{preferred['closure_variable_name']}(t)`",
            f"- Interpretation: {preferred_note}",
            "",
            "## Pre-Click Transparency",
            "",
            f"- Winner-law RMS transparency shift: {float(summary_metrics['pre_click_transparency_rms_shift']):.6f}",
            f"- Transparency pass: {bool(summary_metrics['pre_click_transparency_pass'])}",
            "",
            "## Post-Click Exclusivity",
            "",
            f"- Mean winner drain fraction: {float(summary_metrics['mean_winner_drain_fraction']):.6f}",
            f"- Mean loser residual fraction: {float(summary_metrics['mean_loser_fraction']):.6f}",
            f"- Winner drain dominance pass: {bool(summary_metrics['winner_dominance_pass'])}",
            "",
            "## Trial Completion",
            "",
            f"- Completion rate: {float(summary_metrics['completion_rate']):.6f}",
            f"- Mean completion time (s): {float(summary_metrics['mean_completion_time_s']):.6f}",
            f"- Monotonic shared energy: {bool(summary_metrics['monotonic_remaining_energy'])}",
            "",
            "## Design Note",
            "",
            "- Closure variable `Z(t)` rises only after `winner_valid=True`.",
            "- Non-winning branches are suppressed by the shared closure state, not by any pre-click feedback path.",
            "- A winner-associated drain path receives the dominant share of the remaining shared energy.",
            "- Trial-complete is defined by remaining shared energy falling below a fixed fraction of the captured post-click energy reservoir.",
            "- Reset / re-arm remains an external operation after the trial-complete condition.",
            "",
            "## Artifacts",
            "",
            f"- Reduced-model summary: `{outputs['reduced_model_csv']}`",
            f"- Integration summary: `{outputs['integration_csv']}`",
            f"- Design note: `{outputs['design_md']}`",
            "",
        ]
    )


def build_post_click_closure_report(
    outdir: str | Path = "artifacts/post_click_closure_spec",
    *,
    detector_next_summary_csv: str | Path = "artifacts/detector_next/results_summary.csv",
    n_trials: int = 24,
    seed: int = 20260403,
    interpretation_names: Sequence[str] | None = None,
    case_names: Sequence[str] | None = None,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    reduced_dir = output_dir / "reduced_model"
    integration_dir = output_dir / "integration"
    reduced_dir.mkdir(parents=True, exist_ok=True)
    integration_dir.mkdir(parents=True, exist_ok=True)

    detector_spec = load_top_shot_trigger_spec(detector_next_summary_csv)
    detector_model_spec = {
        "family": detector_spec["family"],
        "model_params": dict(detector_spec["model_params"]),
        "gain_scale": 2.0,
    }

    interpretation_rows: list[dict[str, Any]] = []
    integration_rows: list[dict[str, Any]] = []
    example_closure: dict[str, Any] | None = None
    preferred_result: dict[str, Any] | None = None

    selected_interpretation_names = None if interpretation_names is None else set(interpretation_names)
    selected_case_names = None if case_names is None else set(case_names)
    interpretations = [
        interpretation
        for interpretation in closure_interpretations()
        if selected_interpretation_names is None or interpretation.name in selected_interpretation_names
    ]
    cases = [
        case
        for case in benchmark_resonant_four_branch_cases()
        if selected_case_names is None or case["case"] in selected_case_names
    ]

    if not interpretations:
        raise ValueError("No closure interpretations selected.")
    if not cases:
        raise ValueError("No resonant benchmark cases selected.")

    case_runs: list[tuple[int, dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    for case_index, case in enumerate(cases):
        candidate = simulate_resonant_four_branch_candidate(case["state4"], a_deg=case["a_deg"], b_deg=case["b_deg"])
        race_result = simulate_four_branch_candidate_pre_click_race(
            candidate,
            detector_model_spec,
            n_trials=n_trials,
            seed=seed + 1_003 * case_index,
        )
        case_runs.append((case_index, case, candidate, race_result))

    for interp_index, interpretation in enumerate(interpretations):
        case_rows: list[dict[str, Any]] = []
        for case_index, case, candidate, race_result in case_runs:
            result = run_four_branch_candidate_with_closure(
                candidate,
                detector_model_spec,
                interpretation=interpretation,
                n_trials=n_trials,
                seed=seed + 10_000 * interp_index + 1_003 * case_index,
                race_result=race_result,
            )
            case_row = {
                "interpretation": interpretation.name,
                "label": interpretation.label,
                "case": case["case"],
                "a_deg": case["a_deg"],
                "b_deg": case["b_deg"],
                "winner_rms_error": float(result["metrics"]["rms_error"]),
                "winner_max_error": float(result["metrics"]["max_abs_error"]),
                "correlator_error": float(result["metrics"]["correlator_error"]),
                "decisive_fraction": float(result["decisive_fraction"]),
                "pre_click_transparency_rms_shift": float(result["closure_metrics"]["pre_click_transparency_rms_shift"]),
                "winner_drain_fraction": float(result["closure_metrics"]["mean_winner_drain_fraction"]),
                "loser_fraction": float(result["closure_metrics"]["mean_loser_fraction"]),
                "completion_rate": float(result["closure_metrics"]["completion_rate"]),
                "mean_completion_time_s": float(result["closure_metrics"]["mean_completion_time_s"]),
                "monotonic_remaining_energy": bool(result["closure_metrics"]["monotonic_remaining_energy"]),
            }
            case_rows.append(case_row)
            integration_rows.append(case_row)
            if example_closure is None and result["example_trial"] is not None:
                example_closure = {
                    "interpretation": interpretation,
                    "closure": result["example_trial"]["closure"],
                }

        winner_drain_fraction = float(np.mean([row["winner_drain_fraction"] for row in case_rows]))
        loser_fraction = float(np.mean([row["loser_fraction"] for row in case_rows]))
        transparency_shift = float(np.sqrt(np.mean(np.square([row["pre_click_transparency_rms_shift"] for row in case_rows]))))
        completion_rate = float(np.mean([row["completion_rate"] for row in case_rows]))
        completion_time = float(np.mean([row["mean_completion_time_s"] for row in case_rows]))
        monotonic = bool(all(bool(row["monotonic_remaining_energy"]) for row in case_rows))
        interpretation_row = {
            "interpretation": interpretation.name,
            "label": interpretation.label,
            "closure_variable_name": interpretation.closure_variable_name,
            "description": interpretation.description,
            "mean_winner_drain_fraction": winner_drain_fraction,
            "mean_loser_fraction": loser_fraction,
            "pre_click_transparency_rms_shift": transparency_shift,
            "completion_rate": completion_rate,
            "mean_completion_time_s": completion_time,
            "monotonic_remaining_energy": monotonic,
            "score": _interpretation_score(
                {
                    "mean_winner_drain_fraction": winner_drain_fraction,
                    "mean_loser_fraction": loser_fraction,
                    "pre_click_transparency_rms_shift": transparency_shift,
                    "completion_rate": completion_rate,
                }
            ),
        }
        interpretation_rows.append(interpretation_row)
        if preferred_result is None or float(interpretation_row["score"]) > float(preferred_result["score"]):
            preferred_result = dict(interpretation_row)

    if preferred_result is None:
        raise RuntimeError("No closure interpretation results were produced.")

    reduced_model_csv = reduced_dir / "closure_interpretations.csv"
    integration_csv = integration_dir / "integration_summary.csv"
    _write_csv(reduced_model_csv, interpretation_rows)
    _write_csv(integration_csv, integration_rows)

    if example_closure is not None:
        closure = example_closure["closure"]
        variable_name = example_closure["interpretation"].closure_variable_name
        plot_closure_variable(closure, variable_name=variable_name).savefig(reduced_dir / "closure_variable.png")
        plot_remaining_shared_energy(closure).savefig(reduced_dir / "remaining_shared_energy.png")
        plot_winner_drain_accumulation(closure).savefig(reduced_dir / "winner_drain_accumulation.png")
        plot_loser_suppression(closure).savefig(reduced_dir / "loser_suppression.png")
        _write_csv(
            reduced_dir / "example_closure_trace.csv",
            [
                {
                    "time_s": closure["time_s"][index],
                    "closure_variable": closure["closure_variable"][index],
                    "remaining_shared_energy_j": closure["remaining_shared_energy_j"][index],
                    "winner_drain_energy_j": closure["winner_drain_energy_j"][index],
                    **{f"{label}_suppression": values[index] for label, values in closure["loser_suppression"].items()},
                }
                for index in range(len(closure["time_s"]))
            ],
        )

    plot_post_click_energy_partition(interpretation_rows).savefig(integration_dir / "post_click_energy_partition.png")

    preferred = preferred_result
    summary_metrics = {
        "preferred_interpretation": preferred["label"],
        "closure_variable_name": preferred["closure_variable_name"],
        "mean_winner_drain_fraction": float(preferred["mean_winner_drain_fraction"]),
        "mean_loser_fraction": float(preferred["mean_loser_fraction"]),
        "pre_click_transparency_rms_shift": float(preferred["pre_click_transparency_rms_shift"]),
        "completion_rate": float(preferred["completion_rate"]),
        "mean_completion_time_s": float(preferred["mean_completion_time_s"]),
        "monotonic_remaining_energy": bool(preferred["monotonic_remaining_energy"]),
        "pre_click_transparency_pass": float(preferred["pre_click_transparency_rms_shift"]) < 0.01,
        "winner_dominance_pass": float(preferred["mean_winner_drain_fraction"]) > 0.75 and float(preferred["mean_loser_fraction"]) < 0.1,
    }

    summary_csv = output_dir / "summary_metrics.csv"
    _write_csv(summary_csv, [{"metric": key, "value": value} for key, value in summary_metrics.items()])

    design_md = output_dir / "closure_design_note.md"
    design_md.write_text(
        "\n".join(
            [
                "# Closure / Drain Design Note",
                "",
                "## Closure Variable",
                "",
                f"- Shared closure variable: `{preferred['closure_variable_name']}(t)`.",
                "- Meaning: a shared post-click closure state driven only by `winner_valid` and `winner_index` after latch capture.",
                "",
                "## Winner Drain Path",
                "",
                "- Winner-valid enables a winner-associated drain path once the latch settles.",
                "- The drain path receives the dominant share of the remaining stored/shared energy.",
                "",
                "## Loser Suppression",
                "",
                "- Non-winning branches are attenuated as a monotone function of the shared closure variable.",
                "- Suppression begins only after winner capture; no pre-click race feedback is introduced.",
                "",
                "## Trial Completion",
                "",
                "- Trial-complete is declared when the remaining shared energy falls below a fixed fraction of the post-click reservoir.",
                "- The reduced model also records a reproducible completion time for each trial.",
                "",
                "## Reset / Re-Arm",
                "",
                "- Reset remains external to this ticket.",
                "- Re-arm assumes the shared energy reservoir is near zero and the latch/detector state has been reset between trials.",
                "",
                "## Candidate Physical Interpretations",
                "",
                "1. Winner-gated common shunt.",
                "2. Shared bias collapse controlled by the winner latch.",
                "3. Common-mode inhibit plus winner-only drain enable.",
                "4. Zero-sequence-like closure state coupled to all branches.",
                "5. Coupled-port recombination drain activated by winner selection.",
                "",
                "## Preferred Candidate",
                "",
                f"- `{preferred['label']}` was selected as the best reduced interpretation under the current score.",
                f"- Interpretation note: {preferred['description']}",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    outputs = {
        "reduced_model_csv": str(reduced_model_csv),
        "integration_csv": str(integration_csv),
        "design_md": str(design_md),
    }
    summary_json = output_dir / "summary_metrics.json"
    summary_json.write_text(
        json.dumps(
            {
                "summary_metrics": summary_metrics,
                "interpretations": interpretation_rows,
                "integration_rows": integration_rows,
                "preferred": preferred,
                "outputs": outputs,
            },
            indent=2,
            default=_json_default,
        )
        + "\n",
        encoding="utf-8",
    )
    summary_md = output_dir / "summary_report.md"
    summary_md.write_text(_summary_markdown(preferred=preferred, summary_metrics=summary_metrics, outputs=outputs) + "\n", encoding="utf-8")
    return {
        "summary_md": str(summary_md),
        "summary_json": str(summary_json),
        "summary_csv": str(summary_csv),
        "reduced_model_csv": str(reduced_model_csv),
        "integration_csv": str(integration_csv),
        "design_md": str(design_md),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the post-click closure / drain specification report.")
    parser.add_argument("--outdir", default="artifacts/post_click_closure_spec")
    parser.add_argument("--detector-next-summary", default="artifacts/detector_next/results_summary.csv")
    parser.add_argument("--trials", type=int, default=24)
    args = parser.parse_args()
    build_post_click_closure_report(
        args.outdir,
        detector_next_summary_csv=args.detector_next_summary,
        n_trials=args.trials,
    )


if __name__ == "__main__":
    main()
