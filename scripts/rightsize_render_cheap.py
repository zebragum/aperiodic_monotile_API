"""Right-size the Untiling API Render service for personal/pack use.

- Downgrade instance plan to ``standard`` (~$25/mo)
- Set SPECTRE_PATCH_WORKER_COUNT=1 (and keep launch secrets from local .env)
- Attempt disk shrink (Render usually rejects shrinks; report clearly)
- Trigger a deploy so env changes load
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sync_render_env import OPTIONAL_SYNC_KEYS, SYNC_KEYS, parse_env, render_request  # noqa: E402

TARGET_PLAN = "standard"
TARGET_DISK_GB = 10
WORKER_COUNT = "1"


def main() -> int:
    env = parse_env()
    api_key = env.get("RENDER_API_KEY", "").strip()
    service_id = env.get("RENDER_SERVICE_ID", "").strip()
    if not api_key or not service_id:
        print("Missing RENDER_API_KEY or RENDER_SERVICE_ID", file=sys.stderr)
        return 2

    before = render_request(api_key, "GET", f"/services/{service_id}")
    details = before.get("serviceDetails") or {}
    disk = details.get("disk") or {}
    print(f"before plan={details.get('plan')} disk_gb={disk.get('sizeGB')} disk_id={disk.get('id')}")

    render_request(
        api_key,
        "PATCH",
        f"/services/{service_id}",
        {"serviceDetails": {"plan": TARGET_PLAN}},
    )
    print(f"requested plan -> {TARGET_PLAN}")

    # PUT replaces the whole env set; always re-apply launch secrets from .env.
    existing = render_request(api_key, "GET", f"/services/{service_id}/env-vars")
    items = existing if isinstance(existing, list) else existing.get("envVars", [])
    env_vars: dict[str, str] = {}
    for item in items:
        ev = item.get("envVar", item) if isinstance(item, dict) else {}
        key = ev.get("key")
        if key:
            env_vars[str(key)] = str(ev.get("value", ""))
    for key in SYNC_KEYS:
        if env.get(key):
            env_vars[key] = env[key]
    for key in OPTIONAL_SYNC_KEYS:
        if env.get(key):
            env_vars[key] = env[key]
    env_vars["SPECTRE_PATCH_WORKER_COUNT"] = WORKER_COUNT
    env_vars["UVICORN_WORKERS"] = "1"
    env_vars["WEB_CONCURRENCY"] = "1"
    render_request(
        api_key,
        "PUT",
        f"/services/{service_id}/env-vars",
        [{"key": k, "value": v} for k, v in sorted(env_vars.items())],
    )
    print(f"set SPECTRE_PATCH_WORKER_COUNT={WORKER_COUNT} (secrets re-synced from .env)")

    disk_id = disk.get("id")
    current_gb = disk.get("sizeGB")
    if disk_id and current_gb and int(current_gb) > TARGET_DISK_GB:
        try:
            render_request(api_key, "PATCH", f"/disks/{disk_id}", {"sizeGB": TARGET_DISK_GB})
            print(f"requested disk -> {TARGET_DISK_GB}GB")
        except Exception as e:
            print(
                f"disk shrink not applied (expected on Render): {e}\n"
                f"  Keeping {current_gb}GB (~${float(current_gb) * 0.25:.2f}/mo). "
                "To cut this later, recreate the service with a 10GB disk.",
                file=sys.stderr,
            )
    elif current_gb:
        print(f"disk already <= target ({current_gb}GB)")

    render_request(
        api_key,
        "POST",
        f"/services/{service_id}/deploys",
        {"clearCache": "do_not_clear"},
    )
    print("deploy triggered")

    after = render_request(api_key, "GET", f"/services/{service_id}")
    ad = after.get("serviceDetails") or {}
    disk_gb = int((ad.get("disk") or {}).get("sizeGB") or 0)
    print(f"after plan={ad.get('plan')} disk_gb={disk_gb}")
    print(f"Rough Untiling API burn: ~$25 compute + ~${disk_gb * 0.25:.0f} disk /mo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
