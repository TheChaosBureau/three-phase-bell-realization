from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from detector_integration.detectors.closure_latch import validated_latch_arbiter_config
from detector_integration.experiments.sweep_four_branch_angles import benchmark_angle_pairs
from detector_integration.experiments.sweep_latch_enabled_four_branch_angles import DEFAULT_ENVELOPE, default_detector_spec
from detector_integration.experiments.sweep_two_branch_states import representative_two_branch_cases
from detector_integration.plots import plot_latch_enabled_mismatch_sensitivity
from detector_integration.sim.run_four_branch_latch_integration import DEFAULT_CHSH_SETTINGS, run_four_branch_latch_trials, run_latch_enabled_chsh_trials
from detector_integration.sim.run_two_branch_latch_integration import run_two_branch_latch_trials
from src.shared_4tank_core import singlet_state


def _branch_mismatch_specs(base_spec: dict[str, Any], level: float, kind: str, n_branches: int) -> list[dict[str, Any]]:
    base_params = dict(base_spec["model_params"])
    specs: list[dict[str, Any]] = []
    for branch_index in range(n_branches):
        sign = 1.0 if branch_index % 2 == 0 else -1.0
        branch_spec = {"family": base_spec["family"], "model_params": dict(base_params)}
        if kind == "gain":
            branch_spec["gain_scale"] = 1.0 + sign * level
        elif kind == "dark_count":
            params = dict(base_params)
            params["lambda_dark"] = max(params.get("lambda_dark", 0.0) * (1.0 + sign * level), 0.0)
            branch_spec["model_params"] = params
        elif kind == "dead_time":
            params = dict(base_params)
            params["dead_time"] = max(params.get("dead_time", 0.0) * (1.0 + sign * level), 0.0)
            branch_spec["model_params"] = params
        else:
            raise ValueError(f"Unsupported mismatch kind: {kind}")
        specs.append(branch_spec)
    return specs


def run_latch_enabled_mismatch_sweep(
    outdir: str | Path,
    *,
    detector_family: str = "shot_trigger",
    detector_spec: dict[str, Any] | None = None,
    envelope_params: dict[str, Any] | None = None,
    n_trials: int = 2_000,
    seed: int = 20260402,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)
    resolved_detector_spec = default_detector_spec(detector_family) if detector_spec is None else detector_spec
    resolved_envelope = DEFAULT_ENVELOPE if envelope_params is None else envelope_params
    state4 = singlet_state()

    rows: list[dict[str, Any]] = []
    for kind in ("gain", "dark_count", "dead_time", "latch_timing"):
        for level in (0.0, 0.01, 0.02, 0.05):
            if kind == "latch_timing":
                two_detector_spec = resolved_detector_spec
                four_detector_spec = resolved_detector_spec
                two_latch = validated_latch_arbiter_config(2, timing_mismatch_rel=level)
                four_latch = validated_latch_arbiter_config(4, timing_mismatch_rel=level)
            else:
                two_detector_spec = _branch_mismatch_specs(resolved_detector_spec, level=level, kind=kind, n_branches=2)
                four_detector_spec = _branch_mismatch_specs(resolved_detector_spec, level=level, kind=kind, n_branches=4)
                two_latch = validated_latch_arbiter_config(2)
                four_latch = validated_latch_arbiter_config(4)

            two_rows: list[dict[str, float]] = []
            for case_index, case in enumerate(representative_two_branch_cases()):
                two_result = run_two_branch_latch_trials(
                    case["state"],
                    case["analyzer"],
                    two_detector_spec,
                    n_trials=n_trials,
                    seed=seed + 701 * case_index + int(level * 100_000),
                    envelope_params=resolved_envelope,
                    latch_config=two_latch,
                )
                two_rows.append(
                    {
                        "rms_error": float(two_result["metrics"]["rms_error"]),
                        "max_abs_error": float(two_result["metrics"]["max_abs_error"]),
                        "winner_law_error": float(two_result["metrics"]["winner_law_error"]),
                    }
                )

            four_rows: list[dict[str, float]] = []
            for angle_index, (_, a_deg, b_deg) in enumerate(benchmark_angle_pairs()):
                four_result = run_four_branch_latch_trials(
                    state4,
                    a_deg=a_deg,
                    b_deg=b_deg,
                    detector_params=four_detector_spec,
                    n_trials=n_trials,
                    seed=seed + 1301 * angle_index + 20_000 + int(level * 100_000),
                    envelope_params=resolved_envelope,
                    latch_config=four_latch,
                )
                four_rows.append(
                    {
                        "rms_error": float(four_result["metrics"]["rms_error"]),
                        "max_abs_error": float(four_result["metrics"]["max_abs_error"]),
                        "correlator_error": float(four_result["metrics"]["correlator_error"]),
                    }
                )

            chsh_result = run_latch_enabled_chsh_trials(
                state4,
                detector_params=four_detector_spec,
                n_trials=n_trials,
                seed=seed + 40_000 + int(level * 100_000),
                envelope_params=resolved_envelope,
                latch_config=four_latch,
                settings=DEFAULT_CHSH_SETTINGS,
            )
            rows.append(
                {
                    "kind": kind,
                    "level": level,
                    "two_branch_mean_rms_error": float(math.sqrt(np.mean([row["winner_law_error"] ** 2 for row in two_rows]))),
                    "two_branch_max_winner_law_error": float(np.max([row["winner_law_error"] for row in two_rows])),
                    "four_branch_mean_rms_error": float(math.sqrt(np.mean([row["rms_error"] ** 2 for row in four_rows]))),
                    "four_branch_max_abs_error": float(np.max([row["max_abs_error"] for row in four_rows])),
                    "max_correlator_error": float(np.max([row["correlator_error"] for row in four_rows])),
                    "chsh_abs_error": float(chsh_result["abs_error"]),
                }
            )

    csv_path = output_dir / "mismatch_summary.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    json_path = output_dir / "mismatch_summary.json"
    json_path.write_text(json.dumps({"rows": rows}, indent=2) + "\n", encoding="utf-8")

    plot_path = output_dir / "mismatch_sensitivity.png"
    plot_latch_enabled_mismatch_sensitivity(rows).savefig(plot_path)
    return {
        "csv": str(csv_path),
        "json": str(json_path),
        "plot": str(plot_path),
        "rows": rows,
        "detector_spec": resolved_detector_spec,
        "envelope_params": resolved_envelope,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run mismatch sweeps for the latch-enabled detector integration.")
    parser.add_argument("--outdir", default="artifacts/front_end_integration/mismatch")
    parser.add_argument("--family", default="shot_trigger", choices=["shot_trigger", "poisson_linear"])
    parser.add_argument("--trials", type=int, default=2_000)
    args = parser.parse_args()

    print(json.dumps(run_latch_enabled_mismatch_sweep(args.outdir, detector_family=args.family, n_trials=args.trials), indent=2))


if __name__ == "__main__":
    main()
