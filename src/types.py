from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
import cmath

Click = Literal[+1, -1]
OutcomeLabel = Literal["++", "+-", "-+", "--"]


@dataclass
class SequenceState:
    # Alice
    VA_plus: complex
    VA_minus: complex
    IA_plus: complex
    IA_minus: complex

    # Bob
    VB_plus: complex
    VB_minus: complex
    IB_plus: complex
    IB_minus: complex


@dataclass
class LocalModeAmplitudes:
    plus: complex
    minus: complex


@dataclass
class AnalyzerOutputs:
    u: complex
    v: complex


@dataclass
class CoincidenceAmplitudes:
    pp: complex
    pm: complex
    mp: complex
    mm: complex


@dataclass
class CoincidenceProbabilities:
    pp: float
    pm: float
    mp: float
    mm: float


@dataclass
class DetectorState:
    xi_plus: float = 0.0
    xi_minus: float = 0.0
    clicked: bool = False
    outcome: Click | None = None
    click_time: float | None = None