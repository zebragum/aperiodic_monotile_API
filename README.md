# Spectre / Tile(1,1) Monotile Patch API (Tier 1)

Deterministic, pipeline-oriented HTTP service and worker for **clipped spectral patches** of the weakly chiral aperiodic monotile **Tile(1,1)** (Smith–Myers–Kaplan–Goodman–Strauss), using the same substitution construction as the reference [Waterloo Spectre explorer](https://cs.uwaterloo.ca/~csk/spectre/) (see `docs/ATTRIBUTION.md`).

## Quick start

```bash
cd spectre_patch_api
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
set SPECTRE_PATCH_API_SECRET=please-change-this-secret-key
uvicorn spectre_patch.api.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for OpenAPI.

## Endpoints

- `GET /v1/capabilities` — formats, masks, retention modes, current limits
- `POST /v1/patch` — enqueues a patch job (idempotent via `Idempotency-Key`)
- `GET /v1/jobs/{job_id}` — status / error / result manifest
- `GET /v1/jobs/{job_id}/urls?ttl_seconds=...` — bundle of signed download URLs
- `GET /v1/downloads/{job_id}/{filename}?exp={unix}&sig={hmac-sha256}` — signed download
- `POST /v1/leads` — public launch-list capture for the static site
- `GET /v1/admin/leads?fmt=json|csv` — private lead export, guarded by `X-Admin-Token`

## Formats

| Format | When to request | Notes |
|--------|----------------|-------|
| `svg` | Vector tools (Illustrator, Inkscape) | Auto-downgrades to STL+JSON above `svg_max_tiles_hard` unless `force_svg_large=true` |
| `csv` | CSV importers, Blender drivers | Columns: `id,tx,ty,rotation_deg,scale,patch_version,seed,tile_family,label` |
| `json` | Pipeline metadata + per-tile transforms | Mirrors CSV with extra context |
| `stl` | Printing or boolean ops | Whole-panel mesh output |
| `stl_zip` / `obj_zip` | Independent tile objects | One movable/exportable file per tile in a ZIP archive |
| `glb` | Three.js / Babylon / glTF-Transform | Single prototile + `EXT_mesh_gpu_instancing` |
| `instance_json` | Custom instancers (USD, Houdini, custom shaders) | 4×4 row lists per instance |
| `png` | Raster previews (requires `[png]` extra) | Bounded by `png_max_pixels` |
| `jpg` / `jpeg` | Raster previews (requires `[png]` extra) | Uses JPEG quality options |

Geometry clipping uses Shapely internally. API users do not install or call Shapely; hosted requests just send masks
and receive artifacts. The Docker image used on Render installs the Cairo/Pillow raster stack, so JPG/PNG exports are
available in production even if a local Windows test skips when Cairo is not installed.

## Curl smoke

```powershell
curl -X POST http://127.0.0.1:8000/v1/patch ^
  -H "Content-Type: application/json" ^
  -d "{\"formats\":[\"png\"],\"png_width_px\":1200,\"png_height_px\":1200,\"mask\":{\"type\":\"circle\",\"radius\":120}}"
```

For a pixel-exact SVG tile patch, keep geometry in canonical units and set the
client scale. Example: a 100 px square at 8 px per canonical unit is a 12.5-unit
square mask:

```json
{
  "scale": 8,
  "mask": {"type": "square", "half_side": 6.25},
  "formats": ["svg"],
  "svg_pixel_target": 100,
  "svg_margin": 0,
  "svg_compact": true
}
```

## API Usage Examples

All geometry is authored in canonical Tile(1,1) units. SVG pixel size is an
export setting; it does not change the raw geometry unless you also set
`scale`.

### 100-Unit Circle, 1000px SVG

```json
{
  "scale": 1,
  "mask": {"type": "circle", "radius": 50},
  "formats": ["svg"],
  "svg_pixel_target": 1000,
  "svg_margin": 0,
  "svg_compact": true
}
```

### 9:4 Rectangle

```json
{
  "scale": 1,
  "mask": {"type": "rectangle", "width": 90, "height": 40},
  "formats": ["svg"],
  "svg_pixel_target": 900,
  "svg_margin": 0,
  "svg_compact": true
}
```

### 50-Unit Equilateral Triangle

```json
{
  "scale": 1,
  "mask": {"type": "triangle", "side_length": 50},
  "formats": ["svg"],
  "svg_pixel_target": 500,
  "svg_margin": 0,
  "svg_compact": true
}
```

The triangle is centered at its centroid. `rotation_deg` is optional and
defaults to `90`, which points one vertex upward in canonical coordinates.

## Auth, Tiers, and Downloads

Production deployments set `SPECTRE_PATCH_REQUIRE_API_KEY=true`. Clients pass
their key as `X-API-Key`; the server maps that key to `tier_free`,
`tier_day_pass`, `tier_solo`, or `tier_teams` with
`SPECTRE_PATCH_API_KEY_TIERS_JSON`. Client-supplied tier headers are ignored
when API keys are configured. Free keys are for small JPG/PNG preview patches;
paid Stripe checkout creates Day Pass, Solo, and Teams keys.

`POST /v1/patch` returns a `job_id`. Poll `GET /v1/jobs/{job_id}` until
`status` is `completed`, then call `GET /v1/jobs/{job_id}/urls` to receive
signed relative URLs for artifacts such as `patch.svg`, `tiles.csv`, or
`tiles.json`. Signed URLs expire; request a fresh bundle when needed.

## Launch Leads

The public website can collect early users before Stripe is fully configured:

```powershell
Invoke-RestMethod -Method Post https://aperiodic-monotile-api.onrender.com/v1/leads `
  -ContentType "application/json" `
  -Body '{"email":"designer@example.com","use_case":"Blender panels","source":"homepage"}'
```

Lead export is intentionally separate from customer API keys. Set
`SPECTRE_PATCH_ADMIN_TOKEN` in the deployment environment, then export leads:

```powershell
Invoke-RestMethod https://aperiodic-monotile-api.onrender.com/v1/admin/leads?fmt=csv `
  -Headers @{"X-Admin-Token"=$env:SPECTRE_PATCH_ADMIN_TOKEN}
```

## Atlas (depth-quantised LOD cores)

Most API requests crop a small region from a much larger fully-tiled patch.
Building the patch from scratch on every request is prohibitive at depths ≥ 8,
so the service ships an **atlas** of pre-computed canonical cores. A request
just selects the smallest core whose inscribed square is large enough, crops
on the fly, applies retention, and emits — no substitution recursion, no
per-request metatile-tree construction.

| File | Depth N | Tiles | Disk | Inscribed square (canonical) |
|------|--------:|------:|-----:|-----------------------------:|
| `core_spectre_tile_1_1_n5.npz` | 5 |     34,649 |   0.9 MB |  ~146 unit square |
| `core_spectre_tile_1_1_n6.npz` | 6 |    272,791 |   6.4 MB |  ~394 unit square |
| `core_spectre_tile_1_1_n7.npz` | 7 |  2,147,679 |  48.6 MB | ~1033 unit square |
| `core_spectre_tile_1_1_n8.npz` | 8 |   ~17.0 M  | ~400 MB  | ~2700 unit square (estimate) |
| `core_spectre_tile_1_1_n9.npz` | 9 |  ~133.0 M  | ~3.1 GB  | ~7100 unit square (estimate) |
| `core_spectre_tile_1_1_n10.npz`| 10|  ~1.05 B   | ~25  GB  |~18000 unit square (estimate) |

Build cores into the atlas dir:

```powershell
python -m spectre_patch.atlas.cli build 5 --out data\atlas
python -m spectre_patch.atlas.cli build 6 --out data\atlas
python -m spectre_patch.atlas.cli build 7 --out data\atlas --raster 1024
python -m spectre_patch.atlas.cli list  --out data\atlas
```

For depth ≥ 8 the inline build will be too slow / RAM-heavy on a laptop. Build
on Colab (high-RAM CPU runtime is enough for n=8; A100 helps for n=9+) using
`scripts/colab_build_deep_core.py`, then copy the resulting `.npz` and updated
`index.json` into the deployment's `data/atlas/`.

Operationally, the API:

1. Loads `data/atlas/index.json` at startup and surfaces it in `GET /v1/capabilities`
   under the `atlas.cores[]` field so clients can verify the maximum mask they
   can request without forcing live substitution.
2. On each `POST /v1/patch`, picks the smallest core whose `inscribed_half_side`
   covers the request's mask half-extent, mmaps the file (cached LRU per
   process), runs an STRtree crop, applies retention, emits.
3. Falls back to live substitution if no core is large enough or the request
   sets `force_substitution=true`. The job's `result_meta.atlas` records which
   path was taken (and which core, if any) for observability.

See `docs/INTEGRATION_BLENDER_AND_ADOBE.md`.

## Licence

MIT for this repository’s service code (see individual files). Mathematical facts are not copyrighted; third-party ports and Waterloo tooling deserve attribution (`docs/ATTRIBUTION.md`).
