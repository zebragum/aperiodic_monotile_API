#!/usr/bin/env python3
"""Build studio-grade Gumroad packs (GLB, instances, hero previews, import docs).

Outputs: C:\\Z\\New folder (3)\\outputs\\studio_packs\\

These replace the old grey-SVG scatter packs. Each SKU is one real pipeline
deliverable: drop a GLB in Blender/Unreal, or rebuild from instance JSON.
"""

from __future__ import annotations

import json
import math
import shutil
import sys
import time
import zipfile
import colorsys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from spectre_patch import PATCH_ENGINE_SEMVER
from spectre_patch.atlas.dispatch import enumerate_emitted_or_atlas
from spectre_patch.config_limits import LimitsSettings
from spectre_patch.export.gltf_export import write_glb_instanced
from spectre_patch.export.stl_export import combined_stl_facets, instancing_manifest_bytes, write_binary_stl
from spectre_patch.export.svg_export import SvgRenderOpts, svg_document
from spectre_patch.export.tile_styling import TileVisualStyle
from spectre_patch.export.stl_export import _world_xy_rings
from spectre_patch.masking import (
    MaskCircle,
    MaskRect,
    MaskSquare,
    RetentionMode,
    mask_polygon,
)

OUT = Path(r"C:\Z\New folder (3)\outputs\studio_packs")
SITE_ASSETS = ROOT / "site" / "assets" / "research" / "wiki"
SITE_DIGITAL = ROOT / "site" / "assets" / "digital"


# ---------------------------------------------------------------------------
# Curated preview palettes (match site hero art direction)
# ---------------------------------------------------------------------------

PALETTE_ZELLIGE = {
    "bg": (12, 28, 24),
    "grout": (6, 14, 12),
    "Gamma": (18, 72, 52),
    "Delta": (22, 88, 64),
    "Theta": (28, 102, 74),
    "Lambda": (34, 118, 86),
    "Xi": (42, 134, 98),
    "Pi": (52, 148, 108),
    "Sigma": (68, 168, 122),
    "Phi": (88, 188, 138),
    "Psi": (120, 210, 158),
    "Gamma1": (160, 228, 178),
    "Gamma2": (210, 245, 220),
    "*": (24, 58, 44),
}

PALETTE_BRASS = {
    "bg": (14, 12, 10),
    "grout": (8, 6, 4),
    "*": (120, 88, 48),
    "Gamma": (148, 108, 58),
    "Delta": (168, 122, 64),
    "Theta": (188, 138, 72),
    "Lambda": (208, 154, 78),
    "Xi": (228, 172, 84),
    "Pi": (240, 188, 92),
    "Sigma": (248, 204, 108),
    "Phi": (252, 218, 128),
    "Psi": (255, 232, 160),
    "Gamma1": (255, 240, 180),
    "Gamma2": (255, 248, 210),
}

PALETTE_SUNSET = {
    "bg": (18, 10, 22),
    "grout": (10, 6, 12),
    "*": (180, 72, 48),
    "Gamma": (220, 96, 52),
    "Delta": (240, 118, 58),
    "Theta": (255, 142, 68),
    "Lambda": (255, 168, 82),
    "Xi": (255, 192, 98),
    "Pi": (255, 210, 118),
    "Sigma": (255, 228, 148),
    "Phi": (255, 200, 180),
    "Psi": (220, 140, 200),
    "Gamma1": (180, 100, 220),
    "Gamma2": (140, 80, 180),
}

PALETTE_CONCRETE = {
    "bg": (28, 30, 34),
    "grout": (18, 19, 22),
    "*": (142, 146, 152),
}


def _hex_rgb(color: str) -> tuple[int, int, int]:
    s = color.strip().lstrip("#")
    if len(s) == 6:
        return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
    return 180, 180, 180


def _tile_color(label: str, palette: dict) -> tuple[int, int, int]:
    if label in palette and label not in ("bg", "grout"):
        c = palette[label]
        if isinstance(c, tuple) and len(c) == 3:
            return c
    star = palette.get("*")
    if isinstance(star, tuple):
        return star
    return 160, 160, 160


def _tile_label(tile) -> str:
    return str(getattr(tile, "tile_label", None) or getattr(tile, "label", None) or "*")


def _jitter_color(rgb: tuple[int, int, int], seed: int, *, amount: float = 0.12) -> tuple[int, int, int]:
    """Handmade glaze variation: stable per-tile hue/lightness shift."""
    r, g, b = rgb
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    h = (h + ((seed % 997) / 997.0 - 0.5) * amount * 0.35) % 1.0
    v = max(0.08, min(1.0, v + ((seed // 997) % 113) / 113.0 * amount - amount * 0.45))
    s = max(0.05, min(1.0, s + ((seed // 113) % 89) / 89.0 * amount * 0.25 - amount * 0.12))
    jr, jg, jb = colorsys.hsv_to_rgb(h, s, v)
    return int(jr * 255), int(jg * 255), int(jb * 255)


def _inset_polygon(poly: list[tuple[float, float]], inset: float) -> list[tuple[float, float]]:
    if len(poly) < 3 or inset <= 0:
        return poly
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    out: list[tuple[float, float]] = []
    for x, y in poly:
        dx, dy = cx - x, cy - y
        d = math.hypot(dx, dy) or 1.0
        out.append((x + dx / d * inset, y + dy / d * inset))
    return out


def _preview_canvas_size(span: np.ndarray, *, long_edge: int = 2560) -> tuple[int, int]:
    w, h = float(span[0]), float(span[1])
    if w <= 1e-6 or h <= 1e-6:
        return long_edge, long_edge
    if w >= h:
        pw = long_edge
        ph = max(720, int(round(long_edge * h / w)))
    else:
        ph = long_edge
        pw = max(720, int(round(long_edge * w / h)))
    return pw, ph


def render_preview_png(
    path: Path,
    tiles,
    *,
    mask_geom,
    style: TileVisualStyle,
    scale: float,
    palette: dict,
    size: int = 2560,
) -> None:
    """Top-down preview with grout gaps, atlas label colors, and glaze variation."""

    from PIL import Image, ImageDraw, ImageFilter

    rings_data: list[tuple[np.ndarray, str, str]] = []
    for tile in tiles:
        label = _tile_label(tile)
        tile_id = str(getattr(tile, "tile_id", label))
        for ring in _world_xy_rings(
            tile,
            scale=scale,
            rotation_deg=0.0,
            tx=0.0,
            ty=0.0,
            visual_style=style,
            mask_geom=mask_geom,
        ):
            if len(ring) >= 3:
                rings_data.append((np.asarray(ring, dtype=np.float64), label, tile_id))

    if not rings_data:
        raise RuntimeError("no geometry to preview")

    pts = np.vstack([r for r, _, _ in rings_data])
    min_xy = pts.min(axis=0)
    max_xy = pts.max(axis=0)
    span = np.maximum(max_xy - min_xy, 1e-6)
    margin = 0.04 * float(max(span))
    min_xy -= margin
    max_xy += margin
    span = max_xy - min_xy
    img_w, img_h = _preview_canvas_size(span, long_edge=size)
    pad = 48
    sc = (min(img_w, img_h) - 2 * pad) / float(max(span[0], span[1]))
    off_x = (img_w - span[0] * sc) / 2.0
    off_y = (img_h - span[1] * sc) / 2.0

    def to_px(xy: np.ndarray) -> list[tuple[float, float]]:
        x = (xy[:, 0] - min_xy[0]) * sc + off_x
        y = (max_xy[1] - xy[:, 1]) * sc + off_y
        return list(zip(x.tolist(), y.tolist()))

    bg = palette.get("bg", (20, 22, 28))
    grout = palette.get("grout", (10, 10, 12))
    img = Image.new("RGB", (img_w, img_h), bg if isinstance(bg, tuple) else (20, 22, 28))
    draw = ImageDraw.Draw(img)
    grout_px = max(1.5, sc * 0.012)

    ordered = sorted(
        rings_data,
        key=lambda item: (float(item[0][:, 1].mean()), float(item[0][:, 0].mean())),
    )

    for ring, label, tile_id in ordered:
        poly = to_px(ring)
        fill = _jitter_color(_tile_color(label, palette), hash(tile_id))
        hi = tuple(min(255, c + 22) for c in fill)
        lo = tuple(max(0, c - 28) for c in fill)
        inner = _inset_polygon(poly, grout_px * 0.55)
        draw.polygon(poly, fill=grout if isinstance(grout, tuple) else (10, 10, 12))
        draw.polygon(inner, fill=fill)
        if len(inner) >= 3:
            cx = sum(p[0] for p in inner) / len(inner)
            cy = sum(p[1] for p in inner) / len(inner)
            for i in range(len(inner)):
                p0, p1 = inner[i], inner[(i + 1) % len(inner)]
                mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
                edge_w = max(1, int(sc * 0.007))
                if my <= cy:
                    draw.line([p0, p1], fill=hi, width=edge_w)
                else:
                    draw.line([p0, p1], fill=lo, width=max(1, edge_w - 1))

    img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=90, threshold=2))
    img.save(path, format="PNG", optimize=True)


def render_lookdev_board(path: Path, preview_paths: list[Path], labels: list[str]) -> None:
    """Horizontal palette strip for Gumroad gallery slide 2."""
    from PIL import Image, ImageDraw, ImageFont

    imgs = [Image.open(p).convert("RGB") for p in preview_paths if p.is_file()]
    if not imgs:
        return
    h = max(im.height for im in imgs)
    gap = 24
    label_h = 52
    total_w = sum(im.width for im in imgs) + gap * (len(imgs) - 1) + 48
    board = Image.new("RGB", (total_w, h + label_h + 48), (12, 14, 18))
    draw = ImageDraw.Draw(board)
    x = 24
    for im, lab in zip(imgs, labels, strict=False):
        if im.height != h:
            im = im.resize((int(im.width * h / im.height), h), Image.Resampling.LANCZOS)
        board.paste(im, (x, 24))
        draw.text((x + 8, h + 32), lab.upper(), fill=(180, 190, 210))
        x += im.width + gap
    board.save(path, format="PNG", optimize=True)


@dataclass(frozen=True)
class AssetSpec:
    slug: str
    title: str
    blurb: str
    mask: object
    scale: float = 1.0
    side_style: str = "flat"
    side_style_amplitude: float = 0.14
    glb_thickness_mm: float = 12.0
    stl_thickness_mm: float = 12.0
    real_world_note: str = ""


@dataclass
class PackSpec:
    slug: str
    title: str
    price_usd: int
    gumroad_slug: str
    tagline: str
    buyer: str
    includes: list[str]
    hero_assets: list[str]
    assets: list[AssetSpec] = field(default_factory=list)


PACKS: list[PackSpec] = [
    PackSpec(
        slug="01_archviz_floor_kit",
        title="Archviz Floor Kit",
        price_usd=49,
        gumroad_slug="untiling-archviz-floor-kit",
        tagline="GLB floor plates that survive the dolly shot.",
        buyer="Archviz studios, interior viz, real-time walkthroughs",
        includes=[
            "3 square floor plates (10 m, 15 m, 20 m) as instanced GLB",
            "spectre_instances.json per plate for custom DCC rebuilds",
            "Merged STL for CNC / 3D print reference",
            "Top-down lookdev PNGs (zellige, brass, concrete) with atlas label colors",
            "Palette JSON + MATERIALS.md for Blender / UE5",
            "Blender + Unreal import guides + commercial LICENSE",
            "Periodic vs aperiodic comparison still (marketing license)",
        ],
        hero_assets=[
            "design-zellige-emerald.jpg",
            "computer-graphics-brass.jpg",
            "periodic-vs-aperiodic.jpg",
        ],
        assets=[
            AssetSpec(
                "floor_10m",
                "Floor plate 10 m × 10 m",
                "Lobby, bathroom, product hero. ~500 tiles.",
                MaskSquare((0.0, 0.0), 5.0),
                side_style="flat",
                real_world_note="10 m square at 1 unit = 1 m. Origin centered.",
            ),
            AssetSpec(
                "floor_15m",
                "Floor plate 15 m × 15 m",
                "Living room, gallery, open-plan viz. ~1,100 tiles.",
                MaskSquare((0.0, 0.0), 7.5),
                side_style="curvy",
                side_style_amplitude=0.1,
                real_world_note="15 m square. Curvy edges read as handmade tile.",
            ),
            AssetSpec(
                "floor_20m",
                "Floor plate 20 m × 20 m",
                "Atrium, museum, large exterior pad. ~2,000 tiles.",
                MaskSquare((0.0, 0.0), 10.0),
                side_style="curvy",
                side_style_amplitude=0.12,
                real_world_note="20 m square. Use for wide shots; instancing keeps GLB editable.",
            ),
        ],
    ),
    PackSpec(
        slug="02_game_environment_kit",
        title="Game Environment Kit",
        price_usd=39,
        gumroad_slug="untiling-game-environment-kit",
        tagline="Corridor floors and plaza pads without obvious CG repeat.",
        buyer="Game environment artists, level blockout, sci-fi / fantasy sets",
        includes=[
            "2 corridor plates (24×8 m, 36×12 m) with curvy / blocky tile edges",
            "1 circular plaza pad (24 m diameter), jagged stone profile",
            "GLB + instance JSON + merged STL per asset",
            "Sunset + concrete lookdev PNGs (wide aspect for corridors)",
            "Palette JSON + Unreal Engine 5 + Blender import notes",
            "Commercial LICENSE for shipped game levels",
        ],
        hero_assets=[
            "computer-graphics-sunset.jpg",
            "computer-graphics-brass.jpg",
            "design-zellige-emerald.jpg",
        ],
        assets=[
            AssetSpec(
                "corridor_24x8",
                "Corridor floor 24 m × 8 m",
                "Sci-fi hallway, bunker, ship interior.",
                MaskRect(-12.0, -4.0, 12.0, 4.0),
                side_style="curvy",
                side_style_amplitude=0.14,
                real_world_note="24×8 m. Align long axis to camera path.",
            ),
            AssetSpec(
                "corridor_36x12",
                "Corridor floor 36 m × 12 m",
                "Wide hangar aisle, cathedral nave blockout.",
                MaskRect(-18.0, -6.0, 18.0, 6.0),
                side_style="blocky",
                side_style_amplitude=0.18,
                real_world_note="36×12 m. Blocky edges for hard-surface sets.",
            ),
            AssetSpec(
                "plaza_circle_r12",
                "Circular plaza r = 12 m",
                "Town square, dungeon boss room, fountain pad.",
                MaskCircle((0.0, 0.0), 12.0),
                side_style="jagged",
                side_style_amplitude=0.22,
                glb_thickness_mm=18.0,
                real_world_note="24 m diameter. Jagged edges for fantasy stone.",
            ),
        ],
    ),
    PackSpec(
        slug="00_comparison_sample",
        title="Comparison Sample (free)",
        price_usd=0,
        gumroad_slug="untiling-comparison-sample",
        tagline="See the difference before you buy.",
        buyer="Lead magnet for Gumroad / studio outreach",
        includes=[
            "5 m × 5 m floor GLB (single patch)",
            "Periodic vs aperiodic comparison JPEG",
            "Links to full studio kits",
        ],
        hero_assets=["periodic-vs-aperiodic.jpg"],
        assets=[
            AssetSpec(
                "sample_floor_5m",
                "Sample floor 5 m × 5 m",
                "Quick Blender import test.",
                MaskSquare((0.0, 0.0), 2.5),
                side_style="flat",
                real_world_note="Free sample. Upgrade to Archviz Floor Kit for production sizes.",
            ),
        ],
    ),
]


def _style(spec: AssetSpec) -> TileVisualStyle:
    return TileVisualStyle(
        side_style=spec.side_style,  # type: ignore[arg-type]
        side_style_amplitude=spec.side_style_amplitude,
    )


def _emit(spec: AssetSpec):
    mask = spec.mask
    if isinstance(mask, MaskCircle):
        cover = max(4.5, float(mask.radius) * 1.15 + 2.0)
    elif isinstance(mask, MaskSquare):
        cover = max(4.5, float(mask.half_side) * 1.45 + 2.0)
    elif isinstance(mask, MaskRect):
        w = abs(mask.xmax - mask.xmin)
        h = abs(mask.ymax - mask.ymin)
        cover = max(4.5, max(w, h) * 0.75 + 2.0)
    else:
        cover = 30.0
    tiles, resolution = enumerate_emitted_or_atlas(
        tile_family="spectre_tile_1_1",
        patch_version=PATCH_ENGINE_SEMVER,
        seed=f"studio-{spec.slug}-v2",
        half_extent_cover=cover,
        scale=spec.scale,
        tx=0.0,
        ty=0.0,
        rotation_deg=0.0,
        mask=mask,
        retention=RetentionMode.clip,
        limits=LimitsSettings(),
        substitution_iterations=None,
        atlas_index=None,
        require_atlas=False,
    )
    return tiles, mask_polygon(mask), resolution


def _palette_json(palette: dict) -> dict:
    out: dict[str, str] = {}
    for key, val in palette.items():
        if key in ("bg", "grout"):
            continue
        if isinstance(val, tuple) and len(val) == 3:
            out[key] = f"#{val[0]:02x}{val[1]:02x}{val[2]:02x}"
    return {"label_colors_hex": out, "notes": "Map one Principled BSDF per label in Blender or UE Material Instance."}


def _write_palette_docs(pack_dir: Path, palettes: list[tuple[str, dict]]) -> None:
    pal_dir = pack_dir / "palettes"
    pal_dir.mkdir(parents=True, exist_ok=True)
    docs = pack_dir / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    for name, palette in palettes:
        (pal_dir / f"{name}.json").write_text(
            json.dumps(_palette_json(palette), indent=2),
            encoding="utf-8",
        )
    (pack_dir / "docs" / "MATERIALS.md").write_text(
        """# Material lookdev

Each asset folder includes `previews/topdown_*.png` as color reference for your DCC.

## Blender (fast)

1. Import `patch.glb`
2. For each tile object, assign a Principled BSDF using `palettes/*.json` hex values keyed by object name suffix or custom property `tile_label`
3. Duplicate one tile material and drive **Hue** with a Object Info → Random per tile for subtle variation

## Unreal Engine 5

1. Import GLB with **Import Materials** off
2. Create one Material with a **Material Parameter Collection** or per-instance vector params from `palettes/zellige.json` (or sunset / brass)
3. Use **Per Instance Random** in the material graph for glaze variation

## Archviz pitch

Clients notice floor repeat in 3 seconds of dolly. These patches have **no translational period**; hide patch edges with walls, rugs, or landscape blend.
""",
        encoding="utf-8",
    )


def _write_license(pack_dir: Path) -> None:
    (pack_dir / "LICENSE.txt").write_text(
        """Untiling Studio Pack License

You may use the geometry and included preview art in commercial archviz stills,
animations, real-time walkthroughs, and shipped game levels.

You may modify materials, scale, and combine with your scene geometry.

You may not redistribute the raw GLB/STL/SVG files as a competing tile pack or
template marketplace product.

For site-wide or runtime API use, see https://aperiodicgenerator.com/pricing.html
""",
        encoding="utf-8",
    )


def _write_docs(pack_dir: Path, pack: PackSpec) -> None:
    docs = pack_dir / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "IMPORT_BLENDER.md").write_text(
        f"""# Import into Blender 4.x

Pack: **{pack.title}**

## Fast path (GLB)

1. File → Import → glTF 2.0 (`.glb`)
2. Pick `*/patch.glb` inside any asset folder
3. Each tile is a separate object node, ready for material slots or Geometry Nodes
4. Scale is **1 Blender unit = 1 meter** (see each `manifest.json`)

## Rebuild from instances (advanced)

1. Import `spectre_instances.json` with the Untiling Blender add-on, or
2. Build one mesh from `prototile_ring_xy`, then apply each `affine4_row_lists` matrix

## Materials

Use the included `previews/` PNGs as color-reference. Duplicate a Principled BSDF per tile
label, or randomize hue on import for variation without repetition.

## Need custom sizes?

https://aperiodicgenerator.com/pricing.html
""",
        encoding="utf-8",
    )
    (docs / "IMPORT_UNREAL.md").write_text(
        f"""# Import into Unreal Engine 5

Pack: **{pack.title}**

## GLB

1. Import `patch.glb` via Datasmith glTF or built-in glTF importer
2. Enable **Combine Meshes** only if you want a single draw call (loses per-tile edit)
3. Leave separate for material variation in MRQ stills

## Scale

1 unit = 1 cm in UE by default. If the floor looks 100× too small, set Import Uniform Scale to **100**.

## Collision

For walkable floors: duplicate mesh → Nanite off → add Box/Simple Collision, or use merged STL as collision proxy.

## Pipeline note

These patches do **not** tile at the boundary. Cover edges with walls, trim, or blend into landscape.
""",
        encoding="utf-8",
    )


def _write_gumroad_listing(pack_dir: Path, pack: PackSpec) -> None:
    bullets = "\n".join(f"- {item}" for item in pack.includes)
    (pack_dir / "GUMROAD_LISTING.md").write_text(
        f"""# {pack.title} (${pack.price_usd})

**Slug:** `{pack.gumroad_slug}`

## One-line summary
{pack.tagline}

## Who it's for
{pack.buyer}

## What you get
{bullets}

## Cover image
Use `marketing/hero_01.jpg` (included). It is the same art direction as untiling.com hero renders.

## Why studios buy this instead of using the free generator
- **Time:** Production-sized GLB on disk, no API key, no queue, no tile-limit anxiety
- **Pitch:** Show clients a floor that never repeats on the dolly shot
- **Pipeline:** Instance JSON + per-tile GLB nodes match Blender and Unreal workflows
- **License:** Commercial use in your delivered viz / shipped game levels

## Honest limits
- Boundaries are not seamless; hide edges with geometry
- For infinite unique seeds at runtime, pair with Aperiodic Generator API (Pro)
""",
        encoding="utf-8",
    )


def build_asset(pack_dir: Path, spec: AssetSpec, *, preview_palettes: list[tuple[str, dict]]) -> dict:
    asset_dir = pack_dir / "assets" / spec.slug
    asset_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    tiles, mask_geom, resolution = _emit(spec)
    style = _style(spec)

    meta = {
        "slug": spec.slug,
        "title": spec.title,
        "tile_count": len(tiles),
        "scale_units_per_meter": spec.scale,
        "side_style": spec.side_style,
        "engine": PATCH_ENGINE_SEMVER,
        "real_world": spec.real_world_note,
        "files": {},
    }

    # GLB
    glb_path = asset_dir / "patch.glb"
    write_glb_instanced(
        glb_path,
        tiles,
        scale=spec.scale,
        rotation_deg=0.0,
        tx=0.0,
        ty=0.0,
        thickness_mm=spec.glb_thickness_mm,
        visual_style=style,
        mask_geom=mask_geom,
        patch_meta={"seed": f"studio-{spec.slug}-v2", "pack_asset": spec.slug},
    )
    meta["files"]["patch.glb"] = "Instanced GLB, one node per tile, Y-up"

    # Instance manifest
    inst_path = asset_dir / "spectre_instances.json"
    inst_bytes = instancing_manifest_bytes(
        tiles,
        patch_version=PATCH_ENGINE_SEMVER,
        tile_family="spectre_tile_1_1",
        seed=f"studio-{spec.slug}-v2",
        scale=spec.scale,
        rotation_deg=0.0,
        tx=0.0,
        ty=0.0,
        visual_style=style,
    )
    inst_path.write_bytes(inst_bytes)
    meta["files"]["spectre_instances.json"] = "Affine instance manifest"

    # Merged STL (cap only for size)
    solid_style = TileVisualStyle(side_style="flat", side_style_amplitude=0.0)
    facets = combined_stl_facets(
        tiles,
        scale=spec.scale,
        rotation_deg=0.0,
        tx=0.0,
        ty=0.0,
        thickness_mm=spec.stl_thickness_mm,
        visual_style=solid_style,
    )
    stl_path = asset_dir / "patch_merged.stl"
    write_binary_stl(str(stl_path), facets, header_note=b"untiling_studio")
    meta["files"]["patch_merged.stl"] = "Single mesh, flat extrusion"

    # SVG (compact paths for laser/CNC bonus)
    svg_opts = SvgRenderOpts(
        fill="#d8dee9",
        stroke="#1a1a2e",
        stroke_width=0.08,
        opacity=1.0,
        deterministic_colors=True,
        pixel_target=4096,
        margin=1.0,
        compact=True,
        visual_style=style,
        mask_geom=mask_geom,
    )
    svg_path = asset_dir / "patch.svg"
    svg_path.write_text(
        svg_document(
            tiles,
            patch_meta={"engine": PATCH_ENGINE_SEMVER, "slug": spec.slug},
            scale=spec.scale,
            rotation_deg=0.0,
            tx=0.0,
            ty=0.0,
            opts=svg_opts,
        ),
        encoding="utf-8",
    )
    meta["files"]["patch.svg"] = "Plan view, compact instanced paths"

    prev_dir = asset_dir / "previews"
    prev_dir.mkdir(exist_ok=True)
    for name, palette in preview_palettes:
        png_path = prev_dir / f"topdown_{name}.png"
        render_preview_png(
            png_path,
            tiles,
            mask_geom=mask_geom,
            style=style,
            scale=spec.scale,
            palette=palette,
            size=2560,
        )
        meta["files"][f"previews/topdown_{name}.png"] = f"Marketing / lookdev reference ({name})"

    (asset_dir / "manifest.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    (asset_dir / "README.txt").write_text(
        "\n".join(
            [
                spec.title,
                "=" * len(spec.title),
                "",
                spec.blurb,
                "",
                spec.real_world_note,
                "",
                "Files: patch.glb, spectre_instances.json, patch_merged.stl, patch.svg, previews/",
                "",
                f"Tiles: {len(tiles)}",
                f"Engine: {PATCH_ENGINE_SEMVER}",
            ]
        ),
        encoding="utf-8",
    )
    elapsed = time.time() - t0
    print(f"  OK {spec.slug} tiles={len(tiles)} {elapsed:.1f}s", flush=True)
    return meta


def copy_marketing(pack_dir: Path, pack: PackSpec) -> None:
    mdir = pack_dir / "marketing"
    mdir.mkdir(parents=True, exist_ok=True)
    for i, name in enumerate(pack.hero_assets, start=1):
        src = SITE_ASSETS / name
        if src.is_file():
            shutil.copy2(src, mdir / f"hero_{i:02d}.jpg")
    # Gumroad cover = first hero
    first = mdir / "hero_01.jpg"
    if first.is_file():
        shutil.copy2(first, pack_dir / "GUMROAD_COVER.jpg")


def zip_pack(pack_dir: Path) -> Path:
    zpath = pack_dir.with_suffix(".zip")
    with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in pack_dir.rglob("*"):
            if path.is_file() and path.suffix != ".zip":
                zf.write(path, arcname=str(path.relative_to(pack_dir.parent)))
    return zpath


def build_pack(pack: PackSpec) -> dict:
    pack_dir = OUT / pack.slug
    if pack_dir.exists():
        shutil.rmtree(pack_dir)
    pack_dir.mkdir(parents=True)
    print(f"\n=== {pack.title} ===", flush=True)

    palettes: list[tuple[str, dict]] = []
    if "archviz" in pack.slug:
        palettes = [("zellige", PALETTE_ZELLIGE), ("brass", PALETTE_BRASS), ("concrete", PALETTE_CONCRETE)]
    elif "game" in pack.slug:
        palettes = [("sunset", PALETTE_SUNSET), ("concrete", PALETTE_CONCRETE)]
    else:
        palettes = [("concrete", PALETTE_CONCRETE)]

    assets_meta = []
    for spec in pack.assets:
        assets_meta.append(build_asset(pack_dir, spec, preview_palettes=palettes))

    copy_marketing(pack_dir, pack)
    _write_palette_docs(pack_dir, palettes)
    _write_license(pack_dir)
    _write_docs(pack_dir, pack)
    _write_gumroad_listing(pack_dir, pack)

    # Gumroad gallery slide: palette board from flagship asset
    flagship = pack.assets[1].slug if len(pack.assets) > 1 else pack.assets[0].slug
    prev_paths = [pack_dir / "assets" / flagship / "previews" / f"topdown_{n}.png" for n, _ in palettes]
    render_lookdev_board(
        pack_dir / "marketing" / "lookdev_board.png",
        prev_paths,
        [n for n, _ in palettes],
    )
    (pack_dir / "README.txt").write_text(
        "\n".join(
            [
                pack.title,
                f"${pack.price_usd} suggested",
                "",
                pack.tagline,
                "",
                "Included:",
                *[f"  - {x}" for x in pack.includes],
                "",
                "Start with docs/IMPORT_BLENDER.md or docs/IMPORT_UNREAL.md",
            ]
        ),
        encoding="utf-8",
    )
    zpath = zip_pack(pack_dir)
    print(f"  ZIP {zpath}", flush=True)
    return {"pack": pack.slug, "assets": assets_meta, "zip": str(zpath)}


def publish_shop_previews() -> None:
    """Copy best heroes + one preview per paid pack to site/assets/digital/."""
    SITE_DIGITAL.mkdir(parents=True, exist_ok=True)
    mapping = [
        (OUT / "01_archviz_floor_kit" / "marketing" / "hero_01.jpg", "archviz-floor-cover.jpg"),
        (OUT / "01_archviz_floor_kit" / "marketing" / "lookdev_board.png", "archviz-lookdev.png"),
        (OUT / "02_game_environment_kit" / "marketing" / "hero_01.jpg", "game-env-cover.jpg"),
        (OUT / "02_game_environment_kit" / "marketing" / "lookdev_board.png", "game-env-lookdev.png"),
        (OUT / "01_archviz_floor_kit" / "assets" / "floor_15m" / "previews" / "topdown_zellige.png", "archviz-floor-preview.png"),
        (OUT / "02_game_environment_kit" / "assets" / "corridor_24x8" / "previews" / "topdown_sunset.png", "game-env-preview.png"),
        (OUT / "00_comparison_sample" / "marketing" / "hero_01.jpg", "comparison-cover.jpg"),
    ]
    for src, dest in mapping:
        if src.is_file():
            shutil.copy2(src, SITE_DIGITAL / dest)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    results = [build_pack(p) for p in PACKS]
    publish_shop_previews()
    catalog = OUT / "STUDIO_CATALOG.md"
    lines = [
        "# Untiling studio packs (v2)",
        "",
        "Built for archviz and game environment pipelines. GLB + instance JSON + hero marketing art.",
        "",
    ]
    for pack in PACKS:
        lines.append(f"## {pack.title} (${pack.price_usd})")
        lines.append(pack.tagline)
        lines.append("")
        for spec in pack.assets:
            lines.append(f"- `{spec.slug}`: {spec.title}")
        lines.append(f"- ZIP: `{OUT / pack.slug}.zip`")
        lines.append("")
    catalog.write_text("\n".join(lines), encoding="utf-8")
    (OUT / "build_summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nDone -> {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
