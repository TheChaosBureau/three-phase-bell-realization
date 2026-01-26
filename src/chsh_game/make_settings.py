#!/usr/bin/env python3
"""
Generate settings.csv for CHSH runs.

Each row: run,x,y
where x = Alice's setting bit (0 or 1)
      y = Bob's setting bit (0 or 1)

Usage:
  python make_settings.py --runs 100 --out runs_out/settings.csv --seed 42
"""

import csv
import argparse
import numpy as np
from pathlib import Path

def main():
    p = argparse.ArgumentParser(description="Generate CHSH settings.csv with fair coin flips for Alice (x) and Bob (y).")
    p.add_argument("--runs", type=int, required=True, help="Number of runs (rows) to generate.")
    p.add_argument("--out", type=Path, default=Path("settings.csv"), help="Output CSV path.")
    p.add_argument("--seed", type=int, default=None, help="Optional RNG seed for reproducibility.")
    args = p.parse_args()

    rng = np.random.default_rng(args.seed)
    x = rng.integers(0, 2, size=args.runs)
    y = rng.integers(0, 2, size=args.runs)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["run", "x", "y"])
        for i in range(args.runs):
            writer.writerow([i + 1, int(x[i]), int(y[i])])

    print(f"Wrote {args.runs} random settings to {args.out.resolve()}")

if __name__ == "__main__":
    main()
