"""glTF GLB explicit patch mesh smoke test (skipped when pygltflib missing)."""

from __future__ import annotations

import struct
import tempfile
from pathlib import Path

import pytest

pygltflib = pytest.importorskip("pygltflib")

from spectre_patch.config_limits import LimitsSettings  # noqa: E402
from spectre_patch.export.gltf_export import write_glb_instanced  # noqa: E402
from spectre_patch.masking import MaskSquare, RetentionMode  # noqa: E402
from spectre_patch.patch_engine import enumerate_emitted  # noqa: E402


def test_glb_explicit_patch_mesh_writes_valid_header():
    tiles = enumerate_emitted(
        limits=LimitsSettings(),
        tile_family="spectre_tile_1_1",
        patch_version="glb-test",
        seed=None,
        half_extent_cover=1.5,
        scale=1.0,
        tx=0.0,
        ty=0.0,
        rotation_deg=0.0,
        mask=MaskSquare((0.0, 0.0), half_side=8.0),
        retention=RetentionMode.centroid,
        substitution_iterations=2,
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "patch.glb"
        write_glb_instanced(
            path,
            tiles,
            scale=1.0,
            rotation_deg=10.0,
            tx=2.0,
            ty=-1.0,
            thickness_mm=1.5,
        )
        data = path.read_bytes()
        assert data[:4] == b"glTF"
        version = struct.unpack("<I", data[4:8])[0]
        assert version == 2

        gltf = pygltflib.GLTF2().load(str(path))
        assert "EXT_mesh_gpu_instancing" not in (gltf.extensionsUsed or [])
        assert len(gltf.nodes) == len(tiles)
        assert len(gltf.meshes) == len(tiles)
        assert gltf.scenes[0].nodes == list(range(len(tiles)))
        assert all(len(mesh.primitives) == 2 for mesh in gltf.meshes)
        assert gltf.nodes[0].extras["tile_id"] == tiles[0].tile_id
        assert max(abs(float(node.translation[1])) for node in gltf.nodes) == 0.0

        positions = gltf.get_data_from_buffer_uri(gltf.buffers[0].uri)
        first_accessor = gltf.accessors[gltf.meshes[0].primitives[0].attributes.POSITION]
        first_view = gltf.bufferViews[first_accessor.bufferView]
        raw = positions[first_view.byteOffset : first_view.byteOffset + first_view.byteLength]
        xyz = struct.unpack("<" + "f" * (len(raw) // 4), raw)
        ys = xyz[1::3]
        zs = xyz[2::3]
        assert max(ys) - min(ys) < max(zs) - min(zs)


def test_glb_flat_extrusion_writes_single_primitive_per_tile():
    tiles = enumerate_emitted(
        limits=LimitsSettings(),
        tile_family="spectre_tile_1_1",
        patch_version="glb-flat-test",
        seed=None,
        half_extent_cover=1.5,
        scale=1.0,
        tx=0.0,
        ty=0.0,
        rotation_deg=0.0,
        mask=MaskSquare((0.0, 0.0), half_side=8.0),
        retention=RetentionMode.centroid,
        substitution_iterations=2,
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "patch.glb"
        write_glb_instanced(
            path,
            tiles,
            scale=1.0,
            rotation_deg=0.0,
            tx=0.0,
            ty=0.0,
            thickness_mm=0.0,
        )
        gltf = pygltflib.GLTF2().load(str(path))
        assert all(len(mesh.primitives) == 1 for mesh in gltf.meshes)

        positions = gltf.get_data_from_buffer_uri(gltf.buffers[0].uri)
        first_accessor = gltf.accessors[gltf.meshes[0].primitives[0].attributes.POSITION]
        first_view = gltf.bufferViews[first_accessor.bufferView]
        raw = positions[first_view.byteOffset : first_view.byteOffset + first_view.byteLength]
        xyz = struct.unpack("<" + "f" * (len(raw) // 4), raw)
        ys = xyz[1::3]
        assert max(ys) - min(ys) < 1e-5
