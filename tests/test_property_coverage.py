"""Property: a square ±h is fully covered by the canonical Delta substitution patch bbox."""

from __future__ import annotations

import numpy as np

from spectre_patch.config_limits import LimitsSettings
from spectre_patch.core.spectre_t11 import (
    IDENTITY_AFFINE,
    PROTOTILE_RING,
    apply_affine_to_points,
    iter_placed_tiles,
    min_iterations_for_square,
    patch_bbox_iter,
    tile_system_after_iterations,
)


def test_min_iterations_bbox_covers_square():
    h = 2.5
    n = min_iterations_for_square(h, max_iter=LimitsSettings().max_supertile_iterations)
    sysn = tile_system_after_iterations(n)
    placed = list(iter_placed_tiles(sysn["Delta"], IDENTITY_AFFINE, ()))
    minx, miny, maxx, maxy = patch_bbox_iter(placed)
    assert minx <= -h and maxx >= h and miny <= -h and maxy >= h


def test_dfs_paths_unique_and_finite():
    sysn = tile_system_after_iterations(3)
    placed = list(iter_placed_tiles(sysn["Delta"], IDENTITY_AFFINE, ()))
    paths = [p for _l, _m, p in placed]
    assert len(set(paths)) == len(paths)
    rings = np.concatenate(
        [apply_affine_to_points(M, PROTOTILE_RING) for _l, M, _p in placed], axis=0
    )
    assert np.all(np.isfinite(rings))
