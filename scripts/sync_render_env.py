"""Sync launch secrets from .env into a Render service.

The script intentionally prints only env var names, never values.

Required in .env or process env:
  RENDER_API_KEY
  RENDER_SERVICE_ID

Reads Stripe/API launch vars from .env and updates the Render service env group.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ENV_PATHS = (ROOT / ".env", ROOT.parent / ".env")
RENDER_API = "https://api.render.com/v1"

SYNC_KEYS = [
    "SPECTRE_PATCH_API_KEY_TIERS_JSON",
    "SPECTRE_PATCH_ADMIN_TOKEN",
    "SPECTRE_PATCH_STRIPE_SECRET_KEY",
    "SPECTRE_PATCH_STRIPE_PRICE_ID_STUDIO",
    "SPECTRE_PATCH_STRIPE_PRICE_ID_DAY_PASS",
    "SPECTRE_PATCH_STRIPE_PRICE_ID_SOLO_MONTHLY",
    "SPECTRE_PATCH_STRIPE_PRICE_ID_SOLO_YEARLY",
    "SPECTRE_PATCH_STRIPE_PRICE_ID_LIFETIME",
    "SPECTRE_PATCH_STRIPE_PRICE_ID_TEAMS_MONTHLY",
    "SPECTRE_PATCH_STRIPE_PRICE_ID_TEAMS_YEARLY",
    "SPECTRE_PATCH_STRIPE_WEBHOOK_SECRET",
    "SPECTRE_PATCH_PUBLIC_SITE_URL",
    "SPECTRE_PATCH_CORS_ALLOW_ORIGINS",
]


def parse_env() -> dict[str, str]:
    data = dict(os.environ)
    for path in ENV_PATHS:
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            data[key.strip()] = value.strip().strip('"').strip("'")

    if not data.get("SPECTRE_PATCH_STRIPE_SECRET_KEY") and data.get("STRIPE_API_SECRET_KEY"):
        data["SPECTRE_PATCH_STRIPE_SECRET_KEY"] = data["STRIPE_API_SECRET_KEY"]
    if not data.get("SPECTRE_PATCH_CORS_ALLOW_ORIGINS") and data.get("SPECTRE_PATCH_PUBLIC_SITE_URL"):
        data["SPECTRE_PATCH_CORS_ALLOW_ORIGINS"] = data["SPECTRE_PATCH_PUBLIC_SITE_URL"]

    return data


def render_request(api_key: str, method: str, path: str, body: object | None = None) -> object:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        RENDER_API + path,
        data=payload,
        method=method,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"Render {method} {path} failed HTTP {e.code}: {raw}") from e


def main() -> int:
    env = parse_env()
    api_key = env.get("RENDER_API_KEY", "").strip()
    service_id = env.get("RENDER_SERVICE_ID", "").strip()
    if not api_key or not service_id:
        print("Missing RENDER_API_KEY or RENDER_SERVICE_ID. No Render changes made.", file=sys.stderr)
        return 2

    missing = [key for key in SYNC_KEYS if not env.get(key)]
    if missing:
        print("Missing required env vars: " + ", ".join(missing), file=sys.stderr)
        return 2

    existing = render_request(api_key, "GET", f"/services/{service_id}/env-vars")
    existing_items = existing if isinstance(existing, list) else existing.get("envVars", [])
    env_vars: dict[str, str] = {}
    for item in existing_items:
        env_var = item.get("envVar", item) if isinstance(item, dict) else {}
        key = env_var.get("key")
        if key:
            env_vars[str(key)] = str(env_var.get("value", ""))
    for key in SYNC_KEYS:
        env_vars[key] = env[key]

    render_request(
        api_key,
        "PUT",
        f"/services/{service_id}/env-vars",
        [{"key": key, "value": value} for key, value in sorted(env_vars.items())],
    )

    for key in SYNC_KEYS:
        print(f"synced {key}")

    # Env changes are not picked up until the service restarts. Secret vars such as
    # SPECTRE_PATCH_API_KEY_TIERS_JSON also do not appear in GET /env-vars, so we
    # always trigger a deploy after updating launch secrets.
    try:
        render_request(api_key, "POST", f"/services/{service_id}/deploys", {"clearCache": "do_not_clear"})
        print("triggered Render deploy (required for new API keys in SPECTRE_PATCH_API_KEY_TIERS_JSON)")
    except Exception as e:
        print(f"WARNING: env updated but deploy trigger failed: {e}", file=sys.stderr)
        print("Manually restart the Render service or new API keys will 403.", file=sys.stderr)

    print("Render env sync complete. Values were not printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
