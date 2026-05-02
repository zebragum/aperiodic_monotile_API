"""Blender 3.x example — duplicate the exported prototile using `tiles.csv`.

Prereqs
-------
1. Import `spectre_proto.stl` from the job artifacts (instanced mode).
2. Download `tiles.csv` from the same job.
3. Update the two path constants below.
4. Run inside Blender's Text Editor (not system Python).

The CSV already encodes the **fully composed** world similarity for each tile
(`tx`, `ty`, `rotation_deg`, `scale`) after the internal substitution matrix is
applied, so you can treat the prototile mesh as living in canonical coordinates
and simply apply those transforms per row.
"""

from __future__ import annotations

import csv
from math import radians
from pathlib import Path

import bpy
from mathutils import Euler, Vector


PROTO_STL = Path(r"C:\path\to\spectre_proto.stl")
CSV_FILE = Path(r"C:\path\to\tiles.csv")
MAX_DUPES = 4096  # safety during interactive testing


def import_proto() -> bpy.types.Object:
    bpy.ops.wm.stl_import(filepath=str(PROTO_STL))
    obj = bpy.context.selected_objects[0]
    obj.name = "spectre_tile11_proto"
    return obj


def main() -> None:
    proto = import_proto()
    collection = bpy.context.collection

    with CSV_FILE.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for idx, row in enumerate(reader):
            if idx >= MAX_DUPES:
                break

            dupe = proto.copy()
            dupe.data = proto.data.copy()
            dupe.animation_data_clear()

            tx = float(row["tx"])
            ty = float(row["ty"])
            rot = float(row["rotation_deg"])
            scl = float(row["scale"])

            dupe.location = Vector((tx, ty, 0.0))
            dupe.rotation_mode = "XYZ"
            dupe.rotation_euler = Euler((0.0, 0.0, radians(rot)), "XYZ")
            dupe.scale = (scl, scl, scl)

            dupe.name = row["id"][:60]
            collection.objects.link(dupe)


if __name__ == "__main__":
    main()
