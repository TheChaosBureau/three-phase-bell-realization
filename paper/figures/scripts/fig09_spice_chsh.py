"""
Figure 9: SPICE-driven preferred chain — CHSH magnitude.

The SPICE-driven preferred chain report builder
(`physical_front_end_candidate/experiments/build_spice_driven_preferred_chain_report.py`)
already produces a publication-quality CHSH plot via
`physical_front_end_candidate.spice_driven_preferred_chain_plots.plot_spice_driven_chsh`,
saved to:

    artifacts/spice_driven_preferred_chain/full_chain/chsh_exact_vs_empirical.png

This script copies that PNG into paper/figures/fig09_spice_chsh.png so the
paper can embed it. It does NOT re-render the figure; the source-of-truth
plotting is in the existing report builder.

Requires: prior `make spice-driven-preferred-chain-report` run.

Run inside the nix dev shell:
    poetry run python paper/figures/scripts/fig09_spice_chsh.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent.parent

SRC = REPO / "artifacts" / "spice_driven_preferred_chain" / "full_chain" / "chsh_exact_vs_empirical.png"
DST = OUT / "fig09_spice_chsh.png"


def main() -> int:
    if not SRC.exists():
        print(f"[fig09] missing artifact: {SRC}", file=sys.stderr)
        print("        Run: make spice-driven-preferred-chain-report",
              file=sys.stderr)
        return 1
    shutil.copyfile(SRC, DST)
    print(f"copied {SRC} -> {DST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
