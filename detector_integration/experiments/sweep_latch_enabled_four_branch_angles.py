from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from detector_integration.detectors.closure_latch import validated_latch_arbiter_config
from detector_integration.experiments.sweep_four_branch_angles import (
    DEFAULT_ENVELOPE,
    _json_default,
    benchmark_angle_pairs,
    default_detector_spec,
)
from detector_integration.plots import (
    plot_chsh_comparison,
    plot_correlator_comparison,
    plot_four_branch_weight_comparison,
)
from detector_integration.sim.run_four_branch_latch_integration import (
    DEFAULT_CHSH_SETTINGS,
    run_four_branch_latch_trials,
    run_latch_enabled_chsh_trials,
)
from src.shared_4tank_core import singlet_state


def _latch_json_default(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    return _json_default(value)


def run_latch_enabled_four_branch_angle_sweep(
    outdir: str | Path,
    *,
    detector_family: str = "shot_trigger",
    detector_spec: dict[str, Any] | None = None,
    envelope_params: dict[str, Any] | None = None,
    n_trials: int = 4_000,
    seed: int = 20260402,
) -> dict[str, Any]:
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)
    resolved_detector_spec = default_detector_spec(detector_family) if detector_spec is None else detector_spec
    resolved_envelope = DEFAULT_ENVELOPE if envelope_params is None else envelope_params
    resolved_latch = validated_latch_arbiter_config(4)
    state4 = singlet_state()

    rows: list[dict[str, Any]] = []
    full_results: list[dict[str, Any]] = []
    for index, (label, a_deg, b_deg) in enumerate(benchmark_angle_pairs()):
        result = run_four_branch_latch_trials(
            state4,
            a_deg=a_deg,
            b_deg=b_deg,
            detector_params=resolved_detector_spec,
            n_trials=n_trials,
            seed=seed + 101 * index,
            envelope_params=resolved_envelope,
            latch_config=resolved_latch,
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
                "tie_region_fraction": result["tie_region_fraction"],
            }
        )

    chsh_result = run_latch_enabled_chsh_trials(
        state4,
        detector_params=resolved_detector_spec,
        n_trials=n_trials,
        seed=seed + 9_000,
        envelope_params=resolved_envelope,
        latch_config=resolved_latch,
        settings=DEFAULT_CHSH_SETTINGS,
    )

    csv_path = output_dir / "four_branch_summary.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    json_path = output_dir / "four_branch_summary.json"
    json_path.write_text(
        json.dumps({"rows": full_results, "chsh": chsh_result}, default=_latch_json_default, indent=2) + "\n",
        encoding="utf-8",
    )

    weights_plot = output_dir / "four_branch_weights.png"
    plot_four_branch_weight_comparison(rows).savefig(weights_plot)

    correlator_plot = output_dir / "correlator_comparison.png"
    plot_correlator_comparison(chsh_result["rows"]).savefig(correlator_plot)

    chsh_plot = output_dir / "chsh_comparison.png"
    plot_chsh_comparison(chsh_result).savefig(chsh_plot)
    return {
        "csv": str(csv_path),
        "json": str(json_path),
        "weights_plot": str(weights_plot),
        "correlator_plot": str(correlator_plot),
        "chsh_plot": str(chsh_plot),
        "rows": rows,
        "chsh": chsh_result,
        "detector_spec": resolved_detector_spec,
        "latch_config": resolved_latch,
        "envelope_params": resolved_envelope,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep four-branch singlet angles through the latch-enabled detector layer.")
    parser.add_argument("--outdir", default="artifacts/front_end_integration/four_branch")
    parser.add_argument("--family", default="shot_trigger", choices=["shot_trigger", "poisson_linear"])
    parser.add_argument("--trials", type=int, default=4_000)
    args = parser.parse_args()

    print(json.dumps(run_latch_enabled_four_branch_angle_sweep(args.outdir, detector_family=args.family, n_trials=args.trials), indent=2))


if __name__ == "__main__":
    main()
