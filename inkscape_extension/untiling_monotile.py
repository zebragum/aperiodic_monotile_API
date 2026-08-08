#!/usr/bin/env python3
"""Inkscape 1.2+ effect: fetch an aperiodic monotile SVG from the hosted API.

Flow matches the Blender add-on:
  POST /v1/patch  ->  poll GET /v1/jobs/{id}  ->  GET .../urls  ->  download patch.svg

API key (first match wins):
  1) Extension UI field
  2) Environment variable UNTILING_API_KEY
  3) Config file untiling_api_key.txt next to this script (single line)
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import uuid
import urllib.error
import urllib.request
from pathlib import Path

import inkex
from inkex import etree

DEFAULT_API_BASE = "https://api.aperiodicgenerator.com"
CONFIG_FILENAME = "untiling_api_key.txt"


def _script_dir() -> Path:
    return Path(__file__).resolve().parent


def _load_api_key(ui_value: str) -> str:
    key = (ui_value or "").strip()
    if key:
        return key
    env = (os.environ.get("UNTILING_API_KEY") or "").strip()
    if env:
        return env
    cfg = _script_dir() / CONFIG_FILENAME
    if cfg.is_file():
        return cfg.read_text(encoding="utf-8").strip().splitlines()[0].strip()
    return ""


def _clean_base_url(value: str) -> str:
    return (value or DEFAULT_API_BASE).strip().rstrip("/")


def _json_request(
    method: str,
    url: str,
    *,
    api_key: str = "",
    body: dict | None = None,
    timeout: int = 60,
) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
        headers["Idempotency-Key"] = f"inkscape-{uuid.uuid4()}"
    if api_key:
        headers["X-API-Key"] = api_key.strip()
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw or "{}")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
            message = (
                (payload.get("error") or {}).get("message")
                or payload.get("detail")
                or raw
            )
        except json.JSONDecodeError:
            message = raw or str(exc)
        raise RuntimeError(f"HTTP {exc.code}: {message}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error: {exc}") from exc


def _download_bytes(url: str, *, timeout: int = 180) -> bytes:
    request = urllib.request.Request(url, headers={"Accept": "*/*"}, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _absolute_url(api_base: str, url: str) -> str:
    return f"{api_base}{url}" if url.startswith("/") else url


def _run_patch_job(
    *,
    api_base: str,
    api_key: str,
    width: float,
    height: float,
    scale: float,
    wait_timeout: int,
    svg_compact: bool,
) -> tuple[str, bytes]:
    body = {
        "formats": ["svg"],
        "mask": {"type": "rectangle", "width": float(width), "height": float(height)},
        "scale": float(scale),
        "svg_compact": bool(svg_compact),
    }
    response = _json_request("POST", f"{api_base}/v1/patch", api_key=api_key, body=body)
    job_id = response.get("job_id")
    if not job_id:
        raise RuntimeError(f"API did not return job_id: {response}")

    deadline = time.time() + max(15, int(wait_timeout))
    status = response.get("status", "queued")
    while time.time() < deadline:
        if status in {"completed", "failed", "cancelled"}:
            break
        time.sleep(2.0)
        response = _json_request("GET", f"{api_base}/v1/jobs/{job_id}", api_key=api_key)
        status = response.get("status", status)

    if status != "completed":
        raise RuntimeError(f"Job {job_id} did not complete. Final status: {status}")

    url_payload = _json_request(
        "GET", f"{api_base}/v1/jobs/{job_id}/urls", api_key=api_key
    )
    urls = url_payload.get("urls") or {}
    svg_path = urls.get("patch.svg")
    if not svg_path:
        raise RuntimeError(f"No patch.svg in job urls. Files: {', '.join(urls.keys())}")

    svg_bytes = _download_bytes(_absolute_url(api_base, svg_path))
    return job_id, svg_bytes


class UntilingMonotileEffect(inkex.EffectExtension):
    def add_arguments(self, pars):
        pars.add_argument("--api_key", type=str, default="")
        pars.add_argument("--api_base", type=str, default=DEFAULT_API_BASE)
        pars.add_argument("--width", type=float, default=40.0)
        pars.add_argument("--height", type=float, default=24.0)
        pars.add_argument("--scale", type=float, default=1.0)
        pars.add_argument("--wait_timeout", type=int, default=180)
        pars.add_argument("--svg_compact", type=inkex.Boolean, default=True)

    def effect(self):
        api_key = _load_api_key(self.options.api_key)
        if not api_key:
            raise inkex.AbortExtension(
                "API key required. Set the UI field, UNTILING_API_KEY, "
                f"or create {_script_dir() / CONFIG_FILENAME}."
            )

        api_base = _clean_base_url(self.options.api_base)
        try:
            job_id, svg_bytes = _run_patch_job(
                api_base=api_base,
                api_key=api_key,
                width=self.options.width,
                height=self.options.height,
                scale=self.options.scale,
                wait_timeout=self.options.wait_timeout,
                svg_compact=bool(self.options.svg_compact),
            )
        except Exception as exc:
            raise inkex.AbortExtension(str(exc)) from exc

        # Prefer merging into the open document. Also keep a tempfile for debugging /
        # alternate workflows that consume a file path.
        tmp = Path(tempfile.gettempdir()) / f"untiling_monotile_{job_id[:8]}.svg"
        tmp.write_bytes(svg_bytes)

        try:
            imported = etree.fromstring(svg_bytes)
        except etree.XMLSyntaxError as exc:
            raise inkex.AbortExtension(
                f"Downloaded SVG is invalid XML (saved to {tmp}): {exc}"
            ) from exc

        group = inkex.Group()
        group.set("id", f"untiling-monotile-{job_id[:8]}")
        group.label = f"Monotile {job_id[:8]}"

        # Drop nested <svg> chrome; keep drawable children.
        if imported.tag.endswith("svg"):
            for child in list(imported):
                group.append(child)
        else:
            group.append(imported)

        self.svg.get_current_layer().append(group)
        inkex.errormsg(f"Imported monotile patch {job_id} (also saved to {tmp})")


if __name__ == "__main__":
    # Allow CLI dry-run without Inkscape: write SVG to stdout when --stdout is passed.
    if "--stdout" in sys.argv:
        sys.argv = [a for a in sys.argv if a != "--stdout"]
        # Minimal argparse-free CLI for packaging tests.
        api_key = _load_api_key(os.environ.get("UNTILING_API_KEY_UI", ""))
        if not api_key:
            sys.stderr.write("Missing API key\n")
            sys.exit(2)
        width = float(os.environ.get("UNTILING_WIDTH", "40"))
        height = float(os.environ.get("UNTILING_HEIGHT", "24"))
        scale = float(os.environ.get("UNTILING_SCALE", "1"))
        timeout = int(os.environ.get("UNTILING_WAIT", "180"))
        base = _clean_base_url(os.environ.get("UNTILING_API_BASE", DEFAULT_API_BASE))
        _, svg_bytes = _run_patch_job(
            api_base=base,
            api_key=api_key,
            width=width,
            height=height,
            scale=scale,
            wait_timeout=timeout,
            svg_compact=True,
        )
        sys.stdout.buffer.write(svg_bytes)
        sys.exit(0)

    UntilingMonotileEffect().run()
