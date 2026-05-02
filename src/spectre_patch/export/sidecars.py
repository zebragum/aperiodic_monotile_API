"""CSV / JSON sidecars consumed by Blender/USD glue."""

from __future__ import annotations

import csv
import io
import json
from typing import Any, Iterable

from spectre_patch.patch_engine import EmittedTile


def tiles_to_csv_rows(
    tiles: Iterable[EmittedTile],
    *,
    patch_version: str,
    tile_family: str,
    seed: str | None,
) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(
        ["id", "tx", "ty", "rotation_deg", "scale", "patch_version", "seed", "tile_family", "label"]
    )
    for t in tiles:
        writer.writerow(
            [
                t.tile_id,
                f"{t.tx:.17g}",
                f"{t.ty:.17g}",
                f"{t.rotation_deg:.17g}",
                f"{t.scale_world:.17g}",
                patch_version,
                seed if seed not in (None, "") else "",
                tile_family,
                t.tile_label,
            ]
        )
    return buf.getvalue().encode("utf-8")


def tiles_to_json_doc(
    tiles: Iterable[EmittedTile],
    *,
    patch_version: str,
    tile_family: str,
    seed: str | None,
    extra: dict[str, Any] | None = None,
) -> bytes:
    doc: dict[str, Any] = {
        "patch_version": patch_version,
        "tile_family": tile_family,
        "seed": seed,
        "tiles": [
            {
                "id": t.tile_id,
                "tx": t.tx,
                "ty": t.ty,
                "rotation_deg": t.rotation_deg,
                "scale": t.scale_world,
                "label": t.tile_label,
                "centroid_canonical_xy": t.centroid_canonical_xy,
                "generator_affine6": t.affine_canonical_gen6,
            }
            for t in tiles
        ],
    }
    if extra:
        doc.update(extra)
    return json.dumps(doc, sort_keys=True, indent=2).encode("utf-8")
