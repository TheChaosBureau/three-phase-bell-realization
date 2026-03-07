from __future__ import annotations
import cmath
import math

from .types import SequenceState, LocalModeAmplitudes, AnalyzerOutputs, CoincidenceAmplitudes


def power_wave_amplitude(V: complex, I: complex, G0: float) -> complex:
    """
    A = ( sqrt(G0) V + I / sqrt(G0) ) / sqrt(2)
    """
    return (math.sqrt(G0) * V + I / math.sqrt(G0)) / math.sqrt(2.0)


def extract_local_modes_A(state: SequenceState, G0: float) -> LocalModeAmplitudes:
    return LocalModeAmplitudes(
        plus=power_wave_amplitude(state.VA_plus, state.IA_plus, G0),
        minus=power_wave_amplitude(state.VA_minus, state.IA_minus, G0),
    )


def extract_local_modes_B(state: SequenceState, G0: float) -> LocalModeAmplitudes:
    return LocalModeAmplitudes(
        plus=power_wave_amplitude(state.VB_plus, state.IB_plus, G0),
        minus=power_wave_amplitude(state.VB_minus, state.IB_minus, G0),
    )


def rotate_analyzer(modes: LocalModeAmplitudes, theta: float) -> AnalyzerOutputs:
    """
    u = (e^{-j theta} plus + e^{+j theta} minus)/sqrt(2)
    v = (-e^{-j theta} plus + e^{+j theta} minus)/sqrt(2)
    """
    e_minus = cmath.exp(-1j * theta)
    e_plus = cmath.exp(+1j * theta)

    u = (e_minus * modes.plus + e_plus * modes.minus) / math.sqrt(2.0)
    v = (-e_minus * modes.plus + e_plus * modes.minus) / math.sqrt(2.0)
    return AnalyzerOutputs(u=u, v=v)


def coincidence_amplitudes(state: SequenceState, a: float, b: float, G0: float) -> CoincidenceAmplitudes:
    """
    For the simplified bench model, coincidence amplitudes are just products of local analyzer outputs.
    """
    A_modes = extract_local_modes_A(state, G0)
    B_modes = extract_local_modes_B(state, G0)

    A_out = rotate_analyzer(A_modes, a)
    B_out = rotate_analyzer(B_modes, b)

    return CoincidenceAmplitudes(
        pp=A_out.u * B_out.u,
        pm=A_out.u * B_out.v,
        mp=A_out.v * B_out.u,
        mm=A_out.v * B_out.v,
    )


def coincidence_probabilities(state: SequenceState, a: float, b: float, G0: float):
    amps = coincidence_amplitudes(state, a, b, G0)
    raw = {
        "++": abs(amps.pp) ** 2,
        "+-": abs(amps.pm) ** 2,
        "-+": abs(amps.mp) ** 2,
        "--": abs(amps.mm) ** 2,
    }
    total = sum(raw.values())
    return {k: v / total for k, v in raw.items()}