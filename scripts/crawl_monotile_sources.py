#!/usr/bin/env python3
"""Build a repeatable registry of modern aperiodic-monotile sources.

Queries Crossref and arXiv using several terminology variants, deduplicates
records by DOI/arXiv ID/title, and writes the machine-readable registry used
to audit and expand the research wiki.
"""

from __future__ import annotations

import html
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "site" / "research" / "wiki" / "source-registry.json"
USER_AGENT = "AperiodicGeneratorResearch/1.0 (https://aperiodicgenerator.com/research/wiki/)"

QUERIES = (
    "aperiodic monotile",
    "hat monotile",
    "spectre monotile",
    "Tile(1,1) tiling",
    "Smith hat tiling",
    "Hat family tilings",
)

RELEVANT = re.compile(
    r"\b("
    r"aperiodic\s+monotil|"
    r"hat\s+(?:mono)?til|"
    r"spectre\s+(?:mono)?til|"
    r"tile\s*\(\s*1\s*,\s*1\s*\)|"
    r"einstein\s+monotil"
    r")",
    re.IGNORECASE,
)


def request_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def request_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read().decode("utf-8", "replace")


def clean(value: str | None) -> str:
    if not value:
        return ""
    value = html.unescape(re.sub(r"<[^>]+>", " ", value))
    return " ".join(value.split())


def title_key(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", title.casefold())


def year_from_parts(item: dict[str, Any]) -> int | None:
    for field in ("published", "published-print", "published-online", "issued"):
        parts = item.get(field, {}).get("date-parts")
        if parts and parts[0]:
            return int(parts[0][0])
    return None


def crossref_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for query in QUERIES:
        params = urllib.parse.urlencode(
            {
                "query": f'"{query}"',
                "rows": 100,
                "select": (
                    "DOI,title,author,published,published-print,published-online,"
                    "issued,container-title,URL,type,abstract,subject"
                ),
            }
        )
        data = request_json(f"https://api.crossref.org/works?{params}")
        for item in data.get("message", {}).get("items", []):
            title = clean((item.get("title") or [""])[0])
            abstract = clean(item.get("abstract"))
            if not RELEVANT.search(f"{title} {abstract}"):
                continue
            authors = [
                " ".join(p for p in (a.get("given", ""), a.get("family", "")) if p).strip()
                for a in item.get("author", [])
            ]
            records.append(
                {
                    "title": title,
                    "authors": [a for a in authors if a],
                    "year": year_from_parts(item),
                    "doi": item.get("DOI", "").lower() or None,
                    "arxiv": None,
                    "url": item.get("URL"),
                    "venue": clean((item.get("container-title") or [""])[0]) or None,
                    "type": item.get("type"),
                    "abstract": abstract or None,
                    "subjects": item.get("subject", []),
                    "discovered_via": ["Crossref", query],
                }
            )
        time.sleep(0.25)
    return records


def arxiv_records() -> list[dict[str, Any]]:
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    records: list[dict[str, Any]] = []
    for query in QUERIES:
        search = urllib.parse.quote(f'all:"{query}"')
        url = (
            "https://export.arxiv.org/api/query?"
            f"search_query={search}&start=0&max_results=100&sortBy=submittedDate"
        )
        try:
            root = ET.fromstring(request_text(url))
        except Exception as exc:
            print(f"warning: arXiv query failed for {query!r}: {exc}")
            continue
        for entry in root.findall("atom:entry", ns):
            title = clean(entry.findtext("atom:title", "", ns))
            summary = clean(entry.findtext("atom:summary", "", ns))
            if not RELEVANT.search(f"{title} {summary}"):
                continue
            entry_url = entry.findtext("atom:id", "", ns)
            match = re.search(r"/abs/([^v/]+(?:\.\d+)?)", entry_url)
            arxiv_id = match.group(1) if match else None
            authors = [
                clean(author.findtext("atom:name", "", ns))
                for author in entry.findall("atom:author", ns)
            ]
            published = entry.findtext("atom:published", "", ns)
            records.append(
                {
                    "title": title,
                    "authors": [a for a in authors if a],
                    "year": int(published[:4]) if published else None,
                    "doi": None,
                    "arxiv": arxiv_id,
                    "url": entry_url,
                    "venue": "arXiv",
                    "type": "preprint",
                    "abstract": summary or None,
                    "subjects": [
                        category.attrib.get("term")
                        for category in entry.findall("atom:category", ns)
                        if category.attrib.get("term")
                    ],
                    "discovered_via": ["arXiv", query],
                }
            )
        time.sleep(3.1)  # arXiv asks clients to keep request intervals >=3s.
    return records


def merge(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for record in records:
        key = (
            f"doi:{record['doi']}"
            if record.get("doi")
            else f"arxiv:{record['arxiv']}"
            if record.get("arxiv")
            else f"title:{title_key(record['title'])}"
        )
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = record
            continue
        for field in ("authors", "year", "doi", "arxiv", "url", "venue", "type", "abstract"):
            if not existing.get(field) and record.get(field):
                existing[field] = record[field]
        existing["subjects"] = sorted(
            set(existing.get("subjects", [])) | set(record.get("subjects", []))
        )
        existing["discovered_via"] = sorted(
            set(existing.get("discovered_via", []))
            | set(record.get("discovered_via", []))
        )

    # A DOI record and an arXiv record may describe the same work; collapse by
    # normalized title after identifier-level merging.
    by_title: dict[str, dict[str, Any]] = {}
    for record in by_key.values():
        key = title_key(record["title"])
        existing = by_title.get(key)
        if existing is None:
            by_title[key] = record
            continue
        for field in ("authors", "year", "doi", "arxiv", "url", "venue", "type", "abstract"):
            if not existing.get(field) and record.get(field):
                existing[field] = record[field]
        existing["subjects"] = sorted(
            set(existing.get("subjects", [])) | set(record.get("subjects", []))
        )
        existing["discovered_via"] = sorted(
            set(existing.get("discovered_via", []))
            | set(record.get("discovered_via", []))
        )

    return sorted(
        by_title.values(),
        key=lambda r: (r.get("year") or 0, r["title"].casefold()),
    )


def main() -> None:
    crossref = crossref_records()
    arxiv = arxiv_records()
    records = merge(crossref + arxiv)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "method": {
            "indexes": ["Crossref", "arXiv"],
            "queries": list(QUERIES),
            "deduplication": "DOI, arXiv ID, then normalized title",
            "scope_note": (
                "Automated discovery registry; human-curated web resources and "
                "citation-chain findings are maintained separately in the wiki."
            ),
        },
        "count": len(records),
        "records": records,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT} with {len(records)} deduplicated records")


if __name__ == "__main__":
    main()
