"""
Figure 10: Fidelity table for the SPICE-driven preferred chain.

Reads the headline numerical metrics directly from
`artifacts/spice_driven_preferred_chain/summary_metrics.json` (the source of
truth written by `build_spice_driven_preferred_chain_report.py`) and
renders them as a publication-quality table.

The field names below match the schema documented in the report builder's
`_summary_markdown` function.

This script REQUIRES the artifact JSON to exist. It exits non-zero rather
than fabricating values.

Run inside the nix dev shell:
    poetry run python paper/figures/scripts/fig10_fidelity_table.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent.parent
SUMMARY_JSON = (
    REPO / "artifacts" / "spice_driven_preferred_chain" / "summary_metrics.json"
)

# (field_in_summary_metrics, display_label, formatter)
ROWS = [
    ("chsh_abs_error",                   "CHSH absolute error",
     lambda v: f"${v:.4f}$"),
    ("winner_law_rms_error",             "Winner-law RMS error",
     lambda v: f"${v:.4f}$"),
    ("winner_law_max_error",             "Winner-law max error",
     lambda v: f"${v:.4f}$"),
    ("correlator_rms_error",             "Correlator RMS error",
     lambda v: f"${v:.4f}$"),
    ("mean_decisive_fraction",           "Mean decisive fraction",
     lambda v: f"${100*v:.2f}\\%$"),
    ("winner_drain_dominance_rate",      "Winner-drain dominance rate",
     lambda v: f"${100*v:.2f}\\%$"),
    ("mean_loser_fraction_of_post_click",
                                          "Mean loser residual frac.",
     lambda v: f"${100*v:.2f}\\%$"),
    ("completion_rate",                  "Completion rate",
     lambda v: f"${100*v:.2f}\\%$"),
    ("pre_click_transparency_rms_shift", "Pre-click transparency RMS shift",
     lambda v: f"${v:.4f}$"),
]

PASS_FIELDS = [
    ("winner_law_pass",                "winner-law pass"),
    ("correlator_pass",                "correlator pass"),
    ("chsh_pass",                       "CHSH pass"),
    ("pre_click_transparency_pass",    "pre-click transparency pass"),
    ("winner_drain_dominance_pass",    "winner-drain dominance pass"),
    ("energy_accounting_pass",         "energy-accounting pass"),
    ("actual_spice_driven_pass",       "actual SPICE-driven pass"),
]


def main() -> int:
    if not SUMMARY_JSON.exists():
        print(f"[fig10] missing artifact: {SUMMARY_JSON}", file=sys.stderr)
        print("        Run: make spice-driven-preferred-chain-report",
              file=sys.stderr)
        return 1

    with SUMMARY_JSON.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if "summary_metrics" not in payload:
        print(f"[fig10] {SUMMARY_JSON} has no 'summary_metrics' top-level key.",
              file=sys.stderr)
        return 2
    metrics = payload["summary_metrics"]

    cell_text: list[list[str]] = []
    for key, label, fmt in ROWS:
        if key not in metrics:
            print(f"[fig10] WARNING: 'summary_metrics' missing key '{key}'; "
                  f"row will show '?'", file=sys.stderr)
            cell_text.append([label, "?"])
            continue
        cell_text.append([label, fmt(float(metrics[key]))])

    # Pass/fail flags
    check = "✓"   # ✓
    cross = "✗"   # ✗
    pass_summary = []
    for key, label in PASS_FIELDS:
        if key in metrics:
            ok = bool(metrics[key])
            mark = check if ok else cross
            pass_summary.append(f"{label}: {mark}")
    if pass_summary:
        cell_text.append(["Pass flags",
                          ", ".join(pass_summary)])

    fig, ax = plt.subplots(figsize=(9.4, 0.5 + 0.36 * len(cell_text)),
                           constrained_layout=True)
    ax.axis("off")
    table = ax.table(cellText=cell_text,
                     colLabels=["Metric", "Value"],
                     cellLoc="left", colLoc="left",
                     loc="center", colWidths=[0.50, 0.48])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.0, 1.5)
    for k in range(2):
        cell = table[(0, k)]
        cell.set_text_props(weight="bold")
        cell.set_facecolor("#e8e8e8")

    ax.set_title("SPICE-driven preferred chain on the CHSH four-angle test "
                 f"(source: {SUMMARY_JSON.relative_to(REPO)})",
                 fontsize=10, pad=14)

    for ext in ("pdf", "png"):
        out = OUT / f"fig10_fidelity_table.{ext}"
        fig.savefig(out, dpi=200, bbox_inches="tight")
        print(f"wrote {out}")
    plt.close(fig)
    return 0


if __name__ == "__main__":
    sys.exit(main())
