"""Emit compact instanced SVG for arbitrary tile budgets (with optional gzip)."""

from __future__ import annotations

import gzip
import json
import xml.sax.saxutils as saxutils
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry

from spectre_patch.core.spectre_t11 import PROTOTILE_RING, apply_affine_to_points
from spectre_patch.export.svg_utils import deterministic_palette, svg_matrix_tuple_from_world6
from spectre_patch.export.tile_styling import (
    TileVisualStyle,
    export_ring_for_style,
    ring_to_polygon,
    ring_to_svg_path_d,
)
from spectre_patch.geometry_affine import compose_world_affine, similarity_client
from spectre_patch.patch_engine import EmittedTile


def meta_comment(meta: dict) -> str:
    blob = json.dumps(meta, separators=(",", ":"), sort_keys=True)
    return blob.replace("--", "\\u002d\\u002d")


@dataclass(frozen=True, slots=True)
class SvgRenderOpts:
    fill: str | None = "#cdd6ea"
    stroke: str | None = "#171b38"
    stroke_width: float = 0.04
    opacity: float = 1.0
    deterministic_colors: bool = False
    background: str | None = None
    flip_y: bool = True
    margin: float = 1.0
    pixel_target: int = 1200
    compact: bool = False
    """When True, drop per-tile <g id> wrappers and inherit fill/stroke from a
    root <g>. Cuts file size dramatically (the 14-vertex prototype is shared via
    <use>; only a single matrix is emitted per tile)."""
    coord_precision: int = 6
    """Decimal precision for matrix entries. 6 is plenty for canonical units."""
    visual_style: TileVisualStyle | None = None
    palette_by_label: dict[str, dict[str, str | float | bool]] | None = None
    mask_geom: Any | None = None


def _sanitize_xml_id(tile_id: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "_-:.[]" else "_" for ch in tile_id)


def _export_ring(opts: SvgRenderOpts) -> np.ndarray:
    if opts.visual_style is not None and (
        opts.visual_style.side_style != "flat"
        or abs(opts.visual_style.tile_edge_ratio - 1.0) > 1e-9
    ):
        return export_ring_for_style(opts.visual_style)
    return PROTOTILE_RING


def _styled_clip_geom_world(
    tile: EmittedTile,
    *,
    export_ring: np.ndarray,
    mask_geom: Any,
    client_world: np.ndarray,
) -> BaseGeometry | None:
    """Re-clip a styled prototile against the mask for export (tile set unchanged)."""

    if mask_geom is None:
        return tile.clip_geom
    gen6 = np.asarray(tile.affine_canonical_gen6, dtype=np.float64)
    xy = apply_affine_to_points(gen6, export_ring)
    styled = ring_to_polygon(xy)
    if not styled.is_valid:
        styled = styled.buffer(0)
    clipped = styled.intersection(mask_geom)
    if clipped.is_empty:
        return None
    return clipped


def _tile_style_attrs(
    tile: EmittedTile,
    opts: SvgRenderOpts,
    *,
    default_fill: str | None,
    default_stroke: str | None,
) -> tuple[str | None, str | None, float]:
    opacity = float(opts.opacity)
    fill_val = default_fill
    stroke_val = default_stroke
    if opts.palette_by_label:
        spec = opts.palette_by_label.get(tile.tile_label) or opts.palette_by_label.get("*")
        if spec:
            if bool(spec.get("transparent")):
                fill_val = "none"
            elif "fill" in spec and spec["fill"] is not None:
                fill_val = str(spec["fill"])
            if "stroke" in spec and spec["stroke"] is not None:
                stroke_val = str(spec["stroke"])
            if "opacity" in spec:
                opacity = float(spec["opacity"])
    elif opts.deterministic_colors:
        fg, stk = deterministic_palette(tile.tile_id)
        fill_val = fg
        if opts.stroke is not None:
            stroke_val = stk
    return fill_val, stroke_val, opacity


def world_affine_rowmajor(
    tile: EmittedTile, *, scale: float, rotation_deg: float, tx: float, ty: float
) -> tuple[float, float, float, float, float, float]:
    gen6 = np.asarray(tile.affine_canonical_gen6, dtype=np.float64)
    W = compose_world_affine(
        canonical_gen6=gen6,
        scale=scale,
        rotation_deg=rotation_deg,
        tx=tx,
        ty=ty,
    )
    return (
        float(W[0, 0]),
        float(W[0, 1]),
        float(W[0, 2]),
        float(W[1, 0]),
        float(W[1, 1]),
        float(W[1, 2]),
    )


def _iter_polygons(geom: BaseGeometry) -> list[Polygon]:
    """Return polygonal components from a Shapely geometry."""

    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return [poly for poly in geom.geoms if not poly.is_empty]
    if isinstance(geom, GeometryCollection):
        polys: list[Polygon] = []
        for child in geom.geoms:
            polys.extend(_iter_polygons(child))
        return polys
    return []


def _polygon_path_d_world(geom: BaseGeometry, world: np.ndarray) -> str:
    """Map canonical clipped geometry into a world XY SVG compound path."""

    def world_xy(x: float, y: float) -> tuple[float, float]:
        return (
            float(world[0, 0] * x + world[0, 1] * y + world[0, 2]),
            float(world[1, 0] * x + world[1, 1] * y + world[1, 2]),
        )

    cmds: list[str] = []
    for poly in _iter_polygons(geom):
        rings = [poly.exterior, *poly.interiors]
        for ring in rings:
            coords = list(ring.coords)
            if len(coords) < 3:
                continue
            for i, (x, y) in enumerate(coords[:-1]):
                wx, wy = world_xy(x, y)
                cmds.append(f"{'M' if i == 0 else 'L'}{wx:.8g} {wy:.8g}")
            cmds.append("Z")
    return " ".join(cmds)


def svg_document(
    tiles: list[EmittedTile],
    *,
    patch_meta: dict,
    scale: float,
    rotation_deg: float,
    tx: float,
    ty: float,
    opts: SvgRenderOpts | None = None,
) -> str:
    """Emit deterministic SVG.

    Tiles whose `clip_geom` is set (retention=clip) are rendered as raw `<path d=...>`
    elements expressed in world coordinates, so no `<use href="#proto">` reference is
    used and the boundary is exactly the canonical mask intersection.
    """

    opts = opts or SvgRenderOpts()
    export_ring = _export_ring(opts)
    dpath = saxutils.quoteattr(ring_to_svg_path_d(export_ring)).strip("\"'")

    bbox = _world_bbox(tiles, scale=scale, rotation_deg=rotation_deg, tx=tx, ty=ty)
    minx, miny, maxx, maxy = bbox
    minx -= opts.margin
    miny -= opts.margin
    maxx += opts.margin
    maxy += opts.margin
    width = max(maxx - minx, 1e-9)
    height = max(maxy - miny, 1e-9)
    aspect = width / height
    if aspect >= 1:
        out_w = opts.pixel_target
        out_h = max(1, int(round(opts.pixel_target / aspect)))
    else:
        out_h = opts.pixel_target
        out_w = max(1, int(round(opts.pixel_target * aspect)))

    parts: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            '<svg xmlns="http://www.w3.org/2000/svg"'
            ' xmlns:xlink="http://www.w3.org/1999/xlink"'
            f' viewBox="{minx:.6g} {miny:.6g} {width:.6g} {height:.6g}"'
            f' width="{out_w}" height="{out_h}"'
            ' version="1.1">'
        ),
        f'<!--spectre-patch-meta {_sanitize_xml_comment(meta_comment(patch_meta))}-->',
    ]
    if opts.background:
        parts.append(
            f'<rect x="{minx:.6g}" y="{miny:.6g}" width="{width:.6g}" height="{height:.6g}"'
            f' fill="{saxutils.escape(opts.background)}"/>'
        )
    parts.append("<defs>")
    parts.append(f'<path id="proto" d="{dpath}" fill-rule="evenodd"/>')
    parts.append("</defs>")

    # Optional vertical flip so canonical math y-up displays naturally in SVG y-down viewers.
    if opts.flip_y:
        cy = (miny + maxy) / 2.0
        parts.append(f'<g transform="matrix(1 0 0 -1 0 {2.0 * cy:.8g})">')

    # Compact mode: emit a single root <g> carrying default fill/stroke/opacity so each
    # tile only needs `<use href="#proto" transform="matrix(...)"/>`.
    if opts.compact:
        root_attrs: list[str] = []
        if opts.fill is not None:
            root_attrs.append(f'fill="{saxutils.escape(opts.fill)}"')
        if opts.stroke is not None:
            root_attrs.append(f'stroke="{saxutils.escape(opts.stroke)}"')
            root_attrs.append(f'stroke-width="{opts.stroke_width:g}"')
            root_attrs.append('stroke-linejoin="round"')
        else:
            root_attrs.append('stroke="none"')
        if opts.opacity != 1.0:
            root_attrs.append(f'opacity="{opts.opacity:g}"')
        parts.append("<g " + " ".join(root_attrs) + ">")

    stroke_w = opts.stroke_width if opts.stroke else 0.0
    client_world = similarity_client(scale, rotation_deg, tx, ty)
    prec = max(2, int(opts.coord_precision))
    for tile in tiles:
        if opts.compact:
            fill_val, stroke_val, opacity = _tile_style_attrs(
                tile, opts, default_fill=opts.fill, default_stroke=opts.stroke
            )
            tile_fill_attr = ""
            if fill_val and fill_val != "none":
                tile_fill_attr = f' fill="{saxutils.escape(fill_val)}"'
            stroke_attr = ""
            if stroke_val:
                tile_fill_attr += (
                    f' stroke="{saxutils.escape(stroke_val)}" stroke-width="{stroke_w:g}"'
                    ' stroke-linejoin="round"'
                )
            if opacity != 1.0:
                tile_fill_attr += f' opacity="{opacity:g}"'

            if tile.clip_geom is not None:
                clip_src = _styled_clip_geom_world(
                    tile,
                    export_ring=export_ring,
                    mask_geom=opts.mask_geom,
                    client_world=client_world,
                )
                d_attr = _polygon_path_d_world(clip_src or tile.clip_geom, client_world)
                if not d_attr:
                    continue
                parts.append(f'<path d="{d_attr}" fill-rule="evenodd"{tile_fill_attr}/>')
            else:
                a, b, t1, c, d_, t2 = world_affine_rowmajor(
                    tile, scale=scale, rotation_deg=rotation_deg, tx=tx, ty=ty
                )
                mtx = " ".join(f"{float(v):.{prec}g}" for v in (a, c, b, d_, t1, t2))
                parts.append(
                    f'<use href="#proto"{tile_fill_attr} transform="matrix({mtx})"/>'
                )
            continue

        fill_val, stroke_val, opacity = _tile_style_attrs(
            tile, opts, default_fill=opts.fill, default_stroke=opts.stroke
        )
        fill_val = fill_val if fill_val is not None else "none"

        if stroke_val is None:
            stroke_attr = ""
        else:
            stroke_attr = f' stroke="{saxutils.escape(stroke_val)}" stroke-width="{stroke_w:g}"'

        gid = saxutils.escape(_sanitize_xml_id(tile.tile_id))
        common = (
            f' fill="{saxutils.escape(fill_val)}"'
            f' opacity="{opacity:g}"' + stroke_attr
        )

        if tile.clip_geom is not None:
            clip_src = _styled_clip_geom_world(
                tile,
                export_ring=export_ring,
                mask_geom=opts.mask_geom,
                client_world=client_world,
            )
            d_attr = _polygon_path_d_world(clip_src or tile.clip_geom, client_world)
            if not d_attr:
                continue
            parts.append(
                f'<g id="{gid}"><path d="{d_attr}" fill-rule="evenodd"' + common + "/></g>"
            )
        else:
            a, b, t1, c, d_, t2 = world_affine_rowmajor(
                tile, scale=scale, rotation_deg=rotation_deg, tx=tx, ty=ty
            )
            sm = svg_matrix_tuple_from_world6(a, b, t1, c, d_, t2)
            mtx = " ".join(sm)
            xf = ' transform="matrix(' + mtx + ')"'
            parts.append(
                f'<g id="{gid}">'
                '<use xlink:href="#proto" href="#proto"'
                + common
                + xf
                + "/></g>"
            )

    if opts.compact:
        parts.append("</g>")
    if opts.flip_y:
        parts.append("</g>")
    parts.append("</svg>")
    return "".join(parts)


def _sanitize_xml_comment(text: str) -> str:
    return "".join(ch if 32 <= ord(ch) < 0x110000 and ch != "--" else " " for ch in text)


def _world_bbox(
    tiles: list[EmittedTile],
    *,
    scale: float,
    rotation_deg: float,
    tx: float,
    ty: float,
) -> tuple[float, float, float, float]:
    """Compute world-space (post-client-similarity) bbox from prototile rings + clip geoms."""

    if not tiles:
        return (-1.0, -1.0, 1.0, 1.0)

    minx = miny = float("inf")
    maxx = maxy = float("-inf")
    for tile in tiles:
        if tile.clip_geom is not None:
            cli = similarity_client(scale, rotation_deg, tx, ty)
            coords: list[tuple[float, float]] = []
            for poly in _iter_polygons(tile.clip_geom):
                coords.extend((float(x), float(y)) for x, y in poly.exterior.coords)
            if not coords:
                continue
            xs, ys = np.asarray(coords, dtype=np.float64).T
            xs = np.asarray(xs, dtype=np.float64)
            ys = np.asarray(ys, dtype=np.float64)
            wx = cli[0, 0] * xs + cli[0, 1] * ys + cli[0, 2]
            wy = cli[1, 0] * xs + cli[1, 1] * ys + cli[1, 2]
        else:
            gen6 = np.asarray(tile.affine_canonical_gen6, dtype=np.float64)
            W = compose_world_affine(
                canonical_gen6=gen6,
                scale=scale,
                rotation_deg=rotation_deg,
                tx=tx,
                ty=ty,
            )
            ring = PROTOTILE_RING
            wx = W[0, 0] * ring[:, 0] + W[0, 1] * ring[:, 1] + W[0, 2]
            wy = W[1, 0] * ring[:, 0] + W[1, 1] * ring[:, 1] + W[1, 2]
        minx = min(minx, float(wx.min()))
        maxx = max(maxx, float(wx.max()))
        miny = min(miny, float(wy.min()))
        maxy = max(maxy, float(wy.max()))
    return minx, miny, maxx, maxy


def write_svg_or_svgz(path: Path | str, svg_text: str) -> int:
    """Persist `svg_text` to disk; gzip transparently when the path ends with `.svgz`.

    Browsers and Adobe products read `.svgz` natively (gzip transport). The
    on-the-wire format is identical to plain SVG, so the saving is pure I/O
    plus client decompression. Tier-1 cores compress 8-12x because the bulk of
    a compact instanced patch is `<use ... matrix(...)/>` repetitions.

    Returns the on-disk byte count (post-compression for `.svgz`).
    """

    p = Path(path)
    payload = svg_text.encode("utf-8")
    if p.suffix.lower() == ".svgz":
        with gzip.open(p, "wb", compresslevel=6) as fh:
            fh.write(payload)
    else:
        p.write_bytes(payload)
    return p.stat().st_size

