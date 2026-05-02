"""Execute deterministic patch synthesis + artifact writes."""

from __future__ import annotations

import json
import sqlite3
import traceback
from pathlib import Path

from spectre_patch import PATCH_ENGINE_SEMVER
from spectre_patch.atlas import AtlasIndex, enumerate_emitted_or_atlas
from spectre_patch.config_limits import LimitsSettings, tier_limits_resolver
from spectre_patch.export import stl_export
from spectre_patch.export.sidecars import tiles_to_csv_rows, tiles_to_json_doc
from spectre_patch.export.svg_export import SvgRenderOpts, svg_document
from spectre_patch.jobs.repo import artifact_dir, fetch_job, mark_done, mark_failed
from spectre_patch.masking import (
    MaskCircle,
    MaskHexagon,
    MaskRect,
    MaskRoundedRect,
    MaskSquare,
    RetentionMode,
)


def coerce_mask(ms: dict):
    mt = ms["type"].lower().strip()
    if mt == "rectangle":
        r = ms["bounds"]
        return MaskRect(float(r["xmin"]), float(r["ymin"]), float(r["xmax"]), float(r["ymax"]))
    if mt == "square":
        cx, cy = float(ms["center"][0]), float(ms["center"][1])
        return MaskSquare((cx, cy), float(ms["half_side"]))
    if mt == "circle":
        cx, cy = float(ms["center"][0]), float(ms["center"][1])
        return MaskCircle((cx, cy), float(ms["radius"]))
    if mt in ("regular_hexagon", "hexagon"):
        cx, cy = float(ms["center"][0]), float(ms["center"][1])
        return MaskHexagon((cx, cy), float(ms["circumradius"]))
    if mt in ("rounded_rect", "rounded-rect"):
        cx, cy = float(ms["center"][0]), float(ms["center"][1])
        return MaskRoundedRect(
            (cx, cy),
            float(ms["width"]),
            float(ms["height"]),
            float(ms.get("corner_radius", 0.0)),
        )
    raise ValueError(f"Unsupported mask type {mt!r}")


def _value_or_default(req: dict, key: str, default):
    value = req.get(key)
    return default if value is None else value


def run_patch_job(
    conn: sqlite3.Connection,
    *,
    job_id: str,
    storage_root: Path,
    base_limits: LimitsSettings,
    atlas_index: AtlasIndex | None = None,
) -> None:

    row = fetch_job(conn, job_id)
    if row is None:
        return
    req = json.loads(row["request_json"])
    tier = row["tier"] or "tier_free"
    limits = tier_limits_resolver(tier, base_limits)

    try:
        mask = coerce_mask(req["mask"])
        retention = RetentionMode(req.get("retention", "centroid"))
        emitted, atlas_resolution = enumerate_emitted_or_atlas(
            tile_family=req["tile_family"],
            patch_version=str(req.get("patch_version") or PATCH_ENGINE_SEMVER),
            seed=req.get("seed"),
            half_extent_cover=float(req.get("coverage_half_extent") or req.get("half_extent") or 4.5),
            scale=float(req["scale"]),
            tx=float(req.get("tx", 0.0)),
            ty=float(req.get("ty", 0.0)),
            rotation_deg=float(req.get("rotation_deg", 0.0)),
            mask=mask,
            retention=retention,
            limits=limits,
            substitution_iterations=req.get("substitution_iterations"),
            atlas_index=atlas_index,
            force_substitution=bool(req.get("force_substitution", False)),
        )

        nt = len(emitted)
        if nt > limits.max_tiles_per_job:
            raise ValueError(f"tile count {nt} exceeds SKU limit {limits.max_tiles_per_job}")

        art = artifact_dir(storage_root, job_id)
        fmts = {str(f).lower() for f in req.get("formats", ["svg"])}

        if "svg" in fmts and nt > limits.svg_max_tiles_hard:
            if bool(req.get("force_svg_large")):
                raise ValueError("Refusing unsafe SVG — lower coverage or disable force_svg_large")
            fmts.discard("svg")
            fmts.update({"stl", "instance_json"})

        if "svg" in fmts:
            meta = {"patch_engine": PATCH_ENGINE_SEMVER}
            svg_opts = SvgRenderOpts(
                fill=req.get("svg_fill") or "#cdd6ea",
                stroke=req.get("svg_stroke") or "#171b38",
                stroke_width=float(_value_or_default(req, "svg_stroke_width", 0.04)),
                opacity=float(_value_or_default(req, "svg_opacity", 1.0)),
                deterministic_colors=bool(req.get("svg_deterministic_palette")),
                pixel_target=int(_value_or_default(req, "svg_pixel_target", 1200)),
                margin=float(_value_or_default(req, "svg_margin", 1.0)),
                compact=bool(req.get("svg_compact", False)),
            )
            svg_text = svg_document(
                emitted,
                patch_meta=meta,
                scale=float(req["scale"]),
                rotation_deg=float(req.get("rotation_deg", 0.0)),
                tx=float(req.get("tx", 0.0)),
                ty=float(req.get("ty", 0.0)),
                opts=svg_opts,
            )
            if len(svg_text) > limits.svg_max_chars:
                raise ValueError("SVG plaintext exceeds svg_max_chars — reduce coverage")
            (art / "patch.svg").write_text(svg_text, encoding="utf-8")

        if "csv" in fmts:
            (art / "tiles.csv").write_bytes(
                tiles_to_csv_rows(
                    emitted,
                    patch_version=str(req.get("patch_version") or PATCH_ENGINE_SEMVER),
                    tile_family=req["tile_family"],
                    seed=req.get("seed"),
                )
            )

        if "json" in fmts:
            (art / "tiles.json").write_bytes(
                tiles_to_json_doc(
                    emitted,
                    patch_version=str(req.get("patch_version") or PATCH_ENGINE_SEMVER),
                    tile_family=req["tile_family"],
                    seed=req.get("seed"),
                    extra={"transform_convention": "World = client_similarity ⊗ generator"},
                )
            )

        thickness = float(req.get("stl_extrusion_mm", 1.0))

        manifest_inst = stl_export.instancing_manifest_bytes(
            emitted,
            patch_version=str(req.get("patch_version") or PATCH_ENGINE_SEMVER),
            tile_family=req["tile_family"],
            seed=req.get("seed"),
            scale=float(req["scale"]),
            rotation_deg=float(req.get("rotation_deg", 0.0)),
            tx=float(req.get("tx", 0.0)),
            ty=float(req.get("ty", 0.0)),
        )

        if "stl" in fmts:
            if nt >= limits.stl_tile_instancing_floor:
                stl_export.write_prototype_stl(str(art / "spectre_proto.stl"), thickness)
                (art / "spectre_instances.json").write_bytes(manifest_inst)
            else:
                facets = stl_export.combined_stl_facets(
                    emitted,
                    scale=float(req["scale"]),
                    rotation_deg=float(req.get("rotation_deg", 0.0)),
                    tx=float(req.get("tx", 0.0)),
                    ty=float(req.get("ty", 0.0)),
                    thickness_mm=thickness,
                )
                stl_export.write_binary_stl(str(art / "patch.stl"), facets)

        if "instance_json" in fmts and not (art / "spectre_instances.json").exists():
            (art / "spectre_instances.json").write_bytes(manifest_inst)

        if "glb" in fmts:
            from spectre_patch.export.gltf_export import write_glb_instanced  # noqa: PLC0415

            write_glb_instanced(
                art / "patch.glb",
                emitted,
                scale=float(req["scale"]),
                rotation_deg=float(req.get("rotation_deg", 0.0)),
                tx=float(req.get("tx", 0.0)),
                ty=float(req.get("ty", 0.0)),
                thickness_mm=thickness,
                patch_meta={
                    "patch_engine": PATCH_ENGINE_SEMVER,
                    "tile_family": req["tile_family"],
                    "patch_version": str(req.get("patch_version") or PATCH_ENGINE_SEMVER),
                    "seed": req.get("seed"),
                },
            )

        if "png" in fmts:
            from spectre_patch.export.png_export import render_svg_to_png_file  # noqa: PLC0415

            w = int(req.get("png_width_px", 4096))
            h = int(req.get("png_height_px", 4096))
            if w * h > limits.png_max_pixels:
                raise ValueError("PNG pixel budget exceeded")
            if not (art / "patch.svg").exists():
                raise RuntimeError("PNG requested but SVG raster source missing — keep svg format")
            render_svg_to_png_file(str(art / "patch.svg"), str(art / "patch.png"), width_px=w, height_px=h)

        names = sorted(p.name for p in art.glob("*") if p.is_file())
        mark_done(
            conn,
            job_id,
            {
                "artifacts": names,
                "tiles": nt,
                "tier": tier,
                "atlas": {
                    "used_atlas": atlas_resolution.used_atlas,
                    "selected_iterations": atlas_resolution.selected_iterations,
                    "selected_file": atlas_resolution.selected_file,
                    "fallback_reason": atlas_resolution.fallback_reason,
                    "tile_count_pre_mask": atlas_resolution.tile_count_pre_mask,
                },
            },
        )
    except Exception as e:
        tb = "".join(traceback.format_exception_only(e.__class__, e)).strip()
        mark_failed(conn, job_id, tb)
