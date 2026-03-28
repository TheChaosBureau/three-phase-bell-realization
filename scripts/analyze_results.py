from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sim.io import dump_json, ensure_dir, load_json

PRIMARY_WINDOW = 0.25
SIGNALING_THRESHOLD = 0.05


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze saved anisotropic-damping simulation artifacts.")
    parser.add_argument("artifact_dir", type=Path, help="Artifact root created by scripts/run_sweeps.py")
    parser.add_argument(
        "--state-cloud-limit",
        type=int,
        default=400,
        help="Max plotted points for the state-cloud scatter plot.",
    )
    return parser.parse_args()


def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def choose_primary_ratio(single_ratio_summary: pd.DataFrame, rule_summary: pd.DataFrame) -> float | None:
    candidates: list[float] = []
    if not single_ratio_summary.empty:
        candidates.extend(single_ratio_summary["anisotropy_ratio"].dropna().tolist())
    if not rule_summary.empty:
        candidates.extend(rule_summary["anisotropy_ratio"].dropna().tolist())
    if not candidates:
        return None
    return float(max(candidates))


def plot_projectivity_vs_ratio(single_ratio_summary: pd.DataFrame, out_path: Path) -> None:
    if single_ratio_summary.empty:
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    for window_fraction, group in single_ratio_summary.groupby("window_fraction"):
        ax.plot(
            group["anisotropy_ratio"],
            group["projectivity_score"],
            marker="o",
            label=f"T={window_fraction:.3f}",
        )
    ax.set_title("Projectivity vs Anisotropy Ratio")
    ax.set_xlabel("Anisotropy ratio gamma_plus / gamma_minus")
    ax.set_ylabel("Projectivity score")
    ax.legend()
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_residual_quality_vs_ratio(single_ratio_summary: pd.DataFrame, out_path: Path) -> None:
    if single_ratio_summary.empty:
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    for window_fraction, group in single_ratio_summary.groupby("window_fraction"):
        ax.plot(
            group["anisotropy_ratio"],
            group["residual_branch_quality"],
            marker="o",
            label=f"T={window_fraction:.3f}",
        )
    ax.set_title("Residual Branch Quality vs Anisotropy Ratio")
    ax.set_xlabel("Anisotropy ratio gamma_plus / gamma_minus")
    ax.set_ylabel("Residual purity")
    ax.legend()
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_branch_response_vs_angle(single_summary: pd.DataFrame, out_path: Path) -> None:
    if single_summary.empty:
        return
    primary = single_summary[
        single_summary["window_fraction"].round(6) == round(PRIMARY_WINDOW, 6)
    ]
    if primary.empty:
        primary = single_summary
    primary = primary[primary["anisotropy_ratio"] == primary["anisotropy_ratio"].max()]
    if primary.empty:
        return

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(primary["angle_deg"], primary["projectivity_score"], marker="o", label="Projectivity")
    ax.plot(
        primary["angle_deg"],
        primary["residual_branch_quality"],
        marker="s",
        label="Residual quality",
    )
    ax.set_title("Single-Analyzer Branch Response vs Angle")
    ax.set_xlabel("Analyzer angle (deg)")
    ax.set_ylabel("Mean response")
    ax.legend()
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_state_clouds(single_trials: pd.DataFrame, out_path: Path, state_cloud_limit: int) -> None:
    if single_trials.empty:
        return
    primary = single_trials[
        single_trials["window_fraction"].round(6) == round(PRIMARY_WINDOW, 6)
    ]
    if primary.empty:
        primary = single_trials
    primary = primary[primary["anisotropy_ratio"] == primary["anisotropy_ratio"].max()]
    if primary.empty:
        return
    angle_target = 45.0 if (primary["angle_deg"] == 45.0).any() else float(primary["angle_deg"].iloc[0])
    primary = primary[primary["angle_deg"].round(6) == round(angle_target, 6)].head(state_cloud_limit)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    axes[0].scatter(primary["pre_plus_power"], primary["pre_minus_power"], alpha=0.45, s=18)
    axes[0].set_title("Before Window")
    axes[1].scatter(primary["post_plus_power"], primary["post_minus_power"], alpha=0.45, s=18)
    axes[1].set_title("After Window")
    for axis in axes:
        axis.set_xlabel("|c_+|^2")
        axis.set_ylabel("|c_-|^2")
        axis.grid(alpha=0.2)
    fig.suptitle("State Clouds in Analyzer Basis")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_marginal_drift(rule_summary: pd.DataFrame, out_path: Path) -> None:
    if rule_summary.empty:
        return
    primary = rule_summary[
        (rule_summary["rule"] == "residual_classifier")
        & (rule_summary["window_fraction"].round(6) == round(PRIMARY_WINDOW, 6))
    ]
    if primary.empty:
        primary = rule_summary[rule_summary["rule"] == "residual_classifier"]
    if primary.empty:
        primary = rule_summary
    primary = primary[primary["anisotropy_ratio"] == primary["anisotropy_ratio"].max()]
    if primary.empty:
        return

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), sharey=True)
    alice_slice = primary[primary["angle_a_deg"] == primary["angle_a_deg"].min()]
    bob_slice = primary[primary["angle_b_deg"] == primary["angle_b_deg"].min()]
    axes[0].plot(alice_slice["angle_b_deg"], alice_slice["alice_marginal"], marker="o")
    axes[0].set_title("Alice vs Bob Angle")
    axes[1].plot(bob_slice["angle_a_deg"], bob_slice["bob_marginal"], marker="o")
    axes[1].set_title("Bob vs Alice Angle")
    for axis in axes:
        axis.set_xlabel("Remote angle (deg)")
        axis.set_ylabel("Local marginal mean")
        axis.grid(alpha=0.2)
    fig.suptitle("Marginal Drift vs Remote Angle")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_aligned_mass(rule_summary: pd.DataFrame, out_path: Path) -> None:
    if rule_summary.empty:
        return
    aligned = rule_summary[
        (rule_summary["rule"] == "residual_classifier")
        & (rule_summary["angle_a_deg"].round(6) == rule_summary["angle_b_deg"].round(6))
    ]
    if aligned.empty:
        return
    aligned = (
        aligned.groupby(["window_fraction", "anisotropy_ratio"], as_index=False)
        .agg(same_sign_mass=("same_sign_mass", "mean"), anti_sign_mass=("anti_sign_mass", "mean"))
    )
    fig, ax = plt.subplots(figsize=(8, 5))
    for window_fraction, group in aligned.groupby("window_fraction"):
        ax.plot(group["anisotropy_ratio"], group["same_sign_mass"], marker="o", label=f"same T={window_fraction:.3f}")
        ax.plot(group["anisotropy_ratio"], group["anti_sign_mass"], marker="s", linestyle="--", label=f"anti T={window_fraction:.3f}")
    ax.set_title("Aligned Same-Sign Mass vs Anisotropy")
    ax.set_xlabel("Anisotropy ratio gamma_plus / gamma_minus")
    ax.set_ylabel("Mass")
    ax.legend(ncol=2, fontsize=8)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_correlation_vs_delta(rule_summary: pd.DataFrame, out_path: Path) -> None:
    if rule_summary.empty:
        return
    primary = rule_summary[
        (rule_summary["rule"] == "residual_classifier")
        & (rule_summary["window_fraction"].round(6) == round(PRIMARY_WINDOW, 6))
    ]
    if primary.empty:
        primary = rule_summary[rule_summary["rule"] == "residual_classifier"]
    if primary.empty:
        return
    primary = primary[primary["anisotropy_ratio"] == primary["anisotropy_ratio"].max()].copy()
    primary["delta_deg"] = primary["angle_b_deg"] - primary["angle_a_deg"]
    grouped = primary.groupby("delta_deg", as_index=False).agg(correlation=("correlation", "mean"))

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(grouped["delta_deg"], grouped["correlation"], marker="o")
    ax.set_title("Correlation Function E(Delta)")
    ax.set_xlabel("Delta angle (deg)")
    ax.set_ylabel("Correlation")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_chsh(chsh_summary: pd.DataFrame, out_path: Path) -> None:
    if chsh_summary.empty:
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    for rule, group in chsh_summary.groupby("rule"):
        ax.plot(group["anisotropy_ratio"], group["chsh"], marker="o", label=rule)
    ax.axhline(2.0, color="tab:red", linestyle="--", linewidth=1, label="CHSH=2")
    ax.set_title("CHSH vs Anisotropy Ratio")
    ax.set_xlabel("Anisotropy ratio gamma_plus / gamma_minus")
    ax.set_ylabel("CHSH")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def detect_failures(
    single_ratio_summary: pd.DataFrame,
    drift_summary: pd.DataFrame,
    chsh_summary: pd.DataFrame,
) -> dict[str, dict[str, object]]:
    failures: dict[str, dict[str, object]] = {}

    if not single_ratio_summary.empty:
        isotropic = single_ratio_summary[single_ratio_summary["anisotropy_ratio"].round(6) == 1.0]
        if not isotropic.empty:
            failures["F1_isotropic_nonprojective"] = {
                "triggered": bool(isotropic["projectivity_score"].mean() < 0.7),
                "mean_projectivity": float(isotropic["projectivity_score"].mean()),
            }
        generic = single_ratio_summary[
            (single_ratio_summary["branch_loss_mean"] > 0.05)
            & (single_ratio_summary["residual_branch_quality"] < 0.7)
        ]
        failures["F2_generic_deformation"] = {
            "triggered": bool(not generic.empty),
            "rows": int(len(generic)),
        }

        baseline = single_ratio_summary[
            single_ratio_summary["window_fraction"].round(6) == round(PRIMARY_WINDOW, 6)
        ][["anisotropy_ratio", "projectivity_score"]].rename(columns={"projectivity_score": "baseline_projectivity"})
        long_windows = single_ratio_summary[single_ratio_summary["window_fraction"] >= 0.5].merge(
            baseline,
            on="anisotropy_ratio",
            how="left",
        )
        washed_out = long_windows[
            long_windows["baseline_projectivity"].notna()
            & (long_windows["projectivity_score"] < 0.8 * long_windows["baseline_projectivity"])
        ]
        failures["F4_washout_regime"] = {
            "triggered": bool(not washed_out.empty),
            "rows": int(len(washed_out)),
        }

    if not drift_summary.empty:
        signaling = drift_summary[
            (drift_summary["alice_drift_max"] > SIGNALING_THRESHOLD)
            | (drift_summary["bob_drift_max"] > SIGNALING_THRESHOLD)
        ]
        failures["F3_signaling_regime"] = {
            "triggered": bool(not signaling.empty),
            "rows": int(len(signaling)),
        }

    if not chsh_summary.empty and not drift_summary.empty:
        chsh_peaks = chsh_summary.sort_values("chsh", ascending=False).head(5)
        drift_peaks = drift_summary.rename(columns={"rule": "drift_rule"})
        merged = chsh_peaks.merge(
            drift_peaks,
            left_on=["rule", "window_fraction", "anisotropy_ratio"],
            right_on=["drift_rule", "window_fraction", "anisotropy_ratio"],
            how="left",
        )
        overfit = merged[
            (merged["chsh"] > 1.9)
            & (
                (merged["alice_drift_max"].fillna(0.0) > SIGNALING_THRESHOLD)
                | (merged["bob_drift_max"].fillna(0.0) > SIGNALING_THRESHOLD)
            )
        ]
        failures["F5_overfit_readout"] = {
            "triggered": bool(not overfit.empty),
            "rows": int(len(overfit)),
        }

    return failures


def build_report_answers(
    single_ratio_summary: pd.DataFrame,
    drift_summary: pd.DataFrame,
    chsh_summary: pd.DataFrame,
) -> dict[str, str]:
    answers: dict[str, str] = {}

    if not single_ratio_summary.empty:
        strongest = single_ratio_summary.sort_values("anisotropy_ratio").tail(1)
        peak_projectivity = float(strongest["projectivity_score"].iloc[0])
        answers["q1_projective_residuals"] = (
            "Strong anisotropy reaches near-projective residual branches."
            if peak_projectivity >= 0.9
            else "Strong anisotropy improves residual branching, but does not reach a clean near-projective regime."
        )

        by_window = (
            single_ratio_summary.groupby("window_fraction", as_index=False)
            .agg(projectivity_score=("projectivity_score", "mean"))
            .sort_values("projectivity_score", ascending=False)
        )
        best_window = float(by_window.iloc[0]["window_fraction"])
        worst_window = float(by_window.iloc[-1]["window_fraction"])
        answers["q2_window_durations"] = (
            f"Best average projectivity appears near T={best_window:.3f}; the weakest window is T={worst_window:.3f}."
        )
    else:
        answers["q1_projective_residuals"] = "Single-analyzer artifacts were not present."
        answers["q2_window_durations"] = "Window comparison was not available."

    if not drift_summary.empty:
        low_drift = drift_summary[
            (drift_summary["alice_drift_max"] <= SIGNALING_THRESHOLD)
            & (drift_summary["bob_drift_max"] <= SIGNALING_THRESHOLD)
        ]
        if not low_drift.empty:
            preferred_rule = str(low_drift.sort_values(["alice_drift_max", "bob_drift_max"]).iloc[0]["rule"])
            answers["q3_rule_meaningfulness"] = (
                f"Lowest-drift behavior comes from {preferred_rule}; dominant-pre style rules are least dynamical because they rely on pre-window branch weights."
            )
        else:
            answers["q3_rule_meaningfulness"] = (
                "Every tested readout shows noticeable drift; residual-classifier and extracted-energy rules remain the most dynamical, but none are drift-free."
            )
        answers["q5_marginal_protection"] = (
            "Some marginal protection is available in the tested regime."
            if not low_drift.empty
            else "Projectivity and marginal protection trade off sharply in the tested regime."
        )
    else:
        answers["q3_rule_meaningfulness"] = "Sequential readout comparisons were not available."
        answers["q5_marginal_protection"] = "Marginal drift was not available."

    if not chsh_summary.empty:
        peak = chsh_summary.sort_values("chsh", ascending=False).iloc[0]
        answers["q4_pair_statistics"] = (
            f"Peak sequential structure appears for rule={peak['rule']} at window={peak['window_fraction']:.3f} and ratio={peak['anisotropy_ratio']:.3f}, which should be compared against the drift summary before calling it sphere-like."
        )
    else:
        answers["q4_pair_statistics"] = "Sequential pair statistics were not available."

    return answers


def main() -> None:
    args = parse_args()
    artifact_dir = args.artifact_dir.resolve()
    plots_dir = ensure_dir(artifact_dir / "plots")

    summary = load_json(artifact_dir / "summary.json") if (artifact_dir / "summary.json").exists() else {}
    single_trials = load_csv(artifact_dir / "single" / "trial_metrics.csv")
    single_summary = load_csv(artifact_dir / "single" / "summary.csv")
    single_ratio_summary = load_csv(artifact_dir / "single" / "ratio_summary.csv")
    rule_summary = load_csv(artifact_dir / "sequential" / "rule_summary.csv")
    drift_summary = load_csv(artifact_dir / "sequential" / "drift_summary.csv")
    chsh_summary = load_csv(artifact_dir / "sequential" / "chsh_summary.csv")

    plot_projectivity_vs_ratio(single_ratio_summary, plots_dir / "projectivity-vs-anisotropy.png")
    plot_residual_quality_vs_ratio(single_ratio_summary, plots_dir / "residual-quality-vs-anisotropy.png")
    plot_branch_response_vs_angle(single_summary, plots_dir / "single-branch-response-vs-angle.png")
    plot_state_clouds(single_trials, plots_dir / "state-clouds-before-after.png", args.state_cloud_limit)
    plot_marginal_drift(rule_summary, plots_dir / "marginal-drift-vs-remote-angle.png")
    plot_aligned_mass(rule_summary, plots_dir / "aligned-same-sign-mass-vs-anisotropy.png")
    plot_correlation_vs_delta(rule_summary, plots_dir / "correlation-vs-delta.png")
    plot_chsh(chsh_summary, plots_dir / "chsh-vs-anisotropy.png")

    summary["plots"] = {
        "projectivity_vs_anisotropy": str(plots_dir / "projectivity-vs-anisotropy.png"),
        "residual_quality_vs_anisotropy": str(plots_dir / "residual-quality-vs-anisotropy.png"),
        "single_branch_response_vs_angle": str(plots_dir / "single-branch-response-vs-angle.png"),
        "state_clouds_before_after": str(plots_dir / "state-clouds-before-after.png"),
        "marginal_drift_vs_remote_angle": str(plots_dir / "marginal-drift-vs-remote-angle.png"),
        "aligned_same_sign_mass_vs_anisotropy": str(plots_dir / "aligned-same-sign-mass-vs-anisotropy.png"),
        "correlation_vs_delta": str(plots_dir / "correlation-vs-delta.png"),
        "chsh_vs_anisotropy": str(plots_dir / "chsh-vs-anisotropy.png"),
    }
    summary["failure_modes"] = detect_failures(single_ratio_summary, drift_summary, chsh_summary)
    summary["report_answers"] = build_report_answers(single_ratio_summary, drift_summary, chsh_summary)
    dump_json(artifact_dir / "summary.json", summary)
    print(f"Wrote plots and updated summary in {artifact_dir}")


if __name__ == "__main__":
    main()
