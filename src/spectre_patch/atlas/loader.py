"""Lazy mmap-friendly atlas loader + cropping.

Most API requests crop a tiny region; we want loading a depth-N core to be
constant-time (memory-mapped npz) and cropping to be O(tiles_in_mask) with a
spatial index built on first crop.

Crop semantics:

- Build a per-tile axis-aligned bbox from each affine (4 corners of the
  prototile's local AABB transformed; this is a tight upper bound for
  rotational placements and we rotate-only inside the substitution).
- Compute which tiles' bbox overlaps the user's mask bbox via STRtree.
- The caller iterates the surviving tile indices, materialises the affine,
  reconstructs the DFS path, and applies retention rules.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from shapely.geometry import box as shp_box
from shapely.strtree import STRtree

from spectre_patch.atlas.schema import AtlasIndexEntry, unpack_dfs_path
from spectre_patch.core.spectre_t11 import PROTOTILE_LOCAL_BBOX, TILE_NAMES


_BBOX_LOCAL_CORNERS = np.array(
    [
        [PROTOTILE_LOCAL_BBOX[0], PROTOTILE_LOCAL_BBOX[1]],
        [PROTOTILE_LOCAL_BBOX[2], PROTOTILE_LOCAL_BBOX[1]],
        [PROTOTILE_LOCAL_BBOX[2], PROTOTILE_LOCAL_BBOX[3]],
        [PROTOTILE_LOCAL_BBOX[0], PROTOTILE_LOCAL_BBOX[3]],
    ],
    dtype=np.float64,
)


def _per_tile_bboxes(affine6: np.ndarray) -> np.ndarray:
    """Vectorised per-tile world bbox from canonical affine.

    Returns a (T, 4) array: ``[minx, miny, maxx, maxy]`` for each tile.
    """

    a = affine6[:, 0]
    b = affine6[:, 1]
    c = affine6[:, 2]
    d = affine6[:, 3]
    e = affine6[:, 4]
    f = affine6[:, 5]

    cx = _BBOX_LOCAL_CORNERS[:, 0]
    cy = _BBOX_LOCAL_CORNERS[:, 1]

    # corners_x[i, k] = a[i]*cx[k] + b[i]*cy[k] + c[i]
    corners_x = np.outer(a, cx) + np.outer(b, cy) + c[:, None]
    corners_y = np.outer(d, cx) + np.outer(e, cy) + f[:, None]

    out = np.empty((affine6.shape[0], 4), dtype=np.float64)
    out[:, 0] = corners_x.min(axis=1)
    out[:, 1] = corners_y.min(axis=1)
    out[:, 2] = corners_x.max(axis=1)
    out[:, 3] = corners_y.max(axis=1)
    return out


@dataclass(slots=True)
class LoadedCore:
    """In-memory view of an atlas core file.

    Arrays are lazily-loaded numpy archives; the spatial index is built once
    on first :meth:`crop` and reused thereafter (per-process).
    """

    entry: AtlasIndexEntry
    path: Path
    affine6: np.ndarray
    centroid: np.ndarray
    label_idx: np.ndarray
    path_packed: np.ndarray
    path_depth: np.ndarray
    bbox: tuple[float, float, float, float]
    inscribed_center: tuple[float, float]
    inscribed_half_side: float
    _tile_bboxes: np.ndarray | None = field(default=None, repr=False)
    _strtree: STRtree | None = field(default=None, repr=False)
    _index_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def tile_count(self) -> int:
        return int(self.affine6.shape[0])

    @property
    def tile_family(self) -> str:
        return self.entry.tile_family

    @property
    def iterations(self) -> int:
        return int(self.entry.iterations)

    @property
    def patch_version(self) -> str:
        return self.entry.patch_version

    def label_for(self, idx: int) -> str:
        return TILE_NAMES[int(self.label_idx[idx])]

    def dfs_path_for(self, idx: int) -> tuple[int, ...]:
        return unpack_dfs_path(int(self.path_packed[idx]), int(self.path_depth[idx]))

    def affine6_for(self, idx: int) -> tuple[float, float, float, float, float, float]:
        row = self.affine6[idx]
        return (
            float(row[0]),
            float(row[1]),
            float(row[2]),
            float(row[3]),
            float(row[4]),
            float(row[5]),
        )

    def _ensure_index(self) -> None:
        if self._strtree is not None:
            return
        with self._index_lock:
            if self._strtree is not None:
                return
            bboxes = _per_tile_bboxes(self.affine6)
            polys = [shp_box(*bb) for bb in bboxes]
            self._tile_bboxes = bboxes
            self._strtree = STRtree(polys)

    def crop(
        self,
        target_bbox: tuple[float, float, float, float],
    ) -> np.ndarray:
        """Return indices of tiles whose bbox overlaps ``target_bbox``.

        ``target_bbox`` is in canonical coordinates (no client-side similarity yet).
        The result is a uint32 numpy array of row indices into this core's arrays.
        """

        if self.tile_count == 0:
            return np.empty((0,), dtype=np.uint32)

        # Fast path: if the mask bbox covers the whole patch, return everything.
        minx, miny, maxx, maxy = target_bbox
        if (
            minx <= self.bbox[0]
            and miny <= self.bbox[1]
            and maxx >= self.bbox[2]
            and maxy >= self.bbox[3]
        ):
            return np.arange(self.tile_count, dtype=np.uint32)

        self._ensure_index()
        assert self._strtree is not None
        assert self._tile_bboxes is not None

        query_geom = shp_box(minx, miny, maxx, maxy)
        idxs = self._strtree.query(query_geom)
        if not isinstance(idxs, np.ndarray):
            idxs = np.asarray(list(idxs), dtype=np.int64)
        return idxs.astype(np.uint32, copy=False)

    def crop_inside(
        self,
        target_bbox: tuple[float, float, float, float],
    ) -> np.ndarray:
        """Variant of :meth:`crop` that requires tiles to be fully inside ``target_bbox``."""

        if self.tile_count == 0:
            return np.empty((0,), dtype=np.uint32)
        self._ensure_index()
        assert self._tile_bboxes is not None
        bboxes = self._tile_bboxes
        minx, miny, maxx, maxy = target_bbox
        mask = (
            (bboxes[:, 0] >= minx)
            & (bboxes[:, 1] >= miny)
            & (bboxes[:, 2] <= maxx)
            & (bboxes[:, 3] <= maxy)
        )
        return np.flatnonzero(mask).astype(np.uint32, copy=False)


def load_core(entry: AtlasIndexEntry, atlas_root: Path | str) -> LoadedCore:
    """Load (mmap) a core file referenced by an :class:`AtlasIndexEntry`."""

    root = Path(atlas_root)
    path = root / entry.file
    if not path.exists():
        raise FileNotFoundError(f"atlas core file missing: {path}")

    with np.load(path, allow_pickle=True, mmap_mode="r") as npz:
        affine6 = np.asarray(npz["affine6"], dtype=np.float64)
        centroid = np.asarray(npz["centroid"], dtype=np.float64)
        label_idx = np.asarray(npz["label_idx"], dtype=np.uint8)
        path_packed = np.asarray(npz["path_packed"], dtype=np.uint64)
        path_depth = np.asarray(npz["path_depth"], dtype=np.uint8)
        bbox = tuple(float(v) for v in np.asarray(npz["bbox"], dtype=np.float64).tolist())
        insc_center = tuple(
            float(v) for v in np.asarray(npz["inscribed_center"], dtype=np.float64).tolist()
        )
        insc_hs = float(np.asarray(npz["inscribed_half_side"], dtype=np.float64).item())

    return LoadedCore(
        entry=entry,
        path=path,
        affine6=affine6,
        centroid=centroid,
        label_idx=label_idx,
        path_packed=path_packed,
        path_depth=path_depth,
        bbox=bbox,  # type: ignore[arg-type]
        inscribed_center=insc_center,  # type: ignore[arg-type]
        inscribed_half_side=insc_hs,
    )
