"""Emit site logo SVG: canonical Tile(1,1) outline from spectre_t11.PROTOTILE_RING.

Regenerate after changing core geometry:
  python scripts/gen_brand_mark.py > site/assets/brand-mark.svg
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from spectre_patch.core.spectre_t11 import PROTOTILE_CENTROID, PROTOTILE_RING
from spectre_patch.export.svg_utils import prototile_path_d

# Site theme (--accent, --accent-2 from site/styles.css)
GRAD_START = "#ff6a4a"
GRAD_END = "#ffd166"
VIEW = 32.0
INSET = 13.5


def brand_path_d() -> str:
    pts = (PROTOTILE_RING - PROTOTILE_CENTROID).astype(np.float64).copy()
    # Match svg_export-style math coordinates to SVG (Y down)
    pts[:, 1] *= -1.0
    extent = float(np.abs(pts).max())
    scale = INSET / extent
    pts = pts * scale + np.array([VIEW / 2.0, VIEW / 2.0])
    return prototile_path_d(pts)


def build_svg(d: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(VIEW)} {int(VIEW)}" role="img" aria-label="Tile(1,1) Spectre monotile outline">
  <defs>
    <linearGradient id="brand-mark-grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{GRAD_START}"/>
      <stop offset="100%" stop-color="{GRAD_END}"/>
    </linearGradient>
  </defs>
  <path fill="url(#brand-mark-grad)" stroke="rgba(255,255,255,0.14)" stroke-width="0.35" d="{d}"/>
</svg>
"""


def main() -> None:
    p = argparse.ArgumentParser(description="Write brand-mark.svg from PROTOTILE_RING.")
    p.add_argument(
        "-o",
        "--out",
        type=Path,
        default=None,
        help="Output path (default: stdout)",
    )
    args = p.parse_args()
    svg = build_svg(brand_path_d())
    if args.out is None:
        print(svg, end="")
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    main()
