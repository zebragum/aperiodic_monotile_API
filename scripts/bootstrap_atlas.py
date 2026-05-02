"""Download atlas release assets into SPECTRE_PATCH_ATLAS_DIR if missing.

Render web services don't share local disks across services. For the simple
single-service Render launch, we seed the service's attached disk from a public
GitHub Release the first time the container boots.

Usage:
    python scripts/bootstrap_atlas.py

Env:
    SPECTRE_PATCH_ATLAS_DIR=data/atlas
    SPECTRE_PATCH_ATLAS_RELEASE_URL=https://github.com/zebragum/aperiodic_monotile_API/releases/download/atlas-v1
    SPECTRE_PATCH_ATLAS_ASSETS=index.json,core_spectre_tile_1_1_n5.npz,...
"""

from __future__ import annotations

import os
import sys
import time
import urllib.request
from pathlib import Path


DEFAULT_RELEASE_URL = (
    "https://github.com/zebragum/aperiodic_monotile_API/releases/download/atlas-v1"
)
DEFAULT_ASSETS = [
    "index.json",
    "core_spectre_tile_1_1_n5.npz",
    "core_spectre_tile_1_1_n6.npz",
    "core_spectre_tile_1_1_n7.npz",
    "core_spectre_tile_1_1_n8.npz",
]


def _download(url: str, dest: Path) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    started = time.perf_counter()
    print(f"atlas bootstrap: downloading {url} -> {dest}", flush=True)
    with urllib.request.urlopen(url, timeout=60) as resp, tmp.open("wb") as out:
        total = int(resp.headers.get("Content-Length") or 0)
        seen = 0
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            seen += len(chunk)
            if total and seen % (64 * 1024 * 1024) < len(chunk):
                pct = seen * 100.0 / total
                print(f"  ... {seen / 1e6:.1f} MB / {total / 1e6:.1f} MB ({pct:.1f}%)", flush=True)
    tmp.replace(dest)
    elapsed = time.perf_counter() - started
    print(f"atlas bootstrap: wrote {dest} ({dest.stat().st_size / 1e6:.1f} MB) in {elapsed:.1f}s", flush=True)


def main() -> int:
    atlas_dir = Path(os.environ.get("SPECTRE_PATCH_ATLAS_DIR", "data/atlas"))
    release_url = os.environ.get("SPECTRE_PATCH_ATLAS_RELEASE_URL", DEFAULT_RELEASE_URL).rstrip("/")
    assets_env = os.environ.get("SPECTRE_PATCH_ATLAS_ASSETS")
    assets = [x.strip() for x in assets_env.split(",") if x.strip()] if assets_env else DEFAULT_ASSETS

    atlas_dir.mkdir(parents=True, exist_ok=True)
    for name in assets:
        dest = atlas_dir / name
        if dest.exists() and dest.stat().st_size > 0:
            print(f"atlas bootstrap: exists {dest} ({dest.stat().st_size / 1e6:.1f} MB)", flush=True)
            continue
        _download(f"{release_url}/{name}", dest)

    print("atlas bootstrap: complete", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
