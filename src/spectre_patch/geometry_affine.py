"""2D affine composition for canonical → world similarity transforms."""

from __future__ import annotations

import numpy as np


def mat3_from_affine6(M: np.ndarray) -> np.ndarray:
    return np.array(
        [
            [M[0], M[1], M[2]],
            [M[3], M[4], M[5]],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )


def similarity_client(scale: float, rotation_deg: float, tx: float, ty: float) -> np.ndarray:
    th = np.deg2rad(float(rotation_deg))
    c, s = np.cos(th), np.sin(th)
    k = float(scale)
    return np.array(
        [[k * c, -k * s, float(tx)], [k * s, k * c, float(ty)], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )


def compose_world_affine(
    *,
    canonical_gen6: np.ndarray,
    scale: float,
    rotation_deg: float,
    tx: float,
    ty: float,
) -> np.ndarray:
    """World = ClientSimilarity ⊗ CanonicalPlacement (applied to column vectors)."""
    return similarity_client(scale, rotation_deg, tx, ty) @ mat3_from_affine6(canonical_gen6)


def decompose_uniform_similarity(W: np.ndarray) -> tuple[float, float, float, float]:
    """Return (tx, ty, theta_rad, scale) assuming near-uniform similarity."""
    a, b = float(W[0, 0]), float(W[0, 1])
    c = float(W[1, 0])
    tx, ty = float(W[0, 2]), float(W[1, 2])
    scale_x = float(np.hypot(a, c))
    scale_y = float(np.hypot(b, float(W[1, 1])))
    scale = float((scale_x + scale_y) / 2.0)
    theta = float(np.arctan2(c, a))
    return tx, ty, theta, scale
