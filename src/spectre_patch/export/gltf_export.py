"""glTF 2.0 GLB exporter with EXT_mesh_gpu_instancing.

Produces a single binary GLB containing one extruded prototile mesh (Tile(1,1) prism)
and one node carrying per-instance TRANSLATION/ROTATION/SCALE attributes, so receivers
that support `EXT_mesh_gpu_instancing` (Three.js, Babylon, glTF-Transform) render the
whole patch as GPU instances.

Soft-fails with a clear ImportError when `pygltflib` is absent.
"""

from __future__ import annotations

import struct
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np

from spectre_patch.core.spectre_t11 import PROTOTILE_RING
from spectre_patch.export.stl_export import _triangulate_cap
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
    """Write `<path>` as a single GLB with EXT_mesh_gpu_instancing instances of one prism."""

    try:
        import pygltflib  # type: ignore[import-not-found]  # noqa: PLC0415
    except Exception as e:
        raise RuntimeError(
            "glTF export disabled — install `pip install spectre-patch-api[gltf]` (pygltflib)."
        ) from e

    pos, idx = _prism_mesh_arrays(thickness_mm)

    n = len(tiles)
    translations = np.zeros((n, 3), dtype=np.float32)
    rotations = np.zeros((n, 4), dtype=np.float32)
    scales = np.zeros((n, 3), dtype=np.float32)
    for i, t in enumerate(tiles):
        gen6 = np.asarray(t.affine_canonical_gen6, dtype=np.float64)
        W = compose_world_affine(
            canonical_gen6=gen6,
            scale=scale,
            rotation_deg=rotation_deg,
            tx=tx,
            ty=ty,
        )
        T, R, S = _decompose_world_to_trs(W)
        translations[i] = T
        rotations[i] = R
        scales[i] = S

    pos_bytes = pos.tobytes()
    idx_bytes = idx.tobytes()
    t_bytes = translations.tobytes()
    r_bytes = rotations.tobytes()
    s_bytes = scales.tobytes()

    blob, offs = _pack_buffer([pos_bytes, idx_bytes, t_bytes, r_bytes, s_bytes])
    (pos_off, pos_len), (idx_off, idx_len), (t_off, t_len), (r_off, r_len), (s_off, s_len) = offs

    pos_min = pos.min(axis=0).astype(np.float32).tolist()
    pos_max = pos.max(axis=0).astype(np.float32).tolist()

    gltf = pygltflib.GLTF2()
    gltf.scene = 0
    gltf.scenes = [pygltflib.Scene(nodes=[0])]

    gltf.buffers = [pygltflib.Buffer(byteLength=len(blob))]

    bv_pos = pygltflib.BufferView(
        buffer=0, byteOffset=pos_off, byteLength=pos_len, target=pygltflib.ARRAY_BUFFER
    )
    bv_idx = pygltflib.BufferView(
        buffer=0, byteOffset=idx_off, byteLength=idx_len, target=pygltflib.ELEMENT_ARRAY_BUFFER
    )
    bv_tr = pygltflib.BufferView(buffer=0, byteOffset=t_off, byteLength=t_len)
    bv_rt = pygltflib.BufferView(buffer=0, byteOffset=r_off, byteLength=r_len)
    bv_sc = pygltflib.BufferView(buffer=0, byteOffset=s_off, byteLength=s_len)
    gltf.bufferViews = [bv_pos, bv_idx, bv_tr, bv_rt, bv_sc]

    acc_pos = pygltflib.Accessor(
        bufferView=0,
        componentType=pygltflib.FLOAT,
        count=len(pos),
        type=pygltflib.VEC3,
        min=pos_min,
        max=pos_max,
    )
    acc_idx = pygltflib.Accessor(
        bufferView=1,
        componentType=pygltflib.UNSIGNED_INT,
        count=len(idx),
        type=pygltflib.SCALAR,
    )
    acc_tr = pygltflib.Accessor(
        bufferView=2, componentType=pygltflib.FLOAT, count=n, type=pygltflib.VEC3
    )
    acc_rt = pygltflib.Accessor(
        bufferView=3, componentType=pygltflib.FLOAT, count=n, type=pygltflib.VEC4
    )
    acc_sc = pygltflib.Accessor(
        bufferView=4, componentType=pygltflib.FLOAT, count=n, type=pygltflib.VEC3
    )
    gltf.accessors = [acc_pos, acc_idx, acc_tr, acc_rt, acc_sc]

    primitive = pygltflib.Primitive(
        attributes=pygltflib.Attributes(POSITION=0),
        indices=1,
        mode=pygltflib.TRIANGLES,
    )
    gltf.meshes = [pygltflib.Mesh(primitives=[primitive], name="spectre_tile_1_1_proto")]

    node = pygltflib.Node(mesh=0, name="spectre_patch_instanced")
    node.extensions = {
        "EXT_mesh_gpu_instancing": {
            "attributes": {"TRANSLATION": 2, "ROTATION": 3, "SCALE": 4},
        }
    }
    gltf.nodes = [node]
    gltf.extensionsUsed = ["EXT_mesh_gpu_instancing"]
    gltf.extensionsRequired = ["EXT_mesh_gpu_instancing"]

    if patch_meta:
        gltf.asset = pygltflib.Asset(version="2.0", generator="spectre_patch_api", extras=patch_meta)
    else:
        gltf.asset = pygltflib.Asset(version="2.0", generator="spectre_patch_api")

    gltf.set_binary_blob(blob)
    gltf.save_binary(str(path))
