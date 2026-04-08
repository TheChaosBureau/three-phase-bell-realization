from __future__ import annotations

import argparse
from dataclasses import replace
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .config import (
    BRANCHES,
    DEFAULT_ANALYZER_PARAMS,
    DEFAULT_CHSH_SETTINGS,
    DEFAULT_DETECTOR_PARAMS_OU,
    DEFAULT_DETECTOR_PARAMS_POISSON,
    DEFAULT_RECOMBINER_PARAMS,
    DEFAULT_SHARED_CORE_PARAMS,
    DEFAULT_SWEEP_ANGLE_PAIRS,
    AnalyzerParams,
    DetectorParams,
    RecombinerParams,
    SharedCoreParams,
)
from .io import dataclass_to_dict, ensure_outdir, git_commit_hash, utc_timestamp, write_dataframe, write_json
from .metrics import compute_chsh, correlator_from_probs, empirical_joint_probs, winner_law_errors
from .playback import export_trial_playback
from .trial import run_trial


def _summarize_angles(trial_results: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (angle_a, angle_b), df_pair in trial_results.groupby(["angle_a", "angle_b"], sort=False):
        decisive = df_pair[df_pair["winner"] != "none"]
        probs = empirical_joint_probs(df_pair)
        target = {
            branch: float(df_pair[f"w_{branch}_target"].mean())
            for branch in BRANCHES
        }
        delta = float(df_pair["delta"].iloc[0])
        decisive_fraction = float(df_pair["decisive"].mean())
        rms_error, max_error = winner_law_errors(probs, target)
        correlator_empirical = correlator_from_probs(probs) if len(decisive) else float("nan")
        row = {
            "detector_mode": str(df_pair["detector_mode"].iloc[0]),
            "angle_a": float(angle_a),
            "angle_b": float(angle_b),
            "delta": delta,
            "n_trials": int(len(df_pair)),
            "decisive_fraction": decisive_fraction,
            "p_pp": probs["pp"] if len(decisive) else float("nan"),
            "p_pm": probs["pm"] if len(decisive) else float("nan"),
            "p_mp": probs["mp"] if len(decisive) else float("nan"),
            "p_mm": probs["mm"] if len(decisive) else float("nan"),
            "w_pp_target_mean": target["pp"],
            "w_pm_target_mean": target["pm"],
            "w_mp_target_mean": target["mp"],
            "w_mm_target_mean": target["mm"],
            "winner_law_rms_error": rms_error if len(decisive) else float("nan"),
            "winner_law_max_error": max_error if len(decisive) else float("nan"),
            "marginal_a_plus": (probs["pp"] + probs["pm"]) if len(decisive) else float("nan"),
            "marginal_b_plus": (probs["pp"] + probs["mp"]) if len(decisive) else float("nan"),
            "correlator_empirical": correlator_empirical,
            "correlator_target": -math.cos(2.0 * delta),
            "correlator_abs_error": abs(correlator_empirical + math.cos(2.0 * delta))
            if len(decisive)
            else float("nan"),
            "mean_trigger_time": float(decisive["trigger_time"].mean()) if len(decisive) else float("nan"),
            "dark_fraction": float(decisive["dark_triggered"].mean()) if len(decisive) else float("nan"),
        }
        rows.append(row)
    return pd.DataFrame(rows)


def _run_metadata(
    angle_pairs: list[tuple[float, float]],
    trials_per_pair: int,
    core_params: SharedCoreParams,
    analyzer_params: AnalyzerParams,
    recombiner_params: RecombinerParams,
    detector_params: DetectorParams,
) -> dict[str, Any]:
    return {
        "timestamp": utc_timestamp(),
        "git_commit_hash": git_commit_hash(),
        "random_seed": detector_params.seed,
        "detector_mode": detector_params.mode,
        "trials_per_pair": trials_per_pair,
        "angle_pairs": [list(pair) for pair in angle_pairs],
        "shared_core": dataclass_to_dict(core_params),
        "analyzer": dataclass_to_dict(analyzer_params),
        "recombiner": dataclass_to_dict(recombiner_params),
        "detector": dataclass_to_dict(detector_params),
    }


def run_angle_sweep(
    angle_pairs: list[tuple[float, float]],
    trials_per_pair: int,
    core_params: SharedCoreParams,
    analyzer_params: AnalyzerParams,
    recombiner_params: RecombinerParams,
    detector_params: DetectorParams,
    outdir: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    output_root = ensure_outdir(outdir)
    run_rng = np.random.default_rng(detector_params.seed)

    trial_records: list[dict[str, Any]] = []
    first_trial_payload: tuple[int, dict[str, Any]] | None = None
    sampled_trial_payload: tuple[int, dict[str, Any]] | None = None

    trial_index = 0
    for angle_a, angle_b in angle_pairs:
        for _ in range(trials_per_pair):
            child_seed = int(run_rng.integers(0, np.iinfo(np.int64).max))
            trial_detector_params = replace(detector_params, seed=child_seed)
            result = run_trial(
                angle_a=angle_a,
                angle_b=angle_b,
                core_params=core_params,
                analyzer_params=analyzer_params,
                recombiner_params=recombiner_params,
                detector_params=trial_detector_params,
            )

            summary = dict(result["summary"])
            summary["trial_index"] = trial_index
            trial_records.append(summary)

            if first_trial_payload is None:
                first_trial_payload = (trial_index, result)
            if sampled_trial_payload is None and summary["decisive"]:
                sampled_trial_payload = (trial_index, result)

            trial_index += 1

    trial_results = pd.DataFrame(trial_records)
    angle_summary = _summarize_angles(trial_results)
    chsh_summary = pd.DataFrame(
        [
            {
                "detector_mode": detector_params.mode,
                **compute_chsh(angle_summary, DEFAULT_CHSH_SETTINGS),
            }
        ]
    )

    write_dataframe(trial_results, output_root / "trial_results.csv")
    write_dataframe(angle_summary, output_root / "angle_summary.csv")
    write_dataframe(chsh_summary, output_root / "chsh_summary.csv")
    write_json(
        _run_metadata(
            angle_pairs=angle_pairs,
            trials_per_pair=trials_per_pair,
            core_params=core_params,
            analyzer_params=analyzer_params,
            recombiner_params=recombiner_params,
            detector_params=detector_params,
        ),
        output_root / "run_metadata.json",
    )

    selected_trial = sampled_trial_payload or first_trial_payload
    if selected_trial is not None:
        selected_index, selected_result = selected_trial
        export_trial_playback(
            trial_index=selected_index,
            timeseries=selected_result["timeseries"],
            summary=selected_result["summary"],
            outdir=output_root,
        )

    return trial_results, angle_summary, chsh_summary


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the wavepool entanglement reduced simulator.")
    parser.add_argument("--trials-per-pair", type=int, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--detector-mode", choices=("ou_threshold", "poisson_linear"), required=True)
    parser.add_argument("--alpha-poisson", type=float, default=DEFAULT_DETECTOR_PARAMS_POISSON.alpha_poisson)
    parser.add_argument("--eps1", type=float, default=DEFAULT_RECOMBINER_PARAMS.eps1)
    parser.add_argument("--eps2", type=float, default=DEFAULT_RECOMBINER_PARAMS.eps2)
    parser.add_argument("--eps3", type=float, default=DEFAULT_RECOMBINER_PARAMS.eps3)
    parser.add_argument("--eps4", type=float, default=DEFAULT_RECOMBINER_PARAMS.eps4)
    parser.add_argument("--sigma", type=float, default=DEFAULT_DETECTOR_PARAMS_OU.sigma)
    parser.add_argument("--beta", type=float, default=DEFAULT_DETECTOR_PARAMS_OU.beta)
    parser.add_argument("--threshold", type=float, default=DEFAULT_DETECTOR_PARAMS_OU.threshold)
    parser.add_argument("--t-max", type=float, default=DEFAULT_DETECTOR_PARAMS_OU.t_max)
    parser.add_argument("--dt", type=float, default=DEFAULT_DETECTOR_PARAMS_OU.dt)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    detector_defaults = (
        DEFAULT_DETECTOR_PARAMS_OU
        if args.detector_mode == "ou_threshold"
        else DEFAULT_DETECTOR_PARAMS_POISSON
    )
    detector_params = replace(
        detector_defaults,
        seed=args.seed,
        alpha_poisson=args.alpha_poisson,
        sigma=args.sigma,
        beta=args.beta,
        threshold=args.threshold,
        t_max=args.t_max,
        dt=args.dt,
    )
    recombiner_params = replace(
        DEFAULT_RECOMBINER_PARAMS,
        eps1=args.eps1,
        eps2=args.eps2,
        eps3=args.eps3,
        eps4=args.eps4,
    )

    run_angle_sweep(
        angle_pairs=DEFAULT_SWEEP_ANGLE_PAIRS,
        trials_per_pair=args.trials_per_pair,
        core_params=DEFAULT_SHARED_CORE_PARAMS,
        analyzer_params=DEFAULT_ANALYZER_PARAMS,
        recombiner_params=recombiner_params,
        detector_params=detector_params,
        outdir=str(args.outdir),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
