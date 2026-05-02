"""Direct rasterisation of an inscribed-square patch to PNG.

Streams tiles from `iter_placed_tiles_in_bbox` (with bbox pruning) and draws each
tile polygon into a Pillow image. Memory bounded by the image buffer; works for
many millions of tiles given enough wall time.

Output is always pixel-square, deterministic, and aligned to the canonical
inscribed square so downstream consumers can map pixel→canonical via a single
linear transform.
"""

from __future__ import annotations

import hashlib
import struct
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from spectre_patch.core.spectre_t11 import (
    IDENTITY_AFFINE,
    PROTOTILE_RING,
    apply_affine_to_points,
    iter_placed_tiles_in_bbox,
    tile_system_after_iterations,
)


@dataclass(frozen=True, slots=True)
class RasterOpts:
    pixels_per_side: int = 4096
    background_rgb: tuple[int, int, int] = (16, 16, 24)
    deterministic_palette: bool = True
    fill_rgb: tuple[int, int, int] = (210, 215, 232)
    stroke_rgb: tuple[int, int, int] | None = (24, 28, 56)
    stroke_width_px: int = 1
    progress_every: int = 50_000


def _palette_rgb_for_id(seed: str) -> tuple[int, int, int]:
    h = hashlib.sha256(seed.encode()).digest()
    hue = int.from_bytes(h[0:2], "big") / 65535.0
    light = 0.55 + ((h[2] % 50) / 50.0) * 0.25
    sat = 0.32 + ((h[3] % 40) / 40.0) * 0.30
    return _hls_to_rgb(hue, light, sat)


def _hls_to_rgb(h: float, l: float, s: float) -> tuple[int, int, int]:
    chroma = (1.0 - abs(2.0 * l - 1.0)) * s
    hp = h * 6.0
    x = chroma * (1.0 - abs(hp % 2.0 - 1.0))
    if hp < 1:
        r, g, b = chroma, x, 0.0
    elif hp < 2:
        r, g, b = x, chroma, 0.0
    elif hp < 3:
        r, g, b = 0.0, chroma, x
    elif hp < 4:
        r, g, b = 0.0, x, chroma
    elif hp < 5:
        r, g, b = x, 0.0, chroma
    else:
        r, g, b = chroma, 0.0, x
    m = l - chroma / 2.0
    return (
        int(round((r + m) * 255)),
        int(round((g + m) * 255)),
        int(round((b + m) * 255)),
    )


def render_inscribed_square_png(
    *,
    iterations: int,
    center: tuple[float, float],
    half_side: float,
    out_path: Path | str,
    opts: RasterOpts | None = None,
    progress: Callable[[int, float], None] | None = None,
) -> dict:
    """Stream the inscribed-square patch into a PNG.

    The output PNG is `pixels_per_side`×`pixels_per_side`. Canonical→pixel mapping:

        px = (canonical_x - (cx - half_side)) * pixels_per_side / (2 * half_side)
        py = pixels_per_side - (canonical_y - (cy - half_side)) * pixels_per_side / (2 * half_side)

    (The Y axis is flipped so canonical y-up matches image y-up on screen.)
    """

    try:
        from PIL import Image, ImageDraw  # type: ignore[import-not-found]  # noqa: PLC0415
    except Exception as e:
        raise RuntimeError(
            "PNG raster export requires Pillow — install `pip install spectre-patch-api[png]`."
        ) from e

    opts = opts or RasterOpts()
    cx, cy = float(center[0]), float(center[1])
    h = float(half_side)
    side = 2.0 * h
    pps = int(opts.pixels_per_side)

    img = Image.new("RGB", (pps, pps), opts.background_rgb)
    draw = ImageDraw.Draw(img)

    sysn = tile_system_after_iterations(iterations)
    target_bbox = (cx - h, cy - h, cx + h, cy + h)

    tile_count = 0
    drawn = 0
    started = time.perf_counter()
    cache: dict[int, tuple[float, float, float, float]] = {}

    def to_px(xy: np.ndarray) -> list[tuple[float, float]]:
        scaled_x = (xy[:, 0] - (cx - h)) * (pps / side)
        scaled_y = pps - (xy[:, 1] - (cy - h)) * (pps / side)
        return list(zip(scaled_x.tolist(), scaled_y.tolist(), strict=True))

    fill_default = opts.fill_rgb
    stroke_default = opts.stroke_rgb
    stroke_w = max(0, int(opts.stroke_width_px))

    for label, M, path in iter_placed_tiles_in_bbox(
        sysn["Delta"], IDENTITY_AFFINE, target_bbox, bbox_cache=cache
    ):
        tile_count += 1
        ring = apply_affine_to_points(M, PROTOTILE_RING)
        # Skip if the tile bbox is fully outside the square (pruning may pass tiles whose bbox grazes).
        if (
            ring[:, 0].max() < cx - h
            or ring[:, 0].min() > cx + h
            or ring[:, 1].max() < cy - h
            or ring[:, 1].min() > cy + h
        ):
            continue
        pts = to_px(ring)

        if opts.deterministic_palette:
            seed_str = f"{label}::{path}"
            fill = _palette_rgb_for_id(seed_str)
        else:
            fill = fill_default

        if stroke_default is None or stroke_w == 0:
            draw.polygon(pts, fill=fill)
        else:
            draw.polygon(pts, fill=fill, outline=stroke_default)
        drawn += 1

        if progress is not None and (tile_count % opts.progress_every == 0):
            progress(tile_count, time.perf_counter() - started)

    elapsed = time.perf_counter() - started
    img.save(str(out_path), format="PNG", optimize=False)

    return {
        "pixels_per_side": pps,
        "tiles_visited": tile_count,
        "tiles_drawn": drawn,
        "iterations": iterations,
        "center": [cx, cy],
        "half_side": h,
        "elapsed_seconds": elapsed,
        "out_bytes": Path(out_path).stat().st_size,
    }


def render_core_inscribed_square_png(
    *,
    core,  # LoadedCore (avoid circular import)
    out_path: Path | str,
    opts: RasterOpts | None = None,
    progress: Callable[[int, float], None] | None = None,
) -> dict:
    """Same as :func:`render_inscribed_square_png` but reads tile data from a
    pre-built atlas core. Skips the substitution rebuild — useful in Colab when
    you've just produced the core and want a preview without paying another
    O(metatile tree) cost.
    """

    try:
        from PIL import Image, ImageDraw  # type: ignore[import-not-found]  # noqa: PLC0415
    except Exception as e:
        raise RuntimeError(
            "PNG raster export requires Pillow — install `pip install spectre-patch-api[png]`."
        ) from e

    opts = opts or RasterOpts()
    cx, cy = float(core.inscribed_center[0]), float(core.inscribed_center[1])
    h = float(core.inscribed_half_side)
    if h <= 0:
        raise ValueError("core has zero inscribed_half_side; cannot render preview")

    side = 2.0 * h
    pps = int(opts.pixels_per_side)

    img = Image.new("RGB", (pps, pps), opts.background_rgb)
    draw = ImageDraw.Draw(img)

    target = (cx - h, cy - h, cx + h, cy + h)
    indices = core.crop(target)
    if indices.size == 0:
        raise RuntimeError("inscribed-square crop returned zero tiles")

    tile_count = 0
    drawn = 0
    started = time.perf_counter()

    fill_default = opts.fill_rgb
    stroke_default = opts.stroke_rgb
    stroke_w = max(0, int(opts.stroke_width_px))

    affine6 = core.affine6
    for ridx in indices:
        ridx_int = int(ridx)
        gen6 = affine6[ridx_int]
        ring = apply_affine_to_points(gen6, PROTOTILE_RING)
        if (
            ring[:, 0].max() < cx - h
            or ring[:, 0].min() > cx + h
            or ring[:, 1].max() < cy - h
            or ring[:, 1].min() > cy + h
        ):
            tile_count += 1
            continue
        scaled_x = (ring[:, 0] - (cx - h)) * (pps / side)
        scaled_y = pps - (ring[:, 1] - (cy - h)) * (pps / side)
        pts = list(zip(scaled_x.tolist(), scaled_y.tolist(), strict=True))

        if opts.deterministic_palette:
            label = core.label_for(ridx_int)
            path = core.dfs_path_for(ridx_int)
            fill = _palette_rgb_for_id(f"{label}::{path}")
        else:
            fill = fill_default

        if stroke_default is None or stroke_w == 0:
            draw.polygon(pts, fill=fill)
        else:
            draw.polygon(pts, fill=fill, outline=stroke_default)

        drawn += 1
        tile_count += 1
        if progress is not None and (tile_count % opts.progress_every == 0):
            progress(tile_count, time.perf_counter() - started)

    elapsed = time.perf_counter() - started
    img.save(str(out_path), format="PNG", optimize=False)

    return {
        "pixels_per_side": pps,
        "tiles_visited": tile_count,
        "tiles_drawn": drawn,
        "iterations": int(core.iterations),
        "center": [cx, cy],
        "half_side": h,
        "elapsed_seconds": elapsed,
        "out_bytes": Path(out_path).stat().st_size,
    }
