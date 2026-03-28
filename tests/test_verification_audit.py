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

    single_full = pd.read_csv(audit_dir / "tables" / "single_full.csv")
    sequential_full = pd.read_csv(audit_dir / "tables" / "sequential_full.csv")
    gated_summary = pd.read_csv(audit_dir / "tables" / "sequential_gated_summary.csv")
    residual_agreement = pd.read_csv(audit_dir / "tables" / "sequential_residual_agreement.csv")
    aligned_support = pd.read_csv(audit_dir / "tables" / "aligned_support_by_confidence.csv")
    legacy_controls = pd.read_csv(audit_dir / "tables" / "legacy_rule_controls.csv")
    top_chsh_audit = pd.read_csv(audit_dir / "tables" / "top_sequential_chsh_audit.csv")

    assert {
        "angle_deg",
        "anisotropy_ratio",
        "gamma_plus",
        "gamma_minus",
        "window_fraction",
        "branch_loss_mean",
        "projectivity_score",
    }.issubset(single_full.columns)
    assert {
        "rule",
        "rule_display_name",
        "phiA",
        "phiB",
        "E_phiA_phiB",
        "group_residual_agreement_rate",
        "CHSH_raw",
        "headline_eligible",
    }.issubset(sequential_full.columns)
    assert {
        "rule",
        "rule_display_name",
        "residual_agreement_rate",
        "residual_ambiguity_rate",
        "mean_confidence_margin",
        "mean_projectivity_compatibility",
    }.issubset(residual_agreement.columns)
    assert {
        "rule",
        "rule_display_name",
        "alice_marginal_drift",
        "bob_marginal_drift",
        "aligned_same_sign_mass",
        "aligned_anti_mass",
        "CHSH_raw",
        "CHSH_gated",
        "headline_eligible",
    }.issubset(gated_summary.columns)
    assert {
        "rule",
        "rule_display_name",
        "aligned_same_sign_mass",
        "aligned_same_sign_mass_high_confidence",
        "high_confidence_trial_count",
        "low_confidence_trial_count",
    }.issubset(aligned_support.columns)
    assert {"rule", "rule_display_name"}.issubset(legacy_controls.columns)
    assert {"rule", "gate_blockers", "audit_note", "CHSH_raw"}.issubset(top_chsh_audit.columns)

    assert (audit_dir / "definitions" / "readout_rules.md").exists()
    assert (audit_dir / "definitions" / "metrics.md").exists()
    assert (audit_dir / "definitions" / "gate_thresholds.json").exists()
    assert (audit_dir / "plots" / "manifest.json").exists()
    assert (audit_dir / "plots" / "residual-agreement-vs-anisotropy.png").exists()
    assert (audit_dir / "plots" / "legacy-vs-redesigned-rule-comparison.png").exists()
    assert (audit_dir / "raw_cases" / "manifest.json").exists()
    assert (audit_dir / "README.md").exists()
