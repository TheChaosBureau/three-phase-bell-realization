from __future__ import annotations

import math

import numpy as np


def build_basin_grid(size: int = 192) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    axis = np.linspace(-1.05, 1.05, size)
    x, y = np.meshgrid(axis, axis)
    radius = np.sqrt(x**2 + y**2)
    mask = radius <= 1.0
    return x, y, radius, mask


def shared_modes(x: np.ndarray, y: np.ndarray, radius: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    envelope = np.clip(1.0 - radius**2, 0.0, None)
    return envelope * x, envelope * y


def gaussian_mode(x: np.ndarray, y: np.ndarray, center: tuple[float, float], sigma: float) -> np.ndarray:
    cx, cy = center
    return np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2.0 * sigma**2))


def oriented_local_mode(
    x: np.ndarray,
    y: np.ndarray,
    center: tuple[float, float],
    angle: float,
    sigma: float,
    alpha: float,
    beta: float,
) -> np.ndarray:
    cx, cy = center
    dx = x - cx
    dy = y - cy
    local_u = dx * math.cos(angle) + dy * math.sin(angle)
    local_v = -dx * math.sin(angle) + dy * math.cos(angle)
    envelope = np.exp(-(dx**2 + dy**2) / (2.0 * sigma**2))
    return envelope * (alpha * local_u + beta * local_v)


def annular_mode(
    x: np.ndarray,
    y: np.ndarray,
    radius: np.ndarray,
    ring_radius: float,
    ring_width: float,
    angular_order: int,
    phase: float = 0.0,
) -> np.ndarray:
    theta = np.arctan2(y, x)
    radial = np.exp(-((radius - ring_radius) ** 2) / (2.0 * ring_width**2))
    return radial * np.cos(angular_order * theta + phase)
