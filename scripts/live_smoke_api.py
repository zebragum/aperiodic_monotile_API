"""Live API smoke test for a deployed Aperiodic Monotile API.

This intentionally avoids Stripe. It assumes you already have a free or paid
API key from the deployment environment.

Usage:
    SPECTRE_PATCH_SMOKE_API_BASE=https://aperiodic-monotile-api.onrender.com \
    SPECTRE_PATCH_SMOKE_API_KEY=free_xxx \
    python scripts/live_smoke_api.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def _request(
    method: str,
    url: str,
    *,
    api_key: str = "",
    body: dict | None = None,
    timeout: float = 30.0,
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


def main() -> int:
    base = os.environ.get("SPECTRE_PATCH_SMOKE_API_BASE", "https://aperiodic-monotile-api.onrender.com").rstrip("/")
    api_key = os.environ.get("SPECTRE_PATCH_SMOKE_API_KEY", "").strip()
    if not api_key:
        print("Set SPECTRE_PATCH_SMOKE_API_KEY to a deployed free or paid API key.", file=sys.stderr)
        return 2

    print(f"smoke: base={base}")
    health_status, _ = _request("GET", f"{base}/healthz")
    if health_status != 200:
        raise RuntimeError(f"healthz failed HTTP {health_status}")
    print("smoke: healthz ok")

    ready = _json("GET", f"{base}/readyz", api_key=api_key)
    if not ready.get("db") or not ready.get("storage"):
        raise RuntimeError(f"readyz not ready: {ready}")
    print(f"smoke: readyz ok {ready}")

    caps = _json("GET", f"{base}/v1/capabilities", api_key=api_key)
    print(f"smoke: capabilities tier={caps.get('tier')} formats={caps.get('supported_formats')}")

    body = {
        "formats": ["png", "jpg"],
        "mask": {"type": "circle", "radius": 16.0},
        "png_width_px": 512,
        "png_height_px": 512,
        "jpg_width_px": 512,
        "jpg_height_px": 512,
        "jpg_quality": 90,
    }
    job = _json("POST", f"{base}/v1/patch", api_key=api_key, body=body)
    job_id = job["job_id"]
    print(f"smoke: queued job_id={job_id}")

    final = {}
    deadline = time.time() + 120.0
    while time.time() < deadline:
        final = _json("GET", f"{base}/v1/jobs/{job_id}", api_key=api_key)
        status = final.get("status")
        print(f"smoke: job status={status}")
        if status in {"completed", "failed"}:
            break
        time.sleep(2.0)
    if final.get("status") != "completed":
        raise RuntimeError(f"job did not complete: {final}")

    urls = _json("GET", f"{base}/v1/jobs/{job_id}/urls?ttl_seconds=300", api_key=api_key)
    for filename in ("patch.png", "patch.jpg"):
        rel_url = urls["urls"].get(filename)
        if not rel_url:
            raise RuntimeError(f"missing expected raster artifact: {filename}; urls={urls}")
        download_url = urllib.parse.urljoin(base, rel_url)
        status, artifact = _request("GET", download_url, api_key=api_key, timeout=60.0)
        if status != 200 or len(artifact) < 100:
            raise RuntimeError(f"{filename} download failed HTTP {status} bytes={len(artifact)}")
        print(f"smoke: downloaded {filename} bytes={len(artifact)}")
    print("smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
