bl_info = {
    "name": "Aperiodic Monotile Generator",
    "author": "Aperiodic Monotile Generator",
    "version": (0, 1, 1),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Monotile",
    "description": "Generate aperiodic monotile GLB patches from the hosted API and import them into Blender.",
    "category": "Import-Export",
}
import json
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import bpy
from mathutils import Vector
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import Operator, Panel, PropertyGroup


DEFAULT_API_BASE = "https://aperiodic-monotile-api.onrender.com"


def _clean_base_url(value: str) -> str:
    return (value or DEFAULT_API_BASE).strip().rstrip("/")


def _json_request(method: str, url: str, *, api_key: str = "", body: dict | None = None, timeout: int = 60) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
        headers["Idempotency-Key"] = f"blender-{uuid.uuid4()}"
    if api_key:
        headers["X-API-Key"] = api_key.strip()
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw or "{}")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
            message = payload.get("error", {}).get("message") or payload.get("detail") or raw
        except json.JSONDecodeError:
            message = raw or str(exc)
        raise RuntimeError(f"HTTP {exc.code}: {message}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error: {exc}") from exc


def _download_file(url: str, path: Path, *, timeout: int = 180) -> None:
    request = urllib.request.Request(url, headers={"Accept": "*/*"}, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        path.write_bytes(response.read())


def _active_collection_name() -> str:
    obj = bpy.context.object
    if obj and obj.users_collection:
        return obj.users_collection[0].name
    return bpy.context.scene.collection.name


class MonotileGeneratorSettings(PropertyGroup):
    api_base: StringProperty(
        name="API Base",
        default=DEFAULT_API_BASE,
        description="Hosted Aperiodic Monotile API base URL",
    )
    api_key: StringProperty(
        name="API Key",
        default="",
        subtype="PASSWORD",
        description="Paid API key. Stored in this Blender file if saved.",
    )
    boundary: EnumProperty(
        name="Boundary",
        items=[
            ("rectangle", "Rectangle", "Fill a rectangle"),
            ("square", "Square", "Fill a square"),
            ("circle", "Circle", "Fill a circle"),
            ("triangle", "Triangle", "Fill an equilateral triangle"),
            ("regular_hexagon", "Hexagon", "Fill a regular hexagon"),
            ("rounded_rect", "Rounded rectangle", "Fill a rounded rectangle"),
        ],
        default="rectangle",
    )
    width: FloatProperty(name="Width", default=40.0, min=1.0, soft_max=300.0)
    height: FloatProperty(name="Height", default=24.0, min=1.0, soft_max=300.0)
    half_side: FloatProperty(name="Half Side", default=20.0, min=0.5, soft_max=150.0)
    radius: FloatProperty(name="Radius", default=20.0, min=1.0, soft_max=150.0)
    side_length: FloatProperty(name="Side", default=40.0, min=1.0, soft_max=300.0)
    corner_radius: FloatProperty(name="Corner", default=3.0, min=0.0, soft_max=50.0)
    tile_scale: FloatProperty(
        name="Tile Scale",
        default=1.0,
        min=0.05,
        soft_min=0.25,
        soft_max=5.0,
        description="API scale parameter in canonical tile units",
    )
    extrusion_mm: FloatProperty(
        name="Depth",
        default=1.0,
        min=0.0,
        soft_max=20.0,
        description="GLB/STL extrusion depth in mm; 0 = flat tile caps only (extrude yourself in Blender)",
    )
    import_json: BoolProperty(
        name="Also request JSON",
        default=False,
        description="Request JSON metadata along with GLB. The add-on imports GLB only in this version.",
    )
    wait_timeout_seconds: IntProperty(
        name="Max Wait",
        default=180,
        min=15,
        max=1800,
        description="How long Blender should wait for the API job before giving up. The job may still finish later.",
    )
    last_job_id: StringProperty(name="Last job", default="")
    last_status: StringProperty(name="Status", default="Ready")


def _mask_from_settings(settings: MonotileGeneratorSettings) -> dict:
    if settings.boundary == "square":
        return {"type": "square", "half_side": settings.half_side}
    if settings.boundary == "circle":
        return {"type": "circle", "radius": settings.radius}
    if settings.boundary == "triangle":
        return {"type": "triangle", "side_length": settings.side_length}
    if settings.boundary == "regular_hexagon":
        return {"type": "regular_hexagon", "circumradius": settings.radius}
    if settings.boundary == "rounded_rect":
        return {
            "type": "rounded_rect",
            "width": settings.width,
            "height": settings.height,
            "corner_radius": min(settings.corner_radius, min(settings.width, settings.height) / 2),
        }
    return {"type": "rectangle", "width": settings.width, "height": settings.height}


def _request_body(settings: MonotileGeneratorSettings) -> dict:
    formats = ["glb"]
    if settings.import_json:
        formats.append("json")
    return {
        "formats": formats,
        "mask": _mask_from_settings(settings),
        "scale": settings.tile_scale,
        "stl_extrusion_mm": settings.extrusion_mm,
    }


class MONOTILE_OT_use_selected_bounds(Operator):
    bl_idname = "monotile.use_selected_bounds"
    bl_label = "Use Selected Bounds"
    bl_description = "Use the selected object's world-space bounding box as a rectangle boundary"

    def execute(self, context):
        settings = context.scene.monotile_generator
        obj = context.object
        if obj is None:
            self.report({"ERROR"}, "Select an object first.")
            return {"CANCELLED"}

        corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        xs = [corner.x for corner in corners]
        ys = [corner.y for corner in corners]
        settings.boundary = "rectangle"
        settings.width = max(max(xs) - min(xs), 1.0)
        settings.height = max(max(ys) - min(ys), 1.0)
        settings.last_status = f"Using selected bounds: {settings.width:.2f} x {settings.height:.2f}"
        return {"FINISHED"}


class MONOTILE_OT_generate_import_glb(Operator):
    bl_idname = "monotile.generate_import_glb"
    bl_label = "Generate and Import GLB"
    bl_description = "Submit a GLB job to the Aperiodic Monotile API, download it, and import it into Blender"

    def execute(self, context):
        settings = context.scene.monotile_generator
        api_key = settings.api_key.strip()
        if not api_key:
            self.report({"ERROR"}, "Enter an API key first.")
            return {"CANCELLED"}

        api_base = _clean_base_url(settings.api_base)
        body = _request_body(settings)

        try:
            settings.last_status = "Submitting job..."
            response = _json_request("POST", f"{api_base}/v1/patch", api_key=api_key, body=body)
            job_id = response.get("job_id")
            if not job_id:
                raise RuntimeError(f"API did not return job_id: {response}")
            settings.last_job_id = job_id

            deadline = time.time() + settings.wait_timeout_seconds
            status = response.get("status", "queued")
            while time.time() < deadline:
                settings.last_status = f"Job {job_id[:8]}: {status}"
                if status in {"completed", "failed", "cancelled"}:
                    break
                time.sleep(2.0)
                status_payload = _json_request("GET", f"{api_base}/v1/jobs/{job_id}", api_key=api_key)
                status = status_payload.get("status", status)

            if status != "completed":
                raise RuntimeError(f"Job did not complete. Final status: {status}")

            url_payload = _json_request("GET", f"{api_base}/v1/jobs/{job_id}/urls", api_key=api_key)
            urls = url_payload.get("urls") or {}
            glb_url = urls.get("patch.glb") or urls.get("scene.glb")
            if not glb_url:
                raise RuntimeError(f"No GLB URL returned. Files: {', '.join(urls.keys())}")
            if glb_url.startswith("/"):
                glb_url = f"{api_base}{glb_url}"

            with tempfile.TemporaryDirectory(prefix="monotile_blender_") as tmp:
                glb_path = Path(tmp) / f"monotile_{job_id}.glb"
                settings.last_status = "Downloading GLB..."
                _download_file(glb_url, glb_path)

                before = set(bpy.data.objects)
                bpy.ops.import_scene.gltf(filepath=str(glb_path))
                imported = [obj for obj in bpy.data.objects if obj not in before]
                collection = bpy.data.collections.new(f"Monotile {job_id[:8]}")
                context.scene.collection.children.link(collection)
                for obj in imported:
                    for owner in list(obj.users_collection):
                        owner.objects.unlink(obj)
                    collection.objects.link(obj)
                    obj["monotile_job_id"] = job_id

            settings.last_status = f"Imported GLB from job {job_id[:8]}"
            self.report({"INFO"}, settings.last_status)
            return {"FINISHED"}
        except Exception as exc:
            settings.last_status = str(exc)
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}


class MONOTILE_OT_randomize_materials(Operator):
    bl_idname = "monotile.randomize_materials"
    bl_label = "Randomize Tile Materials"
    bl_description = "Assign a simple warm palette to selected or recently imported monotile objects"

    def execute(self, context):
        palette = ["#8f2f13", "#b74619", "#d95a24", "#f07048", "#ff875e", "#ffa05f", "#ffb85f", "#f4c86a", "#ffd166"]
        mats = []
        for color in palette:
            mat = bpy.data.materials.new(f"Monotile {color}")
            mat.use_nodes = True
            rgb = tuple(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
            mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*rgb, 1.0)
            mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.62
            mats.append(mat)

        objects = context.selected_objects or list(bpy.context.scene.objects)
        count = 0
        for obj in objects:
            if obj.type != "MESH":
                continue
            key = obj.name
            idx = sum(ord(ch) for ch in key) % len(mats)
            obj.data.materials.clear()
            obj.data.materials.append(mats[idx])
            count += 1
        self.report({"INFO"}, f"Assigned materials to {count} mesh objects.")
        return {"FINISHED"}


class MONOTILE_PT_panel(Panel):
    bl_label = "Aperiodic Monotile"
    bl_idname = "MONOTILE_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Monotile"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.monotile_generator

        layout.prop(settings, "api_base")
        layout.prop(settings, "api_key")

        box = layout.box()
        box.label(text="Boundary")
        box.prop(settings, "boundary")
        if settings.boundary in {"rectangle", "rounded_rect"}:
            row = box.row(align=True)
            row.prop(settings, "width")
            row.prop(settings, "height")
            if settings.boundary == "rounded_rect":
                box.prop(settings, "corner_radius")
        elif settings.boundary == "square":
            box.prop(settings, "half_side")
        elif settings.boundary == "circle":
            box.prop(settings, "radius")
        elif settings.boundary == "regular_hexagon":
            box.prop(settings, "radius", text="Circumradius")
        elif settings.boundary == "triangle":
            box.prop(settings, "side_length")
        box.operator("monotile.use_selected_bounds", icon="PIVOT_BOUNDBOX")

        box = layout.box()
        box.label(text="Generation")
        box.prop(settings, "tile_scale")
        box.prop(settings, "extrusion_mm")
        box.prop(settings, "import_json")
        box.prop(settings, "wait_timeout_seconds")

        layout.operator("monotile.generate_import_glb", icon="IMPORT")
        layout.operator("monotile.randomize_materials", icon="MATERIAL_DATA")
        layout.label(text=f"Status: {settings.last_status}")
        if settings.last_job_id:
            layout.label(text=f"Last job: {settings.last_job_id[:12]}...")


classes = (
    MonotileGeneratorSettings,
    MONOTILE_OT_use_selected_bounds,
    MONOTILE_OT_generate_import_glb,
    MONOTILE_OT_randomize_materials,
    MONOTILE_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.monotile_generator = PointerProperty(type=MonotileGeneratorSettings)


def unregister():
    del bpy.types.Scene.monotile_generator
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
