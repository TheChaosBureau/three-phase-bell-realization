#!/usr/bin/env python3
"""
Generate randomized CSV waveforms for Alice and Bob, with manifest and optional previews.

Per run, creates:
  - alice_runNN.csv   (columns: time,v_ab,v_bc,v_ca)
  - bob_runNN.csv     (columns: time,v_ab,v_bc,v_ca)
Optionally:
  - runNN_preview.png (2-row figure: Alice (v_ab,v_bc,v_ca), Bob (v_ab,v_bc,v_ca))

Manifest:
  - manifest.csv with run metadata (duration, points, flips, filenames, etc.)
"""

import argparse
import csv
from pathlib import Path
import numpy as np
from numpy import deg2rad

# Only import pyplot if plotting is requested (lazy import inside function otherwise)
import matplotlib
matplotlib.use("Agg")  # safe for headless; overridden by interactive use if needed
import matplotlib.pyplot as plt

# -----------------------------
# Helpers
# -----------------------------
def phasor(mag, ang_deg):
    return mag * np.exp(1j * deg2rad(ang_deg))

def fortescue_to_phase(V0, V1, V2):
    a = np.exp(1j * 2*np.pi/3)
    Va = V0 + V1 + V2
    Vb = V0 + (a**2)*V1 + a*V2
    Vc = V0 + a*V1 + (a**2)*V2
    return Va, Vb, Vc

def time_domain(V, w, t, phi_ref=0.0):
    return np.sqrt(2) * np.real(V * np.exp(1j*(w*t + phi_ref)))

def make_time_axis(freq_hz, cycles, points_per_cycle):
    T = 1.0 / freq_hz
    N = int(np.round(points_per_cycle * cycles))
    return np.linspace(0.0, cycles * T, N, endpoint=False)

def save_preview_plot(out_path,  # Path to png
                      tA, vab_A, vbc_A, vca_A,
                      tB, vab_B, vbc_B, vca_B,
                      title_top="", title_bottom="", dpi=120):
    """Save a compact 2-row preview (Alice top, Bob bottom) with v_ab, v_bc, v_ca."""
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=False)
    axA, axB = axes

    # Alice
    axA.plot(tA, vab_A, label="v_ab")
    axA.plot(tA, vbc_A, label="v_bc")
    axA.plot(tA, vca_A, label="v_ca")
    axA.set_title(title_top)
    axA.set_ylabel("Alice LL (V)")
    axA.grid(True)
    axA.legend(loc="upper right")

    # Bob
    axB.plot(tB, vab_B, label="v_ab")
    axB.plot(tB, vbc_B, label="v_bc")
    axB.plot(tB, vca_B, label="v_ca")
    axB.set_title(title_bottom)
    axB.set_ylabel("Bob LL (V)")
    axB.set_xlabel("Time (s)")
    axB.grid(True)
    axB.legend(loc="upper right")

    fig.tight_layout()
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)

# -----------------------------
# Main generator
# -----------------------------
def generate_run_pair(rng, out_dir, run_idx, f_fundamental=60.0,
                      points_per_cycle=1000, base_voltage_mag=120.0,
                      save_plots=False, plot_dpi=120):
    theta_deg = rng.uniform(-180.0, 180.0)  # hidden common phasor angle
    phi0 = rng.uniform(0.0, 2.0*np.pi)      # time-phase to randomize start point
    dur_cycles = rng.uniform(20.0, 100.0)
    w = 2*np.pi*f_fundamental
    t = make_time_axis(f_fundamental, dur_cycles, points_per_cycle)

    # zero-sequence off
    V0 = 0.0 + 0.0j
    Vbase = phasor(base_voltage_mag, theta_deg)

    # Opposite sequences (antisymmetric singlet analog)
    alice_positive = rng.random() < 0.5
    if alice_positive:
        V1_A, V2_A = Vbase, 0.0
        V1_B, V2_B = 0.0, Vbase
    else:
        V1_A, V2_A = 0.0, Vbase
        V1_B, V2_B = Vbase, 0.0

    # Randomly flip one sequence on one side (extra antisymmetry variety)
    side_to_flip = "Alice" if rng.random() < 0.5 else "Bob"
    seq_to_flip = "positive" if rng.random() < 0.5 else "negative"

    if side_to_flip == "Alice":
        if seq_to_flip == "positive":
            if V1_A != 0: V1_A = -V1_A
            else: V2_A = -V2_A
        else:
            if V2_A != 0: V2_A = -V2_A
            else: V1_A = -V1_A
    else:
        if seq_to_flip == "positive":
            if V1_B != 0: V1_B = -V1_B
            else: V2_B = -V2_B
        else:
            if V2_B != 0: V2_B = -V2_B
            else: V1_B = -V1_B

    # Phase-domain phasors
    Va_A, Vb_A, Vc_A = fortescue_to_phase(V0, V1_A, V2_A)
    Va_B, Vb_B, Vc_B = fortescue_to_phase(V0, V1_B, V2_B)

    # Time-domain line-neutral
    va_A = time_domain(Va_A, w, t, phi0)
    vb_A = time_domain(Vb_A, w, t, phi0)
    vc_A = time_domain(Vc_A, w, t, phi0)

    va_B = time_domain(Va_B, w, t, phi0)
    vb_B = time_domain(Vb_B, w, t, phi0)
    vc_B = time_domain(Vc_B, w, t, phi0)

    # Line-to-line
    vab_A, vbc_A, vca_A = va_A - vb_A, vb_A - vc_A, vc_A - va_A
    vab_B, vbc_B, vca_B = va_B - vb_B, vb_B - vc_B, vc_B - va_B

    # Write CSVs (exact columns)
    alice_path = out_dir / f"alice_run{run_idx:02d}.csv"
    bob_path   = out_dir / f"bob_run{run_idx:02d}.csv"

    header = ["time", "v_ab", "v_bc", "v_ca"]

    def write_csv(path, time, v_ab, v_bc, v_ca):
        with path.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for i in range(len(time)):
                writer.writerow([f"{time[i]:.9f}",
                                 f"{v_ab[i]:.9f}",
                                 f"{v_bc[i]:.9f}",
                                 f"{v_ca[i]:.9f}"])

    write_csv(alice_path, t, vab_A, vbc_A, vca_A)
    write_csv(bob_path,   t, vab_B, vbc_B, vca_B)

    # Optional preview
    preview_name = f"run{run_idx:02d}_preview.png"
    preview_path = out_dir / preview_name
    if save_plots:
        title_top = f"Alice  (seq: {'+1' if alice_positive else '-1'}; flipped: {side_to_flip=='Alice'} {seq_to_flip})"
        title_bot = f"Bob    (seq: {'-1' if alice_positive else '+1'}; flipped: {side_to_flip=='Bob'} {seq_to_flip})"
        save_preview_plot(preview_path, t, vab_A, vbc_A, vca_A,
                          t, vab_B, vbc_B, vca_B,
                          title_top=title_top, title_bottom=title_bot, dpi=plot_dpi)

    # manifest entry
    return {
        "run": run_idx,
        "freq_hz": f_fundamental,
        "duration_cycles": float(dur_cycles),
        "points": int(len(t)),
        "theta_deg": float(theta_deg),
        "phi0_rad": float(phi0),
        "alice_positive": bool(alice_positive),
        "side_flipped": side_to_flip,
        "seq_flipped": seq_to_flip,
        "alice_file": alice_path.name,
        "bob_file": bob_path.name,
        "preview_file": preview_name if save_plots else "",
    }

# -----------------------------
# CLI
# -----------------------------
def main():
    p = argparse.ArgumentParser(description="Generate randomized Alice/Bob CSV waveform pairs with manifest and optional previews.")
    p.add_argument("-n", "--num-runs", type=int, default=5, help="number of run pairs to generate")
    p.add_argument("-o", "--out-dir", type=Path, default=Path("runs_out"), help="output directory")
    p.add_argument("--freq", type=float, default=60.0, help="fundamental frequency (Hz)")
    p.add_argument("--ppc", type=int, default=1000, help="points per cycle")
    p.add_argument("--mag", type=float, default=120.0, help="phasor magnitude for V1 or V2")
    p.add_argument("--seed", type=int, default=None, help="optional RNG seed for reproducibility")
    p.add_argument("--plot", action="store_true", help="save a PNG preview per run")
    p.add_argument("--plot-dpi", type=int, default=120, help="preview PNG DPI (default 120)")
    args = p.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)

    manifest = []
    print(f"Generating {args.num_runs} run pairs into: {args.out_dir.resolve()}")
    for k in range(1, args.num_runs + 1):
        info = generate_run_pair(
            rng=rng,
            out_dir=args.out_dir,
            run_idx=k,
            f_fundamental=args.freq,
            points_per_cycle=args.ppc,
            base_voltage_mag=args.mag,
            save_plots=args.plot,
            plot_dpi=args.plot_dpi,
        )
        manifest.append(info)
        extra = f", preview={info['preview_file']}" if args.plot else ""
        print(f"[run {k:02d}] {info['alice_file']} | {info['bob_file']} "
              f"(cycles~{info['duration_cycles']:.2f}, pts={info['points']}{extra})")

    # Write manifest CSV
    manifest_path = args.out_dir / "manifest.csv"
    fieldnames = [
        "run", "freq_hz", "duration_cycles", "points",
        "theta_deg", "phi0_rad",
        "alice_positive", "side_flipped", "seq_flipped",
        "alice_file", "bob_file", "preview_file",
    ]
    with manifest_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for entry in manifest:
            writer.writerow(entry)

    print(f"\nManifest written: {manifest_path.resolve()}")

if __name__ == "__main__":
    main()
