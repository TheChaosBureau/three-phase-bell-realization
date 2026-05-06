"""
Figure 12: Closure-latch dynamics — remaining shared energy vs. time.

The SPICE-driven preferred chain report builder
(`physical_front_end_candidate/experiments/build_spice_driven_preferred_chain_report.py`)
already produces a publication-quality plot of the example trial trace via
`physical_front_end_candidate.spice_driven_preferred_chain_plots.plot_remaining_shared_energy_trace`,
saved to:

    artifacts/spice_driven_preferred_chain/post_click/remaining_shared_energy_vs_time.png

This script copies that PNG into paper/figures/fig12_closure_dynamics.png so
the paper can embed it. It does NOT re-render the figure; the source-of-truth
plotting is in the existing report builder, and the underlying trace data
(time_s, common_inhibit_v, winner_gate_v, winner_drain_current_a,
winner_drain_power_w, remaining_shared_energy_j) lives at
`artifacts/spice_driven_preferred_chain/post_click/example_trial_trace.csv`.

Requires: prior `make spice-driven-preferred-chain-report` run.

Run inside the nix dev shell:
    poetry run python paper/figures/scripts/fig12_closure_dynamics.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent.parent

SRC = (
    REPO / "artifacts" / "spice_driven_preferred_chain" / "post_click"
    / "remaining_shared_energy_vs_time.png"
)
DST = OUT / "fig12_closure_dynamics.png"


def main() -> int:
    if not SRC.exists():
        print(f"[fig12] missing artifact: {SRC}", file=sys.stderr)
        print("        Run: make spice-driven-preferred-chain-report",
              file=sys.stderr)
        return 1
    shutil.copyfile(SRC, DST)
    print(f"copied {SRC} -> {DST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
