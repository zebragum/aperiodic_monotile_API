"""High-level dispatch that prefers the atlas when a suitable core exists.

The fallback (when no core is large enough or the atlas is empty) is the live
substitution path :func:`spectre_patch.patch_engine.enumerate_emitted`, which
keeps the API contract unchanged on a fresh install with zero atlas files.

A small in-process LRU cache holds recently-used cores so back-to-back requests
hitting the same depth share the same numpy arrays + STRtree.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

import numpy as np
from shapely.affinity import translate as shp_translate

from spectre_patch.atlas.engine import enumerate_emitted_from_core
from spectre_patch.atlas.loader import LoadedCore, load_core
from spectre_patch.atlas.schema import AtlasIndex, AtlasIndexEntry
from spectre_patch.atlas.selector import MaskExtent, select_core
from spectre_patch.config_limits import LimitsSettings
from spectre_patch.geometry_affine import compose_world_affine, decompose_uniform_similarity
from spectre_patch.masking import RetentionMode, mask_polygon
from spectre_patch.patch_engine import EmittedTile, affine6_tuple, enumerate_emitted
from spectre_patch.patch_inscribe import auto_inscribed_square_for_target_units


@dataclass(slots=True)
class AtlasResolution:
    """Diagnostic record explaining how the engine answered a request."""

    used_atlas: bool
    selected_iterations: int | None
    selected_file: str | None
    fallback_reason: str | None
    tile_count_pre_mask: int | None


class _CoreCache:
    """Bounded LRU of (atlas_root, family, iterations) → LoadedCore."""

    def __init__(self, capacity: int = 4) -> None:
        self._cap = int(capacity)
        self._map: OrderedDict[tuple[str, str, int], LoadedCore] = OrderedDict()
        self._lock = Lock()

    def get_or_load(self, entry: AtlasIndexEntry, atlas_root: Path) -> LoadedCore:
        key = (str(atlas_root.resolve()), entry.tile_family, int(entry.iterations))
        with self._lock:
            existing = self._map.get(key)
            if existing is not None:
                self._map.move_to_end(key)
                return existing
            core = load_core(entry, atlas_root)
            self._map[key] = core
            while len(self._map) > self._cap:
                self._map.popitem(last=False)
            return core

    def clear(self) -> None:
        with self._lock:
            self._map.clear()


_default_cache = _CoreCache(capacity=4)


def get_default_core_cache() -> _CoreCache:
    return _default_cache


def _shift_affine6(gen6: np.ndarray, dx: float, dy: float) -> np.ndarray:
    out = gen6.copy()
    out[2] = float(gen6[2] + dx)
    out[5] = float(gen6[5] + dy)
    return out


def _shift_emitted_to_user_frame(
    emitted: list[EmittedTile],
    *,
    shift_dx: float,
    shift_dy: float,
    scale: float,
    rotation_deg: float,
    tx: float,
    ty: float,
) -> list[EmittedTile]:
    if shift_dx == 0.0 and shift_dy == 0.0:
        return emitted

    out: list[EmittedTile] = []
    for tile in emitted:
        gen6_user = _shift_affine6(np.asarray(tile.affine_canonical_gen6, dtype=np.float64), -shift_dx, -shift_dy)
        W = compose_world_affine(
            canonical_gen6=gen6_user,
            scale=scale,
            rotation_deg=rotation_deg,
            tx=tx,
            ty=ty,
        )
        mtx, mty, th, sc = decompose_uniform_similarity(W)
        clip_geom = (
            shp_translate(tile.clip_geom, xoff=-shift_dx, yoff=-shift_dy)
            if tile.clip_geom is not None
            else None
        )
        out.append(
            EmittedTile(
                tile_id=tile.tile_id,
                tile_label=tile.tile_label,
                dfs_path_indices=tile.dfs_path_indices,
                centroid_canonical_xy=(
                    float(tile.centroid_canonical_xy[0]) - shift_dx,
                    float(tile.centroid_canonical_xy[1]) - shift_dy,
                ),
                affine_canonical_gen6=affine6_tuple(gen6_user),
                tx=float(mtx),
                ty=float(mty),
                rotation_deg=float(np.rad2deg(th)),
                scale_world=float(sc),
                clip_geom=clip_geom,
            )
        )
    return out


def _enumerate_substitution_aligned(
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
) -> tuple[list[EmittedTile], int | None]:
    """Fallback crop from the dense inscribed square, mirroring atlas alignment."""

    mp = mask_polygon(mask)
    extent = MaskExtent.from_bbox(mp.bounds)
    selected_iterations = substitution_iterations
    shift_dx = 0.0
    shift_dy = 0.0
    crop_mask = mask

    if substitution_iterations is None:
        inscribed = auto_inscribed_square_for_target_units(
            extent.half_side * 2.0,
            iterations_ceiling=limits.max_supertile_iterations,
        )
        selected_iterations = inscribed.iterations
        shift_dx = float(inscribed.center[0] - extent.center[0])
        shift_dy = float(inscribed.center[1] - extent.center[1])
        crop_mask = shp_translate(mp, xoff=shift_dx, yoff=shift_dy)
        half_extent_cover = max(float(half_extent_cover), float(inscribed.half_side))

    emitted = enumerate_emitted(
        tile_family=tile_family,
        patch_version=patch_version,
        seed=seed,
        half_extent_cover=half_extent_cover,
        scale=scale,
        tx=tx,
        ty=ty,
        rotation_deg=rotation_deg,
        mask=crop_mask,
        retention=retention,
        limits=limits,
        substitution_iterations=selected_iterations,
    )
    return (
        _shift_emitted_to_user_frame(
            emitted,
            shift_dx=shift_dx,
            shift_dy=shift_dy,
            scale=scale,
            rotation_deg=rotation_deg,
            tx=tx,
            ty=ty,
        ),
        selected_iterations,
    )


def enumerate_emitted_or_atlas(
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
    atlas_index: AtlasIndex | None = None,
    cache: _CoreCache | None = None,
    force_substitution: bool = False,
    require_atlas: bool = False,
) -> tuple[list[EmittedTile], AtlasResolution]:
    """Dispatch: prefer atlas; fall back to substitution unless ``require_atlas``.

    Returns the emitted tile list and an :class:`AtlasResolution` for telemetry
    so the API can log "served from core_n5 (34k tiles)" vs. "live substitution
    at depth=7".
    """

    if require_atlas and force_substitution:
        raise ValueError("force_substitution is disabled when atlas-only mode is required")

    if force_substitution or atlas_index is None or not atlas_index.entries:
        if require_atlas:
            if atlas_index is None or not atlas_index.entries:
                raise LookupError(
                    "atlas required but no cores are loaded; rebuild or bootstrap atlas assets"
                )
            raise ValueError("live substitution is disabled in atlas-only mode")
        emitted, selected_iterations = _enumerate_substitution_aligned(
            tile_family=tile_family,
            patch_version=patch_version,
            seed=seed,
            half_extent_cover=half_extent_cover,
            scale=scale,
            tx=tx,
            ty=ty,
            rotation_deg=rotation_deg,
            mask=mask,
            retention=retention,
            limits=limits,
            substitution_iterations=substitution_iterations,
        )
        return emitted, AtlasResolution(
            used_atlas=False,
            selected_iterations=selected_iterations,
            selected_file=None,
            fallback_reason=(
                "force_substitution_aligned_to_inscribed_core" if force_substitution else "atlas_empty_aligned_to_inscribed_core"
            ),
            tile_count_pre_mask=None,
        )

    mp = mask_polygon(mask)
    extent = MaskExtent.from_bbox(mp.bounds)

    try:
        entry = select_core(atlas_index, tile_family=tile_family, extent=extent)
    except LookupError as e:
        if require_atlas:
            raise LookupError(
                f"mask exceeds largest pre-built atlas core; shrink the mask or upgrade to Pro. {e}"
            ) from e
        emitted, selected_iterations = _enumerate_substitution_aligned(
            tile_family=tile_family,
            patch_version=patch_version,
            seed=seed,
            half_extent_cover=half_extent_cover,
            scale=scale,
            tx=tx,
            ty=ty,
            rotation_deg=rotation_deg,
            mask=mask,
            retention=retention,
            limits=limits,
            substitution_iterations=substitution_iterations,
        )
        return emitted, AtlasResolution(
            used_atlas=False,
            selected_iterations=selected_iterations,
            selected_file=None,
            fallback_reason=f"no_atlas_core_large_enough_aligned_to_inscribed_core: {e}",
            tile_count_pre_mask=None,
        )

    core = (cache or _default_cache).get_or_load(entry, atlas_index.root)
    emitted = enumerate_emitted_from_core(
        core,
        tile_family=tile_family,
        patch_version=patch_version,
        seed=seed,
        scale=scale,
        tx=tx,
        ty=ty,
        rotation_deg=rotation_deg,
        mask=mask,
        retention=retention,
    )
    return emitted, AtlasResolution(
        used_atlas=True,
        selected_iterations=int(entry.iterations),
        selected_file=str(entry.file),
        fallback_reason=None,
        tile_count_pre_mask=int(entry.tile_count),
    )
