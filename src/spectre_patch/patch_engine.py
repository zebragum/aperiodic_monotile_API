"""High-level deterministic patch enumeration + masking + export prep."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator

import numpy as np
from shapely.geometry import Polygon
from shapely.validation import make_valid

from spectre_patch.config_limits import LimitsSettings
from spectre_patch.geometry_affine import compose_world_affine, decompose_uniform_similarity
from spectre_patch.ids import stable_tile_id
from spectre_patch.masking import RetentionMode, mask_polygon, retains_tile_result
from spectre_patch.core.spectre_t11 import (
    IDENTITY_AFFINE,
    PROTOTILE_CENTROID,
    PROTOTILE_RING,
    apply_affine_to_points,
    iter_placed_tiles,
    iter_placed_tiles_in_bbox,
    min_iterations_for_square,
    patch_bbox_iter,
    tile_system_after_iterations,
)


@dataclass(frozen=True, slots=True)
class EmittedTile:
    tile_id: str
    tile_label: str
    dfs_path_indices: tuple[int, ...]

    centroid_canonical_xy: tuple[float, float]

    affine_canonical_gen6: tuple[float, float, float, float, float, float]

    tx: float
    ty: float
    rotation_deg: float
    scale_world: float

    clip_geom: Polygon | None  # canonical intersection geometry if clipped


def affine6_tuple(M: np.ndarray) -> tuple[float, float, float, float, float, float]:
    return (float(M[0]), float(M[1]), float(M[2]), float(M[3]), float(M[4]), float(M[5]))


def _tile_polygon_canonical(gen6: np.ndarray) -> Polygon:
    xy = apply_affine_to_points(gen6, PROTOTILE_RING)
    poly = Polygon(xy)
    if not poly.is_valid:
        poly = make_valid(poly)  # type: ignore [assignment]
    if not isinstance(poly, Polygon):
        # MultiPolygon degeneracy — approximate via convex hull
        poly = poly.convex_hull if hasattr(poly, "convex_hull") else Polygon(xy)
    return poly  # noqa: TRY300


def canonical_placed_leaf_stream(
    *,
    half_extent_cover: float,
    limits: LimitsSettings,
    force_iterations: int | None = None,
    target_bbox: tuple[float, float, float, float] | None = None,
) -> Iterator[tuple[str, np.ndarray, tuple[int, ...]]]:
    """Stream leaf tiles for the canonical patch.

    If `target_bbox` is given, the substitution walk prunes subtrees that can't
    overlap that world-space bbox — essential for high iteration depths.
    """

    h = float(half_extent_cover)
    if h <= 0:
        raise ValueError("half_extent_cover must be positive")

    if force_iterations is not None:
        n = int(force_iterations)
        if n < 0 or n > limits.max_supertile_iterations:
            raise ValueError(f"substitution_iterations must be within [0,{limits.max_supertile_iterations}]")
        sys_n = tile_system_after_iterations(n)
    else:
        n = min_iterations_for_square(h, max_iter=limits.max_supertile_iterations)
        sys_n = tile_system_after_iterations(n)

    root = sys_n["Delta"]
    if target_bbox is None:
        yield from iter_placed_tiles(root, IDENTITY_AFFINE, ())
    else:
        yield from iter_placed_tiles_in_bbox(root, IDENTITY_AFFINE, target_bbox)


def square_coverage_no_voids_inside_bbox(
    half_extent_cover: float, limits: LimitsSettings
) -> None:
    """Property helper: tiled union bbox covers target square."""

    leafs = list(canonical_placed_leaf_stream(half_extent_cover=half_extent_cover, limits=limits))
    minx, miny, maxx, maxy = patch_bbox_iter(leafs)
    h = float(half_extent_cover)
    assert minx <= -h and maxx >= h and miny <= -h and maxy >= h


def enumerate_emitted(
    *,
    tile_family: str,
    patch_version: str,
    seed: str | None,
    half_extent_cover: float,
    scale: float,
    tx: float,
    ty: float,
    rotation_deg: float,
    mask: Any,
    retention: RetentionMode,
    limits: LimitsSettings,
    substitution_iterations: int | None,
    canonical_prune_bbox: tuple[float, float, float, float] | None = None,
) -> list[EmittedTile]:
    mp = mask_polygon(mask)
    out: list[EmittedTile] = []
    if canonical_prune_bbox is None:
        canonical_prune_bbox = mp.bounds
    leafs = list(
        canonical_placed_leaf_stream(
            half_extent_cover=half_extent_cover,
            limits=limits,
            force_iterations=substitution_iterations,
            target_bbox=canonical_prune_bbox,
        )
    )
    ids_seen: set[str] = set()
    for lbl, gen6, path in leafs:
        cen_c = np.asarray(
            [
                gen6[0] * PROTOTILE_CENTROID[0]
                + gen6[1] * PROTOTILE_CENTROID[1]
                + gen6[2],
                gen6[3] * PROTOTILE_CENTROID[0]
                + gen6[4] * PROTOTILE_CENTROID[1]
                + gen6[5],
            ],
            dtype=np.float64,
        )

        tpoly = _tile_polygon_canonical(gen6)
        keep, clipped_geom = retains_tile_result(retention, tpoly, mp, cen_c)
        clip_polygon: Polygon | None = None
        if retention == RetentionMode.clip and keep and clipped_geom is not None:
            if clipped_geom.geom_type != "Polygon":
                continue
            clip_polygon = clipped_geom

        if not keep:
            continue

        tid = stable_tile_id(
            tile_family=tile_family,
            patch_version=patch_version,
            seed=seed,
            path_suffix=path,
        )
        if tid in ids_seen:
            raise AssertionError("stable id collision — investigate hash settings")
        ids_seen.add(tid)

        W = compose_world_affine(
            canonical_gen6=gen6,
            scale=scale,
            rotation_deg=rotation_deg,
            tx=tx,
            ty=ty,
        )
        mtx, mty, th, sc = decompose_uniform_similarity(W)

        out.append(
            EmittedTile(
                tile_id=tid,
                tile_label=lbl,
                dfs_path_indices=path,
                centroid_canonical_xy=(float(cen_c[0]), float(cen_c[1])),
                affine_canonical_gen6=affine6_tuple(gen6),
                tx=float(mtx),
                ty=float(mty),
                rotation_deg=float(np.rad2deg(th)),
                scale_world=float(sc),
                clip_geom=clip_polygon if retention == RetentionMode.clip else None,
            )
        )
    return out
