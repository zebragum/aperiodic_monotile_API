"""Execute deterministic patch synthesis + artifact writes."""

from __future__ import annotations

import json
import sqlite3
import traceback
from pathlib import Path

from spectre_patch import PATCH_ENGINE_SEMVER
from spectre_patch.atlas import AtlasIndex, enumerate_emitted_or_atlas
from spectre_patch.config_limits import FREE_TIER_RASTER_FORMATS, LimitsSettings, tier_limits_resolver
from spectre_patch.export import stl_export
from spectre_patch.export.sidecars import tiles_to_csv_rows, tiles_to_json_doc
from spectre_patch.export.svg_export import SvgRenderOpts, svg_document, write_svg_or_svgz
from spectre_patch.jobs.repo import artifact_dir, fetch_job, mark_done, mark_failed
from spectre_patch.masking import (
    MaskCircle,
    MaskHexagon,
    MaskRect,
    MaskRoundedRect,
    MaskSquare,
    MaskTriangle,
    RetentionMode,
    mask_polygon,
)


def coerce_mask(ms: dict):
    mt = ms["type"].lower().strip()
    if mt == "rectangle":
        if "bounds" in ms and ms["bounds"] is not None:
            r = ms["bounds"]
            return MaskRect(float(r["xmin"]), float(r["ymin"]), float(r["xmax"]), float(r["ymax"]))
        center = ms.get("center") or [0.0, 0.0]
        cx, cy = float(center[0]), float(center[1])
        half_w, half_h = float(ms["width"]) / 2.0, float(ms["height"]) / 2.0
        return MaskRect(cx - half_w, cy - half_h, cx + half_w, cy + half_h)
    if mt == "square":
        center = ms.get("center") or [0.0, 0.0]
        cx, cy = float(center[0]), float(center[1])
        return MaskSquare((cx, cy), float(ms["half_side"]))
    if mt == "circle":
        center = ms.get("center") or [0.0, 0.0]
        cx, cy = float(center[0]), float(center[1])
        return MaskCircle((cx, cy), float(ms["radius"]))
    if mt in ("regular_hexagon", "hexagon"):
        center = ms.get("center") or [0.0, 0.0]
        cx, cy = float(center[0]), float(center[1])
        return MaskHexagon((cx, cy), float(ms["circumradius"]))
    if mt == "triangle":
        center = ms.get("center") or [0.0, 0.0]
        cx, cy = float(center[0]), float(center[1])
        return MaskTriangle(
            (cx, cy),
            float(ms["side_length"]),
            float(ms.get("rotation_deg", 90.0)),
        )
    if mt in ("rounded_rect", "rounded-rect"):
        center = ms.get("center") or [0.0, 0.0]
        cx, cy = float(center[0]), float(center[1])
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


def _coverage_half_extent_for(mask, requested: float | None) -> float:
    if requested is not None:
        return float(requested)
    bounds = mask_polygon(mask).bounds
    extent = max(abs(float(v)) for v in bounds)
    # The enumerator needs enough source geometry beyond the requested crop to
    # cover boundary-crossing tiles. Keep a small absolute floor for tiny masks.
    return max(4.5, extent * 1.15 + 2.0)


def run_patch_job(
    conn: sqlite3.Connection,
    *,
    job_id: str,
    storage_root: Path,
    base_limits: LimitsSettings,
    atlas_index: AtlasIndex | None = None,
    require_atlas: bool = True,
) -> None:

    row = fetch_job(conn, job_id)
    if row is None:
        return
    req = json.loads(row["request_json"])
    tier = row["tier"] or "tier_free"
    limits = tier_limits_resolver(tier, base_limits)

    try:
        mask = coerce_mask(req["mask"])
        mask_geom = mask_polygon(mask)
        visual_style = None
        try:
            from spectre_patch.export.tile_styling import TileVisualStyle

            visual_style = TileVisualStyle.from_request(req)
        except ValueError as e:
            raise ValueError(str(e)) from e
        retention = RetentionMode(req.get("retention", "clip"))
        coverage_half_extent = _coverage_half_extent_for(
            mask, req.get("coverage_half_extent") or req.get("half_extent")
        )
        tile_family = str(req.get("tile_family") or "spectre_tile_1_1")
        patch_version = str(req.get("patch_version") or PATCH_ENGINE_SEMVER)
        scale = float(req.get("scale", 1.0))
        rotation_deg = float(req.get("rotation_deg", 0.0))
        tx = float(req.get("tx", 0.0))
        ty = float(req.get("ty", 0.0))
        emitted, atlas_resolution = enumerate_emitted_or_atlas(
            tile_family=tile_family,
            patch_version=patch_version,
            seed=req.get("seed"),
            half_extent_cover=coverage_half_extent,
            scale=scale,
            tx=tx,
            ty=ty,
            rotation_deg=rotation_deg,
            mask=mask,
            retention=retention,
            limits=limits,
            substitution_iterations=req.get("substitution_iterations"),
            atlas_index=atlas_index,
            force_substitution=bool(req.get("force_substitution", False)),
            require_atlas=require_atlas,
        )

        nt = len(emitted)
        if nt > limits.max_tiles_per_job:
            raise ValueError(f"tile count {nt} exceeds SKU limit {limits.max_tiles_per_job}")

        art = artifact_dir(storage_root, job_id)
        fmts = {str(f).lower() for f in req.get("formats", ["svg"])}

        if tier == "tier_free" and not fmts <= FREE_TIER_RASTER_FORMATS:
            bad = sorted(fmts - FREE_TIER_RASTER_FORMATS)
            raise ValueError(
                f"tier_free allows only raster previews {sorted(FREE_TIER_RASTER_FORMATS)}; "
                f"disallowed={bad}"
            )

        if "svg" in fmts and nt > limits.svg_max_tiles_hard:
            if bool(req.get("force_svg_large")):
                raise ValueError("Refusing unsafe SVG — lower coverage or disable force_svg_large")
            fmts.discard("svg")
            fmts.update({"stl", "instance_json"})

        raster_basis_fmts = {"svg", "svgz", "png", "jpg", "jpeg"}
        svg_text_for_rasters: str | None = None
        if fmts.intersection(raster_basis_fmts):
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
                visual_style=visual_style,
                palette_by_label=req.get("palette_by_label"),
                mask_geom=mask_geom,
            )
            svg_text_for_rasters = svg_document(
                emitted,
                patch_meta=meta,
                scale=scale,
                rotation_deg=rotation_deg,
                tx=tx,
                ty=ty,
                opts=svg_opts,
            )
            if len(svg_text_for_rasters) > limits.svg_max_chars:
                raise ValueError("SVG plaintext exceeds svg_max_chars — reduce coverage")

        if svg_text_for_rasters is None and ("svg" in fmts or "svgz" in fmts):
            raise RuntimeError("internal error: svg export missing plaintext buffer")

        if "svg" in fmts and svg_text_for_rasters is not None:
            (art / "patch.svg").write_text(svg_text_for_rasters, encoding="utf-8")

        if "svgz" in fmts and svg_text_for_rasters is not None:
            write_svg_or_svgz(art / "patch.svgz", svg_text_for_rasters)

        if "csv" in fmts:
            (art / "tiles.csv").write_bytes(
                tiles_to_csv_rows(
                    emitted,
                    patch_version=patch_version,
                    tile_family=tile_family,
                    seed=req.get("seed"),
                )
            )

        if "json" in fmts:
            (art / "tiles.json").write_bytes(
                tiles_to_json_doc(
                    emitted,
                    patch_version=patch_version,
                    tile_family=tile_family,
                    seed=req.get("seed"),
                    extra={"transform_convention": "World = client_similarity ⊗ generator"},
                )
            )

        thickness = float(req.get("stl_extrusion_mm", 1.0))

        manifest_inst = stl_export.instancing_manifest_bytes(
            emitted,
            patch_version=patch_version,
            tile_family=tile_family,
            seed=req.get("seed"),
            scale=scale,
            rotation_deg=rotation_deg,
            tx=tx,
            ty=ty,
            visual_style=visual_style,
        )

        if "stl" in fmts:
            if nt >= limits.stl_tile_instancing_floor:
                stl_export.write_prototype_stl(str(art / "spectre_proto.stl"), thickness)
                (art / "spectre_instances.json").write_bytes(manifest_inst)
            else:
                # Combined STL is visual/fabrication linework: STL has no native stroke
                # styling, so we turn tile outlines into thin extruded rails.
                facets = stl_export.stroke_stl_facets_for_tiles(
                    emitted,
                    scale=scale,
                    rotation_deg=rotation_deg,
                    tx=tx,
                    ty=ty,
                    thickness_mm=thickness,
                    visual_style=visual_style,
                    mask_geom=mask_geom,
                )
                stl_export.write_binary_stl(str(art / "patch.stl"), facets)

        if "stl_zip" in fmts:
            stl_export.write_independent_tiles_zip(
                art / "tiles_stl.zip",
                emitted,
                format_name="stl",
                scale=scale,
                rotation_deg=rotation_deg,
                tx=tx,
                ty=ty,
                thickness_mm=thickness,
                visual_style=visual_style,
                mask_geom=mask_geom,
            )

        if "obj_zip" in fmts:
            stl_export.write_independent_tiles_zip(
                art / "tiles_obj.zip",
                emitted,
                format_name="obj",
                scale=scale,
                rotation_deg=rotation_deg,
                tx=tx,
                ty=ty,
                thickness_mm=thickness,
                visual_style=visual_style,
                mask_geom=mask_geom,
            )

        if "instance_json" in fmts and not (art / "spectre_instances.json").exists():
            (art / "spectre_instances.json").write_bytes(manifest_inst)

        if "glb" in fmts:
            from spectre_patch.export.gltf_export import write_glb_instanced  # noqa: PLC0415

            write_glb_instanced(
                art / "patch.glb",
                emitted,
                scale=scale,
                rotation_deg=rotation_deg,
                tx=tx,
                ty=ty,
                thickness_mm=thickness,
                visual_style=visual_style,
                mask_geom=mask_geom,
                patch_meta={
                    "patch_engine": PATCH_ENGINE_SEMVER,
                    "tile_family": tile_family,
                    "patch_version": patch_version,
                    "seed": req.get("seed"),
                },
            )

        if "png" in fmts:
            from spectre_patch.export.png_export import (  # noqa: PLC0415
                render_svg_string_to_png_file,
            )

            assert svg_text_for_rasters is not None  # guarded by raster_basis_fmts
            w = int(req.get("png_width_px", 4096))
            h = int(req.get("png_height_px", 4096))
            if w > limits.png_max_dimension_px or h > limits.png_max_dimension_px:
                raise ValueError("PNG width/height exceeds png_max_dimension_px")
            if w * h > limits.png_max_pixels:
                raise ValueError("PNG pixel budget exceeded")
            render_svg_string_to_png_file(
                svg_text_for_rasters,
                art / "patch.png",
                width_px=w,
                height_px=h,
            )

        if fmts.intersection({"jpg", "jpeg"}):
            from spectre_patch.export.png_export import (  # noqa: PLC0415
                render_svg_string_to_jpeg_file,
            )

            assert svg_text_for_rasters is not None
            jw = req.get("jpg_width_px") or req.get("png_width_px") or 4096
            jh = req.get("jpg_height_px") or req.get("png_height_px") or 4096
            w = int(jw)
            h = int(jh)
            if w > limits.png_max_dimension_px or h > limits.png_max_dimension_px:
                raise ValueError("JPEG width/height exceeds png_max_dimension_px")
            if w * h > limits.png_max_pixels:
                raise ValueError("JPEG pixel budget exceeds png_max_pixels")
            q_raw = req.get("jpg_quality")
            quality = int(q_raw) if q_raw is not None else 92
            render_svg_string_to_jpeg_file(
                svg_text_for_rasters,
                art / "patch.jpg",
                width_px=w,
                height_px=h,
                quality=quality,
            )

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
