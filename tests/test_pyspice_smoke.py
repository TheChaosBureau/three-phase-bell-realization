from __future__ import annotations

import ctypes.util

import numpy as np
import pytest

pyspice = pytest.importorskip("PySpice")

from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import u_kOhm, u_V


def test_pyspice_voltage_divider_operating_point() -> None:
    libngspice = ctypes.util.find_library("ngspice") or ctypes.util.find_library("libngspice")
    assert libngspice, (
        "PySpice is installed, but libngspice is not available to the dynamic linker. "
        "Install ngspice and ensure its shared library directory is on LD_LIBRARY_PATH."
    )

    circuit = Circuit("Voltage Divider")
    circuit.V("input", "vin", circuit.gnd, 10 @ u_V)
    circuit.R(1, "vin", "vout", 1 @ u_kOhm)
    circuit.R(2, "vout", circuit.gnd, 1 @ u_kOhm)

    analysis = circuit.simulator().operating_point()
    vout = np.asarray(analysis.vout).reshape(-1)[0]
    assert vout == pytest.approx(5.0, rel=1e-3, abs=1e-3)
