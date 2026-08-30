#!/usr/bin/env python3
"""Publish Untiling studio packs to Gumroad (files, covers, landing pages).

Reads GUMROAD_ACCESS_TOKEN from C:\\Z\\.env or spectre_patch_api/.env.
Never prints secrets.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests
from dotenv import dotenv_values
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
Z_ROOT = ROOT.parent
ENV_CANDIDATES = [Z_ROOT / ".env", ROOT / ".env"]
GEN = Path(r"C:\Users\inthe\.cursor\projects\c-Z-New-folder-3\assets")
OUT = Z_ROOT / "outputs" / "studio_packs"
SITE_DIGITAL = ROOT / "site" / "assets" / "digital"
STATE_PATH = OUT / "gumroad_publish_state.json"
API = "https://api.gumroad.com/v2"


def _token() -> str:
    for path in ENV_CANDIDATES:
        if not path.is_file():
            continue
        vals = dotenv_values(path)
        tok = (vals.get("GUMROAD_ACCESS_TOKEN") or "").strip()
        if tok:
            return tok
    raise SystemExit("GUMROAD_ACCESS_TOKEN missing from .env")


def _session() -> requests.Session:
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {_token()}"
    s.headers["Accept"] = "application/json"
    return s


def jpeg_from(src: Path, dest: Path, *, size: tuple[int, int] | None = None, quality: int = 90) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    im = Image.open(src).convert("RGB")
    if size:
        im = im.resize(size, Image.Resampling.LANCZOS)
    else:
        w, h = im.size
        long_edge = max(w, h)
        if long_edge > 2560:
            scale = 2560 / long_edge
            im = im.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    im.save(dest, format="JPEG", quality=quality, optimize=True, progressive=True)
    return dest


def prepare_images() -> dict[str, Path]:
    SITE_DIGITAL.mkdir(parents=True, exist_ok=True)
    mapping = {
        "archviz_cover": GEN / "archviz-floor-kit-cover.png",
        "archviz_brass": GEN / "archviz-floor-kit-brass.png",
        "archviz_thumb": GEN / "archviz-floor-kit-thumb.png",
        "game_cover": GEN / "game-env-kit-cover.png",
        "game_plaza": GEN / "game-env-kit-plaza.png",
        "game_thumb": GEN / "game-env-kit-thumb.png",
        "sample_cover": GEN / "comparison-sample-cover.png",
        "sample_thumb": GEN / "comparison-sample-thumb.png",
    }
    out: dict[str, Path] = {}
    for key, src in mapping.items():
        if not src.is_file():
            raise SystemExit(f"missing generated image: {src}")
        dest = SITE_DIGITAL / f"{key.replace('_', '-')}.jpg"
        size = (1200, 1200) if key.endswith("thumb") else None
        jpeg_from(src, dest, size=size)
        # Keep a copy next to the ZIPs for local listing work
        jpeg_from(src, OUT / "product_images" / dest.name, size=size)
        out[key] = dest
        print(f"  image {dest.name} {dest.stat().st_size // 1024} KB", flush=True)
    return out


def upload_file(s: requests.Session, path: Path) -> str:
    size = path.stat().st_size
    pres = s.post(
        f"{API}/files/presign",
        data={"filename": path.name, "file_size": str(size)},
        timeout=60,
    )
    pres.raise_for_status()
    body = pres.json()
    if not body.get("success"):
        raise RuntimeError(f"presign failed for {path.name}: {body}")
    parts_out = []
    with path.open("rb") as fh:
        for part in body["parts"]:
            chunk = fh.read(100 * 1024 * 1024)
            put = requests.put(part["presigned_url"], data=chunk, timeout=300)
            put.raise_for_status()
            etag = put.headers.get("ETag", "").strip().strip('"')
            parts_out.append({"part_number": part["part_number"], "etag": etag})
    done = s.post(
        f"{API}/files/complete",
        json={"upload_id": body["upload_id"], "key": body["key"], "parts": parts_out},
        timeout=60,
    )
    if done.status_code >= 400:
        done = s.post(
            f"{API}/files/complete",
            data={
                "upload_id": body["upload_id"],
                "key": body["key"],
                "parts[][part_number]": parts_out[0]["part_number"],
                "parts[][etag]": parts_out[0]["etag"],
            },
            timeout=60,
        )
    done.raise_for_status()
    payload = done.json()
    url = payload.get("file_url") or body.get("file_url")
    if not url:
        raise RuntimeError(f"complete failed for {path.name}: {payload}")
    print(f"  uploaded {path.name}", flush=True)
    return url


def api_json(s: requests.Session, method: str, path: str, **kwargs) -> dict:
    fn = getattr(s, method)
    r = fn(f"{API}{path}", timeout=60, **kwargs)
    try:
        data = r.json()
    except Exception:
        data = {"raw": r.text[:800], "status": r.status_code}
    if r.status_code >= 400 or data.get("success") is False:
        raise RuntimeError(f"{method.upper()} {path} -> {r.status_code} {data}")
    return data


def list_products(s: requests.Session) -> list[dict]:
    data = api_json(s, "get", "/products")
    return data.get("products") or data.get("links") or []


def find_product(products: list[dict], permalink: str, name: str) -> dict | None:
    for p in products:
        if (p.get("custom_permalink") or "") == permalink:
            return p
        if (p.get("name") or "") == name:
            return p
    return None


def html_description(pack: dict) -> str:
    bullets = "".join(f"<li>{item}</li>" for item in pack["includes"])
    return f"""
<p><strong>{pack['tagline']}</strong></p>
<p>{pack['pitch']}</p>
<h3>What's inside</h3>
<ul>{bullets}</ul>
<h3>How studios use it</h3>
<ol>
<li>Import <code>patch.glb</code> into Blender 4.x or Unreal Engine 5.</li>
<li>Assign materials from the included palette JSON and lookdev PNGs.</li>
<li>Hide patch edges with walls, trim, rugs, or landscape blend.</li>
</ol>
<h3>Honest limits</h3>
<p>Boundaries are not seamless. This is a finished patch, not an infinite runtime shader.
Need custom masks or unique seeds at production tile counts?
<a href="https://aperiodicgenerator.com/pricing.html">Pro API, $99/mo</a>.</p>
<p>Commercial license for delivered viz and shipped game levels is included.
Do not resell the raw files as a competing tile pack.</p>
<p>More: <a href="https://untiling.com/digital/">untiling.com/digital</a></p>
""".strip()


def landing_html(pack: dict, cover_url: str, extra_urls: list[str]) -> str:
    extras = "".join(
        f'<img class="shot" src="{u}" alt="" />' for u in extra_urls[:3] if u
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Outfit:wght@400;500;700&display=swap" rel="stylesheet" />
  <style>
    :root {{ color-scheme: dark; }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; background: #0b0c0f; color: #f4efe6;
      font-family: Outfit, sans-serif; line-height: 1.55;
    }}
    .hero {{ position: relative; min-height: 72vh; overflow: hidden; }}
    .hero img {{ width: 100%; height: 72vh; object-fit: cover; display: block; filter: saturate(1.05); }}
    .veil {{
      position: absolute; inset: 0;
      background: linear-gradient(180deg, rgba(11,12,15,.15) 20%, rgba(11,12,15,.92) 100%);
    }}
    .hero-copy {{
      position: absolute; left: 0; right: 0; bottom: 0;
      padding: 2.5rem 7vw 2rem; max-width: 920px;
    }}
    .eyebrow {{ letter-spacing: .18em; text-transform: uppercase; font-size: .72rem; color: #d6b27a; }}
    h1 {{
      font-family: "Instrument Serif", serif; font-weight: 400;
      font-size: clamp(2.4rem, 6vw, 4.4rem); line-height: 1.02; margin: .25rem 0 .6rem;
    }}
    .lede {{ color: #d7d0c4; max-width: 38rem; }}
    .buybar {{
      display: flex; gap: .8rem; flex-wrap: wrap; align-items: center; margin-top: 1.2rem;
    }}
    .price {{ font-size: 1.7rem; font-weight: 700; color: #f0c27a; }}
    button, .ghost {{
      appearance: none; border: 0; cursor: pointer; border-radius: 999px;
      padding: .85rem 1.25rem; font: inherit; font-weight: 700;
    }}
    button {{ background: #f0c27a; color: #1a1208; }}
    .ghost {{ background: transparent; color: #f4efe6; border: 1px solid #5a5348; text-decoration: none; }}
    main {{ padding: 2.5rem 7vw 4rem; max-width: 1100px; }}
    h2 {{ font-family: "Instrument Serif", serif; font-weight: 400; font-size: 2rem; }}
    ul {{ padding-left: 1.15rem; color: #cfc6b8; }}
    .shots {{ display: grid; grid-template-columns: 1fr 1fr; gap: .8rem; margin: 1.4rem 0; }}
    .shots img, .shot {{ width: 100%; border-radius: 14px; display: block; }}
    .fine {{ color: #8d867b; font-size: .92rem; }}
    @media (max-width: 720px) {{ .shots {{ grid-template-columns: 1fr; }} .hero img {{ height: 58vh; }} }}
  </style>
</head>
<body>
  <section class="hero">
    <img src="{cover_url}" alt="" />
    <div class="veil"></div>
    <div class="hero-copy">
      <p class="eyebrow">Untiling studio pack</p>
      <h1 data-gumroad-field="name">{pack['name']}</h1>
      <p class="lede">{pack['tagline']} {pack['pitch']}</p>
      <div class="buybar">
        <span class="price" data-gumroad-field="price">${pack['price_usd']}</span>
        <button type="button" data-gumroad-action="buy">Buy this pack</button>
        <a class="ghost" href="https://untiling.gumroad.com/l/comparison-sample">Free comparison sample</a>
      </div>
    </div>
  </section>
  <main>
    <h2>What you get</h2>
    <ul>{''.join(f'<li>{item}</li>' for item in pack['includes'])}</ul>
    <div class="shots">{extras}</div>
    <h2>Pipeline</h2>
    <p>Drop the GLB into Blender or Unreal. One node per tile. Palette JSON and lookdev stills are included so materials are not guessed from a grey mesh.</p>
    <p class="fine">Patch edges are not seamless. Hide them with architecture. Custom seeds and masks: aperiodicgenerator.com</p>
  </main>
</body>
</html>
"""


PACKS = [
    {
        "key": "archviz",
        "name": "Untiling Archviz Floor Kit",
        "permalink": "archviz-floor-kit",
        "price_usd": 49,
        "price_cents": 4900,
        "zip": OUT / "01_archviz_floor_kit.zip",
        "tagline": "GLB floor plates that survive the dolly shot.",
        "pitch": "Three production-sized aperiodic floors for interiors and walkthroughs. No translational repeat unit. Commercial license included.",
        "summary": "10 m, 15 m, and 20 m instanced GLB floors plus instance JSON, STL, palettes, and Blender / Unreal import guides.",
        "tags": ["archviz", "blender", "unreal", "glb", "floor", "monotile", "aperiodic", "spectre"],
        "includes": [
            "3 square floor plates (10 m, 15 m, 20 m) as instanced GLB",
            "spectre_instances.json per plate for DCC rebuilds",
            "Merged STL, SVG, lookdev PNGs, and palette JSON",
            "Blender + Unreal import guides and commercial LICENSE",
        ],
        "covers": ["archviz_cover", "archviz_brass"],
        "public_covers": [
            "https://untiling.com/assets/research/wiki/design-zellige-emerald.jpg",
            "https://untiling.com/assets/research/wiki/computer-graphics-brass.jpg",
            "https://untiling.com/assets/research/wiki/periodic-vs-aperiodic.jpg",
        ],
        "public_thumb": "https://untiling.com/assets/research/wiki/design-zellige-emerald.jpg",
        "thumb": "archviz_thumb",
        "receipt": "Download the ZIP, then open docs/IMPORT_BLENDER.md or docs/IMPORT_UNREAL.md. Scale is 1 unit = 1 meter. Hide patch edges with walls or trim. Custom sizes: https://aperiodicgenerator.com/pricing.html",
    },
    {
        "key": "game",
        "name": "Untiling Game Environment Kit",
        "permalink": "game-environment-kit",
        "price_usd": 39,
        "price_cents": 3900,
        "zip": OUT / "02_game_environment_kit.zip",
        "tagline": "Corridors and plazas without obvious CG repeat.",
        "pitch": "Environment plates with curvy, blocky, and jagged tile edges for sci-fi and fantasy sets.",
        "summary": "Two corridor floors plus a 24 m circular plaza. GLB, instance JSON, STL, and UE5 notes.",
        "tags": ["gamedev", "unreal", "unity", "environment", "glb", "monotile", "sci-fi", "fantasy"],
        "includes": [
            "Corridor plates 24x8 m and 36x12 m",
            "Circular plaza, 24 m diameter, jagged stone profile",
            "GLB + instance JSON + merged STL + lookdev PNGs",
            "Unreal collision / Nanite notes and commercial LICENSE",
        ],
        "covers": ["game_cover", "game_plaza"],
        "public_covers": [
            "https://untiling.com/assets/research/wiki/computer-graphics-sunset.jpg",
            "https://untiling.com/assets/research/wiki/computer-graphics-brass.jpg",
            "https://untiling.com/assets/research/wiki/design-zellige-emerald.jpg",
        ],
        "public_thumb": "https://untiling.com/assets/research/wiki/computer-graphics-sunset.jpg",
        "thumb": "game_thumb",
        "receipt": "Start with docs/IMPORT_UNREAL.md. If the floor looks 100x too small in UE5, set Import Uniform Scale to 100. Edges do not tile. Cover them with walls or landscape.",
    },
    {
        "key": "sample",
        "name": "Untiling Comparison Sample",
        "permalink": "comparison-sample",
        "price_usd": 0,
        "price_cents": 0,
        "zip": OUT / "00_comparison_sample.zip",
        "tagline": "See the difference before you buy.",
        "pitch": "A 5 m floor GLB plus the periodic-versus-aperiodic still for client decks and import tests.",
        "summary": "Free 5 m sample floor. Import it, then upgrade to the Archviz or Game kit.",
        "tags": ["free", "sample", "blender", "archviz", "monotile"],
        "includes": [
            "5 m x 5 m sample floor as instanced GLB",
            "Periodic vs aperiodic comparison still",
            "Links to the full studio kits",
        ],
        "covers": ["sample_cover"],
        "public_covers": [
            "https://untiling.com/assets/research/wiki/periodic-vs-aperiodic.jpg",
            "https://untiling.com/assets/research/wiki/design-zellige-emerald.jpg",
        ],
        "public_thumb": "https://untiling.com/assets/research/wiki/periodic-vs-aperiodic.jpg",
        "thumb": "sample_thumb",
        "receipt": "Import assets/sample_floor_5m/patch.glb. If the workflow fits, the Archviz Floor Kit and Game Environment Kit are the production sizes.",
        "pwyw": True,
    },
]


def attach_cover(s: requests.Session, product_id: str, url: str) -> bool:
    r = s.post(f"{API}/products/{product_id}/covers", data={"url": url}, timeout=90)
    try:
        data = r.json()
    except Exception:
        print(f"  cover fail status={r.status_code}", flush=True)
        return False
    ok = r.ok and data.get("success") is not False
    print(f"  cover {'ok' if ok else 'fail'} {r.status_code}", flush=True)
    return bool(ok)


def attach_thumb(s: requests.Session, product_id: str, url: str) -> bool:
    r = s.post(f"{API}/products/{product_id}/thumbnail", data={"url": url}, timeout=90)
    try:
        data = r.json()
    except Exception:
        print(f"  thumb fail status={r.status_code}", flush=True)
        return False
    ok = r.ok and data.get("success") is not False
    print(f"  thumb {'ok' if ok else 'fail'} {r.status_code}", flush=True)
    return bool(ok)


def publish_pack(s: requests.Session, pack: dict, images: dict[str, Path], existing: list[dict]) -> dict:
    print(f"\n=== {pack['name']} ===", flush=True)
    if not pack["zip"].is_file():
        raise SystemExit(f"missing zip {pack['zip']}")

    zip_url = upload_file(s, pack["zip"])

    payload = {
        "native_type": "digital",
        "name": pack["name"],
        "description": html_description(pack),
        "custom_permalink": pack["permalink"],
        "price": pack["price_cents"],
        "price_currency_type": "usd",
        "custom_summary": pack["summary"],
        "custom_receipt": pack["receipt"],
        "tags": pack["tags"],
        "refund_period": "14",
        "display_product_reviews": True,
        "files": [{"url": zip_url, "display_name": pack["zip"].name}],
    }
    if pack.get("pwyw"):
        payload["customizable_price"] = True
        payload["suggested_price_cents"] = 0

    found = find_product(existing, pack["permalink"], pack["name"])
    if found:
        pid = found["id"]
        print(f"  updating {pid}", flush=True)
        data = api_json(s, "put", f"/products/{pid}", json=payload)
    else:
        print("  creating", flush=True)
        data = api_json(s, "post", "/products", json=payload)
    product = data["product"]
    pid = product["id"]

    cover_ok = False
    for url in pack.get("public_covers") or []:
        if attach_cover(s, pid, url):
            cover_ok = True
    if pack.get("public_thumb"):
        attach_thumb(s, pid, pack["public_thumb"])

    fresh = api_json(s, "get", f"/products/{pid}").get("product") or product
    covers = fresh.get("covers") or []
    cover_urls = [c.get("url") or c.get("original_url") for c in covers if c]
    cover_urls = [u for u in cover_urls if u]
    if cover_urls:
        page = landing_html(pack, cover_urls[0], cover_urls[1:])
        try:
            api_json(s, "put", f"/products/{pid}", json={"custom_html": page})
            print("  landing page set", flush=True)
        except Exception as exc:
            print(f"  landing page skipped: {exc}", flush=True)

    enabled = api_json(s, "put", f"/products/{pid}/enable")
    product = enabled.get("product") or fresh
    short = product.get("short_url") or f"https://untiling.gumroad.com/l/{pack['permalink']}"
    print(f"  LIVE {short}", flush=True)
    return {
        "id": pid,
        "name": pack["name"],
        "permalink": pack["permalink"],
        "url": short,
        "price_usd": pack["price_usd"],
        "cover_count": len(cover_urls),
        "cover_ok": cover_ok,
    }


def main() -> int:
    print("Preparing product images...", flush=True)
    images = prepare_images()
    s = _session()
    existing = list_products(s)
    print(f"Existing Gumroad products: {len(existing)}", flush=True)
    results = [publish_pack(s, pack, images, existing) for pack in PACKS]
    STATE_PATH.write_text(json.dumps({"published": results, "ts": time.time()}, indent=2), encoding="utf-8")
    print("\nDone")
    for row in results:
        print(f"  {row['url']}  ${row['price_usd']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
