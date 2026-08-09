# Aperiodic Monotile — Rhino / Grasshopper script

Python client for the hosted [Aperiodic Monotile API](https://api.aperiodicgenerator.com).
Works in the Rhino Script Editor (Rhino 8 CPython recommended) or Grasshopper Python.

Feature parity with Inkscape / Blender for generation options: side styles, coloring,
tile scale, mask shapes, SVG compact mode, and optional curve import into the document.

## Setup

1. Open `untiling_patch.py`.
2. Set `API_KEY` (or use `UNTILING_API_KEY` / `untiling_api_key.txt`) and `OUTPUT_DIR`.
3. Either:
   - Leave `INTERACTIVE = True` and answer Rhino prompts, or
   - Edit the constants (`FORMATS`, `MASK_*`, `TILE_SCALE`, `SIDE_STYLE`, `COLOR_MODE`, …).
4. Run the script.

By default the script also requests `instance_json` and draws closed tile curves onto a
`Monotile-<job>` layer (`IMPORT_CURVES = True`).

`STL_EXTRUSION_MM` defaults to **0** for STL/GLB (flat caps; extrude in Rhino).

## Options (constants or `fetch_and_save(...)` kwargs)

| Option | Values |
|--------|--------|
| Mask | `rectangle`, `circle`, `square`, `triangle`, `regular_hexagon` |
| Tile scale | Larger = chunkier tiles |
| Side style | `flat`, `curvy`, `wavy`, `jagged`, `blocky` (+ amount / wavy detail) |
| Coloring | `greyscale`, `random`, `mystics`, `rainbow` (SVG / PNG / JPG) |
| SVG compact | Instanced `<use>` tiles (still SVG either way) |
| Formats | `svg`, `instance_json`, `glb`, `stl`, `png`, `jpg`, … |

## API key

First match wins:

1. `API_KEY` at the top of the script (or `api_key=` to `fetch_and_save`)
2. Environment variable `UNTILING_API_KEY`
3. File `untiling_api_key.txt` next to `untiling_patch.py` (one line)

## Grasshopper

```python
from untiling_patch import fetch_and_save

meta = fetch_and_save(
    output_dir=r"C:\Z\monotile_out",
    formats=["instance_json", "svg"],
    mask_type="rectangle",
    width=40,
    height=24,
    scale=1.0,
    side_style="curvy",
    side_style_amplitude=0.12,
    color_mode="rainbow",
    svg_compact=True,
    extrusion_mm=0.0,
    interactive=False,
    import_curves=True,
)
a = meta["files"]
```

## How it works

1. `POST /v1/patch` with mask + formats + styling.
2. Poll `GET /v1/jobs/{job_id}` until complete.
3. Download artifacts into `OUTPUT_DIR/<job_prefix>/`.
4. Optionally transform `prototile_ring_xy` by each instance affine and add curves.
5. Writes `job_meta.json` (includes the request body).

HTTP uses **urllib** only (no `requests`).

## Packaging

Zip `untiling_patch.py` + `README.md` at the archive root. Never ship a real API key.
