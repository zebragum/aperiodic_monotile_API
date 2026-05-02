"""Atlas builder / loader / dispatch round-trips.

Compares a small atlas core (n=4) against the live substitution path under
identical request parameters; the two must produce identical tile counts and
identical stable tile IDs since the DFS order is deterministic.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from shapely.geometry import box as shp_box
from shapely.ops import unary_union

from spectre_patch import PATCH_ENGINE_SEMVER
from spectre_patch.atlas import (
    AtlasIndex,
    LoadedCore,
    build_core,
    enumerate_emitted_from_core,
    enumerate_emitted_or_atlas,
    load_core,
    select_core,
)
from spectre_patch.atlas.schema import core_filename, pack_dfs_path, unpack_dfs_path
from spectre_patch.atlas.selector import MaskExtent
from spectre_patch.config_limits import LimitsSettings
from spectre_patch.masking import MaskCircle, MaskSquare, RetentionMode
from spectre_patch.patch_engine import enumerate_emitted


def _build_n4(tmp_path: Path) -> tuple[AtlasIndex, LoadedCore]:
    res = build_core(
        iterations=4,
        out_dir=tmp_path,
        tile_family="spectre_tile_1_1",
        patch_version=PATCH_ENGINE_SEMVER,
        overwrite=True,
        raster_resolution_override=512,
    )
    assert res.file.exists()
    idx = AtlasIndex.load(tmp_path)
    assert len(idx.entries) == 1
    entry = idx.entries[0]
    core = load_core(entry, tmp_path)
    return idx, core


def test_pack_unpack_dfs_round_trip():
    paths = [
        (),
        (0,),
        (7,),
        (0, 1, 2, 3, 4, 5, 6, 7),
        (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1),
    ]
    for p in paths:
        packed, depth = pack_dfs_path(p)
        assert unpack_dfs_path(packed, depth) == p


def test_pack_dfs_rejects_oob():
    with pytest.raises(ValueError):
        pack_dfs_path((8,))
    with pytest.raises(ValueError):
        pack_dfs_path(tuple(0 for _ in range(22)))


def test_atlas_core_filename_deterministic():
    assert core_filename("spectre_tile_1_1", 6) == "core_spectre_tile_1_1_n6.npz"


def test_build_n4_creates_index_and_artifact(tmp_path: Path):
    idx, core = _build_n4(tmp_path)
    assert (tmp_path / "index.json").exists()
    assert core.tile_count > 50
    assert core.iterations == 4
    assert core.tile_family == "spectre_tile_1_1"
    assert core.bbox[0] < core.bbox[2]
    assert core.inscribed_half_side > 0


def test_atlas_dfs_paths_recover_same_ids_as_substitution(tmp_path: Path):
    """The atlas must produce IDs identical to substitution-mode for the same patch."""

    _, core = _build_n4(tmp_path)
    mask = MaskSquare((core.inscribed_center[0], core.inscribed_center[1]), half_side=core.inscribed_half_side)
    emitted_atlas = enumerate_emitted_from_core(
        core,
        tile_family="spectre_tile_1_1",
        patch_version=PATCH_ENGINE_SEMVER,
        seed="atlas-test",
        scale=1.0,
        tx=0.0,
        ty=0.0,
        rotation_deg=0.0,
        mask=mask,
        retention=RetentionMode.centroid,
    )
    emitted_live = enumerate_emitted(
        tile_family="spectre_tile_1_1",
        patch_version=PATCH_ENGINE_SEMVER,
        seed="atlas-test",
        half_extent_cover=core.inscribed_half_side,
        scale=1.0,
        tx=0.0,
        ty=0.0,
        rotation_deg=0.0,
        mask=mask,
        retention=RetentionMode.centroid,
        limits=LimitsSettings(),
        substitution_iterations=4,
    )
    ids_a = sorted(t.tile_id for t in emitted_atlas)
    ids_b = sorted(t.tile_id for t in emitted_live)
    assert ids_a == ids_b
    assert len(ids_a) > 0


def test_select_core_picks_smallest_sufficient(tmp_path: Path):
    """Build n=3 and n=4; mask covered by n=3 must select n=3, not n=4."""

    build_core(
        iterations=3,
        out_dir=tmp_path,
        tile_family="spectre_tile_1_1",
        patch_version=PATCH_ENGINE_SEMVER,
        overwrite=True,
        raster_resolution_override=256,
    )
    build_core(
        iterations=4,
        out_dir=tmp_path,
        tile_family="spectre_tile_1_1",
        patch_version=PATCH_ENGINE_SEMVER,
        overwrite=True,
        raster_resolution_override=512,
    )
    idx = AtlasIndex.load(tmp_path)
    n3 = next(e for e in idx.entries if e.iterations == 3)
    n4 = next(e for e in idx.entries if e.iterations == 4)
    assert n3.inscribed_half_side > 0
    assert n4.inscribed_half_side > n3.inscribed_half_side

    # A mask that fits inside n=3's inscribed square must select n=3.
    half = n3.inscribed_half_side * 0.5
    extent = MaskExtent(center=n3.inscribed_center, half_side=half)
    chosen = select_core(idx, tile_family="spectre_tile_1_1", extent=extent)
    assert chosen.iterations == 3

    # A mask just larger than n=3's must select n=4.
    big = n3.inscribed_half_side + 0.05
    extent_big = MaskExtent(center=n3.inscribed_center, half_side=big)
    chosen_big = select_core(idx, tile_family="spectre_tile_1_1", extent=extent_big)
    assert chosen_big.iterations == 4


def test_dispatch_uses_atlas_when_available(tmp_path: Path):
    idx, core = _build_n4(tmp_path)
    mask = MaskCircle((core.inscribed_center[0], core.inscribed_center[1]), radius=core.inscribed_half_side * 0.5)
    emitted, res = enumerate_emitted_or_atlas(
        tile_family="spectre_tile_1_1",
        patch_version=PATCH_ENGINE_SEMVER,
        seed=None,
        half_extent_cover=core.inscribed_half_side,
        scale=1.0,
        tx=0.0,
        ty=0.0,
        rotation_deg=0.0,
        mask=mask,
        retention=RetentionMode.centroid,
        limits=LimitsSettings(),
        substitution_iterations=4,
        atlas_index=idx,
    )
    assert res.used_atlas is True
    assert res.selected_iterations == 4
    assert res.fallback_reason is None
    assert len(emitted) > 0


def test_atlas_clip_square_has_no_voids(tmp_path: Path):
    """Clipped atlas output must cover the requested square completely."""

    _, core = _build_n4(tmp_path)
    half = min(6.25, core.inscribed_half_side * 0.5)
    mask = MaskSquare((0.0, 0.0), half_side=half)
    emitted = enumerate_emitted_from_core(
        core,
        tile_family="spectre_tile_1_1",
        patch_version=PATCH_ENGINE_SEMVER,
        seed="atlas-clip-coverage",
        scale=1.0,
        tx=0.0,
        ty=0.0,
        rotation_deg=0.0,
        mask=mask,
        retention=RetentionMode.clip,
    )
    mask_poly = shp_box(-half, -half, half, half)
    clipped = [tile.clip_geom for tile in emitted if tile.clip_geom is not None]
    assert clipped

    missing = mask_poly.difference(unary_union(clipped))
    assert missing.area < 1e-7


def test_dispatch_falls_back_when_mask_too_big(tmp_path: Path):
    idx, core = _build_n4(tmp_path)
    # Request a mask far larger than n=4's inscribed square so the selector fails.
    mask = MaskSquare((0.0, 0.0), half_side=core.inscribed_half_side * 10.0)
    emitted, res = enumerate_emitted_or_atlas(
        tile_family="spectre_tile_1_1",
        patch_version=PATCH_ENGINE_SEMVER,
        seed=None,
        half_extent_cover=core.inscribed_half_side * 10.0,
        scale=1.0,
        tx=0.0,
        ty=0.0,
        rotation_deg=0.0,
        mask=mask,
        retention=RetentionMode.centroid,
        limits=LimitsSettings(),
        substitution_iterations=4,
        atlas_index=idx,
    )
    assert res.used_atlas is False
    assert res.fallback_reason is not None
    assert "no_atlas_core_large_enough" in res.fallback_reason
    assert len(emitted) > 0
