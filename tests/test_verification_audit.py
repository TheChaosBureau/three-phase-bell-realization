from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_build_verification_audit_bundle(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "artifact"
    audit_dir = tmp_path / "verification-audit"

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "run_sweeps.py"),
            "--preset",
            "risk_first_full",
            "--artifact-dir",
            str(artifact_dir),
            "--single-samples",
            "8",
            "--sequential-samples",
            "12",
            "--dense-angle-count",
            "5",
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "analyze_results.py"),
            str(artifact_dir),
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "build_verification_audit.py"),
            str(artifact_dir),
            "--output-dir",
            str(audit_dir),
        ],
        cwd=REPO_ROOT,
        check=True,
    )

    sequential_full = pd.read_csv(audit_dir / "tables" / "sequential_full.csv")
    single_full = pd.read_csv(audit_dir / "tables" / "single_full.csv")
    top_chsh = pd.read_csv(audit_dir / "tables" / "top_chsh_audit.csv")
    trust_ranking = pd.read_csv(audit_dir / "tables" / "trust_ranking.csv")

    assert {"rule", "phiA", "phiB", "CHSH", "alice_marginal_drift", "bob_marginal_drift", "no_signaling_flag", "overfit_flag"}.issubset(
        sequential_full.columns
    )
    assert {
        "angle_deg",
        "anisotropy_ratio",
        "gamma_plus",
        "gamma_minus",
        "window_fraction",
        "branch_loss_mean",
        "dominance_mean",
        "quality_to_plus",
        "quality_to_minus",
        "residual_branch_quality",
        "projectivity_score",
        "clusterability",
        "total_norm_before",
        "total_norm_after",
    }.issubset(single_full.columns)
    assert {"rule", "CHSH", "audit_note"}.issubset(top_chsh.columns)
    assert {"rule", "trust_score", "trust_label"}.issubset(trust_ranking.columns)

    assert (audit_dir / "definitions" / "readout_rules.md").exists()
    assert (audit_dir / "definitions" / "metrics.md").exists()
    assert (audit_dir / "plots" / "manifest.json").exists()
    assert (audit_dir / "raw_cases" / "manifest.json").exists()
    assert (audit_dir / "README.md").exists()
