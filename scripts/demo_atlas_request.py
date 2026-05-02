"""End-to-end demo: request a patch through the atlas-backed dispatcher.

Mimics what the API does inside ``run_patch_job`` so you can sanity-check
without spinning up Uvicorn. Writes ``demo_atlas.svg`` and prints a summary.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from spectre_patch import PATCH_ENGINE_SEMVER
from spectre_patch.atlas import AtlasIndex, enumerate_emitted_or_atlas
from spectre_patch.config_limits import LimitsSettings
from spectre_patch.export.svg_export import SvgRenderOpts, svg_document, write_svg_or_svgz
from spectre_patch.masking import MaskCircle, MaskHexagon, MaskSquare, RetentionMode


def main() -> int:
    p = argparse.ArgumentParser(description="End-to-end atlas demo")
    p.add_argument("--atlas", default="data/atlas")
    p.add_argument("--mask", choices=["circle", "square", "hexagon"], default="circle")
    p.add_argument("--radius", type=float, default=8.0)
    p.add_argument("--retention", choices=["centroid", "intersection", "clip"], default="centroid")
    p.add_argument("--out", default="demo_atlas.svg")
    p.add_argument("--compact", action="store_true")
    p.add_argument("--colors", action="store_true", help="deterministic per-tile palette")
    args = p.parse_args()

    atlas_root = Path(args.atlas)
    idx = AtlasIndex.load(atlas_root)
    if not idx.entries:
        print(f"(no atlas at {atlas_root}; build one with `python -m spectre_patch.atlas.cli build N --out {atlas_root}`)")
        return 1

    if args.mask == "circle":
        mask = MaskCircle((0.0, 0.0), radius=float(args.radius))
    elif args.mask == "square":
        mask = MaskSquare((0.0, 0.0), half_side=float(args.radius))
    else:
        mask = MaskHexagon((0.0, 0.0), circumradius=float(args.radius))

    t0 = time.perf_counter()
    emitted, res = enumerate_emitted_or_atlas(
        tile_family="spectre_tile_1_1",
        patch_version=PATCH_ENGINE_SEMVER,
        seed=None,
        half_extent_cover=float(args.radius),
        scale=1.0,
        tx=0.0,
        ty=0.0,
        rotation_deg=0.0,
        mask=mask,
        retention=RetentionMode(args.retention),
        limits=LimitsSettings(),
        substitution_iterations=None,
        atlas_index=idx,
    )
    t_emit = time.perf_counter() - t0

    svg_text = svg_document(
        emitted,
        patch_meta={
            "patch_engine": PATCH_ENGINE_SEMVER,
            "atlas_used": res.used_atlas,
            "atlas_iterations": res.selected_iterations,
            "atlas_file": res.selected_file,
        },
        scale=1.0,
        rotation_deg=0.0,
        tx=0.0,
        ty=0.0,
        opts=SvgRenderOpts(
            compact=bool(args.compact),
            deterministic_colors=bool(args.colors),
        ),
    )
    out_path = Path(args.out)
    nbytes = write_svg_or_svgz(out_path, svg_text)

    print(f"# {args.mask}(r={args.radius}) retention={args.retention}")
    print(f"served from atlas: {res.used_atlas}")
    print(f"selected_iterations: {res.selected_iterations}")
    print(f"selected_file: {res.selected_file}")
    print(f"fallback_reason: {res.fallback_reason}")
    print(f"core_total_tiles: {res.tile_count_pre_mask}")
    print(f"tiles_emitted: {len(emitted):,}")
    print(f"emit_seconds: {t_emit:.3f}")
    print(f"svg: {out_path}  ({nbytes:,} bytes)")
    return 0


if __name__ == "__main__":
    main()
