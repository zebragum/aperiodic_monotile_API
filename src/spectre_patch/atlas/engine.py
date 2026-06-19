"""Bridge between an in-memory atlas core and the existing emit/export pipeline.

This module replaces the inner loop of :func:`spectre_patch.patch_engine.enumerate_emitted`
with an array-based variant that reads from a pre-built core instead of doing
substitution recursion. The output (``list[EmittedTile]``) is identical so the
SVG / STL / GLB / sidecar exporters Just Work.

Coordinate alignment
--------------------
The atlas core has its dense interior (largest fully-tiled square) centered at
``core.inscribed_center``, which moves between depths. The request's mask is
authored in the *user's* canonical frame, where (0, 0) is wherever the user
chose. We bridge the two frames with a single 2D translation::

    shift = core.inscribed_center - mask_center

We translate the user's mask polygon by ``+shift`` to crop the core, run
retention in core-space, and undo the shift on each emitted tile's affine and
centroid so the user observes their mask centered at *their* origin. The
client-side similarity (``scale``, ``rotation_deg``, ``tx``, ``ty``) is
applied last, exactly as in the substitution path.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from shapely.affinity import translate as shp_translate
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

from spectre_patch.atlas.loader import LoadedCore
from spectre_patch.atlas.selector import MaskExtent
from spectre_patch.core.spectre_t11 import PROTOTILE_RING, apply_affine_to_points
from spectre_patch.geometry_affine import compose_world_affine, decompose_uniform_similarity
from spectre_patch.ids import stable_tile_id
from spectre_patch.masking import RetentionMode, mask_polygon, retains_tile_result


def _resolve_mystic_label(label: str, path: tuple[int, ...]) -> str:
    """Split the collapsed atlas "Gamma" back into its Mystic leaves.

    The atlas stores only the 9 canonical label indices, so both halves of the
    Mystic metatile share the index for "Gamma". Their immediate parent is the
    Mystic, so the final DFS child index distinguishes them: 0 -> Gamma1,
    1 -> Gamma2 (matching the live substitution engine, which emits them directly).
    """

    if label == "Gamma" and path:
        return "Gamma1" if int(path[-1]) == 0 else "Gamma2"
    return label
from spectre_patch.patch_engine import EmittedTile, affine6_tuple


def _tile_polygon_canonical(gen6: np.ndarray) -> Polygon:
    xy = apply_affine_to_points(gen6, PROTOTILE_RING)
    poly = Polygon(xy)
    if not poly.is_valid:
        poly = make_valid(poly)  # type: ignore[assignment]
    if not isinstance(poly, Polygon):
        poly = poly.convex_hull if hasattr(poly, "convex_hull") else Polygon(xy)
    return poly  # noqa: TRY300


def _shift_affine6(gen6: np.ndarray, dx: float, dy: float) -> np.ndarray:
    """Return ``T(dx, dy) ⊗ M`` for an affine in 6-element (a, b, tx, c, d, ty) form."""

    out = gen6.copy()
    out[2] = float(gen6[2] + dx)
    out[5] = float(gen6[5] + dy)
    return out


def enumerate_emitted_from_core(
    core: LoadedCore,
    *,
    tile_family: str,
    patch_version: str,
    seed: str | None,
    scale: float,
    tx: float,
    ty: float,
    rotation_deg: float,
    mask: Any,
    retention: RetentionMode,
    align_mask_to_inscribed_center: bool = True,
) -> list[EmittedTile]:
    """Crop ``core`` to ``mask`` + apply retention; return list of :class:`EmittedTile`.

    By default the engine translates the user's mask onto the core's inscribed
    center, runs the crop in core-space, then shifts emitted tiles back into the
    user's frame. Set ``align_mask_to_inscribed_center=False`` to crop with the
    mask used verbatim in the core's coordinate system (useful for tests that
    deliberately probe a known position).
    """

    mp = mask_polygon(mask)
    extent = MaskExtent.from_bbox(mp.bounds)

    if align_mask_to_inscribed_center:
        shift_dx = float(core.inscribed_center[0] - extent.center[0])
        shift_dy = float(core.inscribed_center[1] - extent.center[1])
    else:
        shift_dx = 0.0
        shift_dy = 0.0

    mp_core = mp if (shift_dx == 0.0 and shift_dy == 0.0) else shp_translate(mp, xoff=shift_dx, yoff=shift_dy)
    indices = core.crop(mp_core.bounds)

    out: list[EmittedTile] = []
    if indices.size == 0:
        return out

    affine6 = core.affine6
    centroids = core.centroid

    ids_seen: set[str] = set()
    for ridx in indices:
        ridx_int = int(ridx)
        gen6_core = affine6[ridx_int]
        cen_core = centroids[ridx_int]

        tpoly_core = _tile_polygon_canonical(gen6_core)
        cen_pt_core = np.array([float(cen_core[0]), float(cen_core[1])], dtype=np.float64)
        keep, clipped_geom = retains_tile_result(retention, tpoly_core, mp_core, cen_pt_core)
        clip_polygon_user: BaseGeometry | None = None
        if retention == RetentionMode.clip and keep and clipped_geom is not None:
            clip_polygon_user = (
                clipped_geom
                if (shift_dx == 0.0 and shift_dy == 0.0)
                else shp_translate(clipped_geom, xoff=-shift_dx, yoff=-shift_dy)
            )

        if not keep:
            continue

        # Undo the alignment shift so the user observes tiles in their own frame.
        gen6_user = _shift_affine6(gen6_core, -shift_dx, -shift_dy) if (shift_dx or shift_dy) else gen6_core
        cen_user = (float(cen_core[0]) - shift_dx, float(cen_core[1]) - shift_dy)

        path = core.dfs_path_for(ridx_int)
        tid = stable_tile_id(
            tile_family=tile_family,
            patch_version=patch_version,
            seed=seed,
            path_suffix=path,
        )
        if tid in ids_seen:
            raise AssertionError("stable id collision (atlas crop) — investigate hash settings")
        ids_seen.add(tid)

        W = compose_world_affine(
            canonical_gen6=gen6_user,
            scale=scale,
            rotation_deg=rotation_deg,
            tx=tx,
            ty=ty,
        )
        mtx, mty, th, sc = decompose_uniform_similarity(W)

        out.append(
            EmittedTile(
                tile_id=tid,
                tile_label=_resolve_mystic_label(core.label_for(ridx_int), path),
                dfs_path_indices=path,
                centroid_canonical_xy=cen_user,
                affine_canonical_gen6=affine6_tuple(gen6_user),
                tx=float(mtx),
                ty=float(mty),
                rotation_deg=float(np.rad2deg(th)),
                scale_world=float(sc),
                clip_geom=clip_polygon_user if retention == RetentionMode.clip else None,
            )
        )

    return out
