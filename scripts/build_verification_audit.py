from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sim.audit import build_verification_audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the verification-audit bundle from an existing simulation artifact.")
    parser.add_argument(
        "artifact_dir",
        type=Path,
        help="Existing artifact root produced by scripts/run_sweeps.py and scripts/analyze_results.py",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts") / "sim" / "verification-audit",
        help="Destination for the expanded audit bundle.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = build_verification_audit(args.artifact_dir, args.output_dir)
    print(f"Wrote verification audit to {manifest['audit_dir']}")


if __name__ == "__main__":
    main()
