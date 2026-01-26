#!/usr/bin/env python3
"""
CHSH Aggregator (CLI version)
-----------------------------
Joins Alice/Bob outcomes by run and computes:
  E_ab, E_abp, E_apb, E_apbp, S

Usage:
  python chsh_aggregate.py \
    --alice alice_analysis/alice_outcomes.csv \
    --bob bob_analysis/bob_outcomes.csv \
    --out chsh_summary.csv
"""

import csv
import argparse
from pathlib import Path

def read_outcomes(path):
    rows = {}
    with open(path, "r", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            run = int(row["run"])
            bit = int(row["setting_bit"])     # x for Alice, y for Bob
            vote = int(row["vote"])           # +1 or -1
            rows[run] = {"bit": bit, "vote": vote}
    return rows

def avg(lst):
    return sum(lst) / len(lst) if lst else 0.0

def main():
    ap = argparse.ArgumentParser(description="Compute CHSH correlations and S value from Alice/Bob outcomes.")
    ap.add_argument("--alice", required=True, help="Path to alice_outcomes.csv")
    ap.add_argument("--bob", required=True, help="Path to bob_outcomes.csv")
    ap.add_argument("--out", default="chsh_summary.csv", help="Output CSV file (default: chsh_summary.csv)")
    args = ap.parse_args()

    A = read_outcomes(args.alice)
    B = read_outcomes(args.bob)
    runs = sorted(set(A.keys()) & set(B.keys()))

    buckets = {(0,0): [], (0,1): [], (1,0): [], (1,1): []}
    for run in runs:
        x = A[run]["bit"]
        y = B[run]["bit"]
        a = A[run]["vote"]
        b = B[run]["vote"]
        if (x, y) in buckets:
            buckets[(x, y)].append(a * b)

    E_ab    = avg(buckets[(0,0)])
    E_abp   = avg(buckets[(0,1)])
    E_apb   = avg(buckets[(1,0)])
    E_apbp  = avg(buckets[(1,1)])
    S = E_ab - E_abp + E_apb + E_apbp

    out_path = Path(args.out)
    with out_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["E_ab","E_abp","E_apb","E_apbp","S","N00","N01","N10","N11","N_total"])
        w.writerow([
            f"{E_ab:.6f}", f"{E_abp:.6f}", f"{E_apb:.6f}", f"{E_apbp:.6f}", f"{S:.6f}",
            len(buckets[(0,0)]), len(buckets[(0,1)]),
            len(buckets[(1,0)]), len(buckets[(1,1)]),
            len(runs)
        ])

    print(f"E_ab={E_ab:.6f}  E_ab'={E_abp:.6f}  E_a'b={E_apb:.6f}  E_a'b'={E_apbp:.6f}")
    print(f"S = {S:.6f}")
    print(f"N00={len(buckets[(0,0)])}  N01={len(buckets[(0,1)])}  N10={len(buckets[(1,0)])}  N11={len(buckets[(1,1)])}")
    print(f"Wrote summary: {out_path.resolve()}")

if __name__ == "__main__":
    main()
