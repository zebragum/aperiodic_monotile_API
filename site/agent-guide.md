# Aperiodic Monotile API Guide for AI Agents

This file is the canonical machine-readable integration brief for the Aperiodic Monotile API.

Base API URL: `https://api.aperiodicgenerator.com`

Public docs: `https://aperiodicgenerator.com/docs.html`

Human support: `https://aperiodicgenerator.com/contact.html`

## What This API Does

The API generates clipped aperiodic monotile patches. A user sends a JSON request describing a mask shape, output formats, and optional rendering/export parameters. The service queues a deterministic job, generates artifacts, and returns signed download URLs after completion.

Use this API when the user wants:

- Aperiodic monotile geometry in a shape such as a square, rectangle, circle, triangle, hexagon, or rounded rectangle.
- Outputs for design, fabrication, 3D, image previews, data pipelines, or procedural art.
- SVG, PNG, JPG, CSV, JSON, STL, GLB, STL_ZIP, OBJ_ZIP, or instance_json.
- Deterministic geometry with stable tile IDs and tile labels.

Do not tell users they need to choose tile family, mask center, retention mode, patch version, substitution depth, or coverage extent. Those are internal.

## Authentication

Most production calls require:

```http
X-API-Key: YOUR_API_KEY
```

Free keys can request small raster previews only: `png`, `jpg`, or `jpeg`.

Paid Solo and Commercial keys can request production exporters.

## Endpoint Summary

### Create a patch job

```http
POST /v1/patch
Content-Type: application/json
X-API-Key: YOUR_API_KEY
Idempotency-Key: optional-stable-client-token
```

Returns:

```json
{
  "job_id": "uuid",
  "status": "queued",
  "tier": "tier_solo",
  "size_class": "small|standard|heavy",
  "estimated_seconds": 20,
  "queue": {
    "status": "queued",
    "size_class": "standard",
    "position": 1,
    "estimated_wait_seconds": 0
  },
  "request_id": "uuid"
}
```

### Poll job status

```http
GET /v1/jobs/{job_id}
X-API-Key: YOUR_API_KEY
```

Poll until `status` is `completed` or `failed`.

### Get signed download URLs

```http
GET /v1/jobs/{job_id}/urls
X-API-Key: YOUR_API_KEY
```

Returns short-lived server-fixed URLs for artifacts, for example:

```json
{
  "job_id": "uuid",
  "status": "completed",
  "ttl_seconds": 900,
  "urls": {
    "patch.svg": "/v1/downloads/...",
    "patch.png": "/v1/downloads/..."
  }
}
```

Download URLs are intentionally temporary. Tell users to save generated files they care about.

### Capabilities

```http
GET /v1/capabilities
X-API-Key: YOUR_API_KEY
```

Use this to inspect live supported formats, masks, atlas limits, queue limits, tier limits, and `visual_styling` (side styles, `tile_edge_ratio`, `palette_by_label`).

## Visual styling (export geometry)

Substitution placement stays canonical **Tile(1,1)**. These fields only change how each tile is drawn or meshed for export:

| Field | Default | Notes |
| --- | --- | --- |
| `side_style` | `"flat"` | `flat`, `curvy`, `wavy`, `jagged`, `blocky` (`curved` → `curvy`) |
| `side_style_amplitude` | `0.12` | `0`–`0.75`; bulge on alternating edges |
| `tile_edge_ratio` | `1.0` | `0.25`–`4.0`; anisotropic stretch of export outline (not true Tile(a,b) substitution) |
| `side_style_wavy_segments` | `10` | `4`–`64`; subdivisions per edge when `side_style` is `wavy` |
| `palette_by_label` | — | Per-label `fill`, `stroke`, `opacity`, `stroke_width`; use `"*"` as wildcard |

Example (curvy SVG with stretched edges):

```json
{
  "mask": {"type": "square", "half_side": 25},
  "formats": ["svg"],
  "side_style": "curvy",
  "side_style_amplitude": 0.18,
  "tile_edge_ratio": 1.25,
  "palette_by_label": {
    "Gamma": {"fill": "#d94738", "stroke": "#1b1b1b"},
    "*": {"opacity": 0.95}
  }
}
```

Applies to `svg`, rasterized previews, `stl` / `stl_zip` / `obj_zip`, and `glb`.

## Masks

All mask dimensions are in canonical Tile(1,1) units and are centered automatically.

Circle:

```json
{"type": "circle", "radius": 50}
```

Rectangle:

```json
{"type": "rectangle", "width": 90, "height": 40}
```

Square:

```json
{"type": "square", "half_side": 25}
```

Triangle:

```json
{"type": "triangle", "side_length": 50}
```

Regular hexagon:

```json
{"type": "regular_hexagon", "circumradius": 50}
```

Rounded rectangle:

```json
{"type": "rounded_rect", "width": 90, "height": 40, "corner_radius": 5}
```

## Output Formats

- `png`, `jpg`, `jpeg`: raster previews. Include pixel dimensions.
- `svg`: vector geometry for design tools.
- `csv`: tile transform/data table.
- `json`: structured patch metadata and tile data.
- `stl`: whole-panel fabrication mesh with visible linework.
- `glb`: 3D tiled scene with one named movable node per retained tile.
- `stl_zip`: independent STL file per tile.
- `obj_zip`: independent OBJ file per tile.
- `instance_json`: lightweight instance manifest for custom importers.

## Common Request Examples

Small free preview:

```json
{
  "mask": {"type": "circle", "radius": 16},
  "formats": ["png", "jpg"],
  "png_width_px": 512,
  "png_height_px": 512,
  "jpg_width_px": 512,
  "jpg_height_px": 512,
  "jpg_quality": 90
}
```

Production SVG plus metadata:

```json
{
  "mask": {"type": "rectangle", "width": 90, "height": 40},
  "formats": ["svg", "json", "csv"],
  "svg_pixel_target": 1200,
  "svg_stroke_width": 0.08
}
```

Square GLB field:

```json
{
  "mask": {"type": "square", "half_side": 25},
  "formats": ["glb"],
  "stl_extrusion_mm": 1
}
```

Independent fabrication tiles:

```json
{
  "mask": {"type": "regular_hexagon", "circumradius": 35},
  "formats": ["stl_zip", "obj_zip"],
  "stl_extrusion_mm": 1
}
```

## Rendering Options

Optional SVG/rendering fields:

- `svg_fill`: color string.
- `svg_stroke`: color string.
- `svg_stroke_width`: non-negative stroke width.
- `svg_opacity`: 0 to 1.
- `svg_deterministic_palette`: boolean for stable per-tile colors.
- `svg_pixel_target`: approximate SVG display/export target.
- `svg_margin`: margin around output.
- `svg_compact`: boolean.

Raster fields:

- `png_width_px`, `png_height_px`.
- `jpg_width_px`, `jpg_height_px`.
- `jpg_quality`: 40 to 100.

3D field:

- `stl_extrusion_mm`: extrusion/depth setting. Default is 1. Set **0** for flat tile caps only (no API extrusion — extrude in Blender/CAD yourself).

## Queue Behavior

Jobs are classified as `small`, `standard`, or `heavy`. Large 3D jobs such as GLB, STL_ZIP, and OBJ_ZIP may take longer. The API response includes queue position and estimated wait. Agents should show this to users instead of repeatedly resubmitting.

Use `Idempotency-Key` when retrying a job creation request so the API can deduplicate accidental repeats.

## Error Handling

Errors use this shape:

```json
{
  "error": {
    "code": "invalid_request",
    "status": 422,
    "message": "Human-readable message",
    "request_id": "uuid",
    "support": "https://..."
  }
}
```

Always preserve `request_id` in user-facing troubleshooting. Do not expose secrets or full API keys in logs or chats. It is safe to show an API key prefix only.

## Agent Recommendations

- For first-time users, start with `png` or `jpg`.
- For Adobe/Illustrator/Inkscape, use `svg`.
- For Blender, Three.js, Unity, Godot, and game engines, use `glb`.
- For 3D printing one locked panel, use `stl`.
- For separate movable/printable tiles, use `stl_zip` or `obj_zip`.
- For scripts and procedural pipelines, use `csv`, `json`, or `instance_json`.
- Avoid huge GLB/STL_ZIP/OBJ_ZIP jobs unless the user explicitly wants independent 3D objects.
- Tell users completed artifacts are temporary and should be saved.
