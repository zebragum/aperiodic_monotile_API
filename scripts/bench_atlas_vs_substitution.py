"""Benchmark: serve a small mask from the atlas vs. live substitution.

Quick way to confirm "most requests cut a tiny region from a big core" is fast.

Usage::

    python scripts/bench_atlas_vs_substitution.py --atlas data/atlas \
        --depth 7 --circle-radius 12 --reps 5
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from spectre_patch import PATCH_ENGINE_SEMVER
from spectre_patch.atlas import AtlasIndex, enumerate_emitted_or_atlas
from spectre_patch.config_limits import LimitsSettings
from spectre_patch.masking import MaskCircle, RetentionMode


def bench(args: argparse.Namespace) -> None:
    atlas_root = Path(args.atlas)
    idx = AtlasIndex.load(atlas_root)
    if not idx.entries:
        print(f"(no atlas at {atlas_root})")
        return

    radius = float(args.circle_radius)
    mask = MaskCircle((0.0, 0.0), radius=radius)

    print(f"# mask: circle r={radius:.2f}")
    print(f"# atlas root: {atlas_root}  cores: {[e.iterations for e in sorted(idx.entries, key=lambda x: x.iterations)]}")
    print()

    # Atlas mode (warm cache after first call).
    n = int(args.reps)
    print(f"-- atlas mode ({n} reps after warmup) --")
    atlas_emitted, res = enumerate_emitted_or_atlas(
        tile_family="spectre_tile_1_1",
        patch_version=PATCH_ENGINE_SEMVER,
        seed=None,
        half_extent_cover=radius,
        scale=1.0,
        tx=0.0,
        ty=0.0,
        rotation_deg=0.0,
        mask=mask,
        retention=RetentionMode.centroid,
        limits=LimitsSettings(),
        substitution_iterations=None,
        atlas_index=idx,
    )
    print(
        f"warmup: served {len(atlas_emitted):,} tiles "
        f"from core_n{res.selected_iterations} "
        f"({res.tile_count_pre_mask:,} total in core, "
        f"{len(atlas_emitted) / max(res.tile_count_pre_mask or 1, 1) * 100:.2f}% kept)"
    )
    t = time.perf_counter()
    for _ in range(n):
        enumerate_emitted_or_atlas(
            tile_family="spectre_tile_1_1",
            patch_version=PATCH_ENGINE_SEMVER,
            seed=None,
            half_extent_cover=radius,
            scale=1.0,
            tx=0.0,
            ty=0.0,
            rotation_deg=0.0,
            mask=mask,
            retention=RetentionMode.centroid,
            limits=LimitsSettings(),
            substitution_iterations=None,
            atlas_index=idx,
        )
    atlas_secs = (time.perf_counter() - t) / n
    print(f"avg per-request: {atlas_secs * 1000:.1f} ms")

    if args.skip_substitution:
        return

    print()
    print(f"-- substitution mode ({n} reps; depth={args.depth}) --")
    t = time.perf_counter()
    for _ in range(n):
        enumerate_emitted_or_atlas(
            tile_family="spectre_tile_1_1",
            patch_version=PATCH_ENGINE_SEMVER,
            seed=None,
            half_extent_cover=radius,
            scale=1.0,
            tx=0.0,
            ty=0.0,
            rotation_deg=0.0,
            mask=mask,
            retention=RetentionMode.centroid,
            limits=LimitsSettings(),
            substitution_iterations=int(args.depth),
            force_substitution=True,
        )
    sub_secs = (time.perf_counter() - t) / n
    print(f"avg per-request: {sub_secs * 1000:.1f} ms")
    if sub_secs > 0:
        print()
        print(f"speedup: {sub_secs / atlas_secs:.1f}x")


def main() -> int:
    p = argparse.ArgumentParser(description="Atlas vs. substitution timing")
    p.add_argument("--atlas", required=True, help="atlas root dir (with index.json)")
    p.add_argument("--depth", type=int, default=7)
    p.add_argument("--circle-radius", type=float, default=12.0)
    p.add_argument("--reps", type=int, default=5)
    p.add_argument("--skip-substitution", action="store_true")
    bench(p.parse_args())
    return 0


if __name__ == "__main__":
    main()
