from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .analyzer_couplers import AnalyzerCouplers


@dataclass(frozen=True)
class ReadoutImperfections:
    resistor_tolerance: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    branch_gain_error: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)


@dataclass(frozen=True)
class ReadoutResult:
    output_amplitudes: np.ndarray
    branch_energies: np.ndarray
    fractions: np.ndarray
    correlator: float


@dataclass
class JointReadout:
    analyzers: AnalyzerCouplers = field(default_factory=AnalyzerCouplers)
    nominal_resistance_ohm: float = 50.0
    imperfections: ReadoutImperfections = field(default_factory=ReadoutImperfections)

    def branch_resistances(self) -> np.ndarray:
        tolerance = np.asarray(self.imperfections.resistor_tolerance, dtype=float)
        if tolerance.shape != (4,):
            raise ValueError("resistor_tolerance must have length 4.")
        return self.nominal_resistance_ohm * (1.0 + tolerance)

    def branch_scalings(self) -> np.ndarray:
        gains = np.asarray(self.imperfections.branch_gain_error, dtype=float)
        if gains.shape != (4,):
            raise ValueError("branch_gain_error must have length 4.")
        resistances = self.branch_resistances()
        return (1.0 + gains) * (self.nominal_resistance_ohm / resistances)

    def absorbed_energies(self, output_amplitudes: np.ndarray) -> np.ndarray:
        vector = np.asarray(output_amplitudes, dtype=np.complex128).reshape(4)
        energies = np.abs(vector) ** 2 * self.branch_scalings()
        return energies.astype(float)

    def normalized_fractions(self, energies: np.ndarray) -> np.ndarray:
        values = np.asarray(energies, dtype=float).reshape(4)
        total = float(np.sum(values))
        if total <= 0.0:
            raise ValueError("Total absorbed energy must be positive.")
        return values / total

    def correlator(self, fractions: np.ndarray) -> float:
        values = np.asarray(fractions, dtype=float).reshape(4)
        return float(values[0] - values[1] - values[2] + values[3])

    def measure(self, core_state: np.ndarray, a_deg: float, b_deg: float) -> ReadoutResult:
        output_amplitudes = self.analyzers.apply(core_state, a_deg=a_deg, b_deg=b_deg)
        branch_energies = self.absorbed_energies(output_amplitudes)
        fractions = self.normalized_fractions(branch_energies)
        return ReadoutResult(
            output_amplitudes=output_amplitudes,
            branch_energies=branch_energies,
            fractions=fractions,
            correlator=self.correlator(fractions),
        )


__all__ = [
    "JointReadout",
    "ReadoutImperfections",
    "ReadoutResult",
]
