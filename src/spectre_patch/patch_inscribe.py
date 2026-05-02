"""Find a large axis-aligned square fully inside the substitution patch.

Strategy at low depth (≤ 6): Shapely STRtree against tile polygons (precise).
Strategy at high depth (≥ 7): rasterised coverage on a uniform grid in canonical
space — every tile rasterises a few cells; the inscribed square is then the
largest centered square whose every cell is covered.

The rasterised path scales linearly with the substitution depth's tile count
(thanks to bbox pruning) and uses bounded memory regardless of depth.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from shapely.geometry import Point, Polygon
from shapely.strtree import STRtree

from spectre_patch.core.spectre_t11 import (
    IDENTITY_AFFINE,
    PROTOTILE_RING,
    apply_affine_to_points,
    iter_placed_tiles,
    iter_placed_tiles_in_bbox,
    tile_system_after_iterations,
)


@dataclass(frozen=True, slots=True)
class InscribedSquare:
    center: tuple[float, float]
    half_side: float
    iterations: int
    tile_count_full_patch: int
    method: str


def _tile_polygons_canonical(iterations: int) -> tuple[list[Polygon], np.ndarray]:
    sysn = tile_system_after_iterations(iterations)
    leafs = list(iter_placed_tiles(sysn["Delta"], IDENTITY_AFFINE, ()))
    polygons: list[Polygon] = []
    centroids = np.empty((len(leafs), 2), dtype=np.float64)
    for i, (_label, M, _path) in enumerate(leafs):
        ring = apply_affine_to_points(M, PROTOTILE_RING)
        polygons.append(Polygon(ring))
        centroids[i] = ring.mean(axis=0)
    return polygons, centroids


def _shapely_inscribed(iterations: int, grid_samples: int, safety_shrink: float) -> InscribedSquare:
    polys, centroids = _tile_polygons_canonical(iterations)
    tree = STRtree(polys)
    cx = float(np.median(centroids[:, 0]))
    cy = float(np.median(centroids[:, 1]))
    bbox = np.array([p.bounds for p in polys], dtype=np.float64)
    minx, miny = bbox[:, 0].min(), bbox[:, 1].min()
    maxx, maxy = bbox[:, 2].max(), bbox[:, 3].max()
    h_hi = min(cx - minx, maxx - cx, cy - miny, maxy - cy)
    h_lo = 0.0
    eps = h_hi * 1e-3

    def covered(h: float) -> bool:
        xs = np.linspace(cx - h, cx + h, grid_samples)
        ys = np.linspace(cy - h, cy + h, grid_samples)
        for x in xs:
            for y in ys:
                pt = Point(float(x), float(y))
                idxs = tree.query(pt)
                if len(idxs) == 0:
                    return False
                if not any(polys[int(k)].covers(pt) for k in idxs):
                    return False
        return True

    while (h_hi - h_lo) > eps:
        mid = 0.5 * (h_lo + h_hi)
        if covered(mid):
            h_lo = mid
        else:
            h_hi = mid

    return InscribedSquare(
        center=(cx, cy),
        half_side=h_lo * float(safety_shrink),
        iterations=iterations,
        tile_count_full_patch=len(polys),
        method="shapely_strtree",
    )


def _raster_coverage_full_patch(
    iterations: int, raster_resolution: int
) -> tuple[np.ndarray, tuple[float, float, float, float], int]:
    """Rasterise tile coverage onto a `raster_resolution`-square grid, return (mask, bbox, tile_count).

    `mask[r, c] == True` ⇔ cell (r, c) is overlapped by at least one tile centroid bbox.
    Uses bbox pruning during enumeration so it scales gracefully to high depths.
    """

    sysn = tile_system_after_iterations(iterations)
    root = sysn["Delta"]

    # Pass 1: get the world bbox cheaply via the precomputed metatile bbox.
    from spectre_patch.core.spectre_t11 import compute_local_bbox  # local import avoids cycles

    cache: dict[int, tuple[float, float, float, float]] = {}
    minx, miny, maxx, maxy = compute_local_bbox(root, cache)
    width = maxx - minx
    height = maxy - miny
    span = max(width, height)

    # Pad slightly so tile rings on the boundary fall inside the grid.
    pad = span * 0.005
    minx -= pad
    miny -= pad
    maxx += pad
    maxy += pad
    width = maxx - minx
    height = maxy - miny
    span = max(width, height)

    # Use a uniform grid (square cells) with `raster_resolution` rows in the smaller dim.
    cell_size = span / float(raster_resolution)
    grid_w = int(np.ceil(width / cell_size))
    grid_h = int(np.ceil(height / cell_size))
    coverage = np.zeros((grid_h, grid_w), dtype=bool)

    tile_count = 0
    for _label, M, _path in iter_placed_tiles_in_bbox(
        root, IDENTITY_AFFINE, (minx, miny, maxx, maxy), bbox_cache=cache
    ):
        tile_count += 1
        ring = apply_affine_to_points(M, PROTOTILE_RING)
        rx0 = int(np.floor((ring[:, 0].min() - minx) / cell_size))
        ry0 = int(np.floor((ring[:, 1].min() - miny) / cell_size))
        rx1 = int(np.ceil((ring[:, 0].max() - minx) / cell_size))
        ry1 = int(np.ceil((ring[:, 1].max() - miny) / cell_size))
        rx0 = max(0, rx0)
        ry0 = max(0, ry0)
        rx1 = min(grid_w, rx1)
        ry1 = min(grid_h, ry1)
        coverage[ry0:ry1, rx0:rx1] = True

    return coverage, (minx, miny, maxx, maxy), tile_count


def _raster_inscribed(iterations: int, raster_resolution: int, safety_shrink: float) -> InscribedSquare:
    coverage, bbox, tile_count = _raster_coverage_full_patch(iterations, raster_resolution)
    minx, miny, maxx, maxy = bbox
    grid_h, grid_w = coverage.shape
    cell_size = (maxx - minx) / grid_w

    # Center on the centroid of covered cells (roughly the densest interior).
    ys, xs = np.where(coverage)
    if len(xs) == 0:
        raise RuntimeError("substitution patch produced an empty coverage grid")
    cx_cell = float(xs.mean())
    cy_cell = float(ys.mean())
    cx = minx + (cx_cell + 0.5) * cell_size
    cy = miny + (cy_cell + 0.5) * cell_size

    # Distance-to-uncovered transform via repeated AND of erosions: but cheaper to
    # binary-search the half-side and check rectangular sub-blocks all True.
    h_hi = min(cx - minx, maxx - cx, cy - miny, maxy - cy)
    h_lo = 0.0
    eps = cell_size

    def covered(h: float) -> bool:
        x0 = max(0, int(np.floor((cx - h - minx) / cell_size)))
        x1 = min(grid_w, int(np.ceil((cx + h - minx) / cell_size)))
        y0 = max(0, int(np.floor((cy - h - miny) / cell_size)))
        y1 = min(grid_h, int(np.ceil((cy + h - miny) / cell_size)))
        if x1 <= x0 or y1 <= y0:
            return False
        return bool(coverage[y0:y1, x0:x1].all())

    while (h_hi - h_lo) > eps:
        mid = 0.5 * (h_lo + h_hi)
        if covered(mid):
            h_lo = mid
        else:
            h_hi = mid

    return InscribedSquare(
        center=(cx, cy),
        half_side=h_lo * float(safety_shrink),
        iterations=iterations,
        tile_count_full_patch=tile_count,
        method=f"raster_{raster_resolution}",
    )


def find_inscribed_square(
    iterations: int,
    *,
    grid_samples: int = 33,
    safety_shrink: float = 0.985,
    raster_resolution_override: int | None = None,
) -> InscribedSquare:
    """Pick the strategy automatically: Shapely below depth 7, raster otherwise."""

    if iterations <= 6 and raster_resolution_override is None:
        return _shapely_inscribed(iterations, grid_samples=grid_samples, safety_shrink=safety_shrink)
    res = raster_resolution_override or 1024
    return _raster_inscribed(iterations, raster_resolution=res, safety_shrink=safety_shrink)


def auto_inscribed_square_for_target_units(
    target_full_side: float,
    *,
    safety_shrink: float = 0.985,
    raster_resolution_override: int | None = None,
    iterations_floor: int = 5,
    iterations_ceiling: int = 12,
) -> InscribedSquare:
    """Search for the smallest depth N whose inscribed square covers `target_full_side` canonical units.

    Returns an InscribedSquare describing depth N's actual inscribed square — caller
    can use min(found.half_side, target_full_side / 2) as their effective mask.
    """

    target_half = target_full_side / 2.0
    last: InscribedSquare | None = None
    for n in range(iterations_floor, iterations_ceiling + 1):
        last = find_inscribed_square(
            n,
            safety_shrink=safety_shrink,
            raster_resolution_override=raster_resolution_override,
        )
        if last.half_side >= target_half:
            return last
    if last is None:
        raise RuntimeError("auto_inscribed_square_for_target_units exhausted iteration range")
    return last
