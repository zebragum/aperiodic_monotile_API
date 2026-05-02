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

from spectre_patch.atlas.engine import enumerate_emitted_from_core
from spectre_patch.atlas.loader import LoadedCore, load_core
from spectre_patch.atlas.schema import AtlasIndex, AtlasIndexEntry
from spectre_patch.atlas.selector import MaskExtent, select_core
from spectre_patch.config_limits import LimitsSettings
from spectre_patch.masking import RetentionMode, mask_polygon
from spectre_patch.patch_engine import EmittedTile, enumerate_emitted


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
) -> tuple[list[EmittedTile], AtlasResolution]:
    """Dispatch: prefer atlas; fall back to substitution.

    Returns the emitted tile list and an :class:`AtlasResolution` for telemetry
    so the API can log "served from core_n5 (34k tiles)" vs. "live substitution
    at depth=7".
    """

    if force_substitution or atlas_index is None or not atlas_index.entries:
        emitted = enumerate_emitted(
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
            selected_iterations=None,
            selected_file=None,
            fallback_reason=(
                "force_substitution" if force_substitution else "atlas_empty"
            ),
            tile_count_pre_mask=None,
        )

    mp = mask_polygon(mask)
    extent = MaskExtent.from_bbox(mp.bounds)

    try:
        entry = select_core(atlas_index, tile_family=tile_family, extent=extent)
    except LookupError as e:
        emitted = enumerate_emitted(
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
            selected_iterations=None,
            selected_file=None,
            fallback_reason=f"no_atlas_core_large_enough: {e}",
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
