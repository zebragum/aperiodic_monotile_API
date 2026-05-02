"""Atlas CLI.

Build cores into a directory::

    python -m spectre_patch.atlas.cli build 6 --out data/atlas
    python -m spectre_patch.atlas.cli build 7 --out data/atlas
    python -m spectre_patch.atlas.cli build 8 --out data/atlas --raster 2048   # offline only
    python -m spectre_patch.atlas.cli build 9 --out data/atlas --raster 4096   # Colab only

List manifest::

    python -m spectre_patch.atlas.cli list --out data/atlas
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from spectre_patch.atlas.builder import build_core
from spectre_patch.atlas.schema import AtlasIndex


def _cmd_build(args: argparse.Namespace) -> int:
    out_dir = Path(args.out)
    res = build_core(
        iterations=int(args.iterations),
        out_dir=out_dir,
        tile_family=args.family,
        patch_version=args.patch_version,
        overwrite=bool(args.overwrite),
        raster_resolution_override=int(args.raster) if args.raster else None,
    )
    print(
        f"built {res.file.name} | depth={int(args.iterations)} "
        f"tiles={res.tile_count:,} bytes={res.file_bytes:,} "
        f"inscribed_half_side={res.inscribed_half_side:.3f} "
        f"({res.inscribed_method}) "
        f"in {res.builder_seconds:.1f}s"
    )
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    out_dir = Path(args.out)
    idx = AtlasIndex.load(out_dir)
    if not idx.entries:
        print(f"(no entries in {out_dir / 'index.json'})")
        return 0
    print(f"# atlas root: {out_dir}")
    print(
        f"{'family':<24} {'iters':>5} {'tiles':>14} "
        f"{'bytes':>14} {'inscribed_half_side':>20} {'method':>16}"
    )
    for e in sorted(idx.entries, key=lambda x: (x.tile_family, x.iterations)):
        print(
            f"{e.tile_family:<24} {e.iterations:>5} "
            f"{e.tile_count:>14,} {e.file_bytes:>14,} "
            f"{e.inscribed_half_side:>20.3f} {e.inscribed_method:>16}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spectre_patch.atlas", description="Atlas builder")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build", help="build a depth-N core")
    p_build.add_argument("iterations", type=int, help="substitution depth N (5..10)")
    p_build.add_argument("--out", required=True, help="atlas root directory")
    p_build.add_argument("--family", default="spectre_tile_1_1")
    p_build.add_argument("--patch-version", default="0.1.0")
    p_build.add_argument("--raster", default=None, help="override raster resolution")
    p_build.add_argument("--overwrite", action="store_true")
    p_build.set_defaults(func=_cmd_build)

    p_list = sub.add_parser("list", help="list manifest entries")
    p_list.add_argument("--out", required=True, help="atlas root directory")
    p_list.set_defaults(func=_cmd_list)

    ns = p.parse_args(argv)
    return int(ns.func(ns))


if __name__ == "__main__":
    sys.exit(main())
