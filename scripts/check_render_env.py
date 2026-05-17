"""Inspect Render env var names and whether API key tier JSON is present (no values printed)."""

from __future__ import annotations

import json
import sys

from sync_render_env import parse_env, render_request


def main() -> int:
    env = parse_env()
    api_key = env.get("RENDER_API_KEY", "").strip()
    service_id = env.get("RENDER_SERVICE_ID", "").strip()
    if not api_key or not service_id:
        print("Missing RENDER_API_KEY or RENDER_SERVICE_ID", file=sys.stderr)
        return 2

    existing = render_request(api_key, "GET", f"/services/{service_id}/env-vars")
    items = existing if isinstance(existing, list) else existing.get("envVars", [])
    print(f"service_id={service_id} visible_env_vars={len(items)}")

    tiers_val: str | None = None
    for item in items:
        ev = item.get("envVar", item) if isinstance(item, dict) else {}
        if not isinstance(ev, dict):
            continue
        if ev.get("key") == "SPECTRE_PATCH_API_KEY_TIERS_JSON":
            tiers_val = str(ev.get("value", ""))

    if tiers_val is None:
        print(
            "SPECTRE_PATCH_API_KEY_TIERS_JSON: not visible via Render API "
            "(secret vars are hidden). After sync_render_env.py, trigger a deploy "
            "and verify keys with curl against production."
        )
        return 0

    tier_map = json.loads(tiers_val)
    zyla = [k for k in tier_map if str(k).startswith("mono_zyla")]
    print(f"SPECTRE_PATCH_API_KEY_TIERS_JSON: visible, {len(tier_map)} keys, mono_zyla={bool(zyla)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
