"""instance_json manifest carries the clean prototile N-gon + per-tile matrices.

This is what the Blender add-on's "editable N-gon instances" mode consumes to
distribute native instances of a single clean tile (no triangulation).
"""

from __future__ import annotations

import json

import numpy as np

from spectre_patch.config_limits import LimitsSettings
from spectre_patch.core.spectre_t11 import PROTOTILE_RING
from spectre_patch.export import stl_export
from spectre_patch.masking import MaskSquare, RetentionMode
from spectre_patch.patch_engine import enumerate_emitted


def _emit():
    return enumerate_emitted(
        limits=LimitsSettings(),
        tile_family="spectre_tile_1_1",
        patch_version="inst-test",
        seed=None,
        half_extent_cover=1.5,
        scale=1.0,
        tx=0.0,
        ty=0.0,
        rotation_deg=0.0,
        mask=MaskSquare((0.0, 0.0), half_side=8.0),
        retention=RetentionMode.centroid,
        substitution_iterations=2,
    )


def test_manifest_includes_clean_prototile_ring():
    tiles = _emit()
    raw = stl_export.instancing_manifest_bytes(
        tiles,
        patch_version="inst-test",
        tile_family="spectre_tile_1_1",
        seed=None,
        scale=1.0,
        rotation_deg=0.0,
        tx=0.0,
        ty=0.0,
    )
    doc = json.loads(raw)

    ring = doc["prototile_ring_xy"]
    assert doc["prototile_vertex_count"] == len(PROTOTILE_RING) == 14
    assert len(ring) == 14
    # Matches the canonical clean N-gon exactly (single face, no triangulation).
    assert np.allclose(np.array(ring), PROTOTILE_RING)
    assert doc["prototile_winding"] == "ccw"


def test_manifest_instances_have_4x4_matrix_and_labels():
    tiles = _emit()
    raw = stl_export.instancing_manifest_bytes(
        tiles,
        patch_version="inst-test",
        tile_family="spectre_tile_1_1",
        seed=None,
        scale=1.0,
        rotation_deg=0.0,
        tx=0.0,
        ty=0.0,
    )
    doc = json.loads(raw)
    assert doc["instances"], "expected at least one instance"
    for inst in doc["instances"]:
        rows = inst["affine4_row_lists"]
        assert len(rows) == 4
        assert all(len(r) == 4 for r in rows)
        assert rows[3] == [0.0, 0.0, 0.0, 1.0]
        assert "id" in inst
        assert "label" in inst


def test_manifest_uses_styled_ring_when_visual_style_set():
    from spectre_patch.export.tile_styling import TileVisualStyle, export_ring_for_style

    tiles = _emit()
    wavy = TileVisualStyle(side_style="wavy", side_style_amplitude=0.2, tile_edge_ratio=1.0)
    expected = export_ring_for_style(wavy)
    raw = stl_export.instancing_manifest_bytes(
        tiles,
        patch_version="inst-test",
        tile_family="spectre_tile_1_1",
        seed=None,
        scale=1.0,
        rotation_deg=0.0,
        tx=0.0,
        ty=0.0,
        visual_style=wavy,
    )
    doc = json.loads(raw)
    ring = np.array(doc["prototile_ring_xy"])
    assert len(ring) > len(PROTOTILE_RING)
    assert np.allclose(ring, expected)
