"""Rebrand spectre_patch_api/site to Untiling and replace 'free' marketing copy with Preview tier language."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "site"
EXTS = {".html", ".js", ".md", ".xml", ".txt", ".css"}
SKIP = {"site-config.js"}

SUBS = [
    ("Free non-repeating 2D/3D generator", "Non-repeating 2D/3D preview"),
    ("Free aperiodic monotile generator", "Aperiodic monotile preview"),
    ("Download PNG free", "Download PNG preview"),
    ("Download JPG free", "Download JPG preview"),
    ("PNG/JPG free", "PNG/JPG preview"),
    ("free JPG and PNG previews", "JPG and PNG preview exports"),
    ("free JPG or PNG previews", "JPG or PNG preview exports"),
    (
        "Free add-on download. Hosted API for generation.",
        "Blender add-on download. Hosted API for generation.",
    ),
    (
        "The add-on ZIP is a free download from this site.",
        "The add-on ZIP is available from this site.",
    ),
    ("Free preview tier", "Preview tier"),
    ("Free previews", "Preview exports"),
    ("Free Preview", "Preview"),
    ("<h3>Free</h3>", "<h3>Preview</h3>"),
    ("Solo · Pro · Free previews.", "Solo · Pro · Preview exports."),
    (
        "Production geometry with free previews",
        "Production geometry with preview exports",
    ),
    (
        "Raster previews stay free so anyone can sanity-check meshes.",
        "Raster preview exports let you sanity-check meshes before upgrading.",
    ),
    ("Free keys stay constrained", "Preview keys stay constrained"),
    ("Free preview access is limited.", "Preview-tier access is limited."),
    (
        "Use this section to quickly compare free previews, Solo, and Pro access.",
        "Use this section to compare Preview, Solo, and Pro access.",
    ),
    ("Try the free generator", "Open the generator"),
    ("Build free JPG or PNG previews.", "Build JPG or PNG preview exports."),
    ("free/paid API access", "preview and paid API access"),
    ("free_generator_upgrade_prompt", "preview_generator_upgrade_prompt"),
    ("free_generator", "preview_generator"),
    (
        "Could not load the free generator data.",
        "Could not load the preview generator data.",
    ),
    ("Free Blender add-on", "Blender add-on"),
    ("Aperiodic Monotile Generator", "Untiling"),
    ("Aperiodic Monotile API", "Untiling API"),
    ("Aperiodic Generator research", "Untiling research"),
    ("https://aperiodicgenerator.com", "https://untiling.com"),
]


def transform(text: str) -> str:
    for old, new in SUBS:
        text = text.replace(old, new)
    return text


def main() -> None:
    changed: list[str] = []
    for path in sorted(ROOT.rglob("*")):
        if path.suffix not in EXTS or path.name in SKIP:
            continue
        raw = path.read_text(encoding="utf-8")
        new = transform(raw)
        if new != raw:
            path.write_text(new, encoding="utf-8")
            changed.append(str(path.relative_to(ROOT)))
    print(f"updated {len(changed)} files")
    for name in changed:
        print(f"  {name}")


if __name__ == "__main__":
    main()
