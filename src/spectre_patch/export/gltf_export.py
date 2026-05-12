"""glTF 2.0 GLB exporter.

Produces a single binary GLB containing one named glTF node per tile. The nodes
carry local fill/stroke geometry plus tile metadata, so game engines and DCC tools
can select, animate, recolor, or remove individual tiles.

Soft-fails with a clear ImportError when `pygltflib` is absent.
"""

from __future__ import annotations

import struct
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np

from spectre_patch.export.stl_export import safe_object_name, stroke_prism_tris_for_tiles, tile_prism_tris
from spectre_patch.geometry_affine import similarity_client
from spectre_patch.patch_engine import EmittedTile


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


def _to_gltf_ground_space(xyz: np.ndarray) -> np.ndarray:
    """Convert internal X/Y plane with +Z thickness to glTF X/Z ground with +Y up."""

    if len(xyz) == 0:
        return xyz
    out = np.empty_like(xyz, dtype=np.float32)
    out[:, 0] = xyz[:, 0]
    out[:, 1] = xyz[:, 2]
    out[:, 2] = xyz[:, 1]
    return out


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
    """Write `<path>` as a GLB containing one movable node per tile."""

    try:
        import pygltflib  # type: ignore[import-not-found]  # noqa: PLC0415
    except Exception as e:
        raise RuntimeError(
            "glTF export disabled — install `pip install spectre-patch-api[gltf]` (pygltflib)."
        ) from e

    client_world = similarity_client(scale, rotation_deg, tx, ty)
    view_payloads: list[bytes] = []
    view_targets: list[int] = []
    tile_records: list[dict[str, Any]] = []

    for tile in tiles:
        fill_tris = tile_prism_tris(
            tile,
            scale=scale,
            rotation_deg=rotation_deg,
            tx=tx,
            ty=ty,
            thickness_mm=thickness_mm,
        )
        stroke_z = float(thickness_mm) * float(tile.scale_world) * float(scale) * 1.02
        stroke_tris = stroke_prism_tris_for_tiles(
            [tile],
            scale=scale,
            rotation_deg=rotation_deg,
            tx=tx,
            ty=ty,
            thickness_mm=max(float(thickness_mm) * 0.08, 0.04),
            z_base=stroke_z,
        )
        fill_pos, fill_idx = _tris_to_position_index_arrays(fill_tris)
        stroke_pos, stroke_idx = _tris_to_position_index_arrays(stroke_tris)
        if len(fill_pos) == 0:
            continue
        fill_pos = _to_gltf_ground_space(fill_pos)
        stroke_pos = _to_gltf_ground_space(stroke_pos)

        cx, cy = tile.centroid_canonical_xy
        center = np.array(
            [
                client_world[0, 0] * cx + client_world[0, 1] * cy + client_world[0, 2],
                0.0,
                client_world[1, 0] * cx + client_world[1, 1] * cy + client_world[1, 2],
            ],
            dtype=np.float32,
        )
        fill_pos = fill_pos - center
        if len(stroke_pos):
            stroke_pos = stroke_pos - center

        offsets_start = len(view_payloads)
        view_payloads.extend([fill_pos.tobytes(), fill_idx.tobytes()])
        view_targets.extend([pygltflib.ARRAY_BUFFER, pygltflib.ELEMENT_ARRAY_BUFFER])
        has_stroke = len(stroke_pos) > 0 and len(stroke_idx) > 0
        if has_stroke:
            view_payloads.extend([stroke_pos.tobytes(), stroke_idx.tobytes()])
            view_targets.extend([pygltflib.ARRAY_BUFFER, pygltflib.ELEMENT_ARRAY_BUFFER])

        tile_records.append(
            {
                "tile": tile,
                "translation": center.tolist(),
                "view_start": offsets_start,
                "fill_pos": fill_pos,
                "fill_idx": fill_idx,
                "stroke_pos": stroke_pos,
                "stroke_idx": stroke_idx,
                "has_stroke": has_stroke,
            }
        )

    if not tile_records:
        raise ValueError("GLB export has no tile geometry to write")

    blob, offs = _pack_buffer(view_payloads)

    gltf = pygltflib.GLTF2()
    gltf.scene = 0
    gltf.scenes = [pygltflib.Scene(nodes=list(range(len(tile_records))))]

    gltf.buffers = [pygltflib.Buffer(byteLength=len(blob))]

    gltf.bufferViews = []
    for idx, (off, length) in enumerate(offs):
        gltf.bufferViews.append(
            pygltflib.BufferView(
                buffer=0,
                byteOffset=off,
                byteLength=length,
                target=view_targets[idx],
            )
        )

    gltf.accessors = []
    gltf.meshes = []
    gltf.nodes = []
    for record in tile_records:
        tile = record["tile"]
        fill_pos = record["fill_pos"]
        fill_idx = record["fill_idx"]
        stroke_pos = record["stroke_pos"]
        stroke_idx = record["stroke_idx"]
        view_start = int(record["view_start"])

        fill_pos_acc = len(gltf.accessors)
        gltf.accessors.append(
            pygltflib.Accessor(
                bufferView=view_start,
                componentType=pygltflib.FLOAT,
                count=len(fill_pos),
                type=pygltflib.VEC3,
                min=fill_pos.min(axis=0).astype(np.float32).tolist(),
                max=fill_pos.max(axis=0).astype(np.float32).tolist(),
            )
        )
        fill_idx_acc = len(gltf.accessors)
        gltf.accessors.append(
            pygltflib.Accessor(
                bufferView=view_start + 1,
                componentType=pygltflib.UNSIGNED_INT,
                count=len(fill_idx),
                type=pygltflib.SCALAR,
            )
        )

        primitives = [
            pygltflib.Primitive(
                attributes=pygltflib.Attributes(POSITION=fill_pos_acc),
                indices=fill_idx_acc,
                mode=pygltflib.TRIANGLES,
                material=0,
            )
        ]
        if record["has_stroke"]:
            stroke_pos_acc = len(gltf.accessors)
            gltf.accessors.append(
                pygltflib.Accessor(
                    bufferView=view_start + 2,
                    componentType=pygltflib.FLOAT,
                    count=len(stroke_pos),
                    type=pygltflib.VEC3,
                    min=stroke_pos.min(axis=0).astype(np.float32).tolist(),
                    max=stroke_pos.max(axis=0).astype(np.float32).tolist(),
                )
            )
            stroke_idx_acc = len(gltf.accessors)
            gltf.accessors.append(
                pygltflib.Accessor(
                    bufferView=view_start + 3,
                    componentType=pygltflib.UNSIGNED_INT,
                    count=len(stroke_idx),
                    type=pygltflib.SCALAR,
                )
            )
            primitives.append(
                pygltflib.Primitive(
                    attributes=pygltflib.Attributes(POSITION=stroke_pos_acc),
                    indices=stroke_idx_acc,
                    mode=pygltflib.TRIANGLES,
                    material=1,
                )
            )

        safe_name = safe_object_name(tile.tile_id)
        mesh_idx = len(gltf.meshes)
        gltf.meshes.append(pygltflib.Mesh(primitives=primitives, name=f"tile_mesh_{safe_name}"))
        gltf.nodes.append(
            pygltflib.Node(
                mesh=mesh_idx,
                name=f"tile_{safe_name}",
                translation=record["translation"],
                extras={
                    "tile_id": tile.tile_id,
                    "tile_label": tile.tile_label,
                    "clipped": tile.clip_geom is not None,
                },
            )
        )

    gltf.materials = [
        _material(pygltflib, color=[0.72, 0.78, 0.90, 1.0], name="tile_fill"),
        _material(pygltflib, color=[0.02, 0.03, 0.08, 1.0], name="tile_strokes"),
    ]

    if patch_meta:
        meta = {**patch_meta, "glb_export": "individual_tile_nodes_with_strokes", "tile_count": len(tile_records)}
        gltf.asset = pygltflib.Asset(version="2.0", generator="spectre_patch_api", extras=meta)
    else:
        gltf.asset = pygltflib.Asset(version="2.0", generator="spectre_patch_api")

    gltf.set_binary_blob(blob)
    gltf.save_binary(str(path))
