from __future__ import annotations

from dataclasses import dataclass
import math

import matplotlib.pyplot as plt
import numpy as np

from .analyzer_couplers import AnalyzerCouplers
from .joint_readout import JointReadout
from .shared_4tank_core import BASIS_LABELS, Shared4TankCore, singlet_state


def singlet_closed_form_weights(a_deg: float, b_deg: float) -> np.ndarray:
    delta = math.radians(a_deg - b_deg)
    return np.array(
        [
            0.5 * math.sin(delta) ** 2,
            0.5 * math.cos(delta) ** 2,
            0.5 * math.cos(delta) ** 2,
            0.5 * math.sin(delta) ** 2,
        ],
        dtype=float,
    )


def theory_correlator(a_deg: float, b_deg: float) -> float:
    delta = math.radians(a_deg - b_deg)
    return -math.cos(2.0 * delta)


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    a_deg: float
    b_deg: float
    expected_weights: np.ndarray
    expected_correlator: float


@dataclass(frozen=True)
class BenchmarkResult:
    case: BenchmarkCase
    fractions: np.ndarray
    branch_energies: np.ndarray
    correlator: float
    rms_error: float
    absolute_error: np.ndarray


def benchmark_cases() -> tuple[BenchmarkCase, ...]:
    return (
        BenchmarkCase(
            name="Case A",
            a_deg=0.0,
            b_deg=0.0,
            expected_weights=np.array([0.0, 0.5, 0.5, 0.0], dtype=float),
            expected_correlator=-1.0,
        ),
        BenchmarkCase(
            name="Case B",
            a_deg=45.0,
            b_deg=22.5,
            expected_weights=singlet_closed_form_weights(45.0, 22.5),
            expected_correlator=theory_correlator(45.0, 22.5),
        ),
    )


def run_benchmark_case(
    core: Shared4TankCore,
    readout: JointReadout,
    case: BenchmarkCase,
    prepared_state: np.ndarray | None = None,
) -> BenchmarkResult:
    state = singlet_state() if prepared_state is None else prepared_state
    measurement = readout.measure(state, a_deg=case.a_deg, b_deg=case.b_deg)
    absolute_error = np.abs(measurement.fractions - case.expected_weights)
    return BenchmarkResult(
        case=case,
        fractions=measurement.fractions,
        branch_energies=measurement.branch_energies,
        correlator=measurement.correlator,
        rms_error=float(np.sqrt(np.mean((measurement.fractions - case.expected_weights) ** 2))),
        absolute_error=absolute_error,
    )


def chsh_value(
    readout: JointReadout,
    state: np.ndarray | None = None,
    *,
    a0_deg: float = 0.0,
    a1_deg: float = 45.0,
    b0_deg: float = 22.5,
    b1_deg: float = -22.5,
) -> float:
    vector = singlet_state() if state is None else state
    e_a0b0 = readout.measure(vector, a0_deg, b0_deg).correlator
    e_a0b1 = readout.measure(vector, a0_deg, b1_deg).correlator
    e_a1b0 = readout.measure(vector, a1_deg, b0_deg).correlator
    e_a1b1 = readout.measure(vector, a1_deg, b1_deg).correlator
    return e_a0b0 + e_a0b1 + e_a1b0 - e_a1b1


def angle_sweep(
    readout: JointReadout,
    a_values_deg: np.ndarray,
    b_values_deg: np.ndarray,
    state: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    vector = singlet_state() if state is None else state
    correlators = np.empty((len(a_values_deg), len(b_values_deg)), dtype=float)
    theory = np.empty_like(correlators)

    for i, a_deg in enumerate(a_values_deg):
        for j, b_deg in enumerate(b_values_deg):
            correlators[i, j] = readout.measure(vector, float(a_deg), float(b_deg)).correlator
            theory[i, j] = theory_correlator(float(a_deg), float(b_deg))

    return correlators, theory, correlators - theory


def coupling_sweep(
    kappas: np.ndarray,
    *,
    omega0: float = 1.0,
    gamma: float = 0.01,
) -> list[tuple[float, float, float]]:
    rows: list[tuple[float, float, float]] = []
    for kappa in kappas:
        core = Shared4TankCore(omega0=omega0, kappa=float(kappa), gamma=gamma)
        preparation = core.prepare_singlet_mode()
        rows.append((float(kappa), preparation.singlet_mode_energy, preparation.singlet_state_overlap))
    return rows


def sensitivity_sweep(
    core: Shared4TankCore,
    analyzers: AnalyzerCouplers,
    readout: JointReadout,
    *,
    mismatch_levels: tuple[float, ...],
) -> list[tuple[float, float, float]]:
    rows: list[tuple[float, float, float]] = []
    for level in mismatch_levels:
        disturbed_core = Shared4TankCore(
            omega0=core.omega0,
            kappa=core.kappa,
            gamma=core.gamma,
            imperfections=core.imperfections.__class__(
                lc_mismatch=(level, -level, level, -level),
                damping_imbalance=(0.5 * level,) * 4,
                coupling_scale=1.0 - level,
                prep_amplitude_imbalance=level,
                prep_phase_error_deg=45.0 * level,
            ),
        )
        disturbed_analyzers = AnalyzerCouplers(
            imperfections=analyzers.imperfections.__class__(
                alice_angle_offset_deg=45.0 * level,
                bob_angle_offset_deg=-45.0 * level,
                alice_gain_error=level,
                bob_gain_error=-level,
                alice_phase_error_deg=90.0 * level,
                bob_phase_error_deg=-90.0 * level,
            )
        )
        disturbed_readout = JointReadout(
            analyzers=disturbed_analyzers,
            nominal_resistance_ohm=readout.nominal_resistance_ohm,
            imperfections=readout.imperfections.__class__(
                resistor_tolerance=(level, -level, level, -level),
                branch_gain_error=(0.5 * level, -0.5 * level, 0.5 * level, -0.5 * level),
            ),
        )
        prepared_state = disturbed_core.prepare_singlet_mode().normalized_state
        case_b = BenchmarkCase(
            name="Case B",
            a_deg=45.0,
            b_deg=22.5,
            expected_weights=singlet_closed_form_weights(45.0, 22.5),
            expected_correlator=theory_correlator(45.0, 22.5),
        )
        result = run_benchmark_case(
            disturbed_core,
            disturbed_readout,
            case_b,
            prepared_state=prepared_state,
        )
        rows.append((level, result.rms_error, abs(result.correlator - case_b.expected_correlator)))
    return rows


def benchmark_table(results: list[BenchmarkResult]) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for result in results:
        row: dict[str, float | str] = {
            "case": result.case.name,
            "a_deg": result.case.a_deg,
            "b_deg": result.case.b_deg,
            "correlator_exact": result.case.expected_correlator,
            "correlator_simulated": result.correlator,
            "rms_error": result.rms_error,
        }
        for label, exact, simulated in zip(
            BASIS_LABELS,
            result.case.expected_weights,
            result.fractions,
            strict=True,
        ):
            row[f"{label}_exact"] = float(exact)
            row[f"{label}_simulated"] = float(simulated)
            row[f"{label}_abs_error"] = float(abs(simulated - exact))
        rows.append(row)
    return rows


def plot_core_spectrum(core: Shared4TankCore) -> plt.Figure:
    uncoupled = core.analyze_modes(coupled=False).eigenvalues
    coupled = core.analyze_modes(coupled=True).eigenvalues
    figure, axis = plt.subplots(figsize=(7, 4))
    indices = np.arange(4)
    axis.scatter(indices - 0.08, uncoupled, label="Uncoupled", color="#607d8b", s=70)
    axis.scatter(indices + 0.08, coupled, label="Coupled", color="#c0392b", s=70)
    axis.set_xticks(indices, BASIS_LABELS)
    axis.set_ylabel("Eigenfrequency (rad/s)")
    axis.set_title("Shared 4-Tank Core Spectrum")
    axis.legend(frameon=False)
    axis.grid(alpha=0.2)
    return figure


def plot_singlet_overlap(kappas: np.ndarray, sweep_rows: list[tuple[float, float, float]]) -> plt.Figure:
    _, singlet_mode_energy, singlet_state_overlap = zip(*sweep_rows, strict=True)
    figure, axis = plt.subplots(figsize=(7, 4))
    axis.plot(kappas, singlet_mode_energy, label="Mode energy overlap", color="#1b998b", linewidth=2)
    axis.plot(kappas, singlet_state_overlap, label="State overlap", color="#2d3047", linewidth=2)
    axis.set_xlabel("Coupling strength kappa")
    axis.set_ylabel("Overlap")
    axis.set_ylim(0.0, 1.05)
    axis.set_title("Singlet Preparation Robustness")
    axis.grid(alpha=0.2)
    axis.legend(frameon=False)
    return figure


def plot_correlator_surface(
    a_values_deg: np.ndarray,
    b_values_deg: np.ndarray,
    correlators: np.ndarray,
) -> plt.Figure:
    figure, axis = plt.subplots(figsize=(7, 4.5))
    image = axis.imshow(
        correlators,
        origin="lower",
        aspect="auto",
        extent=[b_values_deg[0], b_values_deg[-1], a_values_deg[0], a_values_deg[-1]],
        cmap="coolwarm",
        vmin=-1.0,
        vmax=1.0,
    )
    axis.set_xlabel("Bob angle b (deg)")
    axis.set_ylabel("Alice angle a (deg)")
    axis.set_title("Correlator Surface E(a, b)")
    figure.colorbar(image, ax=axis, label="E(a, b)")
    return figure


__all__ = [
    "BenchmarkCase",
    "BenchmarkResult",
    "angle_sweep",
    "benchmark_cases",
    "benchmark_table",
    "chsh_value",
    "coupling_sweep",
    "plot_core_spectrum",
    "plot_correlator_surface",
    "plot_singlet_overlap",
    "run_benchmark_case",
    "sensitivity_sweep",
    "singlet_closed_form_weights",
    "theory_correlator",
]
