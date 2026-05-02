"""Smoke-test render_core_inscribed_square_png against the local n=6 atlas core.

Usage:
    python scripts/smoke_test_core_preview.py
"""

from __future__ import annotations

import time
from pathlib import Path

from spectre_patch.atlas import AtlasIndex, load_core
from spectre_patch.export.raster_export import RasterOpts, render_core_inscribed_square_png


def main() -> int:
    atlas_dir = Path("data/atlas")
    idx = AtlasIndex.load(atlas_dir)
    if not idx.entries:
        print(f"no atlas at {atlas_dir}")
        return 1

    entry = next((e for e in idx.entries if e.iterations == 6), None)
    if entry is None:
        print("no n=6 core in atlas; build one with `python -m spectre_patch.atlas.cli build 6 --out data/atlas`")
        return 1

    core = load_core(entry, atlas_dir)
    out_path = Path(f"core_preview_n{core.iterations}_smoke.png")
    opts = RasterOpts(
        pixels_per_side=2048,
        background_rgb=(20, 20, 35),
        fill_rgb=(205, 214, 234),
        stroke_rgb=(23, 27, 56),
        stroke_width_px=1,
        deterministic_palette=True,
        progress_every=50_000,
    )

    def cb(n_seen: int, secs: float) -> None:
        print(f"  ... visited {n_seen:,} tiles in {secs:.1f}s")

    print(f"rendering n={core.iterations} ({core.tile_count:,} tiles) -> {out_path}")
    t0 = time.perf_counter()
    info = render_core_inscribed_square_png(
        core=core,
        out_path=out_path,
        opts=opts,
        progress=cb,
    )
    elapsed = time.perf_counter() - t0
    print()
    print(f"  elapsed:     {elapsed:.1f}s")
    print(f"  tiles_drawn: {info['tiles_drawn']:,}")
    print(f"  out_bytes:   {info['out_bytes']:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
