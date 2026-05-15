# Aperiodic Monotile Generator

Generate non-repeating aperiodic monotile geometry for previews, vector tools,
3D scenes, procedural pipelines, and design/research workflows.

Public generator: https://aperiodicgenerator.com

Hosted API: https://aperiodic-monotile-api.onrender.com

This repository contains the public website, API client examples, and Blender
add-on for the Aperiodic Monotile Generator. The hosted service accepts simple
shape requests and returns generated artifacts such as SVG, PNG, JPG, GLB, STL,
CSV, and JSON.

## Quick API Example

```bash
curl -X POST https://aperiodic-monotile-api.onrender.com/v1/patch \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "formats": ["svg", "glb"],
    "mask": {"type": "rectangle", "width": 90, "height": 40},
    "scale": 1
  }'
```

The API returns a queued job. Poll the job, then fetch signed download URLs when
it completes. See `site/agent-guide.md` for a concise machine-readable guide.

## Blender Add-on

An installable Blender add-on is included:

```text
blender_addon/dist/aperiodic_monotile_generator.zip
```

Install it in Blender with:

`Edit > Preferences > Add-ons > Install...`

The add-on lets you choose a boundary, set tile scale/depth, call the hosted
API, download a GLB, and import it into the current Blender scene.

## Formats

| Format | When to request | Notes |
|--------|----------------|-------|
| `png`, `jpg` | Free previews and quick visual checks | Raster image outputs |
| `svg` | Vector tools such as Illustrator or Inkscape | Compact vector geometry |
| `glb` | Blender, Three.js, Unity, Godot | One named/movable node per retained tile |
| `csv`, `json` | Scripts and procedural pipelines | Stable tile IDs, labels, and transforms |
| `stl` | Physical or mesh workflows | Whole-panel mesh output |
| `stl_zip` / `obj_zip` | Independent tile objects | One movable/exportable file per tile in a ZIP archive |

## API Usage Examples

### Circle Preview

```json
{
  "mask": {"type": "circle", "radius": 50},
  "formats": ["png"],
  "png_width_px": 1200,
  "png_height_px": 1200
}
```

### Rectangle GLB

```json
{
  "mask": {"type": "rectangle", "width": 90, "height": 40},
  "formats": ["glb"],
  "scale": 1,
  "stl_extrusion_mm": 1
}
```

### Square Data Export

```json
{
  "mask": {"type": "square", "half_side": 25},
  "formats": ["csv", "json"]
}
```

## Public Resources

- Website: https://aperiodicgenerator.com
- Human docs: `site/docs.html`
- AI agent guide: `site/agent-guide.md`
- Blender add-on: `blender_addon/dist/aperiodic_monotile_generator.zip`

## Notes

This public repository is intended for integration, examples, website assets,
and client tooling. The hosted generator remains the recommended way to produce
production outputs.

## Licence

MIT for this repository’s service code and examples, unless noted otherwise.
Mathematical facts are not copyrighted; third-party research and reference
implementations deserve attribution.
