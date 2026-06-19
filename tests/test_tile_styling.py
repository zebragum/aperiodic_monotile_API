"""Unit tests for export-side tile styling."""

from __future__ import annotations

import numpy as np

from spectre_patch.export.tile_styling import (
    TileVisualStyle,
    build_base_ring,
    decorate_ring_with_profile,
    export_ring_for_style,
    normalize_side_profile,
    normalize_side_style,
    ring_to_svg_path_d,
    style_ring_vertices,
)
from spectre_patch.core.spectre_t11 import PROTOTILE_RING


def test_normalize_side_style_aliases():
    assert normalize_side_style("curved") == "curvy"
    assert normalize_side_style("CURVY") == "curvy"


def test_tile_edge_ratio_stretches_ring():
    flat = build_base_ring(1.0)
    stretched = build_base_ring(2.0)
    assert not np.allclose(flat, stretched)
    assert len(stretched) == len(PROTOTILE_RING)


def test_curvy_increases_vertex_count():
    base = build_base_ring(1.0)
    flat = style_ring_vertices(base, "flat", 0.12)
    curvy = style_ring_vertices(base, "curvy", 0.12)
    assert len(curvy) > len(flat)


def test_from_request_rejects_bad_amplitude():
    try:
        TileVisualStyle.from_request({"side_style_amplitude": 2.0})
    except ValueError as e:
        assert "amplitude" in str(e).lower()
    else:
        raise AssertionError("expected ValueError")


def test_custom_profile_decorates_ring():
    profile = [(0.0, 0.0), (0.25, 0.15), (0.5, -0.1), (0.75, 0.15), (1.0, 0.0)]
    ring = decorate_ring_with_profile(PROTOTILE_RING, profile, amplitude=0.12)
    assert len(ring) > len(PROTOTILE_RING)
    original = {tuple(np.round(p, 6)) for p in PROTOTILE_RING}
    moved = [p for p in ring if tuple(np.round(p, 6)) not in original]
    assert moved, "expected profile to introduce off-edge bulge points"


def test_normalize_side_profile_endpoints():
    pts = normalize_side_profile([[0.0, 0.0], [0.5, 0.1], [1.0, 0.0]])
    assert pts == ((0.0, 0.0), (0.5, 0.1), (1.0, 0.0))


def test_export_ring_for_style_custom_profile():
    profile = ((0.0, 0.0), (0.5, 0.2), (1.0, 0.0))
    style = TileVisualStyle(
        side_style="custom",
        side_style_amplitude=0.1,
        side_profile_normalized=profile,
    )
    ring = export_ring_for_style(style)
    assert len(ring) > len(PROTOTILE_RING)


def test_export_ring_path_differs_for_wavy():
    flat_style = TileVisualStyle(side_style="flat", side_style_amplitude=0.12, tile_edge_ratio=1.0)
    wavy_style = TileVisualStyle(side_style="wavy", side_style_amplitude=0.2, tile_edge_ratio=1.0)
    flat_d = ring_to_svg_path_d(export_ring_for_style(flat_style))
    wavy_d = ring_to_svg_path_d(export_ring_for_style(wavy_style))
    assert flat_d != wavy_d
    assert wavy_d.count("L") > flat_d.count("L")
