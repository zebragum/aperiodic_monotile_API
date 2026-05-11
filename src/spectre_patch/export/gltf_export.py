"""glTF 2.0 GLB exporter.

Produces a single binary GLB containing explicit patch geometry. We avoid relying on
``EXT_mesh_gpu_instancing`` for the launch export because many general-purpose viewers
display only the prototype mesh when they do not implement that extension.

Soft-fails with a clear ImportError when `pygltflib` is absent.
"""

from __future__ import annotations

import struct
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np

from spectre_patch.core.spectre_t11 import PROTOTILE_RING
from spectre_patch.export.stl_export import stroke_prism_tris_for_tiles, tile_prism_tris, _triangulate_cap
from spectre_patch.geometry_affine import compose_world_affine
from spectre_patch.patch_engine import EmittedTile


def _quaternion_from_yaw(theta_rad: float) -> tuple[float, float, float, float]:
    """[x, y, z, w] for rotation about +Z by theta_rad."""

    h = float(theta_rad) * 0.5
    return (0.0, 0.0, float(np.sin(h)), float(np.cos(h)))


def _decompose_world_to_trs(W: np.ndarray) -> tuple[np.ndarray, tuple[float, float, float, float], np.ndarray]:
    a, b = float(W[0, 0]), float(W[0, 1])
    c = float(W[1, 0])
    tx, ty = float(W[0, 2]), float(W[1, 2])
    sx = float(np.hypot(a, c))
    sy = float(np.hypot(b, float(W[1, 1])))
    s_uniform = float((sx + sy) / 2.0)
    theta = float(np.arctan2(c, a))
    return (
        np.array([tx, ty, 0.0], dtype=np.float32),
        _quaternion_from_yaw(theta),
        np.array([s_uniform, s_uniform, s_uniform], dtype=np.float32),
    )


def _prism_mesh_arrays(thickness_mm: float) -> tuple[np.ndarray, np.ndarray]:
    """Return (positions float32 [N,3], indices uint32 [M*3])."""

    xy = PROTOTILE_RING[:, :2].astype(np.float64, copy=False)
    z0, zt = 0.0, float(thickness_mm)
    cap_idx = _triangulate_cap(xy)

    bottom = np.column_stack([xy, np.full(len(xy), z0, dtype=np.float64)])
    top = np.column_stack([xy, np.full(len(xy), zt, dtype=np.float64)])
    positions = np.vstack([bottom, top]).astype(np.float32, copy=False)

    n = len(xy)
    indices: list[int] = []

    for tri in cap_idx:
        a, b, c = int(tri[0]), int(tri[1]), int(tri[2])
        indices += [a, c, b]
        indices += [n + a, n + b, n + c]

    for i in range(n):
        j = (i + 1) % n
        b0, b1 = i, j
        t0, t1 = n + i, n + j
        indices += [b0, b1, t1]
        indices += [b0, t1, t0]

    return positions, np.asarray(indices, dtype=np.uint32)


def _pack_buffer(views: list[bytes]) -> tuple[bytes, list[tuple[int, int]]]:
    """Concatenate buffer views, padding each to 4-byte alignment; returns (blob, [(offset,length)...])."""

    out = bytearray()
    offsets: list[tuple[int, int]] = []
    for v in views:
        pad = (-len(out)) & 3
        out.extend(b"\x00" * pad)
        offsets.append((len(out), len(v)))
        out.extend(v)
    return bytes(out), offsets


def _tris_to_position_index_arrays(tris: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    if not tris:
        return np.zeros((0, 3), dtype=np.float32), np.zeros((0,), dtype=np.uint32)
    positions = np.asarray(tris, dtype=np.float32).reshape((-1, 3))
    indices = np.arange(len(positions), dtype=np.uint32)
    return positions, indices


def _material(pygltflib, *, color: list[float], name: str):
    return pygltflib.Material(
        name=name,
        pbrMetallicRoughness=pygltflib.PbrMetallicRoughness(
            baseColorFactor=color,
            metallicFactor=0.0,
            roughnessFactor=0.75,
        ),
    )


def write_glb_instanced(
    path: Path | str,
    tiles: list[EmittedTile],
    *,
    scale: float,
    rotation_deg: float,
    tx: float,
    ty: float,
    thickness_mm: float,
    patch_meta: dict[str, Any] | None = None,
) -> None:
    """Write `<path>` as a normal GLB containing the full clipped tiled patch."""

    try:
        import pygltflib  # type: ignore[import-not-found]  # noqa: PLC0415
    except Exception as e:
        raise RuntimeError(
            "glTF export disabled — install `pip install spectre-patch-api[gltf]` (pygltflib)."
        ) from e

    fill_tris: list[np.ndarray] = []
    for tile in tiles:
        fill_tris.extend(
            tile_prism_tris(
                tile,
                scale=scale,
                rotation_deg=rotation_deg,
                tx=tx,
                ty=ty,
                thickness_mm=thickness_mm,
            )
        )
    stroke_tris = stroke_prism_tris_for_tiles(
        tiles,
        scale=scale,
        rotation_deg=rotation_deg,
        tx=tx,
        ty=ty,
        thickness_mm=max(float(thickness_mm) * 0.08, 0.04),
        z_base=float(thickness_mm) * float(scale) * 1.02,
    )

    fill_pos, fill_idx = _tris_to_position_index_arrays(fill_tris)
    stroke_pos, stroke_idx = _tris_to_position_index_arrays(stroke_tris)

    views = [
        fill_pos.tobytes(),
        fill_idx.tobytes(),
        stroke_pos.tobytes(),
        stroke_idx.tobytes(),
    ]
    blob, offs = _pack_buffer(views)
    (fill_pos_off, fill_pos_len), (fill_idx_off, fill_idx_len), (stroke_pos_off, stroke_pos_len), (
        stroke_idx_off,
        stroke_idx_len,
    ) = offs

    all_pos = np.vstack([arr for arr in (fill_pos, stroke_pos) if len(arr)])
    pos_min = all_pos.min(axis=0).astype(np.float32).tolist()
    pos_max = all_pos.max(axis=0).astype(np.float32).tolist()

    gltf = pygltflib.GLTF2()
    gltf.scene = 0
    gltf.scenes = [pygltflib.Scene(nodes=[0])]

    gltf.buffers = [pygltflib.Buffer(byteLength=len(blob))]

    bv_fill_pos = pygltflib.BufferView(
        buffer=0, byteOffset=fill_pos_off, byteLength=fill_pos_len, target=pygltflib.ARRAY_BUFFER
    )
    bv_fill_idx = pygltflib.BufferView(
        buffer=0, byteOffset=fill_idx_off, byteLength=fill_idx_len, target=pygltflib.ELEMENT_ARRAY_BUFFER
    )
    bv_stroke_pos = pygltflib.BufferView(
        buffer=0, byteOffset=stroke_pos_off, byteLength=stroke_pos_len, target=pygltflib.ARRAY_BUFFER
    )
    bv_stroke_idx = pygltflib.BufferView(
        buffer=0, byteOffset=stroke_idx_off, byteLength=stroke_idx_len, target=pygltflib.ELEMENT_ARRAY_BUFFER
    )
    gltf.bufferViews = [bv_fill_pos, bv_fill_idx, bv_stroke_pos, bv_stroke_idx]

    acc_fill_pos = pygltflib.Accessor(
        bufferView=0,
        componentType=pygltflib.FLOAT,
        count=len(fill_pos),
        type=pygltflib.VEC3,
        min=pos_min,
        max=pos_max,
    )
    acc_fill_idx = pygltflib.Accessor(
        bufferView=1,
        componentType=pygltflib.UNSIGNED_INT,
        count=len(fill_idx),
        type=pygltflib.SCALAR,
    )
    acc_stroke_pos = pygltflib.Accessor(
        bufferView=2,
        componentType=pygltflib.FLOAT,
        count=len(stroke_pos),
        type=pygltflib.VEC3,
        min=pos_min,
        max=pos_max,
    )
    acc_stroke_idx = pygltflib.Accessor(
        bufferView=3,
        componentType=pygltflib.UNSIGNED_INT,
        count=len(stroke_idx),
        type=pygltflib.SCALAR,
    )
    gltf.accessors = [acc_fill_pos, acc_fill_idx, acc_stroke_pos, acc_stroke_idx]

    fill_primitive = pygltflib.Primitive(
        attributes=pygltflib.Attributes(POSITION=0),
        indices=1,
        mode=pygltflib.TRIANGLES,
        material=0,
    )
    stroke_primitive = pygltflib.Primitive(
        attributes=pygltflib.Attributes(POSITION=2),
        indices=3,
        mode=pygltflib.TRIANGLES,
        material=1,
    )
    gltf.meshes = [pygltflib.Mesh(primitives=[fill_primitive, stroke_primitive], name="spectre_patch_mesh")]
    gltf.materials = [
        _material(pygltflib, color=[0.72, 0.78, 0.90, 1.0], name="tile_fill"),
        _material(pygltflib, color=[0.02, 0.03, 0.08, 1.0], name="tile_strokes"),
    ]

    node = pygltflib.Node(mesh=0, name="spectre_patch")
    gltf.nodes = [node]

    if patch_meta:
        meta = {**patch_meta, "glb_export": "explicit_clipped_patch_mesh_with_strokes", "tile_count": len(tiles)}
        gltf.asset = pygltflib.Asset(version="2.0", generator="spectre_patch_api", extras=meta)
    else:
        gltf.asset = pygltflib.Asset(version="2.0", generator="spectre_patch_api")

    gltf.set_binary_blob(blob)
    gltf.save_binary(str(path))
