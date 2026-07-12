"""Generate and copy illustrative images for wiki application articles."""

from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.patches import Polygon
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "site" / "assets" / "research" / "wiki"
OUTPUTS = Path(r"C:\Z\New folder (3)\outputs")
SVG_PATCH = ROOT / "site" / "assets" / "examples" / "rectangle-9x4.svg"

ASSETS.mkdir(parents=True, exist_ok=True)


def copy_optimize(src: Path, dest_name: str, max_w: int = 1400) -> Path:
    img = Image.open(src).convert("RGB")
    w, h = img.size
    if w > max_w:
        img = img.resize((max_w, int(h * max_w / w)), Image.Resampling.LANCZOS)
    out = ASSETS / dest_name
    img.save(out, optimize=True, quality=88)
    print(f"copied {out.name} ({out.stat().st_size} bytes)")
    return out


def parse_svg_paths(svg_text: str) -> list[tuple[list[tuple[float, float]], str]]:
    tiles: list[tuple[list[tuple[float, float]], str]] = []
    for d, fill in re.findall(r'<path d="([^"]+)"[^>]*fill="([^"]+)"', svg_text):
        pts: list[tuple[float, float]] = []
        tokens = re.findall(r"[MLZ]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", d)
        i = 0
        while i < len(tokens):
            cmd = tokens[i]
            if cmd in ("M", "L"):
                i += 1
                x = float(tokens[i])
                y = float(tokens[i + 1])
                pts.append((x, -y))
                i += 2
            elif cmd == "Z":
                break
            else:
                i += 1
        if len(pts) >= 3:
            tiles.append((pts, fill))
    return tiles


def tile_centroid(pts: list[tuple[float, float]]) -> tuple[float, float]:
    xs, ys = zip(*pts)
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def save_figure(fig: plt.Figure, name: str) -> None:
    out = ASSETS / name
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"rendered {out.name} ({out.stat().st_size} bytes)")


def render_patch(
    tiles: list[tuple[list[tuple[float, float]], str]],
    name: str,
    *,
    facecolors: list | str | None = None,
    edgecolors: str | None = "#ffffff22",
    linewidth: float = 0.15,
    bg: str = "#090b13",
    alpha: float = 1.0,
    centroids: list[tuple[float, float]] | None = None,
    centroid_color: str = "#ffd166",
    centroid_size: float = 8,
    lines: list[tuple[tuple[float, float], tuple[float, float]]] | None = None,
    line_color: str = "#ff6a4acc",
    figsize=(10, 4.5),
) -> None:
    fig, ax = plt.subplots(figsize=figsize, facecolor=bg)
    ax.set_facecolor(bg)
    ax.set_aspect("equal")
    ax.axis("off")

    polys = [Polygon(pts, closed=True) for pts, _ in tiles]
    if facecolors is None:
        facecolors = [fill for _, fill in tiles]
    collection = ax.add_collection(
        PolyCollection(
            [p.get_xy() for p in polys],
            facecolors=facecolors,
            edgecolors=edgecolors,
            linewidths=linewidth,
            alpha=alpha,
        )
    )
    _ = collection

    if lines:
        segs = [[a, b] for a, b in lines]
        ax.add_collection(
            LineCollection(segs, colors=line_color, linewidths=0.6, alpha=0.75)
        )

    if centroids:
        xs, ys = zip(*centroids)
        ax.scatter(xs, ys, s=centroid_size, c=centroid_color, edgecolors="none", alpha=0.95)

    xs = [x for pts, _ in tiles for x, _ in pts]
    ys = [y for pts, _ in tiles for _, y in pts]
    pad = 1.5
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    ax.set_ylim(min(ys) - pad, max(ys) + pad)
    save_figure(fig, name)


def hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))


def mix(a: tuple[float, float, float], b: tuple[float, float, float], t: float) -> tuple[float, float, float]:
    return tuple(x * (1 - t) + y * t for x, y in zip(a, b))


def build_neighbor_lines(centroids: list[tuple[float, float]], k: int = 3, max_dist: float = 4.0):
    pts = np.array(centroids)
    lines: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for i, p in enumerate(pts):
        dists = np.linalg.norm(pts - p, axis=1)
        order = np.argsort(dists)[1 : k + 1]
        for j in order:
            if dists[j] <= max_dist:
                lines.append((tuple(p), tuple(pts[j])))
    return lines


def main() -> None:
    copy_optimize(OUTPUTS / "monotile_sunset_terracotta.png", "computer-graphics-sunset.jpg", max_w=1400)
    copy_optimize(OUTPUTS / "monotile_brass_panel.png", "computer-graphics-brass.jpg", max_w=1400)
    copy_optimize(OUTPUTS / "monotile_sunset_terracotta.png", "design-architecture-facade.jpg", max_w=1400)
    copy_optimize(OUTPUTS / "monotile_brass_panel.png", "materials-fabrication-panel.jpg", max_w=1400)

    tiles = parse_svg_paths(SVG_PATCH.read_text(encoding="utf-8"))
    centroids = [tile_centroid(pts) for pts, _ in tiles]

    render_patch(
        tiles,
        "education-colorful-patch.png",
        facecolors=[fill for _, fill in tiles],
        edgecolors="#160b07",
        linewidth=0.25,
        bg="#f7efe8",
        figsize=(10, 4.5),
    )

    render_patch(
        tiles,
        "signal-processing-sampling.png",
        facecolors="#111523",
        edgecolors="#ffffff10",
        linewidth=0.1,
        centroids=centroids,
        centroid_color="#ff6a4a",
        centroid_size=10,
        bg="#090b13",
    )

    wave_colors = []
    for pts, _ in tiles:
        cx, cy = tile_centroid(pts)
        t = 0.5 + 0.5 * math.sin(cx * 0.55 + cy * 0.35)
        wave_colors.append(mix((0.08, 0.16, 0.28), (0.18, 0.62, 0.82), t))
    render_patch(
        tiles,
        "waves-photonics-diffraction.png",
        facecolors=wave_colors,
        edgecolors="#9adfff55",
        linewidth=0.2,
        bg="#050a12",
    )

    metal_colors = []
    for pts, fill in tiles:
        base = hex_to_rgb(fill)
        lum = 0.2126 * base[0] + 0.7152 * base[1] + 0.0722 * base[2]
        metal_colors.append(mix((0.18, 0.2, 0.24), (0.72, 0.74, 0.78), lum))
    render_patch(
        tiles,
        "materials-science-lattice.png",
        facecolors=metal_colors,
        edgecolors="#ffffff33",
        linewidth=0.18,
        bg="#10141c",
    )

    terrain_colors = []
    for pts, fill in tiles:
        h = int(hashlib.md5(fill.encode()).hexdigest()[:6], 16) / 0xFFFFFF
        terrain_colors.append(mix((0.12, 0.18, 0.1), (0.62, 0.5, 0.28), h))
    render_patch(
        tiles,
        "robotics-terrain-array.png",
        facecolors=terrain_colors,
        edgecolors="#00000044",
        linewidth=0.12,
        bg="#0d1210",
        figsize=(10, 4.5),
    )

    pastel = []
    for pts, fill in tiles:
        base = hex_to_rgb(fill)
        pastel.append(mix((0.95, 0.88, 0.9), base, 0.35))
    render_patch(
        tiles,
        "biology-scaffold-patch.png",
        facecolors=pastel,
        edgecolors="#ffffffaa",
        linewidth=0.22,
        bg="#f3eef8",
    )

    lines = build_neighbor_lines(centroids, k=3, max_dist=3.8)
    render_patch(
        tiles,
        "algorithms-graph-patch.png",
        facecolors="#111523",
        edgecolors="#ffd16655",
        linewidth=0.35,
        centroids=centroids,
        centroid_color="#ffd166",
        centroid_size=7,
        lines=lines,
        line_color="#ff6a4a",
        bg="#090b13",
    )


if __name__ == "__main__":
    main()
