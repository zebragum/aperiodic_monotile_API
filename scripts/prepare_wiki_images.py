"""Prepare wiki imagery: copy patent assets, build tiling zoom GIF, fetch CC hat diagram."""

from __future__ import annotations

import math
import ssl
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "site" / "assets" / "research" / "wiki"
PATENT = Path(r"C:\Z\ZSPACE - Copy\patent")

ASSETS.mkdir(parents=True, exist_ok=True)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def copy_optimize_png(src: Path, name: str, max_w: int = 1200) -> Path:
    img = Image.open(src)
    if name.lower().endswith(".jpg"):
        img = img.convert("RGB")
    else:
        img = img.convert("RGBA")
    w, h = img.size
    if w > max_w:
        img = img.resize((max_w, int(h * max_w / w)), Image.Resampling.LANCZOS)
    out = ASSETS / name
    if name.lower().endswith(".jpg"):
        img.save(out, optimize=True, quality=88)
    else:
        img.save(out, optimize=True)
    print(f"wrote {out.name} ({out.stat().st_size} bytes)")
    return out


def ease(t: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * t)


def build_zoom_gif(src: Path, out_name: str, frames: int = 36, duration_ms: int = 80) -> Path:
    """Steady zoom in then back out: every frame is a real crop of the source
    at a smoothly interpolated scale, centered on a fixed anchor point."""
    img = Image.open(src).convert("RGB")
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    square = img.crop((left, top, left + side, top + side))

    out_size = 480
    # Anchor the zoom slightly off-center so structure sweeps past the camera.
    anchor = (side * 0.46, side * 0.44)
    wide = float(side)
    near = side * 0.12  # ~8x magnification at the closest point

    def crop_at(scale_side: float) -> Image.Image:
        half_s = scale_side / 2.0
        cx = min(max(anchor[0], half_s), side - half_s)
        cy = min(max(anchor[1], half_s), side - half_s)
        box = (int(cx - half_s), int(cy - half_s), int(cx + half_s), int(cy + half_s))
        return square.crop(box).resize((out_size, out_size), Image.Resampling.LANCZOS)

    sequence: list[Image.Image] = []
    half = frames // 2
    for i in range(half):
        t = ease(i / max(half - 1, 1))
        # Interpolate in log space so the zoom speed feels constant.
        s = math.exp(math.log(wide) * (1 - t) + math.log(near) * t)
        frame = crop_at(s)
        sequence.append(frame.quantize(colors=64, method=Image.Quantize.MEDIANCUT))
    # Zoom back out by reversing (skip endpoints to avoid double frames).
    sequence.extend(sequence[-2:0:-1])

    out = ASSETS / out_name
    sequence[0].save(
        out,
        save_all=True,
        append_images=sequence[1:],
        duration=duration_ms,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(f"wrote {out.name} ({out.stat().st_size} bytes, {len(sequence)} frames)")
    return out


def fetch_url(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "aperiodic-wiki-asset-fetch/1.0"})
    with urllib.request.urlopen(req, context=ctx) as resp:
        dest.write_bytes(resp.read())
    print(f"fetched {dest.name} ({dest.stat().st_size} bytes)")


def main() -> None:
    copy_optimize_png(PATENT / "tilevariants.png", "tilevariants-web.png", max_w=1100)

    src_jpg = PATENT / "Z_Space_PPA_Final_html_m7e07b4b9.jpg"
    copy_optimize_png(src_jpg, "tiling-array-web.jpg", max_w=1400)
    build_zoom_gif(src_jpg, "tiling-array-zoom.gif", frames=36, duration_ms=80)

    hat_svg_url = (
        "https://commons.wikimedia.org/wiki/Special:FilePath/"
        "Aperiodic_monotile_smith_2023.svg?width=1100"
    )
    hat_png = ASSETS / "hat-monotile-commons.png"
    fetch_url(hat_svg_url, hat_png)

    spectre_patch_url = (
        "https://commons.wikimedia.org/wiki/Special:FilePath/"
        "Aperiodic_monotile_tiling.png?width=1400"
    )
    fetch_url(spectre_patch_url, ASSETS / "spectre-tiling-commons.jpg")


if __name__ == "__main__":
    main()
