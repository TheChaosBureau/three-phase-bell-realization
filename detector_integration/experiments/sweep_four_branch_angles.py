from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from detector_integration.plots import (
    plot_chsh_comparison,
    plot_correlator_comparison,
    plot_four_branch_weight_comparison,
    plot_mismatch_sensitivity,
)
from detector_integration.sim.run_four_branch_integration import DEFAULT_CHSH_SETTINGS, run_chsh_trials, run_four_branch_trials
from detector_search.sim.search import perturb_params
from src.shared_4tank_core import singlet_state

DEFAULT_ENVELOPE = {"kind": "constant", "power_scale": 4.0, "dt": 1e-4, "t_max": 5.0}


def default_detector_spec(family: str) -> dict[str, Any]:
    if family == "poisson_linear":
        return {"family": "poisson_linear", "model_params": {"lambda_dark": 1e-6, "alpha": 1.6, "dead_time": 0.0}}
    if family == "shot_trigger":
        return {"family": "shot_trigger", "model_params": {"eps_event": 0.5, "p_trig": 0.8, "lambda_dark": 1e-6, "dead_time": 0.0}}
    raise ValueError(f"Unsupported detector family: {family}")


def benchmark_angle_pairs() -> list[tuple[str, float, float]]:
    return [
        ("case_a", 0.0, 0.0),
        ("a0b0", 0.0, 22.5),
        ("a0b1", 0.0, -22.5),
        ("a1b0", 45.0, 22.5),
        ("a1b1", 45.0, -22.5),
    ]


def _json_default(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _branch_mismatch_specs(base_spec: dict[str, Any], level: float, kind: str, n_branches: int) -> list[dict[str, Any]]:
    base_params = dict(base_spec["model_params"])
    specs: list[dict[str, Any]] = []
    for branch_index in range(n_branches):
        sign = 1.0 if branch_index % 2 == 0 else -1.0
        branch_spec = {"family": base_spec["family"], "model_params": dict(base_params)}
        if kind == "gain":
            branch_spec["gain_scale"] = 1.0 + sign * level
        elif kind == "dark_count":
            branch_params = dict(base_spec["model_params"])
            branch_params["lambda_dark"] = max(branch_params.get("lambda_dark", 0.0) * (1.0 + sign * level), 0.0)
            branch_spec["model_params"] = branch_params
        elif kind == "dead_time":
            branch_params = dict(base_spec["model_params"])
            branch_params["dead_time"] = max(branch_params.get("dead_time", 0.0) * (1.0 + sign * level), 0.0)
            branch_spec["model_params"] = branch_params
        else:
            raise ValueError(f"Unsupported mismatch kind: {kind}")
        specs.append(branch_spec)
    return specs


def run_four_branch_angle_sweep(
    outdir: str | Path,
    *,
    detector_family: str = "shot_trigger",
    n_trials: int = 4_000,
    seed: int = 20260402,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)
    detector_spec = default_detector_spec(detector_family)
    state4 = singlet_state()

    rows: list[dict[str, Any]] = []
    full_results: list[dict[str, Any]] = []
    for index, (label, a_deg, b_deg) in enumerate(benchmark_angle_pairs()):
        result = run_four_branch_trials(
            state4,
            a_deg=a_deg,
            b_deg=b_deg,
            detector_params=detector_spec,
            n_trials=n_trials,
            seed=seed + 101 * index,
            envelope_params=DEFAULT_ENVELOPE,
        )
        full_results.append({"label": label, **result})
        rows.append(
            {
                "label": label,
                "a_deg": a_deg,
                "b_deg": b_deg,
                "exact_weights": result["exact_weights"].tolist(),
                "empirical_frequencies": result["empirical_frequencies"].tolist(),
                "rms_error": result["metrics"]["rms_error"],
                "max_abs_error": result["metrics"]["max_abs_error"],
                "correlator_exact": result["metrics"]["correlator_exact"],
                "correlator_empirical": result["metrics"]["correlator_empirical"],
                "correlator_error": result["metrics"]["correlator_error"],
                "decisive_fraction": result["decisive_fraction"],
            }
        )

    chsh_result = run_chsh_trials(
        state4,
        detector_params=detector_spec,
        n_trials=n_trials,
        seed=seed + 9_000,
        envelope_params=DEFAULT_ENVELOPE,
        settings=DEFAULT_CHSH_SETTINGS,
    )

    mismatch_rows: list[dict[str, Any]] = []
    for kind in ("gain", "dark_count", "dead_time"):
        for level in (0.0, 0.01, 0.02, 0.05):
            specs = _branch_mismatch_specs(detector_spec, level=level, kind=kind, n_branches=4)
            mismatch_chsh = run_chsh_trials(
                state4,
                detector_params=specs,
                n_trials=max(1_500, n_trials // 2),
                seed=seed + 17_000 + int(level * 10_000),
                envelope_params=DEFAULT_ENVELOPE,
                settings=DEFAULT_CHSH_SETTINGS,
            )
            mean_rms_error = float(np.mean([row["rms_error"] for row in mismatch_chsh["rows"]]))
            max_corr_error = float(np.max([row["correlator_error"] for row in mismatch_chsh["rows"]]))
            mismatch_rows.append(
                {
                    "kind": kind,
                    "level": level,
                    "mean_rms_error": mean_rms_error,
                    "max_correlator_error": max_corr_error,
                    "chsh_abs_error": mismatch_chsh["abs_error"],
                }
            )

    csv_path = output_dir / "four_branch_summary.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    mismatch_csv = output_dir / "four_branch_mismatch_summary.csv"
    with mismatch_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(mismatch_rows[0].keys()))
        writer.writeheader()
        writer.writerows(mismatch_rows)

    json_path = output_dir / "four_branch_summary.json"
    json_path.write_text(
        json.dumps({"rows": full_results, "chsh": chsh_result, "mismatch_rows": mismatch_rows}, default=_json_default, indent=2)
        + "\n",
        encoding="utf-8",
    )

    weights_plot = output_dir / "four_branch_weights.png"
    plot_four_branch_weight_comparison(rows).savefig(weights_plot)

    correlator_plot = output_dir / "correlator_comparison.png"
    plot_correlator_comparison(chsh_result["rows"]).savefig(correlator_plot)

    chsh_plot = output_dir / "chsh_comparison.png"
    plot_chsh_comparison(chsh_result).savefig(chsh_plot)

    mismatch_plot = output_dir / "mismatch_sensitivity.png"
    plot_mismatch_sensitivity(mismatch_rows).savefig(mismatch_plot)
    return {
        "csv": str(csv_path),
        "mismatch_csv": str(mismatch_csv),
        "json": str(json_path),
        "weights_plot": str(weights_plot),
        "correlator_plot": str(correlator_plot),
        "chsh_plot": str(chsh_plot),
        "mismatch_plot": str(mismatch_plot),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep four-branch singlet angles through the detector layer.")
    parser.add_argument("--outdir", default="artifacts/detector_integration/four_branch")
    parser.add_argument("--family", default="shot_trigger", choices=["shot_trigger", "poisson_linear"])
    parser.add_argument("--trials", type=int, default=4_000)
    args = parser.parse_args()

    print(json.dumps(run_four_branch_angle_sweep(args.outdir, detector_family=args.family, n_trials=args.trials), indent=2))


if __name__ == "__main__":
    main()
