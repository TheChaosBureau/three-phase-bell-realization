#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Sequence


def clear_outputs(path: Path) -> bool:
    """Strip the execution metadata and outputs from a notebook file."""
    text = path.read_text(encoding="utf-8")
    payload = json.loads(text)
    changed = False

    for cell in payload.get("cells", []):
        if cell.get("cell_type") != "code":
            continue

        if cell.get("outputs"):
            cell["outputs"] = []
            changed = True

        if cell.get("execution_count") is not None:
            cell["execution_count"] = None
            changed = True

    if not changed:
        return False

    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return True


def clear_many(paths: Iterable[Path]) -> Sequence[Path]:
    cleared = []
    for path in paths:
        if not path.exists():
            continue

        if clear_outputs(path):
            cleared.append(path)

    return cleared


def staged_notebooks() -> Sequence[Path]:
    diff = subprocess.run(
        [
            "git",
            "diff",
            "--cached",
            "--name-only",
            "--diff-filter=ACMR",
            "-z",
            "--",
            "*.ipynb",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    if not diff.stdout:
        return []

    return [Path(file) for file in diff.stdout.split("\0") if file]


def parse_args(argv: Sequence[str] | None = None) -> Sequence[Path]:
    parser = argparse.ArgumentParser(description="Clear output metadata from staged notebooks.")
    parser.add_argument("notebooks", nargs="*", help="Paths to notebook files to clean.")
    args = parser.parse_args(argv)

    if args.notebooks:
        return [Path(nb) for nb in args.notebooks]

    return staged_notebooks()


def main(argv: Sequence[str] | None = None) -> int:
    paths = parse_args(argv)
    cleared = clear_many(paths)

    if not cleared:
        return 0

    subprocess.run(["git", "add", *[str(path) for path in cleared]], check=True)
    print(f"Cleared outputs from {len(cleared)} notebook(s).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print("Failed to stage cleaned notebooks:", exc, file=sys.stderr)
        raise
