from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sim.config import build_sequential_run_configs, build_single_run_configs, make_preset
from sim.io import default_artifact_dir, dump_json, ensure_dir
from sim.simulate_sequential import run_sequential_batch
from sim.simulate_single import run_single_batch


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run anisotropic-damping simulation sweeps.")
    parser.add_argument(
        "--preset",
        choices=["single", "sequential", "risk_first_full"],
        default="risk_first_full",
        help="Named sweep preset.",
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=None,
        help="Output directory for artifacts. Defaults to artifacts/sim/<timestamp>-<preset>.",
    )
    parser.add_argument("--seed", type=int, default=7, help="Random seed for state sampling.")
    parser.add_argument(
        "--single-samples",
        type=int,
        default=None,
        help="Override sample count for single-analyzer runs.",
    )
    parser.add_argument(
        "--sequential-samples",
        type=int,
        default=None,
        help="Override sample count for sequential runs.",
    )
    parser.add_argument(
        "--dense-angle-count",
        type=int,
        default=None,
        help="Override the number of dense single-analyzer angles in [0, 90].",
    )
    return parser.parse_args()


def write_dataframe(path: Path, frame) -> None:
    ensure_dir(path.parent)
    frame.to_csv(path, index=False)


def write_single_results(artifact_dir: Path, result) -> dict[str, object]:
    single_dir = ensure_dir(artifact_dir / "single")
    write_dataframe(single_dir / "trial_metrics.csv", result.trial_metrics)
    write_dataframe(single_dir / "summary.csv", result.combo_summary)
    write_dataframe(single_dir / "ratio_summary.csv", result.ratio_summary)
    dump_json(single_dir / "run_manifest.json", result.run_manifest)
    np.savez_compressed(
        single_dir / "states.npz",
        combo_keys=np.array(result.combo_keys, dtype=str),
        initial_states=result.initial_states,
        post_states=result.post_states,
    )

    best_combo = (
        result.combo_summary.sort_values("projectivity_score", ascending=False).head(1).to_dict(orient="records")
        if not result.combo_summary.empty
        else []
    )
    return {
        "combo_count": len(result.combo_keys),
        "trial_count": int(len(result.trial_metrics)),
        "best_projectivity_combo": best_combo,
    }


def write_sequential_results(artifact_dir: Path, result) -> dict[str, object]:
    sequential_dir = ensure_dir(artifact_dir / "sequential")
    write_dataframe(sequential_dir / "trial_metrics.csv", result.trial_metrics)
    write_dataframe(sequential_dir / "rule_summary.csv", result.rule_summary)
    write_dataframe(sequential_dir / "drift_summary.csv", result.drift_summary)
    write_dataframe(sequential_dir / "chsh_summary.csv", result.chsh_summary)
    write_dataframe(sequential_dir / "sequential_residual_agreement.csv", result.residual_agreement_summary)
    write_dataframe(sequential_dir / "sequential_gated_summary.csv", result.gated_summary)
    write_dataframe(sequential_dir / "aligned_support_by_confidence.csv", result.aligned_support_by_confidence)
    write_dataframe(sequential_dir / "legacy_rule_controls.csv", result.legacy_rule_controls)
    if hasattr(result, "correlation_summary"):
        write_dataframe(sequential_dir / "correlation_summary.csv", result.correlation_summary)
    dump_json(sequential_dir / "run_manifest.json", result.run_manifest)
    np.savez_compressed(
        sequential_dir / "states.npz",
        combo_keys=np.array(result.combo_keys, dtype=str),
        initial_states=result.initial_states,
        post_alice_states=result.post_alice_states,
        post_bob_states=result.post_bob_states,
    )

    best_chsh = (
        result.gated_summary.sort_values("CHSH_raw", ascending=False).head(3).to_dict(orient="records")
        if not result.gated_summary.empty
        else []
    )
    return {
        "combo_count": len(result.combo_keys),
        "trial_count": int(len(result.trial_metrics)),
        "top_rule_groups": best_chsh,
    }


def main() -> None:
    args = parse_args()
    preset = make_preset(
        args.preset,
        seed=args.seed,
        single_sample_count=args.single_samples,
        sequential_sample_count=args.sequential_samples,
        dense_single_angle_count=args.dense_angle_count,
    )
    artifact_dir = (args.artifact_dir or default_artifact_dir(args.preset)).resolve()
    ensure_dir(artifact_dir)

    summary: dict[str, object] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_dir": str(artifact_dir),
        "preset": preset.to_dict(),
        "modes": [],
    }

    if preset.single_window_fractions:
        single_result = run_single_batch(build_single_run_configs(preset))
        summary["modes"].append("single")
        summary["single"] = write_single_results(artifact_dir, single_result)

    if preset.sequential_window_fractions:
        sequential_result = run_sequential_batch(build_sequential_run_configs(preset))
        summary["modes"].append("sequential")
        summary["sequential"] = write_sequential_results(artifact_dir, sequential_result)

    dump_json(artifact_dir / "manifest.json", summary)
    dump_json(artifact_dir / "summary.json", summary)
    print(f"Wrote sweep artifacts to {artifact_dir}")


if __name__ == "__main__":
    main()
