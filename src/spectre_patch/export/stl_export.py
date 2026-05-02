"""Binary STL export — combined triangle soup or prototile + affine instances."""

from __future__ import annotations

import json
import struct

import numpy as np
import triangle as tr_lib

from spectre_patch.core.spectre_t11 import PROTOTILE_RING
from spectre_patch.geometry_affine import compose_world_affine
from spectre_patch.patch_engine import EmittedTile


def _triangulate_cap(xy: np.ndarray) -> np.ndarray:
    verts = xy.astype(np.float64, copy=False)
    n = len(verts)
    segs = np.array([[i, (i + 1) % n] for i in range(n)], dtype=np.int32)
    result = tr_lib.triangulate({"vertices": verts, "segments": segs}, "p")
    return np.asarray(result["triangles"], dtype=np.int32)


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


def prototype_prism_tris(thickness_mm: float) -> list[np.ndarray]:
    """Triangles (XYZ) for an extruded Tile(1,1) prism with thickness along local +Z."""

    xy = PROTOTILE_RING[:, :2].astype(np.float64, copy=False)
    z0, zt = 0.0, float(thickness_mm)
    tris_idx = _triangulate_cap(xy)
    faces: list[np.ndarray] = []

    for idx in tris_idx:
        a = xy[int(idx[0])]
        b = xy[int(idx[1])]
        c = xy[int(idx[2])]
        faces.append(np.array([[a[0], a[1], zt], [b[0], b[1], zt], [c[0], c[1], zt]], dtype=np.float64))
        faces.append(np.array([[a[0], a[1], z0], [c[0], c[1], z0], [b[0], b[1], z0]], dtype=np.float64))

    n_ring = len(xy)
    for i in range(n_ring):
        j = (i + 1) % n_ring
        p0 = np.array([xy[i, 0], xy[i, 1], z0], dtype=np.float64)
        p1 = np.array([xy[j, 0], xy[j, 1], z0], dtype=np.float64)
        p2 = np.array([xy[j, 0], xy[j, 1], zt], dtype=np.float64)
        p3 = np.array([xy[i, 0], xy[i, 1], zt], dtype=np.float64)
        faces.append(np.stack([p0, p1, p2]))
        faces.append(np.stack([p0, p2, p3]))
    return faces


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


def combined_stl_facets(
    tiles: list[EmittedTile],
    *,
    scale: float,
    rotation_deg: float,
    tx: float,
    ty: float,
    thickness_mm: float,
) -> list[bytes]:
    proto = prototype_prism_tris(thickness_mm)
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
