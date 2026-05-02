"""Smoke checks for tiling + exporters."""

from __future__ import annotations

import hashlib

from spectre_patch import PATCH_ENGINE_SEMVER
from spectre_patch.config_limits import LimitsSettings
from spectre_patch.export.sidecars import tiles_to_csv_rows
from spectre_patch.export.svg_export import SvgRenderOpts, svg_document
from spectre_patch.masking import MaskSquare, RetentionMode
from spectre_patch.patch_engine import enumerate_emitted


def test_emitted_tile_ids_unique_small_patch():
    lim = LimitsSettings()
    emitted = enumerate_emitted(
        tile_family="spectre_tile_1_1",
        patch_version=PATCH_ENGINE_SEMVER,
        seed=None,
        half_extent_cover=1.75,
        scale=1.25,
        tx=1.1,
        ty=-2.2,
        rotation_deg=37.25,
        mask=MaskSquare((0.0, 0.0), half_side=8.5),
        retention=RetentionMode.centroid,
        limits=lim,
        substitution_iterations=5,
    )
    ids = [t.tile_id for t in emitted]
    assert len(ids) == len(set(ids))


def test_svg_hash_length():
    emitted = enumerate_emitted(
        tile_family="spectre_tile_1_1",
        patch_version="test",
        seed="abc",
        half_extent_cover=1.75,
        scale=1.0,
        tx=0.0,
        ty=0.0,
        rotation_deg=0.0,
        mask=MaskSquare((0.0, 0.0), half_side=8.5),
        retention=RetentionMode.centroid,
        limits=LimitsSettings(),
        substitution_iterations=5,
    )
    svg = svg_document(
        emitted[:25],
        patch_meta={"fixture": True},
        scale=1.0,
        rotation_deg=10.5,
        tx=2.25,
        ty=-3.333,
        opts=SvgRenderOpts(deterministic_colors=True),
    )
    digest = hashlib.sha256(svg.encode("utf-8")).hexdigest()
    assert len(digest) == 64


def test_csv_header_present():
    emitted = enumerate_emitted(
        tile_family="spectre_tile_1_1",
        patch_version="1.0-test",
        seed=None,
        half_extent_cover=1.75,
        scale=2.15,
        tx=1.125,
        ty=9.876,
        rotation_deg=-30.333,
        mask=MaskSquare((0.0, 0.0), half_side=8.5),
        retention=RetentionMode.centroid,
        limits=LimitsSettings(),
        substitution_iterations=4,
    )
    csvb = tiles_to_csv_rows(emitted[:10], patch_version="1.0-test", tile_family="spectre_tile_1_1", seed=None)
    first = csvb.splitlines()[0].decode()
    assert first.startswith("id,tx,")
