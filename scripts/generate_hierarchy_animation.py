"""Render the Spectre substitution hierarchy: tile -> cluster -> supercluster.

Uses the real Tile(1,1) substitution system from spectre_patch.core.spectre_t11.
Colors encode which level-1 cluster each leaf tile belongs to, so the
hierarchy stays readable as the camera pulls back through the levels.
Outputs an animated GIF plus a high-res still of the final frame.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from spectre_patch.core.spectre_t11 import (  # noqa: E402
    IDENTITY_AFFINE,
    PROTOTILE_RING,
    apply_affine_to_points,
    iter_placed_tiles,
    tile_system_after_iterations,
)

ASSETS = ROOT / "site" / "assets" / "research" / "wiki"
ASSETS.mkdir(parents=True, exist_ok=True)

BG = "#090b13"
# Site-palette-adjacent cluster colors (one per level-1 cluster index).
CLUSTER_COLORS = [
    "#ff6a4a",  # coral
    "#ffd166",  # gold
    "#4ecdc4",  # teal
    "#8c7ae6",  # violet
    "#f78fb3",  # rose
    "#7bed9f",  # mint
    "#70a1ff",  # sky
    "#e77f67",  # terracotta
]


def gather(level: int) -> list[tuple[np.ndarray, tuple[int, ...]]]:
    system = tile_system_after_iterations(level)
    root = system["Delta"]
    out = []
    for _label, M, path in iter_placed_tiles(root, IDENTITY_AFFINE, ()):
        out.append((apply_affine_to_points(M, PROTOTILE_RING), path))
    return out


def color_for(path: tuple[int, ...], level: int) -> str:
    """Color leaves by their top-level cluster index at this render level."""
    if level == 0 or not path:
        return CLUSTER_COLORS[0]
    return CLUSTER_COLORS[path[0] % len(CLUSTER_COLORS)]


def bounds(rings: list[np.ndarray]) -> tuple[float, float, float, float]:
    all_pts = np.vstack(rings)
    return (
        float(all_pts[:, 0].min()),
        float(all_pts[:, 1].min()),
        float(all_pts[:, 0].max()),
        float(all_pts[:, 1].max()),
    )


def render_frame(
    rings_colors: list[tuple[np.ndarray, str]],
    view: tuple[float, float, float, float],
    size_px: int = 560,
    title: str = "",
) -> Image.Image:
    dpi = 100
    fig, ax = plt.subplots(figsize=(size_px / dpi, size_px / dpi), dpi=dpi, facecolor=BG)
    ax.set_facecolor(BG)
    ax.set_aspect("equal")
    ax.axis("off")

    polys = [r for r, _ in rings_colors]
    colors = [c for _, c in rings_colors]
    ax.add_collection(
        PolyCollection(polys, facecolors=colors, edgecolors="#090b13", linewidths=0.7)
    )
    cx = (view[0] + view[2]) / 2
    cy = (view[1] + view[3]) / 2
    half = max(view[2] - view[0], view[3] - view[1]) / 2 * 1.06
    ax.set_xlim(cx - half, cx + half)
    ax.set_ylim(cy - half, cy + half)
    if title:
        ax.text(
            0.5,
            0.035,
            title,
            transform=ax.transAxes,
            ha="center",
            color="#f7efe8",
            fontsize=13,
            family="sans-serif",
        )

    fig.canvas.draw()
    buf = np.asarray(fig.canvas.buffer_rgba())
    plt.close(fig)
    return Image.fromarray(buf[:, :, :3])


def ease(t: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * t)


def lerp_view(a, b, t):
    return tuple(a[i] * (1 - t) + b[i] * t for i in range(4))


def main() -> None:
    # Level 0: one tile. Level 1: one cluster (8 tiles). Level 2: supercluster (~60).
    levels = []
    for lvl in range(3):
        placed = gather(lvl)
        rings = [r for r, _ in placed]
        levels.append(
            {
                "rings_colors": [(r, color_for(p, lvl)) for r, p in placed],
                "view": bounds(rings),
                "count": len(placed),
            }
        )
    titles = [
        f"1 tile",
        f"cluster · {levels[1]['count']} tiles",
        f"supercluster · {levels[2]['count']} tiles",
    ]

    frames: list[Image.Image] = []
    hold = 10
    steps = 14

    # Hold level 0, then zoom/expand to level 1, hold, expand to level 2, hold.
    for lvl in range(3):
        img = render_frame(levels[lvl]["rings_colors"], levels[lvl]["view"], title=titles[lvl])
        frames.extend([img] * hold)
        if lvl < 2:
            nxt = lvl + 1
            for i in range(1, steps + 1):
                t = ease(i / steps)
                view = lerp_view(levels[lvl]["view"], levels[nxt]["view"], t)
                # Show the next level's geometry as soon as the pull-back starts,
                # so new tiles appear around the existing cluster.
                img = render_frame(
                    levels[nxt]["rings_colors"],
                    view,
                    title=titles[nxt] if t > 0.5 else titles[lvl],
                )
                frames.append(img)

    # Reverse back to the single tile for a seamless loop.
    frames.extend(frames[-2:0:-1])

    quantized = [f.quantize(colors=64, method=Image.Quantize.MEDIANCUT) for f in frames]
    out = ASSETS / "substitution-hierarchy.gif"
    quantized[0].save(
        out,
        save_all=True,
        append_images=quantized[1:],
        duration=90,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(f"wrote {out.name} ({out.stat().st_size} bytes, {len(quantized)} frames)")

    # High-res still of the supercluster for use as a static figure.
    still = render_frame(levels[2]["rings_colors"], levels[2]["view"], size_px=1200)
    still_out = ASSETS / "substitution-hierarchy-still.png"
    still.save(still_out, optimize=True)
    print(f"wrote {still_out.name} ({still_out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
