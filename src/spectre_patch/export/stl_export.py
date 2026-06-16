"""Binary STL export — combined triangle soup or prototile + affine instances."""

from __future__ import annotations

import json
import re
import struct
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import triangle as tr_lib
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry

from spectre_patch.core.spectre_t11 import PROTOTILE_RING
from spectre_patch.export.tile_styling import TileVisualStyle, export_ring_for_style
from spectre_patch.geometry_affine import compose_world_affine, similarity_client
from spectre_patch.patch_engine import EmittedTile


def _triangulate_cap(xy: np.ndarray) -> np.ndarray:
    verts = xy.astype(np.float64, copy=False)
    n = len(verts)
    segs = np.array([[i, (i + 1) % n] for i in range(n)], dtype=np.int32)
    result = tr_lib.triangulate({"vertices": verts, "segments": segs}, "p")
    return np.asarray(result["triangles"], dtype=np.int32)


def _iter_polygons(geom: BaseGeometry) -> list[Polygon]:
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


_FLAT_EXTRUSION_EPS = 1e-9


def _cap_tris_from_xy(xy: np.ndarray, z: float = 0.0) -> list[np.ndarray]:
    """Single planar cap (no side walls) for flat export / custom extrusion in DCC tools."""

    verts = xy[:, :2].astype(np.float64, copy=False)
    zf = float(z)
    tris_idx = _triangulate_cap(verts)
    faces: list[np.ndarray] = []
    for idx in tris_idx:
        a = verts[int(idx[0])]
        b = verts[int(idx[1])]
        c = verts[int(idx[2])]
        faces.append(
            np.array([[a[0], a[1], zf], [b[0], b[1], zf], [c[0], c[1], zf]], dtype=np.float64)
        )
    return faces


def _prism_tris_from_xy(xy: np.ndarray, thickness: float, *, z_base: float = 0.0) -> list[np.ndarray]:
    if float(thickness) <= _FLAT_EXTRUSION_EPS:
        return _cap_tris_from_xy(xy, z_base)
    verts = xy[:, :2].astype(np.float64, copy=False)
    z0, zt = float(z_base), float(z_base) + float(thickness)
    tris_idx = _triangulate_cap(verts)
    faces: list[np.ndarray] = []

    for idx in tris_idx:
        a = verts[int(idx[0])]
        b = verts[int(idx[1])]
        c = verts[int(idx[2])]
        faces.append(np.array([[a[0], a[1], zt], [b[0], b[1], zt], [c[0], c[1], zt]], dtype=np.float64))
        faces.append(np.array([[a[0], a[1], z0], [c[0], c[1], z0], [b[0], b[1], z0]], dtype=np.float64))

    n_ring = len(verts)
    for i in range(n_ring):
        j = (i + 1) % n_ring
        p0 = np.array([verts[i, 0], verts[i, 1], z0], dtype=np.float64)
        p1 = np.array([verts[j, 0], verts[j, 1], z0], dtype=np.float64)
        p2 = np.array([verts[j, 0], verts[j, 1], zt], dtype=np.float64)
        p3 = np.array([verts[i, 0], verts[i, 1], zt], dtype=np.float64)
        faces.append(np.stack([p0, p1, p2]))
        faces.append(np.stack([p0, p2, p3]))
    return faces


def _triangle_normal(v0: np.ndarray, v1: np.ndarray, v2: np.ndarray) -> tuple[float, float, float]:
    e1 = v1 - v0
    e2 = v2 - v0
    nrm = np.cross(e1, e2)
    ln = float(np.linalg.norm(nrm))
    if ln == 0.0:
        return 0.0, 0.0, 1.0
    nrm /= ln
    return float(nrm[0]), float(nrm[1]), float(nrm[2])


def _facet_record(norm: tuple[float, float, float], tri_xyz: np.ndarray) -> bytes:
    buf = bytearray()
    buf += struct.pack("<3f", *norm)
    for i in range(3):
        buf += struct.pack("<3f", float(tri_xyz[i, 0]), float(tri_xyz[i, 1]), float(tri_xyz[i, 2]))
    buf += struct.pack("<H", 0)
    return bytes(buf)


def prototype_prism_tris(
    thickness_mm: float,
    export_ring: np.ndarray | None = None,
) -> list[np.ndarray]:
    """Triangles (XYZ) for an extruded Tile(1,1) prism with thickness along local +Z."""

    ring = PROTOTILE_RING if export_ring is None else export_ring
    xy = ring[:, :2].astype(np.float64, copy=False)
    return _prism_tris_from_xy(xy, thickness_mm)


def _resolve_export_ring(visual_style: TileVisualStyle | None) -> np.ndarray:
    if visual_style is None:
        return PROTOTILE_RING
    if visual_style.side_style == "flat" and abs(visual_style.tile_edge_ratio - 1.0) < 1e-9:
        return PROTOTILE_RING
    return export_ring_for_style(visual_style)


def _planar_xy_scale(W: np.ndarray) -> float:
    return float(np.hypot(W[0, 0], W[1, 0]))


def _transform_triangle_xyz(tri: np.ndarray, W: np.ndarray) -> np.ndarray:
    sc_xy = _planar_xy_scale(W)
    out = np.zeros_like(tri)
    for i in range(3):
        x, y, z = tri[i]
        xp = W[0, 0] * x + W[0, 1] * y + W[0, 2]
        yp = W[1, 0] * x + W[1, 1] * y + W[1, 2]
        zp = sc_xy * z
        out[i] = (xp, yp, zp)
    return out


def write_binary_stl(path: str, facets: list[bytes], header_note: bytes | None = None) -> None:
    hdr = (header_note or b"spectre_patch_api")[:80].ljust(80, b"\0")
    with open(path, "wb") as f:
        f.write(hdr)
        f.write(struct.pack("<I", len(facets)))
        for face in facets:
            f.write(face)


def binary_stl_bytes(facets: list[bytes], header_note: bytes | None = None) -> bytes:
    hdr = (header_note or b"spectre_patch_api")[:80].ljust(80, b"\0")
    return hdr + struct.pack("<I", len(facets)) + b"".join(facets)


def combined_stl_facets(
    tiles: list[EmittedTile],
    *,
    scale: float,
    rotation_deg: float,
    tx: float,
    ty: float,
    thickness_mm: float,
    visual_style: TileVisualStyle | None = None,
) -> list[bytes]:
    export_ring = _resolve_export_ring(visual_style)
    proto = prototype_prism_tris(thickness_mm, export_ring)
    facets: list[bytes] = []
    for tile in tiles:
        gen6 = np.asarray(tile.affine_canonical_gen6, dtype=np.float64)
        W = compose_world_affine(
            canonical_gen6=gen6,
            scale=scale,
            rotation_deg=rotation_deg,
            tx=tx,
            ty=ty,
        )
        for tri in proto:
            world_tri = _transform_triangle_xyz(tri, W)
            nrm = _triangle_normal(world_tri[0], world_tri[1], world_tri[2])
            facets.append(_facet_record(nrm, world_tri))
    return facets


def _facets_from_tris(tris: list[np.ndarray]) -> list[bytes]:
    return [_facet_record(_triangle_normal(tri[0], tri[1], tri[2]), tri) for tri in tris]


def _world_xy_for_clip_geom(
    tile: EmittedTile,
    *,
    scale: float,
    rotation_deg: float,
    tx: float,
    ty: float,
    clip_geom: BaseGeometry | None = None,
) -> list[np.ndarray]:
    geom = clip_geom if clip_geom is not None else tile.clip_geom
    assert geom is not None
    client_world = similarity_client(scale, rotation_deg, tx, ty)
    rings: list[np.ndarray] = []
    for poly in _iter_polygons(geom):
        coords = np.asarray(poly.exterior.coords[:-1], dtype=np.float64)
        if len(coords) < 3:
            continue
        ones = np.ones((len(coords), 1), dtype=np.float64)
        hom = np.column_stack([coords, ones])
        mapped = hom @ client_world.T
        rings.append(mapped[:, :2])
    return rings


def _world_xy_rings(
    tile: EmittedTile,
    *,
    scale: float,
    rotation_deg: float,
    tx: float,
    ty: float,
    visual_style: TileVisualStyle | None = None,
    mask_geom: Any = None,
) -> list[np.ndarray]:
    export_ring = _resolve_export_ring(visual_style)
    use_styled = visual_style is not None and (
        visual_style.side_style != "flat" or abs(visual_style.tile_edge_ratio - 1.0) > 1e-9
    )
    if tile.clip_geom is not None:
        if use_styled and mask_geom is not None:
            from spectre_patch.export.svg_export import _styled_clip_geom_world

            client_world = similarity_client(scale, rotation_deg, tx, ty)
            styled = _styled_clip_geom_world(
                tile,
                export_ring=export_ring,
                mask_geom=mask_geom,
                client_world=client_world,
            )
            if styled is not None:
                return _world_xy_for_clip_geom(
                    tile,
                    scale=scale,
                    rotation_deg=rotation_deg,
                    tx=tx,
                    ty=ty,
                    clip_geom=styled,
                )
        return _world_xy_for_clip_geom(tile, scale=scale, rotation_deg=rotation_deg, tx=tx, ty=ty)

    ring = export_ring

    W = compose_world_affine(
        canonical_gen6=np.asarray(tile.affine_canonical_gen6, dtype=np.float64),
        scale=scale,
        rotation_deg=rotation_deg,
        tx=tx,
        ty=ty,
    )
    xy = ring[:, :2].astype(np.float64, copy=False)
    ones = np.ones((len(xy), 1), dtype=np.float64)
    hom = np.column_stack([xy, ones])
    mapped = hom @ W.T
    return [mapped[:, :2]]


def _segment_prism_tris(
    p0: np.ndarray,
    p1: np.ndarray,
    *,
    width: float,
    thickness: float,
    z_base: float = 0.0,
) -> list[np.ndarray]:
    vec = p1 - p0
    length = float(np.linalg.norm(vec))
    if length <= 1e-9:
        return []
    unit = vec / length
    normal = np.array([-unit[1], unit[0]], dtype=np.float64)
    half = max(float(width), 1e-9) * 0.5
    quad = np.array(
        [
            p0 + normal * half,
            p1 + normal * half,
            p1 - normal * half,
            p0 - normal * half,
        ],
        dtype=np.float64,
    )
    return _prism_tris_from_xy(quad, thickness, z_base=z_base)


def stroke_prism_tris_for_tiles(
    tiles: list[EmittedTile],
    *,
    scale: float,
    rotation_deg: float,
    tx: float,
    ty: float,
    thickness_mm: float,
    stroke_width: float | None = None,
    z_base: float = 0.0,
    visual_style: TileVisualStyle | None = None,
    mask_geom: Any = None,
) -> list[np.ndarray]:
    """Extruded boundary strokes for a patch, using the same clipped outlines as SVG."""

    width = float(stroke_width) if stroke_width is not None else max(0.035 * float(scale), 0.02)
    tris: list[np.ndarray] = []
    for tile in tiles:
        for ring in _world_xy_rings(
            tile,
            scale=scale,
            rotation_deg=rotation_deg,
            tx=tx,
            ty=ty,
            visual_style=visual_style,
            mask_geom=mask_geom,
        ):
            if len(ring) < 2:
                continue
            for i in range(len(ring)):
                p0 = ring[i]
                p1 = ring[(i + 1) % len(ring)]
                tris.extend(
                    _segment_prism_tris(
                        p0,
                        p1,
                        width=width,
                        thickness=thickness_mm,
                        z_base=z_base,
                    )
                )
    return tris


def stroke_stl_facets_for_tiles(
    tiles: list[EmittedTile],
    *,
    scale: float,
    rotation_deg: float,
    tx: float,
    ty: float,
    thickness_mm: float,
    stroke_width: float | None = None,
    visual_style: TileVisualStyle | None = None,
    mask_geom: Any = None,
) -> list[bytes]:
    return _facets_from_tris(
        stroke_prism_tris_for_tiles(
            tiles,
            scale=scale,
            rotation_deg=rotation_deg,
            tx=tx,
            ty=ty,
            thickness_mm=thickness_mm,
            stroke_width=stroke_width,
            visual_style=visual_style,
            mask_geom=mask_geom,
        )
    )


def tile_prism_tris(
    tile: EmittedTile,
    *,
    scale: float,
    rotation_deg: float,
    tx: float,
    ty: float,
    thickness_mm: float,
    visual_style: TileVisualStyle | None = None,
    mask_geom: Any = None,
) -> list[np.ndarray]:
    """Triangles for one independent tile object, honoring clipped edge geometry."""

    if tile.clip_geom is not None:
        tris: list[np.ndarray] = []
        thickness = float(thickness_mm) * float(tile.scale_world) * float(scale)
        for xy in _world_xy_rings(
            tile,
            scale=scale,
            rotation_deg=rotation_deg,
            tx=tx,
            ty=ty,
            visual_style=visual_style,
            mask_geom=mask_geom,
        ):
            tris.extend(_prism_tris_from_xy(xy, thickness))
        return tris

    gen6 = np.asarray(tile.affine_canonical_gen6, dtype=np.float64)
    W = compose_world_affine(
        canonical_gen6=gen6,
        scale=scale,
        rotation_deg=rotation_deg,
        tx=tx,
        ty=ty,
    )
    export_ring = _resolve_export_ring(visual_style)
    return [
        _transform_triangle_xyz(tri, W) for tri in prototype_prism_tris(thickness_mm, export_ring)
    ]


def tile_stl_bytes(
    tile: EmittedTile,
    *,
    scale: float,
    rotation_deg: float,
    tx: float,
    ty: float,
    thickness_mm: float,
    visual_style: TileVisualStyle | None = None,
    mask_geom: Any = None,
) -> bytes:
    tris = tile_prism_tris(
        tile,
        scale=scale,
        rotation_deg=rotation_deg,
        tx=tx,
        ty=ty,
        thickness_mm=thickness_mm,
        visual_style=visual_style,
        mask_geom=mask_geom,
    )
    return binary_stl_bytes(_facets_from_tris(tris), header_note=tile.tile_id.encode("utf-8"))


def tile_obj_bytes(
    tile: EmittedTile,
    *,
    scale: float,
    rotation_deg: float,
    tx: float,
    ty: float,
    thickness_mm: float,
    visual_style: TileVisualStyle | None = None,
    mask_geom: Any = None,
) -> bytes:
    tris = tile_prism_tris(
        tile,
        scale=scale,
        rotation_deg=rotation_deg,
        tx=tx,
        ty=ty,
        thickness_mm=thickness_mm,
        visual_style=visual_style,
        mask_geom=mask_geom,
    )
    lines = [
        "# Generated by spectre_patch_api",
        f"o {safe_object_name(tile.tile_id)}",
        f"# tile_id {tile.tile_id}",
        f"# tile_label {tile.tile_label}",
    ]
    vertex_index = 1
    for tri in tris:
        for x, y, z in tri:
            lines.append(f"v {float(x):.9g} {float(y):.9g} {float(z):.9g}")
        lines.append(f"f {vertex_index} {vertex_index + 1} {vertex_index + 2}")
        vertex_index += 3
    return ("\n".join(lines) + "\n").encode("utf-8")


def safe_object_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    return cleaned[:96] or "tile"


def independent_tiles_manifest(tiles: list[EmittedTile], *, file_extension: str) -> bytes:
    doc = {
        "export_kind": f"independent_tile_{file_extension.lower()}_zip",
        "notes": "Each file is a separate movable tile object. Boundary tiles may be clipped to the requested mask.",
        "tiles": [
            {
                "id": tile.tile_id,
                "label": tile.tile_label,
                "filename": f"tiles/{i:06d}_{safe_object_name(tile.tile_id)}.{file_extension.lower()}",
                "clipped": tile.clip_geom is not None,
            }
            for i, tile in enumerate(tiles)
        ],
    }
    return json.dumps(doc, sort_keys=True, indent=2).encode("utf-8")


def write_independent_tiles_zip(
    path: Path | str,
    tiles: list[EmittedTile],
    *,
    format_name: str,
    scale: float,
    rotation_deg: float,
    tx: float,
    ty: float,
    thickness_mm: float,
    visual_style: TileVisualStyle | None = None,
    mask_geom: Any = None,
) -> None:
    fmt = format_name.lower()
    if fmt not in {"stl", "obj"}:
        raise ValueError("format_name must be 'stl' or 'obj'")

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", independent_tiles_manifest(tiles, file_extension=fmt))
        for i, tile in enumerate(tiles):
            filename = f"tiles/{i:06d}_{safe_object_name(tile.tile_id)}.{fmt}"
            if fmt == "stl":
                payload = tile_stl_bytes(
                    tile,
                    scale=scale,
                    rotation_deg=rotation_deg,
                    tx=tx,
                    ty=ty,
                    thickness_mm=thickness_mm,
                    visual_style=visual_style,
                    mask_geom=mask_geom,
                )
            else:
                payload = tile_obj_bytes(
                    tile,
                    scale=scale,
                    rotation_deg=rotation_deg,
                    tx=tx,
                    ty=ty,
                    thickness_mm=thickness_mm,
                    visual_style=visual_style,
                    mask_geom=mask_geom,
                )
            zf.writestr(filename, payload)


def write_prototype_stl(path: str, thickness_mm: float) -> None:
    facets: list[bytes] = []
    for tri in prototype_prism_tris(thickness_mm):
        nrm = _triangle_normal(tri[0], tri[1], tri[2])
        facets.append(_facet_record(nrm, tri))
    write_binary_stl(path, facets)


def affine4_row_lists_for_matrix(
    tile: EmittedTile, *, scale: float, rotation_deg: float, tx: float, ty: float
) -> list[list[float]]:
    """Return four length-4 rows (XY plane + isolated Z-scale) suitable for Blender `Matrix(rows)`."""

    W = compose_world_affine(
        canonical_gen6=np.asarray(tile.affine_canonical_gen6, dtype=np.float64),
        scale=scale,
        rotation_deg=rotation_deg,
        tx=tx,
        ty=ty,
    )
    sx = float(np.hypot(W[0, 0], W[1, 0]))
    return [
        [float(W[0, 0]), float(W[0, 1]), 0.0, float(W[0, 2])],
        [float(W[1, 0]), float(W[1, 1]), 0.0, float(W[1, 2])],
        [0.0, 0.0, sx, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def instancing_manifest_bytes(
    tiles: list[EmittedTile],
    *,
    patch_version: str,
    tile_family: str,
    seed: str | None,
    scale: float,
    rotation_deg: float,
    tx: float,
    ty: float,
) -> bytes:
    doc = {
        "patch_version": patch_version,
        "tile_family": tile_family,
        "seed": seed,
        "prototile_notes": (
            "Use write_prototype_stl for a single prism of Tile(1,1); "
            "apply each instances[*].affine4_row_lists via Blender mathutils.Matrix(rows)."
        ),
        "instances": [
            {
                "id": t.tile_id,
                "affine4_row_lists": affine4_row_lists_for_matrix(
                    t,
                    scale=scale,
                    rotation_deg=rotation_deg,
                    tx=tx,
                    ty=ty,
                ),
            }
            for t in tiles
        ],
    }
    return json.dumps(doc, sort_keys=True, indent=2).encode("utf-8")
