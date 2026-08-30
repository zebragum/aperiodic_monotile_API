#!/usr/bin/env python3
"""Generate domain-specific sitemaps for untiling.com and aperiodicgenerator.com."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

SITE = Path(__file__).resolve().parents[1] / "site"
WIKI = SITE / "research" / "wiki"
TODAY = date.today().isoformat()

UNTILING = "https://untiling.com"
GENERATOR = "https://aperiodicgenerator.com"


def url(loc: str, *, priority: str, changefreq: str) -> str:
    return f"""  <url>
    <loc>{loc}</loc>
    <lastmod>{TODAY}</lastmod>
    <changefreq>{changefreq}</changefreq>
    <priority>{priority}</priority>
  </url>"""


def wiki_urls() -> list[str]:
    index_path = WIKI / "search-index.json"
    slugs: list[str] = []
    if index_path.is_file():
        slugs = [item["slug"] for item in json.loads(index_path.read_text(encoding="utf-8"))]
    else:
        slugs = [
            p.stem for p in WIKI.glob("*.html")
            if p.name not in {"moire-and-aliasing.html"}
        ]
    entries: list[str] = []
    for slug in slugs:
        path = "index.html" if slug == "index" else f"{slug}.html"
        pri = "0.92" if slug in {"index", "aperiodic-monotile", "spectre-tile", "hat-tile"} else "0.85"
        entries.append(url(f"{UNTILING}/research/wiki/{path}", priority=pri, changefreq="monthly"))
    return entries


def wrap(urls: list[str]) -> str:
    body = "\n".join(urls)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n"
        "</urlset>\n"
    )


def build_untiling() -> str:
    urls = [
        url(f"{UNTILING}/", priority="1.0", changefreq="weekly"),
        url(f"{UNTILING}/art.html", priority="0.9", changefreq="weekly"),
        url(f"{UNTILING}/digital/index.html", priority="0.88", changefreq="weekly"),
        url(f"{UNTILING}/studio.html", priority="0.88", changefreq="monthly"),
        url(f"{UNTILING}/research/", priority="0.95", changefreq="weekly"),
        url(f"{UNTILING}/apparel/", priority="0.85", changefreq="weekly"),
        url(f"{UNTILING}/contact.html", priority="0.5", changefreq="yearly"),
        url(f"{UNTILING}/attribution.html", priority="0.5", changefreq="yearly"),
        url(f"{UNTILING}/terms.html", priority="0.3", changefreq="yearly"),
        url(f"{UNTILING}/privacy.html", priority="0.3", changefreq="yearly"),
        url(f"{UNTILING}/refund.html", priority="0.3", changefreq="yearly"),
    ]
    urls.extend(wiki_urls())
    return wrap(urls)


def build_generator() -> str:
    urls = [
        url(f"{GENERATOR}/", priority="1.0", changefreq="weekly"),
        url(f"{GENERATOR}/generate.html", priority="0.95", changefreq="weekly"),
        url(f"{GENERATOR}/web.html", priority="0.95", changefreq="weekly"),
        url(f"{GENERATOR}/pricing.html", priority="0.9", changefreq="monthly"),
        url(f"{GENERATOR}/docs.html", priority="0.9", changefreq="weekly"),
        url(f"{GENERATOR}/agents.html", priority="0.85", changefreq="monthly"),
        url(f"{GENERATOR}/agent-guide.md", priority="0.8", changefreq="monthly"),
        url(f"{GENERATOR}/rhino.html", priority="0.75", changefreq="monthly"),
        url(f"{GENERATOR}/use-cases/blender.html", priority="0.85", changefreq="monthly"),
        url(f"{GENERATOR}/use-cases/fabrication.html", priority="0.85", changefreq="monthly"),
        url(f"{GENERATOR}/use-cases/applications.html", priority="0.8", changefreq="monthly"),
        url(f"{GENERATOR}/contact.html", priority="0.5", changefreq="yearly"),
        url(f"{GENERATOR}/terms.html", priority="0.3", changefreq="yearly"),
        url(f"{GENERATOR}/privacy.html", priority="0.3", changefreq="yearly"),
        url(f"{GENERATOR}/refund.html", priority="0.3", changefreq="yearly"),
        url(f"{GENERATOR}/attribution.html", priority="0.5", changefreq="yearly"),
    ]
    return wrap(urls)


def main() -> None:
    untiling_path = SITE / "sitemap-untiling.xml"
    generator_path = SITE / "sitemap-aperiodicgenerator.xml"
    index_path = SITE / "sitemap.xml"
    untiling_path.write_text(build_untiling(), encoding="utf-8")
    generator_path.write_text(build_generator(), encoding="utf-8")
    index_path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <sitemap><loc>{UNTILING}/sitemap-untiling.xml</loc><lastmod>{TODAY}</lastmod></sitemap>\n"
        f"  <sitemap><loc>{GENERATOR}/sitemap-aperiodicgenerator.xml</loc><lastmod>{TODAY}</lastmod></sitemap>\n"
        "</sitemapindex>\n",
        encoding="utf-8",
    )
    n_u = untiling_path.read_text(encoding="utf-8").count("<url>")
    n_g = generator_path.read_text(encoding="utf-8").count("<url>")
    print(f"wrote sitemap-untiling.xml ({n_u} urls)")
    print(f"wrote sitemap-aperiodicgenerator.xml ({n_g} urls)")
    print("wrote sitemap.xml (index)")


if __name__ == "__main__":
    main()
