"""Tile(1,1) / Spectre polygon + substitution tiling (deterministic recurrence).

Substitution structure is aligned with Kaplan's browser tooling via community ports
(e.g., shrx/spectre). Edge length reference: unit edges in canonical coordinates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Iterator

import numpy as np

IDENTITY_AFFINE = np.array([1.0, 0.0, 0.0, 0.0, 1.0, 0.0], dtype=np.float64)
TILE_NAMES = ("Gamma", "Delta", "Theta", "Lambda", "Xi", "Pi", "Sigma", "Phi", "Psi")

_SQRT3 = float(np.sqrt(3.0))
# Canonical Tile(1,1) prototile polygon (same vertex order as Kaplan/shrx tooling).
PROTOTILE_RING = np.array(
    [
        [0.0, 0.0],
        [1.0, 0.0],
        [1.5, -_SQRT3 / 2.0],
        [1.5 + _SQRT3 / 2.0, 0.5 - _SQRT3 / 2.0],
        [1.5 + _SQRT3 / 2.0, 1.5 - _SQRT3 / 2.0],
        [2.5 + _SQRT3 / 2.0, 1.5 - _SQRT3 / 2.0],
        [3.0 + _SQRT3 / 2.0, 1.5],
        [3.0, 2.0],
        [3.0 - _SQRT3 / 2.0, 1.5],
        [2.5 - _SQRT3 / 2.0, 1.5 + _SQRT3 / 2.0],
        [1.5 - _SQRT3 / 2.0, 1.5 + _SQRT3 / 2.0],
        [0.5 - _SQRT3 / 2.0, 1.5 + _SQRT3 / 2.0],
        [-_SQRT3 / 2.0, 1.5],
        [0.0, 1.0],
    ],
    dtype=np.float64,
)

PROTOTILE_CENTROID = PROTOTILE_RING.mean(axis=0)
PROTOTILE_LOCAL_BBOX = (
    float(PROTOTILE_RING[:, 0].min()),
    float(PROTOTILE_RING[:, 1].min()),
    float(PROTOTILE_RING[:, 0].max()),
    float(PROTOTILE_RING[:, 1].max()),
)

_DEFAULT_QUAD = (
    PROTOTILE_RING[3],
    PROTOTILE_RING[5],
    PROTOTILE_RING[7],
    PROTOTILE_RING[11],
)


def mul(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Compose affines (column-vector convention); v' = A @ B @ v."""
    return np.array(
        [
            A[0] * B[0] + A[1] * B[3],
            A[0] * B[1] + A[1] * B[4],
            A[0] * B[2] + A[1] * B[5] + A[2],
            A[3] * B[0] + A[4] * B[3],
            A[3] * B[1] + A[4] * B[4],
            A[3] * B[2] + A[4] * B[5] + A[5],
        ],
        dtype=np.float64,
    )


def trot(ang: float) -> np.ndarray:
    c, s = float(np.cos(ang)), float(np.sin(ang))
    return np.array([c, -s, 0.0, s, c, 0.0], dtype=np.float64)


def ttrans(tx: float, ty: float) -> np.ndarray:
    return np.array([1.0, 0.0, tx, 0.0, 1.0, ty], dtype=np.float64)


def trans_to(p: np.ndarray, q: np.ndarray) -> np.ndarray:
    return ttrans(float(q[0] - p[0]), float(q[1] - p[1]))


def trans_pt(M: np.ndarray, p: np.ndarray) -> np.ndarray:
    return np.array(
        [M[0] * p[0] + M[1] * p[1] + M[2], M[3] * p[0] + M[4] * p[1] + M[5]],
        dtype=np.float64,
    )


def apply_affine_to_points(M: np.ndarray, xy: np.ndarray) -> np.ndarray:
    x, y = xy[:, 0], xy[:, 1]
    return np.column_stack(
        [M[0] * x + M[1] * y + M[2], M[3] * x + M[4] * y + M[5]]
    ).astype(np.float64, copy=False)


@dataclass(frozen=True, slots=True)
class Tile:
    label: str
    quad: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]


@dataclass(frozen=True, slots=True)
class MetaTile:
    geometries: tuple[tuple[Any, np.ndarray], ...]
    quad: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]


def build_spectre_base() -> dict[str, Any]:
    spectre_base_cluster: dict[str, Any] = {
        label: Tile(label, _DEFAULT_QUAD) for label in TILE_NAMES if label != "Gamma"
    }
    mystic = MetaTile(
        (
            (Tile("Gamma1", _DEFAULT_QUAD), IDENTITY_AFFINE),
            (
                Tile("Gamma2", _DEFAULT_QUAD),
                mul(
                    ttrans(float(PROTOTILE_RING[8, 0]), float(PROTOTILE_RING[8, 1])),
                    trot(np.pi / 6.0),
                ),
            ),
        ),
        _DEFAULT_QUAD,
    )
    spectre_base_cluster["Gamma"] = mystic
    return spectre_base_cluster


def build_supertiles(tile_system: dict[str, Any]) -> dict[str, MetaTile]:
    quad = tile_system["Delta"].quad
    R = np.array([-1.0, 0.0, 0.0, 0.0, 1.0, 0.0], dtype=np.float64)
    transformation_rules = [
        (60, 3, 1),
        (0, 2, 0),
        (60, 3, 1),
        (60, 3, 1),
        (0, 2, 0),
        (60, 3, 1),
        (-120, 3, 3),
    ]
    transformations: list[np.ndarray] = [IDENTITY_AFFINE]
    total_angle = 0.0
    rotation = IDENTITY_AFFINE
    transformed_quad = list(quad)
    for angle, _from, _to in transformation_rules:
        if angle != 0:
            total_angle += angle
            rotation = trot(np.deg2rad(total_angle))
            transformed_quad = [trans_pt(rotation, np.asarray(q, dtype=np.float64)) for q in quad]
        ttt = trans_to(
            transformed_quad[_to],
            trans_pt(transformations[-1], np.asarray(quad[_from], dtype=np.float64)),
        )
        transformations.append(mul(ttt, rotation))
    transformations = [mul(R, t) for t in transformations]
    super_rules = {
        "Gamma": ["Pi", "Delta", None, "Theta", "Sigma", "Xi", "Phi", "Gamma"],
        "Delta": ["Xi", "Delta", "Xi", "Phi", "Sigma", "Pi", "Phi", "Gamma"],
        "Theta": ["Psi", "Delta", "Pi", "Phi", "Sigma", "Pi", "Phi", "Gamma"],
        "Lambda": ["Psi", "Delta", "Xi", "Phi", "Sigma", "Pi", "Phi", "Gamma"],
        "Xi": ["Psi", "Delta", "Pi", "Phi", "Sigma", "Psi", "Phi", "Gamma"],
        "Pi": ["Psi", "Delta", "Xi", "Phi", "Sigma", "Psi", "Phi", "Gamma"],
        "Sigma": ["Xi", "Delta", "Xi", "Phi", "Sigma", "Pi", "Lambda", "Gamma"],
        "Phi": ["Psi", "Delta", "Psi", "Phi", "Sigma", "Pi", "Phi", "Gamma"],
        "Psi": ["Psi", "Delta", "Psi", "Phi", "Sigma", "Psi", "Phi", "Gamma"],
    }
    super_quad = (
        trans_pt(transformations[6], np.asarray(quad[2], dtype=np.float64)),
        trans_pt(transformations[5], np.asarray(quad[1], dtype=np.float64)),
        trans_pt(transformations[3], np.asarray(quad[2], dtype=np.float64)),
        trans_pt(transformations[0], np.asarray(quad[1], dtype=np.float64)),
    )
    out: dict[str, MetaTile] = {}
    for label, substitutions in super_rules.items():
        geoms: list[tuple[Any, np.ndarray]] = []
        for substitution, transformation in zip(substitutions, transformations, strict=True):
            if substitution is None:
                continue
            geoms.append((tile_system[substitution], transformation))
        out[label] = MetaTile(tuple(geoms), super_quad)
    return out


def tile_system_after_iterations(n_supertile_steps: int) -> dict[str, Any]:
    shapes: dict[str, Any] = build_spectre_base()
    for _ in range(n_supertile_steps):
        shapes = build_supertiles(shapes)
    return shapes


def iter_placed_tiles(
    root: Any,
    root_transform: np.ndarray,
    path_prefix: tuple[int, ...],
) -> Iterator[tuple[str, np.ndarray, tuple[int, ...]]]:
    """Depth-first leaf enumeration with child-index path (stable addressing)."""

    def walk(
        node: Any,
        M: np.ndarray,
        prefix: tuple[int, ...],
    ) -> Iterator[tuple[str, np.ndarray, tuple[int, ...]]]:
        if isinstance(node, Tile):
            yield node.label, M, prefix
            return
        if isinstance(node, MetaTile):
            for i, (child, T) in enumerate(node.geometries):
                yield from walk(child, mul(M, T), prefix + (i,))
            return
        raise TypeError(f"Unknown node type {type(node)!r}")

    yield from walk(root, root_transform, path_prefix)


def patch_bbox_iter(
    placed: Iterable[tuple[str, np.ndarray, tuple[int, ...]]],
) -> tuple[float, float, float, float]:
    minx = miny = float("inf")
    maxx = maxy = float("-inf")
    for _label, M, _path in placed:
        ring = apply_affine_to_points(M, PROTOTILE_RING)
        minx = min(minx, float(ring[:, 0].min()))
        maxx = max(maxx, float(ring[:, 0].max()))
        miny = min(miny, float(ring[:, 1].min()))
        maxy = max(maxy, float(ring[:, 1].max()))
    return minx, miny, maxx, maxy


def min_iterations_for_square(half_extent: float, max_iter: int = 32) -> int:
    """Smallest n so bbox of Delta patch covers [-half_extent,half_extent]^2."""
    h = float(half_extent)
    for n in range(0, max_iter + 1):
        sys_n = tile_system_after_iterations(n)
        root = sys_n["Delta"]
        placed = iter_placed_tiles(root, IDENTITY_AFFINE, ())
        minx, miny, maxx, maxy = patch_bbox_iter(placed)
        if minx <= -h and maxx >= h and miny <= -h and maxy >= h:
            return n
    raise ValueError(
        f"Could not cover square half_extent={half_extent} within max_iter={max_iter}"
    )


def count_tiles(root: Any, M: np.ndarray = IDENTITY_AFFINE) -> int:
    return sum(1 for _ in iter_placed_tiles(root, M, ()))


_BBOX_CORNERS = np.array(
    [[0, 0], [1, 0], [1, 1], [0, 1]],
    dtype=np.float64,
)


def transform_bbox_world(M: np.ndarray, bbox: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    """Map an axis-aligned local bbox by affine M and return new axis-aligned bbox."""

    minx, miny, maxx, maxy = bbox
    w = maxx - minx
    h = maxy - miny
    corners = _BBOX_CORNERS * np.array([w, h], dtype=np.float64) + np.array([minx, miny], dtype=np.float64)
    out = apply_affine_to_points(M, corners)
    return float(out[:, 0].min()), float(out[:, 1].min()), float(out[:, 0].max()), float(out[:, 1].max())


def bbox_intersects(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def compute_local_bbox(node: Any, cache: dict[int, tuple[float, float, float, float]]) -> tuple[float, float, float, float]:
    """Recursive local bbox of all leaves under `node` (node placed at IDENTITY).

    Caches by `id(node)` because `build_supertiles` constructs heavily-shared
    substructures, so the cache is small (~9 entries per substitution depth).
    """

    if isinstance(node, Tile):
        return PROTOTILE_LOCAL_BBOX
    key = id(node)
    cached = cache.get(key)
    if cached is not None:
        return cached
    minx = miny = float("inf")
    maxx = maxy = float("-inf")
    for child, T in node.geometries:
        child_bbox = compute_local_bbox(child, cache)
        wb = transform_bbox_world(T, child_bbox)
        if wb[0] < minx:
            minx = wb[0]
        if wb[1] < miny:
            miny = wb[1]
        if wb[2] > maxx:
            maxx = wb[2]
        if wb[3] > maxy:
            maxy = wb[3]
    out = (minx, miny, maxx, maxy)
    cache[key] = out
    return out


def iter_placed_tiles_in_bbox(
    root: Any,
    root_transform: np.ndarray,
    target_bbox: tuple[float, float, float, float],
    bbox_cache: dict[int, tuple[float, float, float, float]] | None = None,
):
    """Yield only leaves whose subtree's world bbox overlaps `target_bbox`.

    Performs early termination on entire branches whose bounding box cannot
    intersect the target — essential for high substitution depths.
    """

    cache = bbox_cache if bbox_cache is not None else {}

    def walk(node, M, path):
        if isinstance(node, Tile):
            ring = apply_affine_to_points(M, PROTOTILE_RING)
            tbbox = (
                float(ring[:, 0].min()),
                float(ring[:, 1].min()),
                float(ring[:, 0].max()),
                float(ring[:, 1].max()),
            )
            if bbox_intersects(tbbox, target_bbox):
                yield node.label, M, path
            return
        # MetaTile: world bbox prune
        local = compute_local_bbox(node, cache)
        wb = transform_bbox_world(M, local)
        if not bbox_intersects(wb, target_bbox):
            return
        for i, (child, T) in enumerate(node.geometries):
            yield from walk(child, mul(M, T), path + (i,))

    yield from walk(root, root_transform, ())
