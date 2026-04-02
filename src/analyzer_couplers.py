from __future__ import annotations

from dataclasses import dataclass, field
import math

import numpy as np


def rotation(theta_rad: float) -> np.ndarray:
    cosine = math.cos(theta_rad)
    sine = math.sin(theta_rad)
    return np.array([[cosine, sine], [-sine, cosine]], dtype=np.complex128)


@dataclass(frozen=True)
class AnalyzerImperfections:
    alice_angle_offset_deg: float = 0.0
    bob_angle_offset_deg: float = 0.0
    alice_gain_error: float = 0.0
    bob_gain_error: float = 0.0
    alice_phase_error_deg: float = 0.0
    bob_phase_error_deg: float = 0.0


@dataclass
class AnalyzerCouplers:
    imperfections: AnalyzerImperfections = field(default_factory=AnalyzerImperfections)

    def _single_coupler(
        self,
        theta_deg: float,
        *,
        angle_offset_deg: float,
        gain_error: float,
        phase_error_deg: float,
    ) -> np.ndarray:
        theta = math.radians(theta_deg + angle_offset_deg)
        base = rotation(theta)
        gain_matrix = np.diag([1.0 + gain_error, 1.0 - gain_error]).astype(
            np.complex128
        )
        phase = math.radians(phase_error_deg)
        phase_matrix = np.diag(
            [
                np.exp(0.5j * phase),
                np.exp(-0.5j * phase),
            ]
        ).astype(np.complex128)
        return phase_matrix @ gain_matrix @ base

    def alice_matrix(self, a_deg: float) -> np.ndarray:
        return self._single_coupler(
            a_deg,
            angle_offset_deg=self.imperfections.alice_angle_offset_deg,
            gain_error=self.imperfections.alice_gain_error,
            phase_error_deg=self.imperfections.alice_phase_error_deg,
        )

    def bob_matrix(self, b_deg: float) -> np.ndarray:
        return self._single_coupler(
            b_deg,
            angle_offset_deg=self.imperfections.bob_angle_offset_deg,
            gain_error=self.imperfections.bob_gain_error,
            phase_error_deg=self.imperfections.bob_phase_error_deg,
        )

    def joint_matrix(self, a_deg: float, b_deg: float) -> np.ndarray:
        return np.kron(self.alice_matrix(a_deg), self.bob_matrix(b_deg))

    def apply(self, state: np.ndarray, a_deg: float, b_deg: float) -> np.ndarray:
        vector = np.asarray(state, dtype=np.complex128).reshape(4)
        return self.joint_matrix(a_deg, b_deg) @ vector

    def matrix_error_metrics(self, a_deg: float, b_deg: float) -> tuple[float, float]:
        ideal = np.kron(rotation(math.radians(a_deg)), rotation(math.radians(b_deg)))
        actual = self.joint_matrix(a_deg, b_deg)

        amplitude_error = np.max(np.abs(np.abs(actual) - np.abs(ideal)))

        mask = np.abs(ideal) > 1e-12
        relative = actual[mask] / ideal[mask]
        phase_error_deg = np.max(np.abs(np.angle(relative, deg=True)))
        return float(amplitude_error), float(phase_error_deg)


__all__ = [
    "AnalyzerCouplers",
    "AnalyzerImperfections",
    "rotation",
]
