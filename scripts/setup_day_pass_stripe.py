"""Create the $5 Day Pass Stripe price and sync to .env + Render.

Lookup key: aperiodic_monotile_day_pass_5_usd
Env var: SPECTRE_PATCH_STRIPE_PRICE_ID_DAY_PASS
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from sync_render_env import parse_env, render_request

# Solo product — Day Pass is a sibling SKU on the same product line.
SOLO_PRODUCT_ID = "prod_UWWmY0KGho0Nws"

ENV_PATHS = (
    Path(__file__).resolve().parents[2] / ".env",
    Path(__file__).resolve().parents[3] / ".env",
)


def stripe_post(secret: str, path: str, data: dict[str, str]) -> dict:
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.stripe.com/v1/{path}",
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {secret}"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def upsert_env_var(key: str, value: str) -> None:
    updated = False
    for path in ENV_PATHS:
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        out: list[str] = []
        found = False
        for line in lines:
            if line.startswith(f"{key}="):
                out.append(f"{key}={value}")
                found = True
            else:
                out.append(line)
        if not found:
            out.append(f"{key}={value}")
        path.write_text("\n".join(out) + "\n", encoding="utf-8")
        print(f"updated {path.name}: {key}")
        updated = True
    if not updated:
        raise RuntimeError(f"no .env file found to update for {key}")


def main() -> int:
    env = parse_env()
    secret = (env.get("SPECTRE_PATCH_STRIPE_SECRET_KEY") or env.get("STRIPE_API_SECRET_KEY") or "").strip()
    if not secret:
        print("Missing Stripe secret key in .env", file=sys.stderr)
        return 2

    price = stripe_post(
        secret,
        "prices",
        {
            "product": SOLO_PRODUCT_ID,
            "currency": "usd",
            "unit_amount": "500",
            "nickname": "Day Pass",
            "lookup_key": "aperiodic_monotile_day_pass_5_usd",
            "metadata[tier]": "tier_day_pass",
            "metadata[checkout_plan]": "day_pass",
        },
    )
    price_id = str(price["id"])
    print(f"created Day Pass price: {price_id}")

    upsert_env_var("SPECTRE_PATCH_STRIPE_PRICE_ID_DAY_PASS", price_id)

    rkey = env.get("RENDER_API_KEY", "").strip()
    sid = env.get("RENDER_SERVICE_ID", "").strip()
    if not rkey or not sid:
        print("Render credentials missing — .env updated locally only.", file=sys.stderr)
        return 0

    env = parse_env()
    from sync_render_env import SYNC_KEYS

    existing = render_request(rkey, "GET", f"/services/{sid}/env-vars")
    existing_items = existing if isinstance(existing, list) else existing.get("envVars", [])
    env_vars: dict[str, str] = {}
    for item in existing_items:
        env_var = item.get("envVar", item) if isinstance(item, dict) else {}
        key = env_var.get("key")
        if key:
            env_vars[str(key)] = str(env_var.get("value", ""))
    for key in SYNC_KEYS:
        if env.get(key):
            env_vars[key] = env[key]
    env_vars["SPECTRE_PATCH_STRIPE_PRICE_ID_DAY_PASS"] = price_id
    cors = env.get("SPECTRE_PATCH_CORS_ALLOW_ORIGINS", "").strip()
    if cors:
        env_vars["SPECTRE_PATCH_CORS_ALLOW_ORIGINS"] = cors
    else:
        env_vars["SPECTRE_PATCH_CORS_ALLOW_ORIGINS"] = (
            "https://untiling.com,https://www.untiling.com,"
            "https://aperiodicgenerator.com,https://www.aperiodicgenerator.com"
        )

    render_request(
        rkey,
        "PUT",
        f"/services/{sid}/env-vars",
        [{"key": key, "value": value} for key, value in sorted(env_vars.items())],
    )
    render_request(rkey, "POST", f"/services/{sid}/deploys", {"clearCache": "do_not_clear"})
    print("synced Render env + triggered deploy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
