from __future__ import annotations

import math
from typing import Any

import numpy as np

from src.analyzer_couplers import rotation


def _normalize_state(state: np.ndarray) -> np.ndarray:
    vector = np.asarray(state, dtype=np.complex128).reshape(2)
    norm = float(np.linalg.norm(vector))
    if norm <= 0.0:
        raise ValueError("Two-branch state must be nonzero.")
    return vector / norm


def _normalize_vector(vector: np.ndarray) -> np.ndarray:
    values = np.asarray(vector, dtype=np.complex128).reshape(2)
    norm = float(np.linalg.norm(values))
    if norm <= 0.0:
        raise ValueError("Analyzer basis vector must be nonzero.")
    return values / norm


def _analyzer_matrix(analyzer: Any) -> np.ndarray:
    if isinstance(analyzer, (int, float)):
        return rotation(math.radians(float(analyzer)))

    matrix = np.asarray(analyzer, dtype=np.complex128)
    if matrix.shape == (2, 2):
        return matrix

    if isinstance(analyzer, (list, tuple)) and len(analyzer) == 2:
        rows = [np.conjugate(_normalize_vector(analyzer[0])), np.conjugate(_normalize_vector(analyzer[1]))]
        return np.vstack(rows)

    raise TypeError("Analyzer must be an angle in degrees, a 2x2 matrix, or a pair of basis vectors.")


def two_branch_weights(state: np.ndarray, analyzer) -> np.ndarray:
    """Return normalized two-branch weights [w1, w2]."""
    amplitudes = _analyzer_matrix(analyzer) @ _normalize_state(state)
    weights = np.abs(amplitudes) ** 2
    total = float(np.sum(weights))
    if total <= 0.0:
        raise ValueError("Two-branch weights must sum to a positive value.")
    return (weights / total).astype(float)
