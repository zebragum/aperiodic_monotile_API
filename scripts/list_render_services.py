"""List Render services (names/ids only, no secrets)."""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_PATHS = (ROOT / ".env", ROOT.parent / "spectre_patch_api" / ".env", ROOT / "spectre_patch_api" / ".env")


def parse_env() -> dict[str, str]:
    data: dict[str, str] = {}
    for path in ENV_PATHS:
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def main() -> int:
    env = parse_env()
    api_key = env.get("RENDER_API_KEY", "").strip()
    print("RENDER_API_KEY present:", bool(api_key))
    print("RENDER_SERVICE_ID:", env.get("RENDER_SERVICE_ID", "(not set)"))
    if not api_key:
        print("No RENDER_API_KEY — add it to .env to manage Render via API.", file=sys.stderr)
        return 2

    req = urllib.request.Request(
        "https://api.render.com/v1/services?limit=50",
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        items = json.loads(resp.read())

    print("\nRender services:")
    for item in items:
        s = item.get("service", item)
        details = s.get("serviceDetails") or {}
        url = details.get("url") or details.get("externalUrl") or ""
        print(f"  {s.get('name')}")
        print(f"    type: {s.get('type')}")
        print(f"    id:   {s.get('id')}")
        if url:
            print(f"    url:  {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
