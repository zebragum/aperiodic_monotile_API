bl_info = {
    "name": "Aperiodic Monotile Generator",
    "author": "Aperiodic Monotile Generator",
    "version": (0, 3, 10),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Monotile",
    "description": "Generate aperiodic monotile patches from the hosted API as editable N-gon instances or GLB.",
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
from mathutils import Matrix, Vector
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import Operator, Panel, PropertyGroup

# Reload bundled submodules so reinstalling/updating in a running Blender does not
# import a stale cached module (otherwise newly added names fail to import).
import importlib as _importlib

from . import profile_ui as _profile_ui

_importlib.reload(_profile_ui)

from .profile_ui import (
    MonotileProfilePoint,
    PROFILE_OPERATOR_CLASSES,
    PROFILE_PROPERTY_CLASSES,
    draw_side_style_box,
    profile_points_for_api,
    styled_ring_for_settings,
)


DEFAULT_API_BASE = "https://api.aperiodicgenerator.com"

# Aperiodic monotile type label → distinct hues (visible in Material Preview).
_LABEL_COLORS = {
    "Gamma": "#E8B923",
    "Delta": "#2E86AB",
    "Theta": "#A23B72",
    "Lambda": "#F18F01",
    "Xi": "#C73E1D",
    "Pi": "#3B1F2B",
    "Sigma": "#44AF69",
    "Phi": "#5C4D7D",
    "Psi": "#9B5DE5",
    "Gamma1": "#F4D35E",
    "Gamma2": "#FFE066",
}
_FALLBACK_PALETTE = ["#8f2f13", "#b74619", "#d95a24", "#f07048", "#ff875e", "#ffa05f", "#ffb85f", "#f4c86a", "#ffd166"]


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
    geometry_mode: EnumProperty(
        name="Geometry",
        items=[
            (
                "instances",
                "Editable N-gon instances",
                "Build one clean Tile(1,1) N-gon and distribute native linked instances "
                "(shared mesh data). No triangulation; edit one tile and all update",
            ),
            (
                "glb",
                "GLB mesh (triangulated)",
                "Download and import a single triangulated GLB patch. Supports clipped "
                "boundary tiles but is not as clean to edit",
            ),
        ],
        default="instances",
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
        description="Request JSON tile metadata alongside the geometry (GLB mode only).",
    )
    wait_timeout_seconds: IntProperty(
        name="Max Wait",
        default=180,
        min=15,
        max=1800,
        description="How long Blender should wait for the API job before giving up. The job may still finish later.",
    )
    side_style: EnumProperty(
        name="Outline Style",
        items=[
            ("flat", "Flat", "Canonical Tile(1,1) edges"),
            ("curvy", "Curvy", "Smooth bulged edges"),
            ("wavy", "Wavy", "Wavy edges along each side"),
            ("jagged", "Jagged", "Angular zig-zag edges"),
            ("blocky", "Blocky", "Stepped block edges"),
            ("custom", "Custom", "Draw your own edge profile with the guide line"),
        ],
        default="flat",
        description="Visual outline style for tile edges (instances and GLB exports)",
    )
    side_style_amplitude: FloatProperty(
        name="Outline Amount",
        default=0.12,
        min=0.0,
        max=0.75,
        soft_max=0.35,
        description="How strong the outline style is (0 = flat edges)",
    )
    side_style_wavy_segments: IntProperty(
        name="Wavy Segments",
        default=10,
        min=4,
        max=64,
        description="Detail level for wavy outline style",
    )
    profile_points: CollectionProperty(type=MonotileProfilePoint)
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


def _monotile_mesh_objects(context) -> list[bpy.types.Object]:
    """Meshes from Monotile collections or with monotile custom props."""

    if context.selected_objects:
        selected = [obj for obj in context.selected_objects if obj.type == "MESH"]
        if selected:
            return selected

    targets: list[bpy.types.Object] = []
    for coll in bpy.data.collections:
        if coll.name.startswith("Monotile "):
            targets.extend(obj for obj in coll.objects if obj.type == "MESH")
    if targets:
        return targets

    return [
        obj
        for obj in context.scene.objects
        if obj.type == "MESH" and (obj.get("monotile_job_id") or obj.get("monotile_label"))
    ]


def _assign_object_material(obj, mat) -> None:
    """Assign a material per-OBJECT so instances sharing one mesh can differ."""

    me = obj.data
    if len(me.materials) == 0:
        me.materials.append(None)
    slot = obj.material_slots[0]
    slot.link = "OBJECT"
    slot.material = mat


def _set_viewport_material_preview(context) -> bool:
    """Switch 3D viewports to Material Preview so assigned colors are visible."""

    switched = False
    screens = [context.screen] if context.screen else list(bpy.data.screens)
    for screen in screens:
        if not screen:
            continue
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    space.shading.type = "MATERIAL"
                    switched = True
    return switched


def _label_from_object(obj: bpy.types.Object) -> str:
    label = obj.get("monotile_label") or obj.get("tile_label")
    if label:
        return str(label)
    name = obj.name
    if name.startswith("tile_"):
        return ""
    return ""


def _request_body(settings: MonotileGeneratorSettings) -> dict:
    if settings.geometry_mode == "instances":
        formats = ["instance_json"]
    else:
        formats = ["glb"]
        if settings.import_json:
            formats.append("json")
    body = {
        "formats": formats,
        "mask": _mask_from_settings(settings),
        "scale": settings.tile_scale,
        "stl_extrusion_mm": settings.extrusion_mm,
    }
    # Instances mode styles the clean ring locally in Blender (no server dependency,
    # stays fully editable). Only GLB needs the API to bake the styled outline.
    if settings.geometry_mode == "glb" and settings.side_style != "flat":
        if settings.side_style == "custom" and len(settings.profile_points) > 0:
            body["side_style"] = "custom"
            body["side_style_amplitude"] = 1.0
            body["side_profile_normalized"] = profile_points_for_api(settings)
        elif settings.side_style != "custom":
            body["side_style"] = settings.side_style
            body["side_style_amplitude"] = settings.side_style_amplitude
            if settings.side_style == "wavy":
                body["side_style_wavy_segments"] = settings.side_style_wavy_segments
    return body


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


def _format_queue_hint(payload: dict) -> str:
    """Human-readable queue / wait line from a job POST or poll response."""

    parts: list[str] = []
    size_class = payload.get("size_class")
    if size_class:
        label = {"small": "Light", "standard": "Standard", "heavy": "Heavy export"}.get(
            str(size_class), str(size_class)
        )
        parts.append(label)
    est = payload.get("estimated_seconds")
    if est is not None:
        parts.append(f"~{int(float(est))}s")
    queue = payload.get("queue") or {}
    pos = queue.get("position")
    if pos and int(pos) > 0:
        parts.append(f"queue #{int(pos)}")
        wait = queue.get("estimated_wait_seconds")
        if wait is not None and float(wait) > 0:
            parts.append(f"wait ~{int(float(wait))}s")
    return " · ".join(parts)


def _run_patch_job(settings, api_base: str, api_key: str) -> dict:
    """Submit a patch job, poll to completion, and return the signed-URL payload."""

    body = _request_body(settings)
    settings.last_status = "Submitting job..."
    response = _json_request("POST", f"{api_base}/v1/patch", api_key=api_key, body=body)
    job_id = response.get("job_id")
    if not job_id:
        raise RuntimeError(f"API did not return job_id: {response}")
    settings.last_job_id = job_id

    hint = _format_queue_hint(response)
    if hint:
        settings.last_status = f"Queued — {hint}"

    deadline = time.time() + settings.wait_timeout_seconds
    status = response.get("status", "queued")
    while time.time() < deadline:
        hint = _format_queue_hint(response)
        line = f"Job {job_id[:8]}: {status}"
        if hint and status in {"queued", "running"}:
            line = f"{line} — {hint}"
        settings.last_status = line
        if status in {"completed", "failed", "cancelled"}:
            break
        time.sleep(2.0)
        response = _json_request("GET", f"{api_base}/v1/jobs/{job_id}", api_key=api_key)
        status = response.get("status", status)

    if status != "completed":
        raise RuntimeError(f"Job did not complete. Final status: {status}")

    url_payload = _json_request("GET", f"{api_base}/v1/jobs/{job_id}/urls", api_key=api_key)
    urls = url_payload.get("urls") or {}
    return {"job_id": job_id, "urls": urls}


def _absolute_url(api_base: str, url: str) -> str:
    return f"{api_base}{url}" if url.startswith("/") else url


def _new_monotile_collection(context, job_id: str):
    collection = bpy.data.collections.new(f"Monotile {job_id[:8]}")
    context.scene.collection.children.link(collection)
    return collection


def _build_prototile_mesh(ring_xy, name: str):
    """One clean, single-face N-gon at canonical Z=0 — no triangulation."""

    verts = [(float(x), float(y), 0.0) for x, y in ring_xy]
    face = [tuple(range(len(verts)))]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], face)
    mesh.update()
    mesh.validate()
    return mesh


def _import_instances(context, settings, api_base: str, job_id: str, urls: dict) -> int:
    """Distribute native Blender instances of one clean N-gon from instance_json."""

    manifest_url = urls.get("spectre_instances.json")
    if not manifest_url:
        raise RuntimeError(f"No instance manifest returned. Files: {', '.join(urls.keys())}")
    manifest_url = _absolute_url(api_base, manifest_url)

    settings.last_status = "Downloading instance manifest..."
    with tempfile.TemporaryDirectory(prefix="monotile_inst_") as tmp:
        manifest_path = Path(tmp) / "spectre_instances.json"
        _download_file(manifest_url, manifest_path)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    ring_xy = manifest.get("prototile_ring_xy")
    instances = manifest.get("instances") or []
    if not ring_xy:
        raise RuntimeError(
            "Manifest has no prototile_ring_xy. Update the add-on or API to a build "
            "that includes the prototile polygon."
        )
    if not instances:
        raise RuntimeError("Manifest contained no instances.")

    # Apply the selected Side Style to the clean canonical ring locally so it works
    # without a server deploy and stays editable (the shared mesh is one N-gon).
    styled_ring = styled_ring_for_settings(settings, [(float(x), float(y)) for x, y in ring_xy])
    shared_mesh = _build_prototile_mesh(styled_ring, f"Monotile Tile {job_id[:8]}")
    collection = _new_monotile_collection(context, job_id)

    depth = float(settings.extrusion_mm)
    count = 0
    for inst in instances:
        rows = inst.get("affine4_row_lists")
        if not rows or len(rows) != 4:
            continue
        obj = bpy.data.objects.new(str(inst.get("id", f"tile_{count}")), shared_mesh)
        obj.matrix_world = Matrix([[float(v) for v in row] for row in rows])
        if depth > 0.0:
            solid = obj.modifiers.new(name="Depth", type="SOLIDIFY")
            solid.thickness = depth
            solid.offset = 0.0
        obj["monotile_job_id"] = job_id
        if inst.get("label"):
            obj["monotile_label"] = inst["label"]
        collection.objects.link(obj)
        count += 1

    return count


def _import_glb(context, settings, api_base: str, job_id: str, urls: dict) -> int:
    glb_url = urls.get("patch.glb") or urls.get("scene.glb")
    if not glb_url:
        raise RuntimeError(f"No GLB URL returned. Files: {', '.join(urls.keys())}")
    glb_url = _absolute_url(api_base, glb_url)

    with tempfile.TemporaryDirectory(prefix="monotile_blender_") as tmp:
        glb_path = Path(tmp) / f"monotile_{job_id}.glb"
        settings.last_status = "Downloading GLB..."
        _download_file(glb_url, glb_path)

        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(glb_path))
        imported = [obj for obj in bpy.data.objects if obj not in before]
        collection = _new_monotile_collection(context, job_id)
        for obj in imported:
            for owner in list(obj.users_collection):
                owner.objects.unlink(obj)
            collection.objects.link(obj)
            obj["monotile_job_id"] = job_id
            tile_label = obj.get("tile_label")
            if tile_label:
                obj["monotile_label"] = str(tile_label)
    return len(imported)


class MONOTILE_OT_generate_import(Operator):
    bl_idname = "monotile.generate_import"
    bl_label = "Generate and Import"
    bl_description = "Submit a patch job to the Aperiodic Monotile API and import the result into Blender"

    def execute(self, context):
        settings = context.scene.monotile_generator
        api_key = settings.api_key.strip()
        if not api_key:
            self.report({"ERROR"}, "Enter an API key first.")
            return {"CANCELLED"}

        api_base = _clean_base_url(settings.api_base)

        try:
            result = _run_patch_job(settings, api_base, api_key)
            job_id = result["job_id"]
            urls = result["urls"]

            if settings.geometry_mode == "instances":
                count = _import_instances(context, settings, api_base, job_id, urls)
                settings.last_status = (
                    f"Imported {count} editable N-gon instances from job {job_id[:8]}"
                )
            else:
                count = _import_glb(context, settings, api_base, job_id, urls)
                settings.last_status = f"Imported GLB ({count} objects) from job {job_id[:8]}"

            self.report({"INFO"}, settings.last_status)
            return {"FINISHED"}
        except Exception as exc:
            settings.last_status = str(exc)
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}


class MONOTILE_OT_apply_label_materials(Operator):
    bl_idname = "monotile.apply_label_materials"
    bl_label = "Apply Label Materials"
    bl_description = (
        "Color tiles by their type label (Gamma, Delta, …). One special pair "
        "shows as Gamma1/Gamma2 in two yellows; the other types get distinct hues. "
        "Use Material Preview or Rendered viewport shading to see colors"
    )

    def execute(self, context):
        mat_cache: dict[str, tuple[bpy.types.Material, tuple]] = {}

        def material_for_label(label: str):
            key = label or "_fallback"
            if key in mat_cache:
                return mat_cache[key]
            hex_color = _LABEL_COLORS.get(label)
            if not hex_color:
                idx = sum(ord(ch) for ch in label) % len(_FALLBACK_PALETTE)
                hex_color = _FALLBACK_PALETTE[idx]
            rgba = tuple(int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)) + (1.0,)
            mat = bpy.data.materials.new(f"Monotile {label or 'Tile'}")
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes["Principled BSDF"]
            bsdf.inputs["Base Color"].default_value = rgba
            bsdf.inputs["Roughness"].default_value = 0.55
            # Viewport display color so tiles are colored in Solid mode too.
            mat.diffuse_color = rgba
            mat_cache[key] = (mat, rgba)
            return mat_cache[key]

        objects = _monotile_mesh_objects(context)
        if not objects:
            self.report({"ERROR"}, "Import a patch first (or select monotile meshes).")
            return {"CANCELLED"}

        labeled = 0
        count = 0
        for obj in objects:
            label = _label_from_object(obj)
            if label:
                labeled += 1
            mat, rgba = material_for_label(label)
            # Per-OBJECT material slot so tiles sharing one mesh can differ by label.
            _assign_object_material(obj, mat)
            obj.color = rgba
            count += 1

        switched = _set_viewport_material_preview(context)

        msg = f"Colored {count} tile(s) by label ({labeled} with type labels)."
        if labeled == 0:
            msg += " Tip: re-import as N-gon instances for distinct per-label colors."
        elif not switched:
            msg += " Set viewport shading to Material Preview (top-right sphere) to see them."
        self.report({"INFO"}, msg)
        return {"FINISHED"}


# Legacy id kept so old toolbar layouts don't break.
class MONOTILE_OT_randomize_materials(MONOTILE_OT_apply_label_materials):
    bl_idname = "monotile.randomize_materials"
    bl_label = "Apply Label Materials"


class MONOTILE_OT_bevel_tiles(Operator):
    bl_idname = "monotile.bevel_tiles"
    bl_label = "Bevel Imported Tiles"
    bl_description = (
        "Add a small Bevel and Weighted Normal modifier to selected monotile meshes "
        "(or all meshes in Monotile collections). Non-destructive — tweak width in the modifier stack"
    )

    bevel_width: FloatProperty(name="Bevel Width", default=0.03, min=0.0, soft_max=0.2)
    bevel_segments: IntProperty(name="Segments", default=2, min=1, max=8)

    def execute(self, context):
        targets: list[bpy.types.Object] = []
        if context.selected_objects:
            targets = [obj for obj in context.selected_objects if obj.type == "MESH"]
        else:
            for coll in bpy.data.collections:
                if coll.name.startswith("Monotile "):
                    targets.extend(obj for obj in coll.objects if obj.type == "MESH")

        if not targets:
            self.report({"ERROR"}, "Select monotile meshes or import a patch first.")
            return {"CANCELLED"}

        count = 0
        for obj in targets:
            if not any(mod.type == "BEVEL" and mod.name == "Monotile Bevel" for mod in obj.modifiers):
                bevel = obj.modifiers.new(name="Monotile Bevel", type="BEVEL")
                bevel.width = self.bevel_width
                bevel.segments = self.bevel_segments
                bevel.limit_method = "ANGLE"
            if not any(
                mod.type == "WEIGHTED_NORMAL" and mod.name == "Monotile Weighted Normal"
                for mod in obj.modifiers
            ):
                wn = obj.modifiers.new(name="Monotile Weighted Normal", type="WEIGHTED_NORMAL")
                wn.keep_sharp = True
            count += 1

        self.report({"INFO"}, f"Bevel + weighted normals on {count} mesh(es).")
        return {"FINISHED"}


class MONOTILE_OT_organize_by_label(Operator):
    bl_idname = "monotile.organize_by_label"
    bl_label = "Organize Tiles by Label"
    bl_description = (
        "Group tiles into one sub-collection per tile type (Gamma, Delta, …), each "
        "with its own shared mesh. Then you can give a whole tile type its own material — "
        "e.g. grass on every Gamma tile"
    )

    def execute(self, context):
        objects = [
            obj
            for obj in context.scene.objects
            if obj.type == "MESH" and obj.get("monotile_label")
        ]
        if not objects:
            self.report(
                {"ERROR"},
                "No labeled tiles found. Import as Editable N-gon instances first.",
            )
            return {"CANCELLED"}

        groups: dict[str, list[bpy.types.Object]] = {}
        for obj in objects:
            groups.setdefault(str(obj.get("monotile_label")), []).append(obj)

        for label, members in groups.items():
            sub_name = f"Monotile · {label}"
            sub = bpy.data.collections.get(sub_name) or bpy.data.collections.new(sub_name)
            if context.scene.collection.children.get(sub_name) is None:
                try:
                    context.scene.collection.children.link(sub)
                except RuntimeError:
                    pass

            # One mesh per label (independent materials), copied from the current tile mesh.
            label_mesh = members[0].data.copy()
            label_mesh.name = f"Monotile {label}"
            # Per-label mesh carries its own material slot so assigning a material to
            # any tile of this label colors the whole label, and nothing else.
            label_mesh.materials.clear()

            for obj in members:
                obj.data = label_mesh
                for coll in list(obj.users_collection):
                    coll.objects.unlink(obj)
                sub.objects.link(obj)

        self.report(
            {"INFO"},
            f"Organized {len(objects)} tiles into {len(groups)} label collections. "
            "Select a label's collection, then assign it a material.",
        )
        return {"FINISHED"}


def _draw_monotile_panel(layout, context) -> None:
    settings = context.scene.monotile_generator

    layout.prop(settings, "api_base")
    layout.prop(settings, "api_key")

    box = layout.box()
    box.label(text="Output")
    box.prop(settings, "geometry_mode", text="")
    if settings.geometry_mode == "instances":
        box.label(text="Clean N-gon, shared mesh - edit one, all update", icon="MOD_DATA_TRANSFER")
        if settings.extrusion_mm > 0.0:
            box.label(text="Depth adds a Solidify modifier (non-destructive)", icon="MOD_SOLIDIFY")
    else:
        box.label(
            text="Heavier export — use N-gon instances for editable Blender work",
            icon="INFO",
        )

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
    draw_side_style_box(layout, context)
    if settings.geometry_mode == "glb":
        box.prop(settings, "import_json")
    box.prop(settings, "wait_timeout_seconds")

    layout.operator("monotile.generate_import", icon="IMPORT")

    mat_box = layout.box()
    mat_box.label(text="Materials & Cleanup", icon="MATERIAL")
    mat_box.operator(
        "monotile.apply_label_materials", text="Quick Color by Label", icon="MATERIAL_DATA"
    )
    mat_box.operator(
        "monotile.organize_by_label", text="Organize into Label Collections", icon="OUTLINER"
    )
    mat_box.label(text="Then assign your own material per collection", icon="INFO")
    mat_box.operator("monotile.bevel_tiles", icon="MOD_BEVEL")

    layout.label(text=f"Status: {settings.last_status}")
    if settings.last_job_id:
        layout.label(text=f"Last job: {settings.last_job_id[:12]}...")


class MONOTILE_PT_panel(Panel):
    bl_label = "Aperiodic Monotile"
    bl_idname = "MONOTILE_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Monotile"

    def draw(self, context):
        _draw_monotile_panel(self.layout, context)


class MONOTILE_PT_scene_panel(Panel):
    bl_label = "Aperiodic Monotile"
    bl_idname = "MONOTILE_PT_scene_panel"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    def draw(self, context):
        _draw_monotile_panel(self.layout, context)


classes = (
    *PROFILE_PROPERTY_CLASSES,
    MonotileGeneratorSettings,
    MONOTILE_OT_use_selected_bounds,
    MONOTILE_OT_generate_import,
    MONOTILE_OT_apply_label_materials,
    MONOTILE_OT_randomize_materials,
    MONOTILE_OT_bevel_tiles,
    MONOTILE_OT_organize_by_label,
    MONOTILE_PT_panel,
    MONOTILE_PT_scene_panel,
    *PROFILE_OPERATOR_CLASSES,
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
