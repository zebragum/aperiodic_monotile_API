"""Rhino / Grasshopper client for the Aperiodic Monotile API.

Parity with the Inkscape extension / Blender add-on for generation options:
  side styles, coloring, tile scale, masks, svg_compact, multi-format download,
  and (when run inside Rhino) interactive prompts + curve import.

Run in Rhino Script Editor (Rhino 8 CPython recommended), or call
``fetch_and_save(...)`` from Grasshopper.

Typical use:
  1) Set API_KEY (or UNTILING_API_KEY / untiling_api_key.txt)
  2) Set OUTPUT_DIR
  3) Tune options below — or leave INTERACTIVE = True and answer prompts in Rhino
  4) Run — files save under OUTPUT_DIR; curves can be drawn into the document
"""

from __future__ import annotations

import json
import os
import time
import uuid
import urllib.error
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Edit these (or override via env / interactive prompts / Grasshopper inputs)
# ---------------------------------------------------------------------------

API_BASE = "https://api.aperiodicgenerator.com"
API_KEY = ""  # paid key; leave blank to use UNTILING_API_KEY or config file
OUTPUT_DIR = r"C:\Z\monotile_out"  # change me

# When True and rhinoscriptsyntax is available, prompt for key options in Rhino.
INTERACTIVE = True
# After download, draw tile outlines into the active Rhino document.
IMPORT_CURVES = True
# Also try Rhino's SVG importer when patch.svg is present.
IMPORT_SVG = False

# Formats: "instance_json", "svg", "json", "glb", "stl", "png", "jpg", ...
FORMATS = ["instance_json", "svg"]

# Mask: rectangle | circle | square | triangle | regular_hexagon
MASK_TYPE = "rectangle"
MASK_WIDTH = 40.0
MASK_HEIGHT = 24.0
MASK_SIZE = 20.0  # radius / side / half-side for non-rect masks

TILE_SCALE = 1.0  # larger = chunkier tiles

# Side style (same presets as Blender / Inkscape)
SIDE_STYLE = "flat"  # flat | curvy | wavy | jagged | blocky
SIDE_STYLE_AMPLITUDE = 0.12
SIDE_STYLE_WAVY_SEGMENTS = 10

# SVG / raster coloring (also affects PNG/JPG when those formats are requested)
# greyscale | random | mystics | rainbow
COLOR_MODE = "greyscale"
SVG_COMPACT = True

# Depth for STL/GLB. Default 0 = flat caps (extrude yourself in Rhino).
STL_EXTRUSION_MM = 0.0

WAIT_TIMEOUT_SECONDS = 180
POLL_INTERVAL_SECONDS = 2.0

CONFIG_FILENAME = "untiling_api_key.txt"

SIDE_STYLES = ("flat", "curvy", "wavy", "jagged", "blocky")
COLOR_MODES = ("greyscale", "random", "mystics", "rainbow")
MASK_TYPES = ("rectangle", "circle", "square", "triangle", "regular_hexagon")

_GREY_FILL = "#cdd6ea"
_GREY_STROKE = "#171b38"
_LABEL_COLORS = {
    "Gamma": "#E8B923",
    "Delta": "#2E86AB",
    "Theta": "#A23B72",
    "Lambda": "#F18F01",
    "Xi": "#C73E1D",
    "Pi": "#3B1F2B",
    "Sigma": "#44AF69",
    "Phi": "#5C4D7D",
    "Psi": "#9B5DE5",
    "Gamma1": "#F4D35E",
    "Gamma2": "#FFE066",
}

# ---------------------------------------------------------------------------


def _script_dir():
    try:
        return Path(__file__).resolve().parent
    except NameError:
        return Path.cwd()


def load_api_key(explicit=""):
    key = (explicit or "").strip()
    if key:
        return key
    env = (os.environ.get("UNTILING_API_KEY") or "").strip()
    if env:
        return env
    cfg = _script_dir() / CONFIG_FILENAME
    if cfg.is_file():
        return cfg.read_text(encoding="utf-8").strip().splitlines()[0].strip()
    return ""


def clean_base_url(value):
    return (value or API_BASE).strip().rstrip("/")


def json_request(method, url, api_key="", body=None, timeout=60):
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
        headers["Idempotency-Key"] = "rhino-{}".format(uuid.uuid4())
    if api_key:
        headers["X-API-Key"] = api_key.strip()
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        response = urllib.request.urlopen(request, timeout=timeout)
        try:
            raw = response.read().decode("utf-8")
            return json.loads(raw or "{}")
        finally:
            response.close()
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
            err = payload.get("error") or {}
            message = err.get("message") or payload.get("detail") or raw
        except Exception:
            message = raw or str(exc)
        raise RuntimeError("HTTP {}: {}".format(exc.code, message))
    except urllib.error.URLError as exc:
        raise RuntimeError("Network error: {}".format(exc))


def download_file(url, path, timeout=180):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"Accept": "*/*"}, method="GET")
    response = urllib.request.urlopen(request, timeout=timeout)
    try:
        path.write_bytes(response.read())
    finally:
        response.close()


def absolute_url(api_base, url):
    if url.startswith("/"):
        return "{}{}".format(api_base, url)
    return url


def _palette_entry(fill, stroke=_GREY_STROKE):
    return {"fill": fill, "stroke": stroke}


def color_request_fields(color_mode):
    """Map color mode → API SVG / raster coloring fields (same as Inkscape)."""

    mode = (color_mode or "greyscale").strip().lower()
    if mode not in COLOR_MODES:
        mode = "greyscale"

    if mode == "random":
        return {
            "svg_fill": _GREY_FILL,
            "svg_stroke": _GREY_STROKE,
            "svg_deterministic_palette": True,
        }

    if mode == "mystics":
        return {
            "svg_fill": _GREY_FILL,
            "svg_stroke": _GREY_STROKE,
            "palette_by_label": {
                "Gamma": _palette_entry("#E8B923"),
                "Gamma1": _palette_entry("#F4D35E"),
                "Gamma2": _palette_entry("#FFE066"),
                "*": _palette_entry("#b8becc"),
            },
        }

    if mode == "rainbow":
        palette = {label: _palette_entry(fill) for label, fill in _LABEL_COLORS.items()}
        palette["*"] = _palette_entry(_GREY_FILL)
        return {
            "svg_fill": _GREY_FILL,
            "svg_stroke": _GREY_STROKE,
            "palette_by_label": palette,
        }

    return {
        "svg_fill": _GREY_FILL,
        "svg_stroke": _GREY_STROKE,
        "svg_deterministic_palette": False,
    }


def build_mask(mask_type, width, height, size):
    kind = (mask_type or "rectangle").strip().lower()
    if kind not in MASK_TYPES:
        kind = "rectangle"
    size = max(0.1, float(size))
    if kind == "circle":
        return {"type": "circle", "radius": size}
    if kind == "square":
        return {"type": "square", "half_side": size}
    if kind == "triangle":
        return {"type": "triangle", "side_length": size}
    if kind == "regular_hexagon":
        return {"type": "regular_hexagon", "circumradius": size}
    return {
        "type": "rectangle",
        "width": max(0.1, float(width)),
        "height": max(0.1, float(height)),
    }


def build_body(
    formats,
    *,
    mask_type="rectangle",
    width=40.0,
    height=24.0,
    size=20.0,
    scale=1.0,
    extrusion_mm=0.0,
    side_style="flat",
    side_style_amplitude=0.12,
    side_style_wavy_segments=10,
    color_mode="greyscale",
    svg_compact=True,
):
    formats = [str(f).strip().lower() for f in formats if str(f).strip()]
    if not formats:
        raise ValueError("FORMATS must not be empty")

    body = {
        "formats": formats,
        "mask": build_mask(mask_type, width, height, size),
        "scale": max(0.05, float(scale)),
    }

    mesh_fmts = {"glb", "stl", "stl_zip", "obj_zip"}
    if mesh_fmts.intersection(formats):
        body["stl_extrusion_mm"] = float(extrusion_mm)

    style = (side_style or "flat").strip().lower()
    if style not in SIDE_STYLES:
        style = "flat"
    if style != "flat":
        body["side_style"] = style
        body["side_style_amplitude"] = max(0.0, min(0.75, float(side_style_amplitude)))
        if style == "wavy":
            body["side_style_wavy_segments"] = max(
                4, min(64, int(side_style_wavy_segments))
            )

    visual_fmts = {"svg", "svgz", "png", "jpg", "jpeg"}
    if visual_fmts.intersection(formats):
        body.update(color_request_fields(color_mode))
    if "svg" in formats:
        body["svg_compact"] = bool(svg_compact)

    return body


def run_patch_job(api_base, api_key, body, wait_timeout=180, poll_interval=2.0):
    print("Submitting POST {}/v1/patch ...".format(api_base))
    response = json_request("POST", "{}/v1/patch".format(api_base), api_key=api_key, body=body)
    job_id = response.get("job_id")
    if not job_id:
        raise RuntimeError("API did not return job_id: {}".format(response))
    print("Job {} queued (status={})".format(job_id, response.get("status")))

    deadline = time.time() + max(15, int(wait_timeout))
    status = response.get("status", "queued")
    while time.time() < deadline:
        if status in ("completed", "failed", "cancelled"):
            break
        time.sleep(float(poll_interval))
        response = json_request(
            "GET", "{}/v1/jobs/{}".format(api_base, job_id), api_key=api_key
        )
        status = response.get("status", status)
        print("  status={}".format(status))

    if status != "completed":
        raise RuntimeError(
            "Job {} did not complete. Final status: {}".format(job_id, status)
        )

    url_payload = json_request(
        "GET", "{}/v1/jobs/{}/urls".format(api_base, job_id), api_key=api_key
    )
    urls = url_payload.get("urls") or {}
    if not urls:
        raise RuntimeError("Job completed but no download urls were returned")
    return job_id, urls


PREFERRED_FILES = {
    "svg": ("patch.svg",),
    "json": ("tiles.json",),
    "instance_json": ("spectre_instances.json",),
    "glb": ("patch.glb",),
    "stl": ("patch.stl", "spectre_proto.stl"),
    "csv": ("tiles.csv",),
    "png": ("patch.png",),
    "jpg": ("patch.jpg", "patch.jpeg"),
    "jpeg": ("patch.jpg", "patch.jpeg"),
}


def select_downloads(formats, urls):
    """Return list of (filename, url) to save for the requested formats."""
    wanted = set()
    for fmt in formats:
        for name in PREFERRED_FILES.get(fmt, ()):
            if name in urls:
                wanted.add(name)
                break
        else:
            for name in urls:
                if fmt.replace("_", "") in name.replace("_", "").lower() or name.endswith(
                    ".{}".format(fmt.split("_")[0])
                ):
                    wanted.add(name)
    if not wanted:
        wanted = set(urls.keys())
    return [(name, urls[name]) for name in sorted(wanted)]


def _transform_xy(affine4, x, y):
    """Apply 4×4 row-major affine to a 2D point (z=0)."""

    m = affine4
    xp = float(m[0][0]) * x + float(m[0][1]) * y + float(m[0][3])
    yp = float(m[1][0]) * x + float(m[1][1]) * y + float(m[1][3])
    return xp, yp


def import_curves_from_instances(manifest_path, layer_name="Monotile"):
    """Draw closed polylines into Rhino from spectre_instances.json."""

    try:
        import rhinoscriptsyntax as rs  # type: ignore
        import scriptcontext as sc  # type: ignore
        import Rhino  # type: ignore
    except ImportError:
        print("Rhino APIs unavailable — curves not imported (files still on disk).")
        return 0

    data = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    ring = data.get("prototile_ring_xy") or []
    instances = data.get("instances") or []
    if not ring or not instances:
        print("Manifest missing prototile_ring_xy / instances.")
        return 0

    if not rs.IsLayer(layer_name):
        rs.AddLayer(layer_name)
    rs.CurrentLayer(layer_name)

    count = 0
    for inst in instances:
        rows = inst.get("affine4_row_lists")
        if not rows or len(rows) != 4:
            continue
        pts = []
        for xy in ring:
            xp, yp = _transform_xy(rows, float(xy[0]), float(xy[1]))
            pts.append(Rhino.Geometry.Point3d(xp, yp, 0.0))
        if len(pts) < 3:
            continue
        if pts[0].DistanceTo(pts[-1]) > 1e-9:
            pts.append(pts[0])
        curve = Rhino.Geometry.PolylineCurve(pts)
        if curve is None or not curve.IsValid:
            continue
        sc.doc.Objects.AddCurve(curve)
        count += 1

    sc.doc.Views.Redraw()
    print("Imported {} tile curve(s) onto layer '{}'.".format(count, layer_name))
    return count


def import_svg_file(svg_path):
    """Best-effort SVG import via Rhino command (version-dependent)."""

    try:
        import rhinoscriptsyntax as rs  # type: ignore
    except ImportError:
        return False
    path = str(Path(svg_path).resolve())
    if not Path(path).is_file():
        return False
    # Silent import; may no-op on builds without SVG support.
    ok = rs.Command('_-Import "{}" _Enter'.format(path), echo=False)
    return bool(ok)


def _prompt_choice(rs, message, options, default):
    options = list(options)
    default = default if default in options else options[0]
    choice = rs.GetString(message, default, options)
    if not choice:
        return default
    choice = str(choice).strip().lower()
    for opt in options:
        if opt.lower() == choice or opt.lower().startswith(choice):
            return opt
    return default


def prompt_rhino_options(defaults):
    """Interactive overrides when running inside Rhino."""

    try:
        import rhinoscriptsyntax as rs  # type: ignore
    except ImportError:
        return defaults

    opts = dict(defaults)
    rs.MessageBox(
        "Aperiodic Monotile — generation options.\n"
        "Cancel any prompt to keep the current/default value.",
        0,
        "Untiling / Aperiodic Generator",
    )

    fmt_pick = _prompt_choice(
        rs,
        "Primary format",
        ["svg", "instance_json", "glb", "stl", "png", "jpg"],
        (opts.get("formats") or ["svg"])[0],
    )
    # Keep companion instance_json when drawing curves for mesh/svg workflows.
    if fmt_pick == "svg":
        opts["formats"] = ["svg", "instance_json"]
    elif fmt_pick == "instance_json":
        opts["formats"] = ["instance_json"]
    else:
        opts["formats"] = [fmt_pick]

    opts["mask_type"] = _prompt_choice(
        rs, "Mask shape", list(MASK_TYPES), opts.get("mask_type", "rectangle")
    )
    if opts["mask_type"] == "rectangle":
        w = rs.GetReal("Mask width", float(opts.get("width", 40.0)), 0.1)
        h = rs.GetReal("Mask height", float(opts.get("height", 24.0)), 0.1)
        if w:
            opts["width"] = float(w)
        if h:
            opts["height"] = float(h)
    else:
        s = rs.GetReal("Mask size (radius / side)", float(opts.get("size", 20.0)), 0.1)
        if s:
            opts["size"] = float(s)

    scale = rs.GetReal("Tile size / scale (larger = chunkier)", float(opts.get("scale", 1.0)), 0.05)
    if scale:
        opts["scale"] = float(scale)

    opts["side_style"] = _prompt_choice(
        rs, "Side style", list(SIDE_STYLES), opts.get("side_style", "flat")
    )
    if opts["side_style"] != "flat":
        amp = rs.GetReal(
            "Side style amount", float(opts.get("side_style_amplitude", 0.12)), 0.0, 0.75
        )
        if amp is not None:
            opts["side_style_amplitude"] = float(amp)
        if opts["side_style"] == "wavy":
            segs = rs.GetInteger(
                "Wavy detail", int(opts.get("side_style_wavy_segments", 10)), 4, 64
            )
            if segs:
                opts["side_style_wavy_segments"] = int(segs)

    if any(f in ("svg", "png", "jpg", "jpeg") for f in opts["formats"]):
        opts["color_mode"] = _prompt_choice(
            rs,
            "Coloring",
            list(COLOR_MODES),
            opts.get("color_mode", "greyscale"),
        )
        if "svg" in opts["formats"]:
            compact = rs.GetString(
                "Smaller SVG file (instanced tiles)?",
                "Yes" if opts.get("svg_compact", True) else "No",
                ["Yes", "No"],
            )
            opts["svg_compact"] = str(compact or "Yes").lower().startswith("y")

    if any(f in ("glb", "stl") for f in opts["formats"]):
        depth = rs.GetReal(
            "Thickness / extrusion (mm)", float(opts.get("extrusion_mm", 0.0)), 0.0
        )
        if depth is not None:
            opts["extrusion_mm"] = float(depth)

    folder = rs.BrowseForFolder(
        opts.get("output_dir") or OUTPUT_DIR, "Output folder for downloads"
    )
    if folder:
        opts["output_dir"] = folder

    return opts


def fetch_and_save(
    output_dir=None,
    formats=None,
    api_key=None,
    api_base=None,
    mask_type=None,
    width=None,
    height=None,
    size=None,
    scale=None,
    extrusion_mm=None,
    side_style=None,
    side_style_amplitude=None,
    side_style_wavy_segments=None,
    color_mode=None,
    svg_compact=None,
    wait_timeout=None,
    import_curves=None,
    import_svg=None,
    interactive=None,
):
    """Main entry usable from Rhino scripts or Grasshopper Python components."""

    opts = {
        "output_dir": output_dir if output_dir is not None else OUTPUT_DIR,
        "formats": list(formats if formats is not None else FORMATS),
        "api_key": api_key if api_key is not None else API_KEY,
        "api_base": api_base if api_base is not None else API_BASE,
        "mask_type": mask_type if mask_type is not None else MASK_TYPE,
        "width": MASK_WIDTH if width is None else width,
        "height": MASK_HEIGHT if height is None else height,
        "size": MASK_SIZE if size is None else size,
        "scale": TILE_SCALE if scale is None else scale,
        "extrusion_mm": STL_EXTRUSION_MM if extrusion_mm is None else extrusion_mm,
        "side_style": SIDE_STYLE if side_style is None else side_style,
        "side_style_amplitude": (
            SIDE_STYLE_AMPLITUDE if side_style_amplitude is None else side_style_amplitude
        ),
        "side_style_wavy_segments": (
            SIDE_STYLE_WAVY_SEGMENTS
            if side_style_wavy_segments is None
            else side_style_wavy_segments
        ),
        "color_mode": COLOR_MODE if color_mode is None else color_mode,
        "svg_compact": SVG_COMPACT if svg_compact is None else svg_compact,
        "wait_timeout": WAIT_TIMEOUT_SECONDS if wait_timeout is None else wait_timeout,
        "import_curves": IMPORT_CURVES if import_curves is None else import_curves,
        "import_svg": IMPORT_SVG if import_svg is None else import_svg,
    }

    do_interactive = INTERACTIVE if interactive is None else interactive
    if do_interactive:
        opts = prompt_rhino_options(opts)

    api_base = clean_base_url(opts["api_base"])
    api_key = load_api_key(opts["api_key"])
    if not api_key:
        raise RuntimeError(
            "API key required. Set API_KEY, UNTILING_API_KEY, or {}".format(
                _script_dir() / CONFIG_FILENAME
            )
        )

    formats = list(opts["formats"])
    # Ensure instance_json is present when curve import is requested.
    if opts["import_curves"] and "instance_json" not in formats:
        formats.append("instance_json")

    output_dir = Path(opts["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    body = build_body(
        formats,
        mask_type=opts["mask_type"],
        width=opts["width"],
        height=opts["height"],
        size=opts["size"],
        scale=opts["scale"],
        extrusion_mm=opts["extrusion_mm"],
        side_style=opts["side_style"],
        side_style_amplitude=opts["side_style_amplitude"],
        side_style_wavy_segments=opts["side_style_wavy_segments"],
        color_mode=opts["color_mode"],
        svg_compact=opts["svg_compact"],
    )
    job_id, urls = run_patch_job(
        api_base,
        api_key,
        body,
        wait_timeout=opts["wait_timeout"],
        poll_interval=POLL_INTERVAL_SECONDS,
    )

    job_dir = output_dir / job_id[:8]
    job_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for filename, rel_url in select_downloads(formats, urls):
        dest = job_dir / filename
        print("Downloading {} -> {}".format(filename, dest))
        download_file(absolute_url(api_base, rel_url), dest)
        saved.append(str(dest))

    imported = 0
    if opts["import_curves"]:
        inst_path = job_dir / "spectre_instances.json"
        if inst_path.is_file():
            imported = import_curves_from_instances(
                inst_path, layer_name="Monotile-{}".format(job_id[:8])
            )

    if opts["import_svg"]:
        svg_path = job_dir / "patch.svg"
        if svg_path.is_file():
            import_svg_file(svg_path)

    meta = {
        "job_id": job_id,
        "formats": formats,
        "files": saved,
        "urls": urls,
        "request": body,
        "imported_curves": imported,
    }
    meta_path = job_dir / "job_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("Done. Saved {} file(s) under {}".format(len(saved), job_dir))
    return meta


if __name__ == "__main__":
    fetch_and_save()
