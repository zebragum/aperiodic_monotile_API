"""Rhino / Grasshopper-friendly client for the Aperiodic Monotile API.

Run in Rhino Python Script Editor, IronPython, or CPython (Rhino 8+).
Uses urllib only — no third-party packages.

Typical use:
  1) Set API_KEY (or UNTILING_API_KEY env / untiling_api_key.txt beside this file)
  2) Set OUTPUT_DIR
  3) Choose FORMATS: "instance_json", "svg", and/or "glb" / "stl"
  4) Run the script — files are saved under OUTPUT_DIR

stl_extrusion_mm defaults to 0 when requesting STL/GLB (flat caps; extrude in Rhino).
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
# Edit these (or override via env / Grasshopper component inputs)
# ---------------------------------------------------------------------------

API_BASE = "https://api.aperiodicgenerator.com"
API_KEY = ""  # paid key; leave blank to use UNTILING_API_KEY or config file
OUTPUT_DIR = r"C:\Z\monotile_out"  # change me

# Requested formats: "instance_json", "svg", "json", "glb", "stl", ...
FORMATS = ["instance_json", "svg"]

# Rectangle mask (canonical tile units)
MASK_WIDTH = 40.0
MASK_HEIGHT = 24.0
TILE_SCALE = 1.0

# Depth for STL/GLB. Default 0 = flat tile caps only (extrude yourself in Rhino).
STL_EXTRUSION_MM = 0.0

WAIT_TIMEOUT_SECONDS = 180
POLL_INTERVAL_SECONDS = 2.0

CONFIG_FILENAME = "untiling_api_key.txt"

# ---------------------------------------------------------------------------


def _script_dir() -> Path:
    try:
        return Path(__file__).resolve().parent
    except NameError:
        # Rhino / embedded runners sometimes lack __file__
        return Path.cwd()


def load_api_key(explicit: str = "") -> str:
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


def clean_base_url(value: str) -> str:
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


def build_body(formats, width, height, scale, extrusion_mm):
    formats = [str(f).strip().lower() for f in formats if str(f).strip()]
    if not formats:
        raise ValueError("FORMATS must not be empty")
    body = {
        "formats": formats,
        "mask": {"type": "rectangle", "width": float(width), "height": float(height)},
        "scale": float(scale),
    }
    # Only send extrusion when a mesh format is requested; default depth is 0.
    mesh_fmts = {"glb", "stl", "stl_zip", "obj_zip"}
    if mesh_fmts.intersection(formats):
        body["stl_extrusion_mm"] = float(extrusion_mm)
    if "svg" in formats:
        body["svg_compact"] = True
    return body


def run_patch_job(
    api_base,
    api_key,
    body,
    wait_timeout=180,
    poll_interval=2.0,
):
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
        raise RuntimeError("Job {} did not complete. Final status: {}".format(job_id, status))

    url_payload = json_request(
        "GET", "{}/v1/jobs/{}/urls".format(api_base, job_id), api_key=api_key
    )
    urls = url_payload.get("urls") or {}
    if not urls:
        raise RuntimeError("Job completed but no download urls were returned")
    return job_id, urls


# Preferred artifact names by format (API may return a subset).
PREFERRED_FILES = {
    "svg": ("patch.svg",),
    "json": ("tiles.json",),
    "instance_json": ("spectre_instances.json",),
    "glb": ("patch.glb",),
    "stl": ("patch.stl", "spectre_proto.stl"),
    "csv": ("tiles.csv",),
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
            # Fallback: any url whose name hints at the format
            for name in urls:
                if fmt.replace("_", "") in name.replace("_", "").lower() or name.endswith(
                    ".{}".format(fmt.split("_")[0])
                ):
                    wanted.add(name)
    if not wanted:
        # Save everything if we cannot map — better than nothing for GH debugging
        wanted = set(urls.keys())
    return [(name, urls[name]) for name in sorted(wanted)]


def fetch_and_save(
    output_dir=None,
    formats=None,
    api_key=None,
    api_base=None,
    width=None,
    height=None,
    scale=None,
    extrusion_mm=None,
    wait_timeout=None,
):
    """Main entry usable from Rhino scripts or Grasshopper Python components."""
    api_base = clean_base_url(api_base if api_base is not None else API_BASE)
    api_key = load_api_key(api_key if api_key is not None else API_KEY)
    if not api_key:
        raise RuntimeError(
            "API key required. Set API_KEY, UNTILING_API_KEY, or {}".format(
                _script_dir() / CONFIG_FILENAME
            )
        )

    formats = list(formats if formats is not None else FORMATS)
    width = MASK_WIDTH if width is None else width
    height = MASK_HEIGHT if height is None else height
    scale = TILE_SCALE if scale is None else scale
    extrusion_mm = STL_EXTRUSION_MM if extrusion_mm is None else extrusion_mm
    wait_timeout = WAIT_TIMEOUT_SECONDS if wait_timeout is None else wait_timeout
    output_dir = Path(output_dir if output_dir is not None else OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    body = build_body(formats, width, height, scale, extrusion_mm)
    job_id, urls = run_patch_job(
        api_base,
        api_key,
        body,
        wait_timeout=wait_timeout,
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

    meta = {"job_id": job_id, "formats": formats, "files": saved, "urls": urls}
    meta_path = job_dir / "job_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("Done. Saved {} file(s) under {}".format(len(saved), job_dir))
    return meta


# Rhino / script-editor entry
if __name__ == "__main__":
    fetch_and_save()
