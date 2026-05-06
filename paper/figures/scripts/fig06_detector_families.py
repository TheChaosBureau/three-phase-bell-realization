"""
Figure 6: Detector family race-law fidelity comparison.

Reads `artifacts/detector_search/{model}/results.csv` for each of the four
detector families and plots the distribution of `race_rms_error` across the
parameter grid. Field names match the CSV schema documented in
`detector_search/sim/search.py::save_results_csv`:

    fieldnames = [
        "model", "score",
        "lambda_dark_fit", "alpha_fit", "linearity_rms_rel",
        "race_rms_error", "waiting_time_penalty", "mismatch_penalty",
        "params_json",
    ]

This script REQUIRES that you have run

    make detector-search DETECTOR_MODEL=<name>

for each of the four families. It exits non-zero if any family's CSV is
missing rather than fabricating values.

Run inside the nix dev shell:
    poetry run python paper/figures/scripts/fig06_detector_families.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent.parent
ARTIFACTS = REPO / "artifacts" / "detector_search"

# Order chosen to match the in-paper hierarchy: best Born family first.
FAMILIES = [
    ("shot_trigger",            "Shot-trigger",                 "C0", "o"),
    ("poisson_linear",          "Poisson-linear",               "C2", "s"),
    ("metastable_escape",       "Metastable-escape",            "C1", "^"),
    ("accumulator_bad_control", "Accumulator (bad control)",    "C3", "x"),
]


def load_race_rms(family: str) -> np.ndarray:
    """
    Load the race_rms_error column from artifacts/detector_search/{family}/results.csv.

    Schema source: detector_search.sim.search.save_results_csv.
    """
    csv_path = ARTIFACTS / family / "results.csv"
    if not csv_path.exists():
        raise FileNotFoundError(
            f"missing artifact: {csv_path}\n"
            f"Run: make detector-search DETECTOR_MODEL={family}"
        )
    values: list[float] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if "race_rms_error" not in (reader.fieldnames or []):
            raise KeyError(
                f"{csv_path} does not contain a 'race_rms_error' column. "
                f"Found columns: {reader.fieldnames}. "
                f"This script targets the schema written by "
                f"detector_search.sim.search.save_results_csv."
            )
        for row in reader:
            values.append(float(row["race_rms_error"]))
    if not values:
        raise ValueError(f"{csv_path} contained no rows.")
    return np.asarray(values, dtype=float)


def main() -> int:
    # Load all four families up front; bail out if any are missing.
    data: dict[str, np.ndarray] = {}
    missing: list[str] = []
    for family, _label, _color, _marker in FAMILIES:
        try:
            data[family] = load_race_rms(family)
        except FileNotFoundError as exc:
            missing.append(str(exc))
    if missing:
        print("[fig06] required detector_search artifacts are missing:",
              file=sys.stderr)
        for line in missing:
            print(f"  {line}", file=sys.stderr)
        return 1

    fig, ax = plt.subplots(figsize=(8.0, 4.4), constrained_layout=True)

    rng = np.random.default_rng(0)
    for k, (family, label, color, marker) in enumerate(FAMILIES):
        values = data[family]
        jitter = rng.uniform(-0.18, 0.18, size=values.size)
        legend_label = label + "  (n = " + str(values.size) + ")"
        ax.scatter(np.full_like(values, k, dtype=float) + jitter,
                   values, color=color, marker=marker, s=14, alpha=0.6,
                   label=legend_label)
        ax.hlines(float(np.median(values)), k - 0.3, k + 0.3, color=color,
                  lw=2.0)

    ax.set_yscale("log")
    ax.set_xticks(list(range(len(FAMILIES))))
    ax.set_xticklabels([lbl for _, lbl, _, _ in FAMILIES], rotation=12,
                       fontsize=9)
    ax.set_ylabel(r"$\mathrm{race\_rms\_error}$ (log scale)")
    ax.set_title("Detector family fidelity vs.\\ Theorem 7.1 Born target")
    ax.grid(True, axis="y", alpha=0.25, which="both")
    ax.legend(fontsize=8, frameon=False, loc="lower right")

    for ext in ("pdf", "png"):
        out = OUT / f"fig06_detector_families.{ext}"
        fig.savefig(out, dpi=200, bbox_inches="tight")
        print(f"wrote {out}")
    plt.close(fig)
    return 0


if __name__ == "__main__":
    sys.exit(main())
