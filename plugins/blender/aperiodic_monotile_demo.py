bl_info = {
    "name": "Aperiodic Monotile API Demo",
    "author": "Aperiodic Monotile API",
    "version": (0, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Monotile API",
    "description": "Request Spectre monotile SVG patches from the hosted API.",
    "category": "Add Mesh",
}

import json
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import bpy


API_BASE = "https://aperiodic-monotile-api.onrender.com"


def _request_json(method: str, url: str, *, api_key: str, body: dict | None = None) -> dict:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Accept": "application/json", "X-API-Key": api_key}
    if payload is not None:
        headers["Content-Type"] = "application/json"
        headers["Idempotency-Key"] = f"blender-demo-{int(time.time() * 1000)}"
    req = urllib.request.Request(url, data=payload, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API request failed ({exc.code}): {detail}") from exc


def _download_file(url: str, path: Path) -> None:
    with urllib.request.urlopen(url, timeout=60) as resp:
        path.write_bytes(resp.read())


def _mask_body(settings: bpy.types.PropertyGroup) -> dict:
    if settings.shape == "CIRCLE":
        return {"type": "circle", "center": [0, 0], "radius": settings.size / 2.0}
    if settings.shape == "RECTANGLE":
        width = settings.size
        height = settings.size / 2.25
        return {
            "type": "rectangle",
            "bounds": {"xmin": -width / 2.0, "ymin": -height / 2.0, "xmax": width / 2.0, "ymax": height / 2.0},
        }
    if settings.shape == "TRIANGLE":
        return {"type": "triangle", "center": [0, 0], "side_length": settings.size}
    return {"type": "square", "center": [0, 0], "half_side": settings.size / 2.0}


class MonotileSettings(bpy.types.PropertyGroup):
    api_key: bpy.props.StringProperty(
        name="API Key",
        description="Aperiodic Monotile API key",
        subtype="PASSWORD",
        default="",
    )
    shape: bpy.props.EnumProperty(
        name="Shape",
        items=[
            ("CIRCLE", "Circle", "Circular mask"),
            ("RECTANGLE", "9:4 Rectangle", "Wide rectangular mask"),
            ("TRIANGLE", "Triangle", "Equilateral triangle mask"),
            ("SQUARE", "Square", "Square mask"),
        ],
        default="CIRCLE",
    )
    size: bpy.props.FloatProperty(
        name="Size (canonical units)",
        min=5.0,
        max=500.0,
        default=50.0,
    )
    pixel_target: bpy.props.IntProperty(
        name="SVG pixel target",
        min=128,
        max=4000,
        default=1000,
    )


class MONOTILE_OT_generate_svg(bpy.types.Operator):
    bl_idname = "monotile.generate_svg"
    bl_label = "Generate SVG Patch"
    bl_description = "Request an SVG patch from the hosted Aperiodic Monotile API"

    def execute(self, context: bpy.types.Context) -> set[str]:
        settings = context.scene.monotile_api_settings
        if not settings.api_key:
            self.report({"ERROR"}, "Enter an API key first")
            return {"CANCELLED"}

        body = {
            "scale": 1,
            "coverage_half_extent": max(settings.size, 80.0),
            "retention": "clip",
            "formats": ["svg"],
            "svg_pixel_target": int(settings.pixel_target),
            "svg_margin": 0,
            "svg_compact": True,
            "svg_fill": "#d94738",
            "svg_stroke": "#1b1b1b",
            "svg_stroke_width": 0.25,
            "mask": _mask_body(settings),
        }

        try:
            created = _request_json("POST", f"{API_BASE}/v1/patch", api_key=settings.api_key, body=body)
            job_id = created["job_id"]
            job = {}
            for _ in range(45):
                time.sleep(2)
                job = _request_json("GET", f"{API_BASE}/v1/jobs/{job_id}", api_key=settings.api_key)
                if job.get("status") in {"completed", "failed", "cancelled"}:
                    break
            if job.get("status") != "completed":
                raise RuntimeError(f"Job did not complete: {job}")

            urls = _request_json("GET", f"{API_BASE}/v1/jobs/{job_id}/urls", api_key=settings.api_key)
            rel = urls.get("urls", {}).get("patch.svg")
            if not rel:
                raise RuntimeError("patch.svg was not returned")

            out = Path(tempfile.gettempdir()) / f"monotile-{job_id}.svg"
            _download_file(f"{API_BASE}{rel}", out)
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        # Blender's SVG importer is an optional built-in add-on. If unavailable,
        # still give the user the downloaded file path.
        try:
            bpy.ops.import_curve.svg(filepath=str(out))
            self.report({"INFO"}, f"Imported {out.name}")
        except Exception:
            self.report({"INFO"}, f"Downloaded SVG to {out}")
        return {"FINISHED"}


class MONOTILE_PT_panel(bpy.types.Panel):
    bl_label = "Aperiodic Monotile API"
    bl_idname = "MONOTILE_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Monotile API"

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        settings = context.scene.monotile_api_settings
        layout.prop(settings, "api_key")
        layout.prop(settings, "shape")
        layout.prop(settings, "size")
        layout.prop(settings, "pixel_target")
        layout.operator("monotile.generate_svg", icon="MOD_TILING")


classes = (MonotileSettings, MONOTILE_OT_generate_svg, MONOTILE_PT_panel)


def register() -> None:
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.monotile_api_settings = bpy.props.PointerProperty(type=MonotileSettings)


def unregister() -> None:
    del bpy.types.Scene.monotile_api_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
