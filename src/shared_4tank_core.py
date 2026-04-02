from __future__ import annotations

from dataclasses import dataclass, field
import math

import numpy as np

BASIS_LABELS = ("++", "+-", "-+", "--")


def normalize(vector: np.ndarray) -> np.ndarray:
    values = np.asarray(vector, dtype=np.complex128).reshape(-1)
    norm = np.linalg.norm(values)
    if norm == 0.0:
        raise ValueError("Vector must be nonzero.")
    return values / norm


def singlet_state() -> np.ndarray:
    return normalize(np.array([0.0, 1.0, -1.0, 0.0], dtype=np.complex128))


@dataclass(frozen=True)
class DeltaTank:
    label: str
    inductance_h: float
    capacitance_f: float
    nominal_frequency_rad_s: float
    branches: tuple[str, str, str] = ("ab", "bc", "ca")


@dataclass(frozen=True)
class CouplingLink:
    source: str
    target: str
    kind: str
    nominal_strength_rad_s: float
    note: str


@dataclass(frozen=True)
class PhysicalCoreIntent:
    tanks: tuple[DeltaTank, ...]
    couplers: tuple[CouplingLink, ...]
    readout_note: str


@dataclass(frozen=True)
class CoreImperfections:
    lc_mismatch: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    damping_imbalance: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    coupling_scale: float = 1.0
    prep_amplitude_imbalance: float = 0.0
    prep_phase_error_deg: float = 0.0

    def resonance_offsets(self) -> np.ndarray:
        mismatch = np.asarray(self.lc_mismatch, dtype=float)
        if mismatch.shape != (4,):
            raise ValueError("lc_mismatch must have length 4.")
        # For small perturbations, omega ~ 1 / sqrt(LC), so fractional detune is
        # approximately -0.5 * fractional product mismatch.
        return -0.5 * mismatch

    def damping_offsets(self) -> np.ndarray:
        offsets = np.asarray(self.damping_imbalance, dtype=float)
        if offsets.shape != (4,):
            raise ValueError("damping_imbalance must have length 4.")
        return offsets


@dataclass(frozen=True)
class EigenmodeAnalysis:
    eigenvalues: np.ndarray
    eigenvectors: np.ndarray
    singlet_mode_index: int
    singlet_mode_overlap: float


@dataclass(frozen=True)
class PreparationResult:
    drive_vector: np.ndarray
    drive_frequency_rad_s: float
    steady_state: np.ndarray
    normalized_state: np.ndarray
    modal_energies: np.ndarray
    dominant_mode_index: int
    singlet_mode_index: int
    singlet_mode_energy: float
    singlet_state_overlap: float


@dataclass
class Shared4TankCore:
    omega0: float = 1.0
    kappa: float = 0.25
    gamma: float = 0.01
    inductance_h: float = 10e-3
    capacitance_f: float = 1e-6
    imperfections: CoreImperfections = field(default_factory=CoreImperfections)

    def uncoupled_hamiltonian(self) -> np.ndarray:
        offsets = self.imperfections.resonance_offsets()
        resonances = self.omega0 * (1.0 + offsets)
        return np.diag(resonances.astype(np.complex128))

    def coupled_hamiltonian(self) -> np.ndarray:
        hamiltonian = self.uncoupled_hamiltonian()
        coupling = self.kappa * self.imperfections.coupling_scale
        hamiltonian[1, 1] += coupling
        hamiltonian[2, 2] += coupling
        hamiltonian[1, 2] -= coupling
        hamiltonian[2, 1] -= coupling
        return hamiltonian

    def damping_matrix(self) -> np.ndarray:
        offsets = self.imperfections.damping_offsets()
        values = self.gamma * (1.0 + offsets)
        return np.diag(values.astype(np.complex128))

    def effective_generator(self) -> np.ndarray:
        return self.coupled_hamiltonian() - 1j * self.damping_matrix()

    def intended_circuit(self) -> PhysicalCoreIntent:
        nominal_frequency = 1.0 / math.sqrt(self.inductance_h * self.capacitance_f)
        tanks = tuple(
            DeltaTank(
                label=label,
                inductance_h=self.inductance_h,
                capacitance_f=self.capacitance_f,
                nominal_frequency_rad_s=nominal_frequency,
            )
            for label in BASIS_LABELS
        )
        couplers = (
            CouplingLink(
                source="+-",
                target="-+",
                kind="transformer_or_bridging_capacitor",
                nominal_strength_rad_s=self.kappa,
                note="Antisymmetric coupling that isolates the singlet-like eigenmode.",
            ),
        )
        return PhysicalCoreIntent(
            tanks=tanks,
            couplers=couplers,
            readout_note="Readout remains passive and external to the shared core Hamiltonian.",
        )

    def analyze_modes(self, coupled: bool = True) -> EigenmodeAnalysis:
        if coupled:
            matrix = self.coupled_hamiltonian()
        else:
            matrix = self.uncoupled_hamiltonian()
        eigenvalues, eigenvectors = np.linalg.eigh(matrix)
        overlaps = np.abs(np.conjugate(eigenvectors).T @ singlet_state()) ** 2
        singlet_mode_index = int(np.argmax(overlaps))
        return EigenmodeAnalysis(
            eigenvalues=eigenvalues,
            eigenvectors=eigenvectors,
            singlet_mode_index=singlet_mode_index,
            singlet_mode_overlap=float(overlaps[singlet_mode_index]),
        )

    def preparation_drive(self, amplitude: float = 1.0) -> np.ndarray:
        phase_error = math.radians(self.imperfections.prep_phase_error_deg)
        amplitude_skew = self.imperfections.prep_amplitude_imbalance
        drive = np.array(
            [
                0.0,
                amplitude * (1.0 + amplitude_skew),
                -amplitude * (1.0 - amplitude_skew) * np.exp(1j * phase_error),
                0.0,
            ],
            dtype=np.complex128,
        )
        return drive

    def prepare_singlet_mode(
        self,
        amplitude: float = 1.0,
        drive_frequency_rad_s: float | None = None,
    ) -> PreparationResult:
        mode_info = self.analyze_modes(coupled=True)
        if drive_frequency_rad_s is None:
            drive_frequency_rad_s = float(
                np.real(mode_info.eigenvalues[mode_info.singlet_mode_index])
            )

        drive = self.preparation_drive(amplitude=amplitude)
        response_matrix = self.damping_matrix() + 1j * (
            self.coupled_hamiltonian() - drive_frequency_rad_s * np.eye(4)
        )
        steady_state = np.linalg.solve(response_matrix, drive)
        normalized_state = normalize(steady_state)

        effective = self.effective_generator()
        eigenvalues, eigenvectors = np.linalg.eig(effective)
        eigenvectors = np.asarray(
            [normalize(eigenvectors[:, idx]) for idx in range(eigenvectors.shape[1])]
        ).T
        coeffs = np.linalg.solve(eigenvectors, normalized_state)
        modal_energies = np.abs(coeffs) ** 2
        modal_energies /= np.sum(modal_energies)

        singlet_overlaps = np.abs(np.conjugate(eigenvectors).T @ singlet_state()) ** 2
        singlet_mode_index = int(np.argmax(singlet_overlaps))
        dominant_mode_index = int(np.argmax(modal_energies))

        return PreparationResult(
            drive_vector=drive,
            drive_frequency_rad_s=drive_frequency_rad_s,
            steady_state=steady_state,
            normalized_state=normalized_state,
            modal_energies=modal_energies,
            dominant_mode_index=dominant_mode_index,
            singlet_mode_index=singlet_mode_index,
            singlet_mode_energy=float(modal_energies[singlet_mode_index]),
            singlet_state_overlap=float(
                np.abs(np.vdot(singlet_state(), normalized_state)) ** 2
            ),
        )


__all__ = [
    "BASIS_LABELS",
    "CoreImperfections",
    "CouplingLink",
    "DeltaTank",
    "EigenmodeAnalysis",
    "PhysicalCoreIntent",
    "PreparationResult",
    "Shared4TankCore",
    "normalize",
    "singlet_state",
]
