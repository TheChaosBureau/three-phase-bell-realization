from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from detector_integration.experiments.run_summary_report import load_top_shot_trigger_spec

from physical_front_end_candidate.export_interface import (
    HandoffExportConfig,
    build_detector_handoff_envelopes,
    export_mode_slug,
    render_envelope_traces,
    resolve_envelope_config,
)
from physical_front_end_candidate.integration import run_two_branch_physical_handoff
from physical_front_end_candidate.metrics import common_envelope_fidelity_metrics, energy_preservation_metrics
from physical_front_end_candidate.plots import (
    plot_export_comparison,
    plot_gamma_overlay,
    plot_mode_case_residuals,
    plot_mode_error_comparison,
    plot_power_envelopes,
    plot_winner_frequency,
)
from physical_front_end_candidate.two_branch_candidate import representative_physical_cases, simulate_two_branch_physical_candidate


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


def _mode_label(config: HandoffExportConfig) -> str:
    if config.mode == "piecewise_envelope":
        return f"piecewise:{config.piecewise_mode}:{1_000.0 * config.piecewise_bin_width_s:.1f}ms"
    return config.mode


def _aggregate_mode_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["mode_slug"]), []).append(row)
    summary_rows: list[dict[str, Any]] = []
    for mode_slug, values in grouped.items():
        summary_rows.append(
            {
                "mode_slug": mode_slug,
                "mode_family": values[0]["mode_family"],
                "mode_label": values[0]["mode_label"],
                "winner_rms_error": float(np.sqrt(np.mean([float(row["rms_error"]) ** 2 for row in values]))),
                "winner_max_error": float(np.max([float(row["max_abs_error"]) for row in values])),
                "mean_decisive_fraction": float(np.mean([float(row["decisive_fraction"]) for row in values])),
                "common_envelope_rms": float(np.sqrt(np.mean([float(row["common_envelope_rms"]) ** 2 for row in values]))),
                "common_envelope_max": float(np.max([float(row["common_envelope_max"]) for row in values])),
                "mean_branch_energy_rel_error": float(np.mean([float(row["branch_energy_rel_error_mean"]) for row in values])),
                "complexity_note": values[0]["complexity_note"],
                "interpretability_note": values[0]["interpretability_note"],
            }
        )
    return sorted(summary_rows, key=lambda row: (float(row["winner_rms_error"]), float(row["winner_max_error"])))


def _comparison_markdown(
    *,
    selected_mode: dict[str, Any],
    comparison_rows: list[dict[str, Any]],
    summary_metrics: dict[str, Any],
    acceptance: dict[str, Any],
    outputs: dict[str, str],
) -> str:
    lines = [
        "# Physical Front-End Handoff Refinement Summary",
        "",
        "## Selected Mode",
        "",
        f"- Mode: `{selected_mode['mode_label']}`",
        f"- Winner-law RMS error: {float(selected_mode['winner_rms_error']):.6f}",
        f"- Winner-law max error: {float(selected_mode['winner_max_error']):.6f}",
        f"- Mean decisive fraction: {float(selected_mode['mean_decisive_fraction']):.6f}",
        f"- Common-envelope RMS mismatch: {float(selected_mode['common_envelope_rms']):.6f}",
        f"- Decision: {acceptance['recommended_next_ticket']}",
        "",
        "## Mode Comparison",
        "",
        "| mode | RMS winner error | max winner error | decisive fraction | common-envelope RMS |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in comparison_rows:
        lines.append(
            f"| {row['mode_label']} | {float(row['winner_rms_error']):.6f} | {float(row['winner_max_error']):.6f} | "
            f"{float(row['mean_decisive_fraction']):.6f} | {float(row['common_envelope_rms']):.6f} |"
        )
    lines.extend(
        [
            "",
            "## Acceptance",
            "",
            f"- Front-end-only RMS fraction error preserved: {acceptance['front_end_preserved']}",
            f"- Selected handoff RMS winner-law error < 0.03: {acceptance['selected_mode_pass']}",
            f"- Selected handoff max winner-law error < 0.05: {acceptance['selected_mode_max_pass']}",
            f"- Stretch target RMS < 0.02: {acceptance['stretch_target_pass']}",
            f"- Proceed to next phase: {acceptance['proceed_to_next_phase']}",
            "",
            "## Artifacts",
            "",
            f"- Summary metrics: `{outputs['summary_csv']}`",
            f"- Comparison CSV: `{outputs['comparison_csv']}`",
            f"- Handoff design note: `{outputs['handoff_note']}`",
            f"- Winner-law plot: `{outputs['winner_plot']}`",
            f"- Common-envelope plot: `{outputs['gamma_plot']}`",
            "",
        ]
    )
    return "\n".join(lines)


def build_physical_front_end_handoff_report(
    outdir: str | Path = "artifacts/physical_front_end_handoff",
    *,
    detector_next_summary_csv: str | Path = "artifacts/detector_next/results_summary.csv",
    n_trials: int = 240,
    seed: int = 20260403,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    direct_dir = output_dir / "direct_trace"
    piecewise_dir = output_dir / "piecewise_envelope"
    exponential_dir = output_dir / "exponential_fit"
    comparison_dir = output_dir / "comparison"
    for directory in (direct_dir, piecewise_dir, exponential_dir, comparison_dir):
        directory.mkdir(parents=True, exist_ok=True)

    detector_spec = load_top_shot_trigger_spec(detector_next_summary_csv)
    detector_model_spec = {"family": detector_spec["family"], "model_params": dict(detector_spec["model_params"])}

    direct_config = HandoffExportConfig(mode="direct_trace")
    exponential_config = HandoffExportConfig(mode="exponential_fit")
    piecewise_configs = [
        HandoffExportConfig(mode="piecewise_envelope", piecewise_mode="constant", piecewise_bin_width_s=5e-3),
        HandoffExportConfig(mode="piecewise_envelope", piecewise_mode="constant", piecewise_bin_width_s=2e-2),
        HandoffExportConfig(mode="piecewise_envelope", piecewise_mode="linear", piecewise_bin_width_s=5e-3),
        HandoffExportConfig(mode="piecewise_envelope", piecewise_mode="linear", piecewise_bin_width_s=2e-2),
    ]
    all_configs = [direct_config, *piecewise_configs, exponential_config]

    branch_plot_rows: list[dict[str, Any]] = []
    mode_case_rows: list[dict[str, Any]] = []
    piecewise_rows: list[dict[str, Any]] = []
    raw_common_rows: list[dict[str, Any]] = []
    export_examples: dict[str, dict[str, Any]] = {}
    full_results: list[dict[str, Any]] = []

    for case_index, case in enumerate(representative_physical_cases()):
        candidate = simulate_two_branch_physical_candidate(case["state"], case["analyzer"])
        branch_labels = list(candidate["branch_labels"])
        time_s = np.asarray(candidate["time_s"], dtype=float)
        envelope_config = resolve_envelope_config(candidate["envelope_config"])

        branch_plot_rows.append(
            {
                "case": case["case"],
                "time_s": candidate["time_s"],
                "branch_power_1": candidate["branch_power_w"]["branch_1"],
                "branch_power_2": candidate["branch_power_w"]["branch_2"],
            }
        )
        raw_common = common_envelope_fidelity_metrics(branch_labels, candidate["branch_power_w"], candidate["exact_weight"])
        raw_common_rows.append(
            {
                "case": case["case"],
                "time_s": candidate["time_s"],
                "gamma_branch_1": raw_common["gamma"].get("branch_1", np.full_like(time_s, np.nan)).tolist(),
                "gamma_branch_2": raw_common["gamma"].get("branch_2", np.full_like(time_s, np.nan)).tolist(),
            }
        )

        raw_trace_rows = [
            {
                "time_s": time_s[index],
                "branch_power_1_w": float(candidate["branch_power_w"]["branch_1"][index]),
                "branch_power_2_w": float(candidate["branch_power_w"]["branch_2"][index]),
            }
            for index in range(time_s.size)
        ]
        _write_csv(direct_dir / f"{case['case']}_raw_traces.csv", raw_trace_rows)

        for config_index, config in enumerate(all_configs):
            detector_envelopes = build_detector_handoff_envelopes(
                candidate["branch_power_w"],
                time_s=candidate["time_s"],
                branch_labels=branch_labels,
                envelope_config=envelope_config,
                export_config=config,
            )
            exported_branch_power = render_envelope_traces(detector_envelopes, sample_time_s=candidate["time_s"], branch_labels=branch_labels)
            common_metrics = common_envelope_fidelity_metrics(branch_labels, exported_branch_power, candidate["exact_weight"])

            energy_metrics = [
                energy_preservation_metrics(candidate["time_s"], candidate["branch_power_w"][label], exported_branch_power[label])
                for label in branch_labels
            ]
            energy_rel_mean = float(np.mean([metric["rel_error"] for metric in energy_metrics]))

            run = run_two_branch_physical_handoff(
                case["state"],
                case["analyzer"],
                detector_model_spec,
                n_trials=n_trials,
                seed=seed + 997 * case_index + 31 * config_index,
                export_config=asdict(config),
            )

            if config.mode == "direct_trace":
                mode_dir = direct_dir
                complexity_note = "highest detector-side load, lowest export distortion"
                interpretability_note = "closest to measured branch power"
            elif config.mode == "piecewise_envelope":
                mode_dir = piecewise_dir
                complexity_note = "moderate detector-side load, tunable compression"
                interpretability_note = "preserves coarse time structure with explicit binning"
            else:
                mode_dir = exponential_dir
                complexity_note = "lowest detector-side load, strongest model assumption"
                interpretability_note = "assumes a shared exponential envelope"

            mode_slug = export_mode_slug(config)
            mode_label = _mode_label(config)
            exported_rows = [
                {
                    "time_s": time_s[index],
                    "branch_power_1_w": float(candidate["branch_power_w"]["branch_1"][index]),
                    "branch_power_2_w": float(candidate["branch_power_w"]["branch_2"][index]),
                    "exported_power_1_w": float(exported_branch_power["branch_1"][index]),
                    "exported_power_2_w": float(exported_branch_power["branch_2"][index]),
                }
                for index in range(time_s.size)
            ]
            _write_csv(mode_dir / f"{case['case']}_{mode_slug}_export.csv", exported_rows)

            mode_case_row = {
                "case": case["case"],
                "mode_slug": mode_slug,
                "mode_family": config.mode,
                "mode_label": mode_label,
                "piecewise_mode": config.piecewise_mode if config.mode == "piecewise_envelope" else "",
                "piecewise_bin_width_s": float(config.piecewise_bin_width_s) if config.mode == "piecewise_envelope" else "",
                "exact_p1": float(run["exact_weights"][0]),
                "empirical_p1": float(run["empirical_frequencies"][0]),
                "exact_p2": float(run["exact_weights"][1]),
                "empirical_p2": float(run["empirical_frequencies"][1]),
                "rms_error": float(run["metrics"]["rms_error"]),
                "max_abs_error": float(run["metrics"]["max_abs_error"]),
                "decisive_fraction": float(run["decisive_fraction"]),
                "timeout_fraction": float(run["timeout_fraction"]),
                "common_envelope_rms": float(common_metrics["rms_difference"]),
                "common_envelope_max": float(common_metrics["max_abs_difference"]),
                "branch_energy_rel_error_mean": energy_rel_mean,
                "complexity_note": complexity_note,
                "interpretability_note": interpretability_note,
            }
            mode_case_rows.append(mode_case_row)
            if config.mode == "piecewise_envelope":
                piecewise_rows.append(dict(mode_case_row))

            if mode_slug not in export_examples:
                export_examples[mode_slug] = {
                    "case": case["case"],
                    "time_s": candidate["time_s"],
                    "branch_power_1": candidate["branch_power_w"]["branch_1"],
                    "branch_power_2": candidate["branch_power_w"]["branch_2"],
                    "export_power_1": exported_branch_power["branch_1"],
                    "export_power_2": exported_branch_power["branch_2"],
                }

            full_results.append(
                {
                    "case": case["case"],
                    "config": asdict(config),
                    "run": run,
                    "common_envelope": common_metrics,
                    "energy_metrics": energy_metrics,
                }
            )

    mode_summary_rows = _aggregate_mode_rows(mode_case_rows)
    piecewise_summary_rows = [row for row in mode_summary_rows if row["mode_family"] == "piecewise_envelope"]
    best_piecewise = piecewise_summary_rows[0]
    comparison_rows = [
        next(row for row in mode_summary_rows if row["mode_family"] == "direct_trace"),
        best_piecewise,
        next(row for row in mode_summary_rows if row["mode_family"] == "exponential_fit"),
    ]
    selected_mode = min(comparison_rows, key=lambda row: (float(row["winner_rms_error"]), float(row["winner_max_error"])))

    direct_case_rows = [row for row in mode_case_rows if row["mode_family"] == "direct_trace"]
    best_piecewise_case_rows = [row for row in mode_case_rows if row["mode_slug"] == best_piecewise["mode_slug"]]
    exponential_case_rows = [row for row in mode_case_rows if row["mode_family"] == "exponential_fit"]

    _write_csv(direct_dir / "integration_summary.csv", direct_case_rows)
    _write_csv(piecewise_dir / "sensitivity_summary.csv", piecewise_rows)
    _write_csv(piecewise_dir / "integration_summary.csv", best_piecewise_case_rows)
    _write_csv(exponential_dir / "integration_summary.csv", exponential_case_rows)
    comparison_csv = comparison_dir / "mode_comparison.csv"
    _write_csv(comparison_csv, comparison_rows)

    (direct_dir / "integration_summary.json").write_text(json.dumps({"rows": direct_case_rows}, indent=2, default=_json_default) + "\n", encoding="utf-8")
    (piecewise_dir / "integration_summary.json").write_text(
        json.dumps({"selected_rows": best_piecewise_case_rows, "sensitivity_rows": piecewise_rows}, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    (exponential_dir / "integration_summary.json").write_text(json.dumps({"rows": exponential_case_rows}, indent=2, default=_json_default) + "\n", encoding="utf-8")
    (comparison_dir / "comparison.json").write_text(
        json.dumps({"mode_summary_rows": mode_summary_rows, "selected_mode": selected_mode, "full_results": full_results}, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )

    branch_plot = comparison_dir / "branch_power_traces.png"
    plot_power_envelopes(branch_plot_rows).savefig(branch_plot)
    raw_gamma_plot = comparison_dir / "gamma_overlay.png"
    plot_gamma_overlay(raw_common_rows).savefig(raw_gamma_plot)
    winner_plot = comparison_dir / "winner_law_error_by_mode.png"
    plot_mode_error_comparison(comparison_rows).savefig(winner_plot)
    residual_plot = comparison_dir / "residual_error_summary.png"
    plot_mode_case_residuals(direct_case_rows + best_piecewise_case_rows + exponential_case_rows).savefig(residual_plot)

    for row in comparison_rows:
        example = export_examples[row["mode_slug"]]
        plot_export_comparison(example).savefig((direct_dir if row["mode_family"] == "direct_trace" else piecewise_dir if row["mode_family"] == "piecewise_envelope" else exponential_dir) / f"{row['mode_slug']}_export_comparison.png")
        family_rows = [case_row for case_row in mode_case_rows if case_row["mode_slug"] == row["mode_slug"]]
        plot_winner_frequency(family_rows).savefig((direct_dir if row["mode_family"] == "direct_trace" else piecewise_dir if row["mode_family"] == "piecewise_envelope" else exponential_dir) / f"{row['mode_slug']}_winner_frequency.png")

    front_end_rows = []
    for case in representative_physical_cases():
        result = simulate_two_branch_physical_candidate(case["state"], case["analyzer"])
        front_end_rows.append(
            {
                "case": case["case"],
                "rms_error": float(result["metrics"]["rms_error"]),
                "max_abs_error": float(result["metrics"]["max_abs_error"]),
            }
        )
    front_end_rms = float(np.sqrt(np.mean([row["rms_error"] ** 2 for row in front_end_rows])))
    front_end_max = float(np.max([row["max_abs_error"] for row in front_end_rows]))

    summary_metrics = {
        "front_end_rms_error": front_end_rms,
        "front_end_max_error": front_end_max,
        "selected_winner_rms_error": float(selected_mode["winner_rms_error"]),
        "selected_winner_max_error": float(selected_mode["winner_max_error"]),
        "selected_mean_decisive_fraction": float(selected_mode["mean_decisive_fraction"]),
        "selected_common_envelope_rms": float(selected_mode["common_envelope_rms"]),
        "selected_common_envelope_max": float(selected_mode["common_envelope_max"]),
    }
    acceptance = {
        "front_end_preserved": front_end_rms < 0.01 and front_end_max < 0.02,
        "selected_mode_pass": float(selected_mode["winner_rms_error"]) < 0.03,
        "selected_mode_max_pass": float(selected_mode["winner_max_error"]) < 0.05,
        "stretch_target_pass": float(selected_mode["winner_rms_error"]) < 0.02,
    }
    acceptance["proceed_to_next_phase"] = acceptance["front_end_preserved"] and acceptance["selected_mode_pass"] and acceptance["selected_mode_max_pass"]
    acceptance["recommended_next_ticket"] = (
        "Freeze the physical front-end export contract, then extend the physical/SPICE candidate toward the four-branch shared-state case or toward a more explicit resonant front-end realization."
        if acceptance["proceed_to_next_phase"]
        else "Revisit the detector abstraction assumptions before scaling up the physical/SPICE front-end."
    )

    handoff_note = output_dir / "handoff_design_note.md"
    handoff_note.write_text(
        "\n".join(
            [
                "# Handoff Design Note",
                "",
                "## Export Modes",
                "",
                "- `direct_trace`: detector consumes the physical branch absorbed-power trace directly as a sampled waveform.",
                "- `piecewise_envelope`: detector consumes a binned envelope that preserves coarse time structure. Constant mode keeps one value per bin; linear mode keeps knot points with linear interpolation.",
                "- `exponential_fit`: detector consumes a compressed single-exponential approximation of the branch power trace.",
                "",
                "## Detector Assumption Check",
                "",
                "- The common-envelope diagnostic computes `Gamma_k(t) = P_k(t) / w_k` on exported traces.",
                "- Low gamma mismatch means the detector mainly sees weight-scaled copies of one shared envelope.",
                "- High mismatch means the detector is being asked to respond to branch-dependent time structure.",
                "",
                "## Adopted Mode",
                "",
                f"- Selected mode: `{selected_mode['mode_label']}`",
                f"- Why: lowest aggregate winner-law RMS error among the compared handoff modes.",
                f"- Complexity: {selected_mode['complexity_note']}",
                f"- Physical interpretation: {selected_mode['interpretability_note']}",
                "",
                "## Known Limitations",
                "",
                "- This ticket refines only the export boundary, not the physical front-end topology.",
                "- The frozen detector abstraction remains rare-event and branch-local rather than a physical detector circuit.",
                "- If all modes still miss the winner-law gate, the next iteration should revisit detector abstraction assumptions rather than adding hidden export corrections.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary_csv = output_dir / "summary_metrics.csv"
    _write_csv(summary_csv, [{"metric": key, "value": value} for key, value in summary_metrics.items()])
    summary_json = output_dir / "summary_metrics.json"
    summary_json.write_text(
        json.dumps(
            {
                "summary_metrics": summary_metrics,
                "acceptance": acceptance,
                "selected_mode": selected_mode,
                "comparison_rows": comparison_rows,
                "comparison_csv": str(comparison_csv),
                "handoff_design_note": str(handoff_note),
            },
            indent=2,
            default=_json_default,
        )
        + "\n",
        encoding="utf-8",
    )

    outputs = {
        "summary_csv": str(summary_csv),
        "comparison_csv": str(comparison_csv),
        "handoff_note": str(handoff_note),
        "winner_plot": str(winner_plot),
        "gamma_plot": str(raw_gamma_plot),
    }
    summary_md = output_dir / "summary_report.md"
    summary_md.write_text(
        _comparison_markdown(
            selected_mode=selected_mode,
            comparison_rows=comparison_rows,
            summary_metrics=summary_metrics,
            acceptance=acceptance,
            outputs=outputs,
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "summary_md": str(summary_md),
        "summary_json": str(summary_json),
        "summary_csv": str(summary_csv),
        "comparison_csv": str(comparison_csv),
        "handoff_design_note_md": str(handoff_note),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the physical front-end handoff refinement report.")
    parser.add_argument("--outdir", default="artifacts/physical_front_end_handoff")
    parser.add_argument("--detector-next-summary", default="artifacts/detector_next/results_summary.csv")
    parser.add_argument("--trials", type=int, default=240)
    args = parser.parse_args()
    build_physical_front_end_handoff_report(
        args.outdir,
        detector_next_summary_csv=args.detector_next_summary,
        n_trials=args.trials,
    )


if __name__ == "__main__":
    main()
