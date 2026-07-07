"""Cancel a stuck ``running`` job via the admin API.

Usage:
    python cancel_stuck_job.py 22334bd5-60a3-46a0-80f4-b39a2a59fa56

Env: SPECTRE_PATCH_ADMIN_TOKEN, optional SPECTRE_PATCH_SMOKE_API_BASE
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

from sync_render_env import parse_env

BASE_DEFAULT = "https://aperiodic-monotile-api.onrender.com"


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: cancel_stuck_job.py <job_id>", file=sys.stderr)
        return 2
    job_id = sys.argv[1].strip()
    env = parse_env()
    token = (env.get("SPECTRE_PATCH_ADMIN_TOKEN") or "").strip()
    base = (env.get("SPECTRE_PATCH_SMOKE_API_BASE") or BASE_DEFAULT).rstrip("/")
    if not token:
        print("SPECTRE_PATCH_ADMIN_TOKEN missing from .env", file=sys.stderr)
        return 2
    req = urllib.request.Request(
        f"{base}/v1/admin/jobs/{job_id}/cancel",
        data=b"{}",
        headers={
            "X-Admin-Token": token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        print(f"HTTP {e.code}: {raw}", file=sys.stderr)
        return 1
    print(json.dumps(body, indent=2))
    return 0 if body.get("cancelled") else 1


if __name__ == "__main__":
    raise SystemExit(main())
