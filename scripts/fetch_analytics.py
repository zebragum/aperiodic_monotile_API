#!/usr/bin/env python3
"""Fetch production analytics (requires SPECTRE_PATCH_ADMIN_TOKEN in .env)."""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / ".env", ROOT.parent / ".env"):
    if p.is_file():
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


def main() -> int:
    tok = (os.environ.get("SPECTRE_PATCH_ADMIN_TOKEN") or "").strip()
    if not tok:
        print("SPECTRE_PATCH_ADMIN_TOKEN not set in .env", file=sys.stderr)
        return 2
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 90
    for base in (
        "https://api.untiling.com",
        "https://api.aperiodicgenerator.com",
    ):
        req = urllib.request.Request(
            f"{base}/v1/admin/analytics?days={days}",
            headers={"X-Admin-Token": tok},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
        except Exception as exc:
            print(f"{base}: ERROR {exc}", file=sys.stderr)
            continue
        print(f"\n=== {base} (last {days} days) ===")
        print(json.dumps(
            {
                "totals": data.get("totals"),
                "funnel": data.get("funnel"),
                "requested_formats": data.get("requested_formats"),
                "checkout_plans": data.get("checkout_plans"),
                "sample_downloads": data.get("sample_downloads"),
                "sources": data.get("sources"),
                "recent_events": (data.get("recent_events") or [])[:10],
            },
            indent=2,
        ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
