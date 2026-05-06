"""
Figure 11 — DEPRECATED: removed from the paper.

Earlier versions of this script generated a "phase-descent calibration"
figure for the SPICE chain, but the underlying calibration data lives in
notebooks/15_calibration.qmd, which characterizes a *different* network
(a 9-coil bright/dark transformer correlator), not the 4-tank LC chain
of this paper. Quoting those numbers in the SPICE chain section was an
overclaim, and the figure has been removed from `paper/paper.qmd`.

This file is kept as a stub so old `make figures` invocations don't
silently fail with "missing script" — instead it exits with a clear
explanation.

If you later instrument the SPICE chain through the phase-descent
calibration framework of `notebooks/15_calibration.qmd`, replace this
stub with a real loader against the resulting artifacts.
"""

from __future__ import annotations

import sys


def main() -> int:
    print(
        "[fig11] DEPRECATED. Phase-descent calibration data lives in\n"
        "        notebooks/15_calibration.qmd, which targets a different\n"
        "        network than the 4-tank SPICE chain of this paper.\n"
        "        The figure has been removed from paper/paper.qmd.\n"
        "        See the docstring of this file for details.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    main()
