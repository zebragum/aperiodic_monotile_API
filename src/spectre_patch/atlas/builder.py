"""Build a canonical core atlas file for a given substitution depth.

This module is the offline / Colab-side path. It enumerates every leaf of
``Delta`` at depth N, computes per-tile centroids, packs DFS paths, and writes
the npz + updates ``index.json``. It is deliberately decoupled from the API so
heavy builds (n>=8) can run on a beefy box once and the artifacts copied to
the API server's atlas root.

Performance notes:

- Depth 6: ~273k tiles, builds in seconds, ~26 MB on disk.
- Depth 7: ~2.1M tiles, ~30-60s on a laptop, ~200 MB on disk.
- Depth 8: ~17M tiles, several minutes + ~1.6 GB; do not build inline in API.
- Depth 9: ~140M tiles, run on Colab/A100; 13 GB on disk.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from spectre_patch.atlas.schema import (
    ATLAS_FORMAT_VERSION,
    AtlasIndex,
    AtlasIndexEntry,
    core_filename,
    pack_dfs_path,
)
from spectre_patch.core.spectre_t11 import (
    IDENTITY_AFFINE,
    PROTOTILE_CENTROID,
    PROTOTILE_RING,
    TILE_NAMES,
    apply_affine_to_points,
    iter_placed_tiles,
    tile_system_after_iterations,
)
from spectre_patch.patch_inscribe import find_inscribed_square


_LABEL_TO_IDX = {n: i for i, n in enumerate(TILE_NAMES)}
# Allow Mystic-Gamma sub-leaves "Gamma1" / "Gamma2" without expanding the table.
_LABEL_TO_IDX["Gamma1"] = _LABEL_TO_IDX["Gamma"]
_LABEL_TO_IDX["Gamma2"] = _LABEL_TO_IDX["Gamma"]


@dataclass(frozen=True, slots=True)
class BuildResult:
    """Summary returned by :func:`build_core` for logging / tests."""

    file: Path
    tile_count: int
    bbox: tuple[float, float, float, float]
    inscribed_center: tuple[float, float]
    inscribed_half_side: float
    inscribed_method: str
    builder_seconds: float
    file_bytes: int


@dataclass(slots=True)
class _BboxAccumulator:
    minx: float = float("inf")
    miny: float = float("inf")
    maxx: float = float("-inf")
    maxy: float = float("-inf")

    def update(self, ring_xy: np.ndarray) -> None:
        self.minx = min(self.minx, float(ring_xy[:, 0].min()))
        self.miny = min(self.miny, float(ring_xy[:, 1].min()))
        self.maxx = max(self.maxx, float(ring_xy[:, 0].max()))
        self.maxy = max(self.maxy, float(ring_xy[:, 1].max()))


def _enumerate_arrays(
    iterations: int,
) -> tuple[
    np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, tuple[float, float, float, float]
]:
    """Enumerate every leaf of Delta at depth N into dense arrays.

    Returns
    -------
    affine6 : (T, 6) float64
    centroid : (T, 2) float64
    label_idx : (T,) uint8
    path_packed : (T,) uint64
    path_depth : (T,) uint8
    bbox : (minx, miny, maxx, maxy) of the union of leaves' rings
    """

    sys_n = tile_system_after_iterations(iterations)
    root = sys_n["Delta"]

    affines: list[tuple[float, float, float, float, float, float]] = []
    centroids_x: list[float] = []
    centroids_y: list[float] = []
    label_idx: list[int] = []
    path_packed: list[int] = []
    path_depth: list[int] = []

    cx0, cy0 = float(PROTOTILE_CENTROID[0]), float(PROTOTILE_CENTROID[1])
    bbox_acc = _BboxAccumulator()

    for label, M, path in iter_placed_tiles(root, IDENTITY_AFFINE, ()):
        a, b, c, d, e, f = (
            float(M[0]),
            float(M[1]),
            float(M[2]),
            float(M[3]),
            float(M[4]),
            float(M[5]),
        )
        affines.append((a, b, c, d, e, f))
        centroids_x.append(a * cx0 + b * cy0 + c)
        centroids_y.append(d * cx0 + e * cy0 + f)
        label_idx.append(_LABEL_TO_IDX[label])
        packed, depth = pack_dfs_path(path)
        path_packed.append(packed)
        path_depth.append(depth)
        ring = apply_affine_to_points(M, PROTOTILE_RING)
        bbox_acc.update(ring)

    if not affines:
        raise RuntimeError(f"build_core: no leaves enumerated at depth {iterations}")

    aff_arr = np.asarray(affines, dtype=np.float64)
    cen_arr = np.column_stack(
        [np.asarray(centroids_x, dtype=np.float64), np.asarray(centroids_y, dtype=np.float64)]
    )
    lbl_arr = np.asarray(label_idx, dtype=np.uint8)
    pack_arr = np.asarray(path_packed, dtype=np.uint64)
    depth_arr = np.asarray(path_depth, dtype=np.uint8)
    bbox = (bbox_acc.minx, bbox_acc.miny, bbox_acc.maxx, bbox_acc.maxy)

    return aff_arr, cen_arr, lbl_arr, pack_arr, depth_arr, bbox


def build_core(
    *,
    iterations: int,
    out_dir: Path | str,
    tile_family: str = "spectre_tile_1_1",
    patch_version: str = "0.1.0",
    overwrite: bool = False,
    raster_resolution_override: int | None = None,
) -> BuildResult:
    """Build core_<family>_n<N>.npz and update index.json.

    Parameters
    ----------
    iterations : substitution depth N. Tile counts grow ~7.5x per increment.
    out_dir : directory containing ``index.json`` and ``core_*.npz`` files.
    tile_family : currently only ``"spectre_tile_1_1"`` is supported.
    patch_version : recorded in the index for cache busting / id stability.
    overwrite : if True, regenerate even when the target npz exists.
    raster_resolution_override : forwarded to :func:`find_inscribed_square`.
    """

    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    fname = core_filename(tile_family, iterations)
    fpath = out_root / fname

    if fpath.exists() and not overwrite:
        raise FileExistsError(f"{fpath} already exists; pass overwrite=True to rebuild")

    t0 = time.perf_counter()
    affine6, centroid, label_idx, path_packed, path_depth, bbox = _enumerate_arrays(iterations)
    minx, miny, maxx, maxy = bbox
    enum_secs = time.perf_counter() - t0

    insc = find_inscribed_square(
        iterations,
        raster_resolution_override=raster_resolution_override,
    )

    np.savez_compressed(
        fpath,
        affine6=affine6,
        centroid=centroid,
        label_idx=label_idx,
        path_packed=path_packed,
        path_depth=path_depth,
        schema_version=np.int32(ATLAS_FORMAT_VERSION),
        iterations=np.int32(iterations),
        tile_family=np.array(tile_family, dtype=object),
        patch_version=np.array(patch_version, dtype=object),
        bbox=np.array([minx, miny, maxx, maxy], dtype=np.float64),
        inscribed_center=np.array(insc.center, dtype=np.float64),
        inscribed_half_side=np.float64(insc.half_side),
        inscribed_method=np.array(insc.method, dtype=object),
    )
    file_bytes = int(fpath.stat().st_size)
    elapsed = time.perf_counter() - t0

    entry = AtlasIndexEntry(
        tile_family=tile_family,
        iterations=int(iterations),
        patch_version=patch_version,
        file=fname,
        tile_count=int(affine6.shape[0]),
        bbox=(float(minx), float(miny), float(maxx), float(maxy)),
        inscribed_center=(float(insc.center[0]), float(insc.center[1])),
        inscribed_half_side=float(insc.half_side),
        inscribed_method=insc.method,
        file_bytes=file_bytes,
    )

    idx = AtlasIndex.load(out_root).with_entry(entry)
    idx.write()

    _ = enum_secs  # silence linters; surfaced via the index manifest only

    return BuildResult(
        file=fpath,
        tile_count=int(affine6.shape[0]),
        bbox=(float(minx), float(miny), float(maxx), float(maxy)),
        inscribed_center=(float(insc.center[0]), float(insc.center[1])),
        inscribed_half_side=float(insc.half_side),
        inscribed_method=insc.method,
        builder_seconds=float(elapsed),
        file_bytes=file_bytes,
    )
