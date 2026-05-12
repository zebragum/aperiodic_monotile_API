"""Regenerate bundled static-site SVG examples from the current patch engine."""

from __future__ import annotations

import shutil
from pathlib import Path

from shapely.ops import unary_union

from spectre_patch import PATCH_ENGINE_SEMVER
from spectre_patch.atlas import enumerate_emitted_or_atlas
from spectre_patch.config_limits import LimitsSettings
from spectre_patch.export.svg_export import SvgRenderOpts, svg_document
from spectre_patch.jobs.tasks import _coverage_half_extent_for, coerce_mask
from spectre_patch.masking import RetentionMode, mask_polygon


ROOT = Path(__file__).resolve().parents[1]
SITE_EXAMPLES = ROOT / "site" / "assets" / "examples"
MIRROR_EXAMPLES = ROOT.parent / "monotile-site" / "assets" / "examples"


CASES = [
    (
        "circle-100u.svg",
        {"type": "circle", "radius": 50.0},
        1000,
    ),
    (
        "rectangle-9x4.svg",
        {"type": "rectangle", "width": 90.0, "height": 40.0},
        900,
    ),
    (
        "triangle-50u.svg",
        {"type": "triangle", "side_length": 50.0},
        500,
    ),
]


def _assert_no_material_gap(emitted, mask) -> None:
    mask_geom = mask_polygon(mask)
    pieces = [tile.clip_geom for tile in emitted if tile.clip_geom is not None and not tile.clip_geom.is_empty]
    if not pieces:
        raise AssertionError("no clipped geometry emitted")
    covered = unary_union(pieces)
    missing = mask_geom.difference(covered)
    # Tiny slivers can appear from floating-point clipping; visible holes are much larger.
    if missing.area > max(mask_geom.area * 1e-6, 1e-6):
        raise AssertionError(f"visible gap area={missing.area:.6g} mask_area={mask_geom.area:.6g}")


def main() -> int:
    SITE_EXAMPLES.mkdir(parents=True, exist_ok=True)
    MIRROR_EXAMPLES.mkdir(parents=True, exist_ok=True)
    limits = LimitsSettings()

    for filename, mask_body, pixel_target in CASES:
        mask = coerce_mask(mask_body)
        emitted, resolution = enumerate_emitted_or_atlas(
            tile_family="spectre_tile_1_1",
            patch_version=PATCH_ENGINE_SEMVER,
            seed=None,
            half_extent_cover=_coverage_half_extent_for(mask, None),
            scale=1.0,
            tx=0.0,
            ty=0.0,
            rotation_deg=0.0,
            mask=mask,
            retention=RetentionMode.clip,
            limits=limits,
            substitution_iterations=None,
            atlas_index=None,
        )
        _assert_no_material_gap(emitted, mask)
        svg = svg_document(
            emitted,
            patch_meta={
                "patch_engine": PATCH_ENGINE_SEMVER,
                "static_example": filename,
                "tiles": len(emitted),
                "aligned_crop": resolution.fallback_reason,
            },
            scale=1.0,
            rotation_deg=0.0,
            tx=0.0,
            ty=0.0,
            opts=SvgRenderOpts(
                fill="#f1543f",
                stroke="#151821",
                stroke_width=0.08,
                pixel_target=pixel_target,
                margin=0.0,
            ),
        )
        out = SITE_EXAMPLES / filename
        out.write_text(svg, encoding="utf-8")
        shutil.copy2(out, MIRROR_EXAMPLES / filename)
        print(f"{filename}: tiles={len(emitted)} fallback={resolution.fallback_reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
