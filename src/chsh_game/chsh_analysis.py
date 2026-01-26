#!/usr/bin/env python3
"""
Setup:
  - Local CHSH analyzer for Alice or Bob.

Reads:
  - Ref settings CSV: settings.csv with columns [run,x,y]
  - One or more data CSVs: time,v_ab,v_bc,v_ca

Role:
  --role alice  (uses bit x and angles a / a-prime)
  --role bob    (uses bit y and angles b / b-prime)

Outputs:
  - alice_outcomes.csv  OR  bob_outcomes.csv (in --out-dir)
    Columns:
      run,file,setting_bit,angle_deg,Pd,Pq,S,vote,
      resid_rms_llsum,freq_est_hz,points,duration_s,dt_s
"""

import argparse
import csv
import re
from pathlib import Path
import math
import numpy as np
from numpy import deg2rad

# ----------------------------
# IO helpers
# ----------------------------
def load_settings(path):
    """Load settings.csv into dict: run -> (x,y)."""
    table = {}
    with open(path, "r", newline="") as f:
        r = csv.reader(f)
        header = next(r, None)
        if header is None or [h.strip() for h in header] != ["run", "x", "y"]:
            raise ValueError(f"{path}: expected header exactly 'run,x,y'")
        for row in r:
            if len(row) != 3:
                continue
            run = int(row[0])
            x = int(row[1])
            y = int(row[2])
            if x not in (0,1) or y not in (0,1):
                raise ValueError(f"{path}: x/y must be 0 or 1 (got x={x}, y={y}, run={run})")
            table[run] = (x, y)
    return table

def load_ll_csv(path):
    """Load a CSV with header [time,v_ab,v_bc,v_ca]."""
    t_list, vab_list, vbc_list, vca_list = [], [], [], []
    with open(path, "r", newline="") as f:
        r = csv.reader(f)
        header = next(r, None)
        if header is None or [h.strip() for h in header] != ["time", "v_ab", "v_bc", "v_ca"]:
            raise ValueError(f"{path}: expected header exactly 'time,v_ab,v_bc,v_ca'")
        for row in r:
            if len(row) != 4:
                continue
            t_list.append(float(row[0]))
            vab_list.append(float(row[1]))
            vbc_list.append(float(row[2]))
            vca_list.append(float(row[3]))
    t = np.array(t_list, dtype=float)
    vab = np.array(vab_list, dtype=float)
    vbc = np.array(vbc_list, dtype=float)
    vca = np.array(vca_list, dtype=float)
    return t, vab, vbc, vca

# ----------------------------
# Math helpers
# ----------------------------
def reconstruct_line_neutral(vab, vbc, vca):
    """
    Reconstruct va,vb,vc with zero-sequence ~ 0 constraint.
    vb = (vbc - vab)/3
    va = (2*vab + vbc)/3
    vc = -(va + vb)
    resid_rms is RMS of (vab+vbc+vca), ideally ~0.
    """
    vb = (vbc - vab) / 3.0
    va = (2.0*vab + vbc) / 3.0
    vc = -(va + vb)
    resid = vab + vbc + vca
    resid_rms = float(np.sqrt(np.mean(resid*resid)))
    return va, vb, vc, resid_rms

def clarke_transform(va, vb, vc):
    """Power-invariant Clarke to alpha,beta,zero."""
    k = math.sqrt(2.0/3.0)
    v_alpha = k * (1.0*va + (-0.5)*vb + (-0.5)*vc)
    v_beta  = k * (0.0*va + (math.sqrt(3)/2.0)*vb + (-math.sqrt(3)/2.0)*vc)
    v_zero  = k * ((1.0/math.sqrt(2.0))*va + (1.0/math.sqrt(2.0))*vb + (1.0/math.sqrt(2.0))*vc)
    return v_alpha, v_beta, v_zero

def park_transform(v_alpha, v_beta, angle_deg):
    """Rotate alpha/beta by -angle into d/q (angle in degrees)."""
    a = deg2rad(angle_deg)
    cosA, sinA = math.cos(a), math.sin(a)
    v_d =  cosA*v_alpha + sinA*v_beta
    v_q = -sinA*v_alpha + cosA*v_beta
    return v_d, v_q

def square_law_metrics(v_d, v_q):
    Pd = float(np.mean(v_d*v_d))
    Pq = float(np.mean(v_q*v_q))
    denom = Pd + Pq
    S = float((Pd - Pq) / denom) if denom > 0 else 0.0
    return Pd, Pq, S

def rough_freq_est(t, sig):
    """Very rough frequency estimate from zero crossings of a detrended signal."""
    if t.size < 3:
        return float("nan")
    s = np.signbit(sig - np.mean(sig))
    zc = np.where(np.diff(s))[0]
    if zc.size < 3:
        return float("nan")
    periods = []
    for i in range(len(zc) - 2):
        t1 = t[zc[i]+1]
        t2 = t[zc[i+2]+1]
        periods.append(t2 - t1)
    if not periods:
        return float("nan")
    T = float(np.mean(periods))
    return 1.0 / T if T > 0 else float("nan")

# ----------------------------
# Run id parsing
# ----------------------------
_RUN_RE = re.compile(r".*?(\d+)\D*$")  # last integer group in name

def infer_run_id(path: Path) -> int:
    """Extract run id from filename like 'alice_run07.csv' -> 7."""
    m = _RUN_RE.match(path.stem)
    if not m:
        raise ValueError(f"Cannot infer run id from filename: {path.name}")
    return int(m.group(1))

# ----------------------------
# Analysis per file
# ----------------------------
def analyze_file_for_role(csv_path: Path, role: str, settings_by_run: dict,
                          a_deg: float, a_prime_deg: float,
                          b_deg: float, b_prime_deg: float):
    run_id = infer_run_id(csv_path)
    if run_id not in settings_by_run:
        raise ValueError(f"Run {run_id} not present in settings")

    x, y = settings_by_run[run_id]
    if role == "alice":
        setting_bit = x
        angle_deg = a_deg if x == 0 else a_prime_deg
    else:
        setting_bit = y
        angle_deg = b_deg if y == 0 else b_prime_deg

    t, vab, vbc, vca = load_ll_csv(csv_path)
    npts = int(t.size)
    dt = float(t[1] - t[0]) if npts > 1 else float("nan")
    duration = float(t[-1] - t[0]) if npts > 1 else 0.0

    va, vb, vc, resid_rms = reconstruct_line_neutral(vab, vbc, vca)
    v_alpha, v_beta, _ = clarke_transform(va, vb, vc)
    v_d, v_q = park_transform(v_alpha, v_beta, angle_deg)
    Pd, Pq, S = square_law_metrics(v_d, v_q)
    vote = +1 if S >= 0.0 else -1
    freq_est = rough_freq_est(t, vab)

    return {
        "run": run_id,
        "file": csv_path.name,
        "setting_bit": setting_bit,
        "angle_deg": angle_deg,
        "Pd": Pd, "Pq": Pq, "S": S, "vote": vote,
        "resid_rms_llsum": resid_rms,
        "freq_est_hz": freq_est,
        "points": npts,
        "duration_s": duration,
        "dt_s": dt,
    }

# ----------------------------
# CLI
# ----------------------------
def main():
    ap = argparse.ArgumentParser(description="CHSH Option A: local analyzer for Alice or Bob (uses Ref settings).")
    ap.add_argument("inputs", nargs="+", help="Input CSV files (time,v_ab,v_bc,v_ca)")
    ap.add_argument("-r", "--role", choices=["alice", "bob"], required=True, help="Which party you are")
    ap.add_argument("-s", "--settings", type=Path, required=True, help="Ref settings CSV (run,x,y)")
    ap.add_argument("-o", "--out-dir", type=Path, default=Path("analysis_out"), help="Output directory")

    # Default to canonical CHSH angles; can be overridden
    ap.add_argument("--a-deg", type=float, default=0.0, help="Alice angle a (deg) for x=0")
    ap.add_argument("--a-prime-deg", type=float, default=45.0, help="Alice angle a' (deg) for x=1")
    ap.add_argument("--b-deg", type=float, default=22.5, help="Bob angle b (deg) for y=0")
    ap.add_argument("--b-prime-deg", type=float, default=67.5, help="Bob angle b' (deg) for y=1")

    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    # Validate angle pair appropriate for role (not strictly necessary, but helpful)
    if args.role == "alice" and (args.a_deg is None or args.a_prime_deg is None):
        raise SystemExit("For role=alice you must supply --a-deg and --a-prime-deg")
    if args.role == "bob" and (args.b_deg is None or args.b_prime_deg is None):
        raise SystemExit("For role=bob you must supply --b-deg and --b-prime-deg")

    settings_by_run = load_settings(args.settings)

    rows = []
    for inp in args.inputs:
        try:
            res = analyze_file_for_role(
                Path(inp), args.role, settings_by_run,
                a_deg=args.a_deg, a_prime_deg=args.a_prime_deg,
                b_deg=args.b_deg, b_prime_deg=args.b_prime_deg,
            )
            rows.append(res)
            print(f"[OK] run={res['run']:02d} {res['file']}  bit={res['setting_bit']}  angle={res['angle_deg']:.2f}°  vote={res['vote']}  S={res['S']:.6f}")
        except Exception as e:
            print(f"[ERR] {inp}: {e}")

    out_csv = args.out_dir / ("alice_outcomes.csv" if args.role == "alice" else "bob_outcomes.csv")
    fieldnames = [
        "run", "file", "setting_bit", "angle_deg",
        "Pd", "Pq", "S", "vote",
        "resid_rms_llsum", "freq_est_hz",
        "points", "duration_s", "dt_s",
    ]
    with out_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"\nWrote outcomes: {out_csv.resolve()}")

if __name__ == "__main__":
    main()
