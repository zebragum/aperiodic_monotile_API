#!/usr/bin/env python3
"""Build customer kit ZIP and standalone extension ZIP (with blender_manifest.toml)."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = Path(__file__).resolve().parent / "dist"
STAGING = OUT_DIR / "staging"
KIT_ZIP = OUT_DIR / "aperiodic-monotile-blender-kit.zip"
ADDON_ZIP = OUT_DIR / "aperiodic_monotile_generator_blender.zip"
ADDON_SRC = ROOT / "blender_addon" / "aperiodic_monotile_generator"
SITE_DOWNLOADS = ROOT / "site" / "assets" / "downloads"


def _addon_version() -> str:
    manifest = ADDON_SRC / "blender_manifest.toml"
    if manifest.is_file():
        for line in manifest.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("version = "):
                return line.split("=", 1)[1].strip().strip('"')
    return "0.0.0"


def versioned_addon_filename() -> str:
    return f"add-on-aperiodic_monotile_generator-v{_addon_version()}.zip"


def should_skip(path: Path) -> bool:
    return "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}


def write_addon_zip(target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(ADDON_SRC.rglob("*")):
            if f.is_file() and not should_skip(f):
                arc = "aperiodic_monotile_generator/" + f.relative_to(ADDON_SRC).as_posix()
                zf.write(f, arc)


def write_kit_zip(staging: Path, target: Path) -> None:
    if target.exists():
        target.unlink()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in staging.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(staging).as_posix())


def main() -> None:
    if not ADDON_SRC.is_dir():
        raise SystemExit(f"Missing add-on source: {ADDON_SRC}")
    manifest = ADDON_SRC / "blender_manifest.toml"
    if not manifest.is_file():
        raise SystemExit(f"Missing blender_manifest.toml: {manifest}")

    versioned_name = versioned_addon_filename()
    versioned_zip = OUT_DIR / versioned_name
    site_versioned = SITE_DOWNLOADS / versioned_name

    if STAGING.exists():
        shutil.rmtree(STAGING)
    STAGING.mkdir(parents=True)

    write_addon_zip(STAGING / "aperiodic_monotile_generator_blender.zip")
    write_addon_zip(ADDON_ZIP)
    write_addon_zip(versioned_zip)
    write_addon_zip(site_versioned)
    write_addon_zip(SITE_DOWNLOADS / "aperiodic_monotile_generator_blender.zip")

    samples_src = ROOT / "site" / "assets" / "samples"
    if samples_src.is_dir():
        shutil.copytree(samples_src, STAGING / "samples")

    shutil.copy2(
        Path(__file__).resolve().parent / "customer" / "START_HERE.txt",
        STAGING / "START_HERE.txt",
    )

    examples_src = ROOT / "site" / "assets" / "examples"
    if examples_src.is_dir():
        shutil.copytree(examples_src, STAGING / "example_masks_svg")

    write_kit_zip(STAGING, KIT_ZIP)

    print(f"Built kit:        {KIT_ZIP} ({KIT_ZIP.stat().st_size} bytes)")
    print(f"Built addon:      {ADDON_ZIP} ({ADDON_ZIP.stat().st_size} bytes)")
    print(f"Built marketplace: {versioned_zip} ({versioned_zip.stat().st_size} bytes)")
    with zipfile.ZipFile(versioned_zip) as zf:
        print("Versioned zip contents:")
        for name in sorted(zf.namelist()):
            print(f"  {name}")


if __name__ == "__main__":
    main()
