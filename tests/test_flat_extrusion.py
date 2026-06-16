"""Flat (zero-depth) STL/GLB export for custom extrusion workflows."""

from __future__ import annotations

import numpy as np

from spectre_patch.core.spectre_t11 import PROTOTILE_RING
from spectre_patch.export.stl_export import prototype_prism_tris, tile_prism_tris
from spectre_patch.config_limits import LimitsSettings
from spectre_patch.masking import MaskSquare, RetentionMode
from spectre_patch.patch_engine import enumerate_emitted


def test_prototype_prism_zero_extrusion_is_planar_cap():
    tris = prototype_prism_tris(0.0)
    assert tris
    zs = [float(tri[0, 2]) for tri in tris]
    assert max(zs) - min(zs) < 1e-9


def test_tile_prism_zero_extrusion_is_planar():
    tiles = enumerate_emitted(
        limits=LimitsSettings(),
        tile_family="spectre_tile_1_1",
        patch_version="flat-test",
        seed=None,
        half_extent_cover=1.0,
        scale=1.0,
        tx=0.0,
        ty=0.0,
        rotation_deg=0.0,
        mask=MaskSquare((0.0, 0.0), half_side=4.0),
        retention=RetentionMode.centroid,
        substitution_iterations=1,
    )
    tris = tile_prism_tris(
        tiles[0],
        scale=1.0,
        rotation_deg=0.0,
        tx=0.0,
        ty=0.0,
        thickness_mm=0.0,
    )
    assert tris
    zs = np.concatenate([tri[:, 2] for tri in tris])
    assert float(np.max(zs) - np.min(zs)) < 1e-9


def test_positive_extrusion_still_builds_prism():
    tris = prototype_prism_tris(1.0, PROTOTILE_RING)
    zs = [float(tri[0, 2]) for tri in tris]
    assert max(zs) - min(zs) > 0.5
