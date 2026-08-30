#!/usr/bin/env python3
"""Replace em-dashes and en-dashes with ASCII punctuation (no whitespace changes)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
WIKI_BUILD = ROOT / "scripts" / "build_research_wiki.py"

EXTENSIONS = {".html", ".js", ".css", ".md", ".json", ".txt", ".inx"}

EN = "\u2013"
EM = "\u2014"


def fix_text(text: str) -> str:
    text = re.sub(rf"(\d){EN}(\d)", r"\1-\2", text)
    text = re.sub(rf"(\]){EN}(\[)", r"\1-\2", text)
    text = re.sub(rf"(\$[\d.]+){EN}([\d.$]+)", r"\1-\2", text)
    text = re.sub(rf"([A-Za-z]){EN}([A-Za-z])", r"\1-\2", text)
    text = text.replace(EN, "-")

    text = text.replace(f" {EM} ", ", ")
    text = text.replace(f"{EM} ", ", ")
    text = text.replace(f" {EM}", ",")
    text = text.replace(EM, ", ")

    # URL-encoded em dash in mailto/subjects
    text = text.replace("%E2%80%94", "%20")
    text = text.replace("%e2%80%94", "%20")

    return text


def process_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    updated = fix_text(original)
    if updated != original:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def main() -> int:
    changed: list[str] = []
    for path in SITE.rglob("*"):
        if path.is_file() and path.suffix.lower() in EXTENSIONS:
            if process_file(path):
                changed.append(str(path.relative_to(ROOT)))
    if WIKI_BUILD.is_file() and process_file(WIKI_BUILD):
        changed.append(str(WIKI_BUILD.relative_to(ROOT)))
    print(f"updated {len(changed)} files")
    for name in sorted(changed):
        print(f"  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
