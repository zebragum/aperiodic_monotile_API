"""Download one sample artifact per supported format using a Day Pass (or paid) key.

Reads workspace-root ``.env`` for ``SPECTRE_PATCH_DAY_PASS_API_KEY`` and optional
``SPECTRE_PATCH_SMOKE_API_BASE``. Writes files under ``outputs/`` at repo root
(parent of ``spectre_patch_api``).
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


def _request(
    method: str,
    url: str,
    *,
    api_key: str = "",
    body: dict | None = None,
    timeout: float = 120.0,
) -> tuple[int, bytes]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if api_key:
        headers["X-API-Key"] = api_key
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def _json(method: str, url: str, *, api_key: str = "", body: dict | None = None) -> dict:
    status, payload = _request(method, url, api_key=api_key, body=body)
    if status >= 400:
        raise RuntimeError(f"{method} {url} failed HTTP {status}: {payload.decode('utf-8', 'replace')}")
    return json.loads(payload.decode("utf-8"))


def _wait_job(base: str, api_key: str, job_id: str, deadline_sec: float = 300.0) -> dict:
    deadline = time.time() + deadline_sec
    final: dict = {}
    while time.time() < deadline:
        final = _json("GET", f"{base}/v1/jobs/{job_id}", api_key=api_key)
        st = final.get("status")
        if st in ("completed", "failed"):
            break
        time.sleep(2.0)
    return final


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    _load_dotenv(root / ".env")
    _load_dotenv(Path(__file__).resolve().parents[1] / ".env")

    base = os.environ.get("SPECTRE_PATCH_SMOKE_API_BASE", "https://aperiodic-monotile-api.onrender.com").rstrip("/")
    api_key = (
        os.environ.get("SPECTRE_PATCH_DAY_PASS_API_KEY", "").strip()
        or os.environ.get("SPECTRE_PATCH_SMOKE_API_KEY", "").strip()
    )
    if not api_key:
        print("Set SPECTRE_PATCH_DAY_PASS_API_KEY (or SPECTRE_PATCH_SMOKE_API_KEY).", file=sys.stderr)
        return 2

    out_dir = root / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.json"
    runs: list[dict] = []

    # One job per primary artifact type; parameters vary for manual spot-checking.
    cases: list[tuple[str, dict]] = [
        (
            "01_svg",
            {
                "formats": ["svg"],
                "scale": 1.0,
                "tx": 0.25,
                "ty": -0.1,
                "rotation_deg": 15.0,
                "svg_deterministic_palette": True,
                "mask": {"type": "rectangle", "width": 28.0, "height": 18.0},
            },
        ),
        (
            "02_svgz",
            {
                "formats": ["svgz"],
                "scale": 0.9,
                "rotation_deg": -8.0,
                "svg_fill": "#2d3e50",
                "svg_stroke": "#e67e22",
                "mask": {"type": "circle", "radius": 15.0},
            },
        ),
        (
            "03_csv",
            {
                "formats": ["csv"],
                "scale": 1.1,
                "tx": 0.0,
                "ty": 0.4,
                "mask": {"type": "square", "half_side": 12.0},
            },
        ),
        (
            "04_json",
            {
                "formats": ["json"],
                "scale": 1.0,
                "rotation_deg": 22.5,
                "mask": {"type": "regular_hexagon", "circumradius": 11.0},
            },
        ),
        (
            "05_stl_mesh",
            {
                "formats": ["stl"],
                "scale": 1.0,
                "stl_extrusion_mm": 2.5,
                "mask": {"type": "circle", "radius": 10.0},
            },
        ),
        (
            "06_stl_zip",
            {
                "formats": ["stl_zip"],
                "scale": 1.05,
                "stl_extrusion_mm": 1.8,
                "mask": {"type": "triangle", "side_length": 14.0, "rotation_deg": 30.0},
            },
        ),
        (
            "07_obj_zip",
            {
                "formats": ["obj_zip"],
                "scale": 0.95,
                "stl_extrusion_mm": 1.2,
                "mask": {"type": "rounded_rect", "width": 20.0, "height": 12.0, "corner_radius": 2.0},
            },
        ),
        (
            "08_glb",
            {
                "formats": ["glb"],
                "scale": 1.0,
                "rotation_deg": 5.0,
                "stl_extrusion_mm": 1.5,
                "mask": {"type": "rectangle", "width": 22.0, "height": 14.0},
            },
        ),
        (
            "09_instance_json",
            {
                "formats": ["instance_json"],
                "scale": 1.0,
                "mask": {"type": "square", "half_side": 11.0},
            },
        ),
        (
            "10_png",
            {
                "formats": ["png"],
                "scale": 1.0,
                "png_width_px": 1024,
                "png_height_px": 768,
                "mask": {"type": "rectangle", "width": 30.0, "height": 20.0},
            },
        ),
        (
            "11_jpg",
            {
                "formats": ["jpg"],
                "scale": 1.0,
                "tx": -0.2,
                "ty": 0.15,
                "jpg_width_px": 960,
                "jpg_height_px": 720,
                "jpg_quality": 88,
                "mask": {"type": "circle", "radius": 18.0},
            },
        ),
    ]

    health_status, _ = _request("GET", f"{base}/healthz")
    if health_status != 200:
        raise RuntimeError(f"healthz failed HTTP {health_status}")

    for tag, body in cases:
        print(f"queue {tag} ...")
        job = _json("POST", f"{base}/v1/patch", api_key=api_key, body=body)
        job_id = job["job_id"]
        final = _wait_job(base, api_key, job_id)
        if final.get("status") != "completed":
            raise RuntimeError(f"{tag}: job failed: {final}")
        # Server clamps URL TTL; fixed request keeps links short-lived but usable for this run.
        urls_payload = _json(
            "GET",
            f"{base}/v1/jobs/{job_id}/urls?ttl_seconds=3600",
            api_key=api_key,
        )
        url_map = urls_payload.get("urls") or {}
        if not url_map:
            raise RuntimeError(f"{tag}: no urls for job {job_id}")
        entry = {"tag": tag, "job_id": job_id, "request": body, "files": []}
        for fname in sorted(url_map):
            rel_url = url_map[fname]
            download_url = urllib.parse.urljoin(base, rel_url)
            st, data = _request("GET", download_url, timeout=180.0)
            if st != 200:
                raise RuntimeError(f"{tag}: download {fname} failed HTTP {st}")
            dest = out_dir / f"{tag}__{fname}"
            dest.write_bytes(data)
            entry["files"].append({"name": fname, "path": str(dest), "bytes": len(data)})
            print(f"  saved {dest.name} ({len(data)} bytes)")
        runs.append(entry)

    manifest_path.write_text(json.dumps({"base": base, "runs": runs}, indent=2), encoding="utf-8")
    print(f"wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
