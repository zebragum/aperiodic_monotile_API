# Aperiodic Monotile — Inkscape extension

Minimal Inkscape 1.2+ effect that calls the hosted
[Aperiodic Monotile API](https://api.aperiodicgenerator.com), downloads `patch.svg`,
and inserts it into the current document.

## Install

1. Copy **these files** into your Inkscape user extensions folder:
   - `untiling_monotile.inx`
   - `untiling_monotile.py`
   - `cacert.pem` (required — Inkscape’s Python often has no CA store on Windows)
2. Restart Inkscape (or open Extensions → Refresh if available).
3. Open **Extensions → Aperiodic Monotile → Aperiodic Monotile Patch (API)**.

### Extensions folder locations

| OS | Typical path |
|----|----------------|
| Windows | `%APPDATA%\inkscape\extensions` |
| macOS | `~/Library/Application Support/org.inkscape.Inkscape/config/inkscape/extensions` |
| Linux | `~/.config/inkscape/extensions` |

In Inkscape: **Edit → Preferences → System → User extensions** shows the exact folder.

## API key

Pick one (first match wins):

1. Paste the key in the extension dialog.
2. Set environment variable `UNTILING_API_KEY`.
3. Create `untiling_api_key.txt` next to `untiling_monotile.py` with a single line containing the key.

SVG export needs a **paid** API key (free tier is raster-only).

## Parameters

| UI field | Behavior |
|----------|----------|
| Match page aspect ratio | On by default — mask uses the page’s aspect (short side ≈ 21, like A4 21×29) |
| Mask width / height | Used only when match-page is off (defaults 21×29) |
| Tile size | Larger = bigger / chunkier tiles (API `scale`) |
| Side style | Flat / Curvy / Wavy / Jagged / Blocky (same presets as Blender; no custom guide line yet) |
| Side style amount | How strong curvy/wavy/jagged/blocky is |
| Center and fit to page | On by default — scales and centers the import on the page |
| Compact SVG | `svg_compact` |
| Max wait | Client-side poll timeout (seconds) |

No STL extrusion / depth field — this extension requests `formats: ["svg"]` only.

## Packaging (zip-ready)

To distribute a drop-in zip for users:

```text
untiling_inkscape_extension.zip
├── untiling_monotile.inx
├── untiling_monotile.py
└── cacert.pem
```

Zip the **files at the archive root** (do not nest them in an extra folder unless you tell users to flatten on install). Users unzip / copy all three files into the Inkscape extensions folder and restart Inkscape.

Example (from this directory):

```powershell
Compress-Archive -Path untiling_monotile.inx, untiling_monotile.py, cacert.pem `
  -DestinationPath untiling_inkscape_extension.zip -Force
```

```bash
zip untiling_inkscape_extension.zip untiling_monotile.inx untiling_monotile.py cacert.pem
```

Optional: include a one-line `untiling_api_key.txt.example` in the zip, but never ship a real key.

## How it works

1. `POST /v1/patch` with `formats: ["svg"]` and a rectangle mask.
2. Poll `GET /v1/jobs/{job_id}` until `completed` (or timeout).
3. `GET /v1/jobs/{job_id}/urls`, download `patch.svg`.
4. Append a group to the current layer; also write a tempfile under the OS temp dir for debugging.

Uses **urllib** only for HTTP (no `requests`). `inkex` is provided by Inkscape.

## Troubleshooting

- **Missing API key** — set UI / env / config file as above.
- **Free tier error** — SVG is not on the free raster preview tier; use a paid key.
- **Timeout** — raise Max wait; the server job may still finish later.
- **Network blocked** — Inkscape’s Python must reach `https://api.aperiodicgenerator.com`.
- **SSL CERTIFICATE_VERIFY_FAILED** — copy `cacert.pem` next to `untiling_monotile.py` (included in the zip). Restart Inkscape.
