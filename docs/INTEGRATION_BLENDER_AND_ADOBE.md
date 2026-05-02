# Blender / Adobe / Inkscape integration

## Coordinate convention

The API documents each tile with a **single** world similarity transform applied after the internal Spectre substitution matrix. For column vectors \([x,y,1]\), the server composes

\[
W = T_{\mathrm{client}} \cdot G_{\mathrm{generator}}
\]

where \(T_{\mathrm{client}}\) encodes `scale`, `rotation_deg`, `tx`, and `ty`, and \(G_{\mathrm{generator}}\) is the substitution placement for that leaf.

## Blender (Geometry Nodes / Python)

1. Import `spectre_proto.stl` once (instanced mode) or `patch.stl` (moderate combined mesh).
2. Download `spectre_instances.json` and iterate `instances[*].affine4_row_lists`.
3. For each entry, build `Matrix(rows)` in Blender from the four inner lists.
4. Duplicate the prototile mesh with `mesh.copy()` → `mesh.transform(matrix)` → join if needed.

A minimal scripted loop ships in [`examples/blender_duplicate_from_csv.py`](../examples/blender_duplicate_from_csv.py).

Because instancing avoids millions of heavyweight meshes, always prefer `spectre_proto.stl` + JSON when `tiles >= STL tile instancing floor` (defaults to ~50 k retained tiles unless your SKU adjusts it).

### CSV-only workflow

1. Fetch `tiles.csv`.
2. For each row, read `rotation_deg`, `scale`, `tx`, `ty`.
3. Set object location/rotation/scale on a single Tile(1,1) mesh with origin aligned to canonical polygon reference used by the STL/SVG exporters.

You can also import CSV using Blender’s bundled CSV importer to empties then apply drivers.

## Illustrator / Inkscape (SVG Tier)

1. Call `formats: ["svg"]` — the response embeds deterministic `<defs><path id="proto"/></defs>` prototypes and `<use href="#proto">`.
2. Strokes/fills obey exporter options (`svg_fill`, `svg_stroke`, `svg_stroke_width`, `svg_opacity`, `svg_deterministic_palette`).
3. Illustrator honors SVG 1.1 transforms; Inkscape prefers explicit `stroke-linejoin`.

For huge patches the API replaces SVG with STL + manifests unless `force_svg_large: true`.

## Virus scanning / rasterization

PNG export paths call `cairosvg`; keep the converter inside a hardened container (Tier-1+) and optionally route outputs through AV hooks before publishing signed URLs.
