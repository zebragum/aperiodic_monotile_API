# Aperiodic Monotile API — reference

Base: `https://api.aperiodicgenerator.com`

## Endpoints

| Method | Path | Auth | Body |
|--------|------|------|------|
| GET | `/healthz` | No | — |
| GET | `/readyz` | No | — |
| GET | `/v1/capabilities` | Yes | — |
| POST | `/v1/patch` | Yes | JSON `PatchRequest` |
| GET | `/v1/jobs/{job_id}` | Yes | — |
| GET | `/v1/jobs/{job_id}/urls` | Yes | — |
| GET | `/v1/downloads/{job_id}/{filename}?exp=&sig=` | No (signed) | — |

## PatchRequest (POST body)

All fields are in **one JSON object**. `extra` fields are rejected (422).

### Core

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `tile_family` | string | `spectre_tile_1_1` | Only supported family |
| `mask` | object | **required** | See masks below |
| `formats` | string[] | `svg,csv,json` | Non-empty; see supported list |
| `scale` | number | `1.0` | > 0 |
| `rotation_deg` | number | `0` | Applied after placement |
| `tx`, `ty` | number | `0` | Translation |
| `substitution_iterations` | int | auto | 0–12; omit for auto |
| `seed` | string | null | Reproducibility hook |
| `patch_version` | string | null | Atlas patch version hint |
| `force_substitution` | bool | false | Advanced |

### Supported formats

`svg`, `svgz`, `csv`, `json`, `stl`, `stl_zip`, `obj_zip`, `glb`, `instance_json`, `png`, `jpg`, `jpeg`

Free tier: `png`, `jpg`, `jpeg` only.

### Raster

| Field | Type | Notes |
|-------|------|-------|
| `png_width_px`, `png_height_px` | int | Both or neither; one alone → square |
| `jpg_width_px`, `jpg_height_px` | int | Same rule |
| `jpg_quality` | int | 40–100 |

### SVG

| Field | Type | Notes |
|-------|------|-------|
| `svg_fill`, `svg_stroke` | string | Colors |
| `svg_stroke_width` | number | ≥ 0 |
| `svg_opacity` | number | 0–1 |
| `svg_deterministic_palette` | bool | Stable per-tile colors |
| `svg_pixel_target` | int | Display target |
| `svg_margin` | number | ≥ 0 |
| `svg_compact` | bool | Smaller SVG |
| `force_svg_large` | bool | Bypass soft size cap |

### 3D

| Field | Type | Default |
|-------|------|---------|
| `stl_extrusion_mm` | number | `0.0` |

### Visual styling (export only)

| Field | Type | Default |
|-------|------|---------|
| `side_style` | enum | `flat` |
| `side_style_amplitude` | number | `0.12` |
| `tile_edge_ratio` | number | `1.0` |
| `side_style_wavy_segments` | int | `10` |
| `palette_by_label` | object | null |

`palette_by_label` keys per tile label (or `"*"`): `fill`, `stroke`, `opacity`, `transparent` (bool).

## Mask schemas

```json
{"type": "circle", "radius": 50}
{"type": "square", "half_side": 25}
{"type": "rectangle", "width": 90, "height": 40}
{"type": "triangle", "side_length": 50, "rotation_deg": 90}
{"type": "regular_hexagon", "circumradius": 50}
{"type": "rounded_rect", "width": 90, "height": 40, "corner_radius": 5}
```

Aliases: `hexagon` → `regular_hexagon`; `rounded-rect` → `rounded_rect`.

## POST /v1/patch response

```json
{
  "job_id": "uuid",
  "status": "queued",
  "tier": "tier_free|tier_solo|tier_teams|tier_day_pass",
  "size_class": "small|standard|heavy",
  "estimated_seconds": 5,
  "request_id": "uuid",
  "queue": {
    "status": "queued",
    "size_class": "small",
    "position": 1,
    "estimated_wait_seconds": 0
  }
}
```

## GET /v1/jobs/{job_id}

Row fields include `status` (`queued`, `running`, `completed`, `failed`), `request_json`, `result_json`, `error`, `tier`, `size_class`, optional `queue`.

## GET /v1/jobs/{job_id}/urls

Completed:

```json
{
  "job_id": "uuid",
  "status": "completed",
  "ttl_seconds": 900,
  "urls": {
    "patch.svg": "/v1/downloads/{job_id}/patch.svg?exp=...&sig=...",
    "patch.png": "/v1/downloads/..."
  }
}
```

Not completed: `"urls": {}` plus current `status` and optional `queue`.

## Capabilities highlights

`visual_styling.side_styles`, `tile_edge_ratio` range, `palette_by_label`, `supported_masks`, `supported_formats`, `free_tier_formats`, `atlas`, `limits`, `operational`.

## Rejected / internal (do not send)

- `retention`, `coverage_half_extent` — internal worker only
- `mask.center` — masks are auto-centered
- Hat/turtle tile families — not shipped

## Artifact names (typical)

| formats | files |
|---------|-------|
| svg | `patch.svg` |
| png | `patch.png` |
| jpg/jpeg | `patch.jpg` |
| csv | `tiles.csv` |
| json | `tiles.json` |
| stl | `patch.stl` or `spectre_proto.stl` + `spectre_instances.json` (large jobs) |
| glb | `patch.glb` |
| stl_zip / obj_zip | `tiles_stl.zip`, `tiles_obj.zip` |
