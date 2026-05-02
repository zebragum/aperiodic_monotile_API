"""glTF GLB instancing smoke test (skipped when pygltflib missing)."""

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


def test_glb_instancing_writes_valid_header():
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
        assert "EXT_mesh_gpu_instancing" in (gltf.extensionsUsed or [])
        assert gltf.nodes[0].extensions is not None
        instancing = gltf.nodes[0].extensions["EXT_mesh_gpu_instancing"]
        assert "TRANSLATION" in instancing["attributes"]
