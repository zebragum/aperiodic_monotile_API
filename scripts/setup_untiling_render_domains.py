"""Register untiling.com custom domains on Render and print Bluehost DNS steps."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_PATHS = (ROOT / ".env", ROOT.parent / ".env", ROOT / "spectre_patch_api" / ".env")

SITE_SERVICE_ID = "srv-d7r6ue8g4nts73chb9kg"  # aperiodic-monotile-site
API_SERVICE_ID = "srv-d7r4ka1kh4rs73ekmr90"  # aperiodic-monotile-api

SITE_DOMAINS = ["untiling.com", "www.untiling.com"]
API_DOMAINS = ["api.untiling.com"]


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


def render_request(api_key: str, method: str, path: str, body: object | None = None) -> object:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        "https://api.render.com/v1" + path,
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
        raise RuntimeError(f"Render {method} {path} HTTP {e.code}: {raw}") from e


def list_domains(api_key: str, service_id: str) -> list[dict]:
    data = render_request(api_key, "GET", f"/services/{service_id}/custom-domains")
    out = []
    for item in data if isinstance(data, list) else []:
        cd = item.get("customDomain", item)
        out.append(cd)
    return out


def add_domain(api_key: str, service_id: str, name: str) -> dict:
    return render_request(api_key, "POST", f"/services/{service_id}/custom-domains", {"name": name})


def ensure_domain(api_key: str, service_id: str, name: str) -> dict:
    existing = {d.get("name"): d for d in list_domains(api_key, service_id)}
    if name in existing:
        print(f"  already registered: {name}")
        return existing[name]
    result = add_domain(api_key, service_id, name)
    if isinstance(result, list) and result:
        cd = result[0].get("customDomain", result[0])
    elif isinstance(result, dict):
        cd = result.get("customDomain", result)
    else:
        cd = result
    print(f"  added: {name}")
    return cd


def main() -> int:
    env = parse_env()
    api_key = env.get("RENDER_API_KEY", "").strip()
    if not api_key:
        print("Missing RENDER_API_KEY in .env", file=sys.stderr)
        return 2

    print("=== Registering custom domains on Render ===\n")
    print("Static site (aperiodic-monotile-site):")
    for name in SITE_DOMAINS:
        ensure_domain(api_key, SITE_SERVICE_ID, name)

    print("\nAPI (aperiodic-monotile-api):")
    for name in API_DOMAINS:
        ensure_domain(api_key, API_SERVICE_ID, name)

    print("\n=== Current domain status ===\n")
    print("SITE:")
    for d in list_domains(api_key, SITE_SERVICE_ID):
        print(f"  {d.get('name')}  type={d.get('domainType')}  status={d.get('verificationStatus')}")

    print("\nAPI:")
    for d in list_domains(api_key, API_SERVICE_ID):
        print(f"  {d.get('name')}  type={d.get('domainType')}  status={d.get('verificationStatus')}")

    print(
        """
=== YOUR NEXT STEP: Bluehost DNS ===

Log in at https://my.bluehost.com → Domains → untiling.com → DNS / Zone Editor.

Add these records (Render standard targets — confirm in Render Dashboard → each service → Custom Domains):

STATIC SITE (aperiodic-monotile-site):
  Host: @     Type: A or ALIAS   → Render will show the target when you click the domain in Dashboard
  Host: www   Type: CNAME      → aperiodic-monotile-site.onrender.com
            (or the exact CNAME Render displays for www.untiling.com)

API (aperiodic-monotile-api):
  Host: api   Type: CNAME      → aperiodic-monotile-api.onrender.com

Bluehost often uses "Advanced DNS" or "cPanel Zone Editor".
- For root (@): if Bluehost won't allow CNAME on @, use their "A Record" with the IP Render shows,
  OR point nameservers to Cloudflare (optional, later).

After saving DNS, wait 5–30 minutes, then in Render Dashboard check each domain shows "Verified".

Tell me when DNS is saved — I'll update CORS + site code and redeploy.
"""
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
