from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_run_and_analyze_pipeline_smoke(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "artifacts"
    run_cmd = [
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
    ]
    subprocess.run(run_cmd, cwd=REPO_ROOT, check=True)

    analyze_cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "analyze_results.py"),
        str(artifact_dir),
        "--state-cloud-limit",
        "50",
    ]
    subprocess.run(analyze_cmd, cwd=REPO_ROOT, check=True)

    assert (artifact_dir / "summary.json").exists()
    assert (artifact_dir / "single" / "trial_metrics.csv").exists()
    assert (artifact_dir / "single" / "states.npz").exists()
    assert (artifact_dir / "sequential" / "trial_metrics.csv").exists()
    assert (artifact_dir / "sequential" / "chsh_summary.csv").exists()
    assert (artifact_dir / "plots" / "projectivity-vs-anisotropy.png").exists()
