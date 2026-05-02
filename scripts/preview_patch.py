"""Render a square, gap-free Spectre / Tile(1,1) patch as raw vector geometry.

Run via:
    python scripts/preview_patch.py [output_path] [iterations]

If output ends with `.svgz` the document is gzipped on the way out (Inkscape and
all major browsers read svgz transparently; on-disk footprint is roughly 5-15%
of the uncompressed SVG, perfect for distributing huge patches).
"""

from __future__ import annotations

import sys
from pathlib import Path

from spectre_patch import PATCH_ENGINE_SEMVER
from spectre_patch.config_limits import LimitsSettings
from spectre_patch.export.svg_export import SvgRenderOpts, svg_document, write_svg_or_svgz
from spectre_patch.masking import MaskSquare, RetentionMode
from spectre_patch.patch_engine import enumerate_emitted
from spectre_patch.patch_inscribe import find_inscribed_square


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("../core_patch_preview.svg")
    iterations = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    print(f"Generating depth-{iterations} substitution patch...")
    inscribed = find_inscribed_square(iterations)
    print(
        f"  full-patch tiles: {inscribed.tile_count_full_patch}\n"
        f"  inscribed square: center=({inscribed.center[0]:.3f}, {inscribed.center[1]:.3f}) "
        f"half_side={inscribed.half_side:.3f} ({2 * inscribed.half_side:.1f} canonical units wide)\n"
        f"  method: {inscribed.method}"
    )

    tiles = enumerate_emitted(
        tile_family="spectre_tile_1_1",
        patch_version=PATCH_ENGINE_SEMVER,
        seed="preview",
        half_extent_cover=max(abs(inscribed.center[0]), abs(inscribed.center[1])) + inscribed.half_side + 5.0,
        scale=1.0,
        tx=0.0,
        ty=0.0,
        rotation_deg=0.0,
        mask=MaskSquare(inscribed.center, inscribed.half_side),
        retention=RetentionMode.clip,
        limits=LimitsSettings(),
        substitution_iterations=iterations,
    )
    print(f"  tiles after clip: {len(tiles)}")

    svg = svg_document(
        tiles,
        patch_meta={
            "patch_engine": PATCH_ENGINE_SEMVER,
            "iterations": iterations,
            "inscribed_center": list(inscribed.center),
            "inscribed_half_side": inscribed.half_side,
            "tiles_after_clip": len(tiles),
        },
        scale=1.0,
        rotation_deg=0.0,
        tx=0.0,
        ty=0.0,
        opts=SvgRenderOpts(
            fill="#cdd6ea",
            stroke="#1a1a2e",
            stroke_width=0.05,
            opacity=1.0,
            deterministic_colors=True,
            background="#101018",
            flip_y=True,
            margin=0.0,
            pixel_target=1600,
            compact=True,
        ),
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    written = write_svg_or_svgz(out, svg)
    print(f"Wrote {out.resolve()} ({written:,} bytes)")


if __name__ == "__main__":
    main()
