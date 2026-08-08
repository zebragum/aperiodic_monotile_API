# Aperiodic Monotile — Rhino / Grasshopper script

Python client for the hosted [Aperiodic Monotile API](https://api.aperiodicgenerator.com).
Works in the Rhino Script Editor (Rhino 7/8), IronPython components, or CPython GHPython.

## Setup

1. Open `untiling_patch.py`.
2. Set:
   - `API_KEY` — paid key (or use `UNTILING_API_KEY` / `untiling_api_key.txt` beside the script)
   - `OUTPUT_DIR` — folder where downloads are written
   - `FORMATS` — e.g. `["instance_json", "svg"]` or `["glb"]` / `["stl"]`
   - `MASK_WIDTH` / `MASK_HEIGHT` / `TILE_SCALE`
3. Run the script.

`STL_EXTRUSION_MM` defaults to **0** when STL/GLB is requested (flat caps; extrude in Rhino).

## API key

First match wins:

1. `API_KEY` at the top of the script (or the `api_key=` argument to `fetch_and_save`)
2. Environment variable `UNTILING_API_KEY`
3. File `untiling_api_key.txt` next to `untiling_patch.py` (one line)

## Grasshopper notes

Call the reusable entry point from a GHPython / CPython component:

```python
from untiling_patch import fetch_and_save

meta = fetch_and_save(
    output_dir=r"C:\Z\monotile_out",
    formats=["instance_json"],
    width=40,
    height=24,
    scale=1.0,
    extrusion_mm=0.0,
)
a = meta["files"]  # list of saved paths
```

For `instance_json`, open `spectre_instances.json` and place instances with
`prototile_ring_xy` + per-instance transforms (same data the Blender add-on uses).

For SVG, import `patch.svg` with Rhino’s SVG importer or a file-read component.

## How it works

1. `POST /v1/patch` with your mask + formats.
2. Poll `GET /v1/jobs/{job_id}` until complete.
3. `GET /v1/jobs/{job_id}/urls` and download artifacts into `OUTPUT_DIR/<job_prefix>/`.
4. Writes `job_meta.json` listing saved paths.

HTTP uses **urllib** only (no `requests`).

## Packaging

Ship `untiling_patch.py` (+ optional README). No zip layout requirements beyond keeping
the optional `untiling_api_key.txt` out of public releases.
