"""Colab / A100 build script for deep cores (n=8, n=9, n=10).

Run this in a Colab notebook with a high-RAM runtime. After it finishes,
download the produced ``.npz`` and ``index.json`` and copy them into your
deployment's ``data/atlas/`` directory.

Tile counts grow ~7.87x per substitution step::

    n=7 →  2.15M tiles  (~50  MB,  5 min  on a laptop)
    n=8 →   17M tiles   (~400 MB, ~40 min, recommended Colab CPU runtime)
    n=9 →  133M tiles   (~3.1 GB, several hours on Colab; do n=8 first as smoke)
    n=10 → 1.05B tiles  (~25  GB, A100/HPC class; only build if 8192-unit cores
                         are needed inside a single inscribed square)

Substitution depth → inscribed square (canonical units, half-side):

    n=5  72.9         n=8  ~1300 (est.)
    n=6  197.2        n=9  ~3400 (est.)
    n=7  516.4        n=10 ~9000 (est.)

The 8192-unit-wide square the user requested needs n=10 if the user's mask is
square-shaped (inscribed_half_side >= 4096). For circular / hexagonal masks of
diagonal 8192, n=9 may suffice.

Usage in Colab::

    !pip install -e /content/spectre_patch_api
    !python /content/spectre_patch_api/scripts/colab_build_deep_core.py \
        --depth 8 --out /content/spectre_patch_api/data/atlas
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(description="Build a deep atlas core (offline)")
    p.add_argument("--depth", type=int, required=True, help="substitution depth N")
    p.add_argument("--out", type=Path, required=True, help="atlas root directory")
    p.add_argument("--family", default="spectre_tile_1_1")
    p.add_argument(
        "--patch-version",
        default=None,
        help="patch_version string (defaults to importing PATCH_ENGINE_SEMVER)",
    )
    p.add_argument(
        "--raster",
        type=int,
        default=None,
        help=(
            "Raster resolution for inscribed-square detection. "
            "Recommend 2048 for n=8, 4096 for n=9, 8192 for n=10."
        ),
    )
    p.add_argument("--overwrite", action="store_true")
    args = p.parse_args()

    from spectre_patch import PATCH_ENGINE_SEMVER  # noqa: PLC0415
    from spectre_patch.atlas import build_core  # noqa: PLC0415

    depth = int(args.depth)
    if depth < 5 or depth > 12:
        print(f"refusing depth={depth}: choose between 5 and 12", file=sys.stderr)
        return 2

    raster = args.raster
    if raster is None:
        # Sensible defaults so the inscribed-square detector resolves without OOM.
        raster = {5: 256, 6: 512, 7: 1024, 8: 2048, 9: 4096, 10: 8192}.get(depth, 1024)

    print(
        f"# building core (family={args.family!r}, depth={depth}, "
        f"out={args.out}, raster={raster})"
    )
    res = build_core(
        iterations=depth,
        out_dir=args.out,
        tile_family=args.family,
        patch_version=str(args.patch_version or PATCH_ENGINE_SEMVER),
        overwrite=bool(args.overwrite),
        raster_resolution_override=raster,
    )
    print()
    print(f"file:                {res.file}")
    print(f"tile_count:          {res.tile_count:,}")
    print(f"file_bytes:          {res.file_bytes:,}")
    print(f"bbox:                {res.bbox}")
    print(f"inscribed_center:    {res.inscribed_center}")
    print(f"inscribed_half_side: {res.inscribed_half_side:.3f}")
    print(f"inscribed_method:    {res.inscribed_method}")
    print(f"builder_seconds:     {res.builder_seconds:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
