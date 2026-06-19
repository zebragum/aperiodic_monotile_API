"""Custom side profile via a REAL editable guide line in the viewport.

Instead of a modal overlay, the user gets an actual Blender mesh polyline
("Monotile Edge Profile") that they edit with normal Blender tools (move/add
vertices in Edit Mode). On Apply, the guide is normalized to the canonical
edge frame (0,0)->(1,0) and stamped onto every tile edge with alternating
chirality, exactly like the Spectre paper / aspartate/spectre tooling.
"""

from __future__ import annotations

import math

import bmesh
import bpy
from bpy.props import FloatProperty, IntProperty
from bpy.types import Operator, PropertyGroup

GUIDE_NAME = "Monotile Edge Profile"

# Canonical Tile(1,1) ring (same as API) — kept local so Blender does not need spectre_patch.
_SQRT3 = math.sqrt(3.0)
_PROTOTILE_RING = [
    (0.0, 0.0),
    (1.0, 0.0),
    (1.5, -_SQRT3 / 2.0),
    (1.5 + _SQRT3 / 2.0, 0.5 - _SQRT3 / 2.0),
    (1.5 + _SQRT3 / 2.0, 1.5 - _SQRT3 / 2.0),
    (2.5 + _SQRT3 / 2.0, 1.5 - _SQRT3 / 2.0),
    (3.0 + _SQRT3 / 2.0, 1.5),
    (3.0, 2.0),
    (3.0 - _SQRT3 / 2.0, 1.5),
    (2.5 - _SQRT3 / 2.0, 1.5 + _SQRT3 / 2.0),
    (1.5 - _SQRT3 / 2.0, 1.5 + _SQRT3 / 2.0),
    (0.5 - _SQRT3 / 2.0, 1.5 + _SQRT3 / 2.0),
    (-_SQRT3 / 2.0, 1.5),
    (0.0, 1.0),
]


# --------------------------------------------------------------------------- #
# Pure geometry helpers (no bpy)                                              #
# --------------------------------------------------------------------------- #
def _rotate_about(px: float, py: float, angle: float, ox: float, oy: float) -> tuple[float, float]:
    c, s = math.cos(angle), math.sin(angle)
    dx, dy = px - ox, py - oy
    return ox + c * dx - s * dy, oy + s * dx + c * dy


def _inverse_profile(profile: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for x, y in reversed(profile):
        rx, ry = _rotate_about(x, y, math.pi, 0.5, 0.0)
        out.append((rx, ry))
    return out


def decorate_ring_with_profile(
    ring: list[tuple[float, float]],
    profile: list[tuple[float, float]],
    *,
    amplitude: float = 1.0,
    alternate_edges: bool = True,
) -> list[tuple[float, float]]:
    """Replace each edge with a scaled profile (see aspartate/spectre)."""

    if len(profile) < 2:
        return list(ring)

    amp = float(amplitude)
    scaled = [(x, y * amp) for x, y in profile]
    inverse = _inverse_profile(scaled) if alternate_edges else scaled
    out: list[tuple[float, float]] = []
    chirality = 1

    for i in range(len(ring)):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % len(ring)]
        dx, dy = x1 - x0, y1 - y0
        elen = math.hypot(dx, dy)
        if elen < 1e-12:
            continue
        angle = math.atan2(dy, dx)
        edge_profile = scaled if chirality == 1 else inverse

        for j, (px, py) in enumerate(edge_profile):
            lx, ly = px * elen, py * elen
            wx, wy = _rotate_about(lx, ly, angle, 0.0, 0.0)
            wx += x0
            wy += y0
            if j == 0 and out:
                continue
            out.append((wx, wy))

        if alternate_edges:
            chirality *= -1

    return out if out else list(ring)


def style_ring_vertices(
    ring: list[tuple[float, float]],
    style: str,
    amplitude: float,
    *,
    wavy_segments_per_edge: int = 10,
) -> list[tuple[float, float]]:
    """Preset edge styles, ported from the API so instances style locally (no deploy)."""

    n = len(ring)
    if style == "flat" or amplitude <= 1e-12:
        return list(ring)

    amp = float(amplitude)
    segs = max(4, int(wavy_segments_per_edge))
    out: list[tuple[float, float]] = []

    for i in range(n):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % n]
        ex, ey = x1 - x0, y1 - y0
        elen = math.hypot(ex, ey)
        if elen < 1e-12:
            continue
        tx, ty = ex / elen, ey / elen
        nx, ny = -ty, tx
        sign = 1.0 if (i % 2 == 0) else -1.0
        bulge = sign * amp * elen

        if style == "curvy":
            for k in range(segs):
                t0 = k / segs
                t1 = (k + 1) / segs
                q0x, q0y = (1 - t0) * x0 + t0 * x1, (1 - t0) * y0 + t0 * y1
                q1x, q1y = (1 - t1) * x0 + t1 * x1, (1 - t1) * y0 + t1 * y1
                s0 = 4 * t0 * (1 - t0)
                s1 = 4 * t1 * (1 - t1)
                if k == 0:
                    out.append((q0x + nx * bulge * s0, q0y + ny * bulge * s0))
                out.append((q1x + nx * bulge * s1, q1y + ny * bulge * s1))
        elif style == "wavy":
            # Full-period sine is anti-symmetric about the edge midpoint, so its
            # Spectre mirror equals itself — every edge uses the SAME orientation
            # (no per-edge sign flip, unlike the symmetric bump styles).
            mag = amp * elen * 0.55
            for k in range(segs):
                t = k / segs
                bx, by = (1 - t) * x0 + t * x1, (1 - t) * y0 + t * y1
                wave = math.sin(t * math.pi * 2.0) * mag
                out.append((bx + nx * wave, by + ny * wave))
        elif style == "jagged":
            midx = (x0 + x1) * 0.5 + nx * bulge
            midy = (y0 + y1) * 0.5 + ny * bulge
            out.append((x0, y0))
            out.append((midx, midy))
        elif style == "blocky":
            inset = 0.22
            q0x, q0y = (1 - inset) * x0 + inset * x1, (1 - inset) * y0 + inset * y1
            q1x, q1y = inset * x0 + (1 - inset) * x1, inset * y0 + (1 - inset) * y1
            out.append((x0, y0))
            out.append((q0x + nx * bulge, q0y + ny * bulge))
            out.append((q1x + nx * bulge, q1y + ny * bulge))
        else:
            out.append((x0, y0))

    return out if out else list(ring)


def styled_ring_for_settings(settings, base_ring: list[tuple[float, float]] | None = None):
    """Resolve the final edge ring for the current Side Style (local, no API)."""

    ring = [(float(x), float(y)) for x, y in (base_ring or _PROTOTILE_RING)]
    style = settings.side_style

    if style == "custom" and len(settings.profile_points) > 0:
        profile = [(float(x), float(y)) for x, y in profile_points_for_api(settings)]
        return decorate_ring_with_profile(ring, profile, amplitude=1.0, alternate_edges=True)

    if style in {"curvy", "wavy", "jagged", "blocky"}:
        return style_ring_vertices(
            ring,
            style,
            float(settings.side_style_amplitude),
            wavy_segments_per_edge=int(settings.side_style_wavy_segments),
        )

    return ring


# --------------------------------------------------------------------------- #
# Stored profile <-> settings collection                                      #
# --------------------------------------------------------------------------- #
class MonotileProfilePoint(PropertyGroup):
    x: FloatProperty(name="Along edge", min=0.0, max=1.0, default=0.5)
    offset_y: FloatProperty(name="Bulge", min=-0.75, max=0.75, default=0.0)


def _profile_points_sorted(settings) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = [(0.0, 0.0)]
    for item in sorted(settings.profile_points, key=lambda p: p.x):
        pts.append((float(item.x), float(item.offset_y)))
    pts.append((1.0, 0.0))
    return pts


def profile_points_for_api(settings) -> list[list[float]]:
    return [[float(x), float(y)] for x, y in _profile_points_sorted(settings)]


def _store_profile(settings, profile: list[tuple[float, float]]) -> None:
    settings.profile_points.clear()
    for t, perp in profile:
        if t <= 1e-6 or t >= 1.0 - 1e-6:
            continue
        item = settings.profile_points.add()
        item.x = min(1.0, max(0.0, float(t)))
        item.offset_y = max(-0.75, min(0.75, float(perp)))


def has_custom_profile(settings) -> bool:
    return len(settings.profile_points) > 0


# --------------------------------------------------------------------------- #
# Guide object <-> normalized profile                                         #
# --------------------------------------------------------------------------- #
def _guide_object():
    return bpy.data.objects.get(GUIDE_NAME)


def _guide_to_profile(obj) -> list[tuple[float, float]] | None:
    """Project the guide's vertices onto its own endpoint baseline.

    Returns points in normalized edge space: x along the edge (0..1), y as a
    signed fraction of edge length perpendicular to it. Rotation/scale agnostic.
    """

    me = obj.data
    n = len(me.vertices)
    if n < 2:
        return None

    mw = obj.matrix_world
    pts = [(float((mw @ v.co).x), float((mw @ v.co).y)) for v in me.vertices]

    # Endpoints = the farthest-apart pair (robust to vertex order / subdivision).
    ai, bi, best = 0, 1, -1.0
    for i in range(n):
        for j in range(i + 1, n):
            d = (pts[i][0] - pts[j][0]) ** 2 + (pts[i][1] - pts[j][1]) ** 2
            if d > best:
                best, ai, bi = d, i, j

    ax, ay = pts[ai]
    bvx, bvy = pts[bi][0] - ax, pts[bi][1] - ay
    blen2 = bvx * bvx + bvy * bvy
    if blen2 < 1e-12:
        return None

    out: list[tuple[float, float]] = []
    for x, y in pts:
        rx, ry = x - ax, y - ay
        t = (rx * bvx + ry * bvy) / blen2
        perp = (bvx * ry - bvy * rx) / blen2
        out.append((max(0.0, min(1.0, t)), max(-0.75, min(0.75, perp))))

    out.sort(key=lambda p: p[0])
    out[0] = (0.0, 0.0)
    out[-1] = (1.0, 0.0)
    for i in range(1, len(out)):
        if out[i][0] < out[i - 1][0]:
            out[i] = (out[i - 1][0], out[i][1])
    return out


# The guide is normalized on Apply, so its size/position are cosmetic. We make it
# big and place it at the 3D cursor so it is easy to see next to a tile patch.
_GUIDE_SCALE = 6.0


def _build_guide_mesh(verts_xy: list[tuple[float, float]], origin=(0.0, 0.0)):
    ox, oy = origin
    verts = [
        (float(x) * _GUIDE_SCALE + ox, float(y) * _GUIDE_SCALE + oy, 0.0) for x, y in verts_xy
    ]
    edges = [(i, i + 1) for i in range(len(verts) - 1)]
    me = bpy.data.meshes.new(GUIDE_NAME)
    me.from_pydata(verts, edges, [])
    me.update()
    return me


def _ensure_guide(context, verts_xy: list[tuple[float, float]] | None = None):
    obj = _guide_object()
    cursor = context.scene.cursor.location
    origin = (float(cursor.x), float(cursor.y))
    if verts_xy is not None:
        me = _build_guide_mesh(verts_xy, origin)
        if obj is None:
            obj = bpy.data.objects.new(GUIDE_NAME, me)
            context.scene.collection.objects.link(obj)
        else:
            old = obj.data
            obj.data = me
            if old.users == 0:
                bpy.data.meshes.remove(old)
    elif obj is None:
        obj = bpy.data.objects.new(GUIDE_NAME, _build_guide_mesh(_DEFAULT_GUIDE, origin))
        context.scene.collection.objects.link(obj)
    return obj


# A smooth single bump — the default "Curvy" starting point for custom edges.
_CURVY_GUIDE = [
    (0.0, 0.0),
    (0.25, 0.12),
    (0.5, 0.16),
    (0.75, 0.12),
    (1.0, 0.0),
]
_STRAIGHT_GUIDE = [(0.0, 0.0), (0.5, 0.0), (1.0, 0.0)]
_DEFAULT_GUIDE = _CURVY_GUIDE


def _find_shared_monotile_mesh():
    for mesh in bpy.data.meshes:
        if mesh.name.startswith("Monotile Tile "):
            return mesh
    return None


def _rebuild_mesh_from_ring(mesh: bpy.types.Mesh, ring_xy: list) -> None:
    verts = [(float(x), float(y), 0.0) for x, y in ring_xy]
    face = [tuple(range(len(verts)))]
    mesh.clear_geometry()
    mesh.from_pydata(verts, [], face)
    mesh.update()
    mesh.validate()


def _enter_edit_mode(context, obj) -> None:
    try:
        if context.object and context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        for o in context.view_layer.objects:
            o.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")
        # Select every control point and try to frame the guide in the 3D view.
        try:
            bpy.ops.mesh.select_all(action="SELECT")
        except RuntimeError:
            pass
        for area in context.screen.areas if context.screen else []:
            if area.type == "VIEW_3D":
                for region in area.regions:
                    if region.type == "WINDOW":
                        with context.temp_override(area=area, region=region):
                            try:
                                bpy.ops.view3d.view_selected()
                            except RuntimeError:
                                pass
                        break
                break
    except (RuntimeError, AttributeError):
        # Mode switch only works from the 3D view; fall back to just selecting it.
        try:
            obj.select_set(True)
            context.view_layer.objects.active = obj
        except (RuntimeError, AttributeError):
            pass


# --------------------------------------------------------------------------- #
# Operators                                                                    #
# --------------------------------------------------------------------------- #
class MONOTILE_OT_create_edge_guide(Operator):
    bl_idname = "monotile.create_edge_guide"
    bl_label = "Create / Edit Edge Guide"
    bl_description = (
        "Make an editable guide line in the viewport. Move its vertices in Edit Mode "
        "to shape one tile edge, then click Apply Profile to Tiles"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = _ensure_guide(context, None if _guide_object() else _DEFAULT_GUIDE)
        _enter_edit_mode(context, obj)
        context.scene.monotile_generator.side_style = "custom"
        self.report({"INFO"}, "Edit the 'Monotile Edge Profile' line, then Apply Profile to Tiles.")
        return {"FINISHED"}


class MONOTILE_OT_guide_preset(Operator):
    bl_idname = "monotile.guide_preset"
    bl_label = "Shape Guide"
    bl_description = "Reshape the edge guide line to an example profile"
    bl_options = {"REGISTER", "UNDO"}

    preset: bpy.props.EnumProperty(
        items=[
            ("curvy", "Curvy", "Smooth single-bump starting curve"),
            ("straight", "Straight", "Flat starting edge"),
        ],
        default="curvy",
    )

    def execute(self, context):
        verts = _STRAIGHT_GUIDE if self.preset == "straight" else _CURVY_GUIDE
        obj = _ensure_guide(context, verts)
        _enter_edit_mode(context, obj)
        context.scene.monotile_generator.side_style = "custom"
        return {"FINISHED"}


class MONOTILE_OT_guide_subdivide(Operator):
    bl_idname = "monotile.guide_subdivide"
    bl_label = "Add Points"
    bl_description = (
        "Add control points to the edge guide by subdividing it, so you can shape "
        "smoother curves. Then drag the new dots in Edit Mode"
    )
    bl_options = {"REGISTER", "UNDO"}

    cuts: IntProperty(name="Points per segment", default=1, min=1, max=8)

    def execute(self, context):
        obj = _guide_object()
        if obj is None:
            self.report({"ERROR"}, "Create an edge guide first.")
            return {"CANCELLED"}

        if context.object is obj and obj.mode == "EDIT":
            bpy.ops.object.mode_set(mode="OBJECT")

        me = obj.data
        bm = bmesh.new()
        bm.from_mesh(me)
        if bm.edges:
            bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=int(self.cuts))
        bm.to_mesh(me)
        bm.free()
        me.update()

        _enter_edit_mode(context, obj)
        self.report({"INFO"}, f"Guide now has {len(me.vertices)} points. Drag them, then Apply.")
        return {"FINISHED"}


class MONOTILE_OT_apply_side_profile(Operator):
    bl_idname = "monotile.apply_side_profile"
    bl_label = "Apply Profile to Tiles"
    bl_description = (
        "Read the edge guide line, normalize it, and stamp it onto every tile edge "
        "(updates the shared N-gon mesh live). Also used by Generate and Import. No API call"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.monotile_generator

        # For custom mode, read the guide line first and store it.
        if settings.side_style == "custom":
            obj = _guide_object()
            if obj is None:
                self.report({"ERROR"}, "Create an edge guide first.")
                return {"CANCELLED"}
            if context.object is obj and obj.mode == "EDIT":
                bpy.ops.object.mode_set(mode="OBJECT")
            profile = _guide_to_profile(obj)
            if profile is None:
                self.report({"ERROR"}, "Guide needs at least 2 vertices with some length.")
                return {"CANCELLED"}
            _store_profile(settings, profile)

        mesh = _find_shared_monotile_mesh()
        if mesh is None:
            self.report(
                {"INFO"},
                "Style saved. Import a patch (N-gon instances) or Generate to see it.",
            )
            return {"FINISHED"}

        ring = styled_ring_for_settings(settings)
        _rebuild_mesh_from_ring(mesh, ring)
        users = sum(1 for o in bpy.data.objects if o.data == mesh)
        self.report({"INFO"}, f"Style applied to {users} instance(s).")
        return {"FINISHED"}


# --------------------------------------------------------------------------- #
# Panel section                                                                #
# --------------------------------------------------------------------------- #
def draw_side_style_box(layout, context) -> None:
    settings = context.scene.monotile_generator
    box = layout.box()
    box.label(text="Side Style", icon="MOD_CURVE")
    box.prop(settings, "side_style", text="Style")

    if settings.side_style in {"curvy", "wavy", "jagged", "blocky"}:
        box.prop(settings, "side_style_amplitude", text="Amount")
        if settings.side_style == "wavy":
            box.prop(settings, "side_style_wavy_segments", text="Wavy Detail")
        box.operator("monotile.apply_side_profile", text="Apply Style to Tiles", icon="FILE_REFRESH")
        box.label(text="Applied on Generate, or click Apply", icon="INFO")

    if settings.side_style == "custom":
        col = box.column(align=True)
        col.label(text="1. Start the guide line:")
        row = col.row(align=True)
        row.operator("monotile.guide_preset", text="Curvy", icon="SPHERECURVE").preset = "curvy"
        row.operator("monotile.guide_preset", text="Straight", icon="IPO_LINEAR").preset = "straight"
        col.operator("monotile.create_edge_guide", text="Edit Guide Line", icon="GREASEPENCIL")
        col.operator("monotile.guide_subdivide", text="Add Points", icon="ADD")
        col.separator()
        col.label(text="2. In Edit Mode, drag the dots (G)")
        col.label(text="3. Tab to Object Mode, then:")
        col.operator("monotile.apply_side_profile", text="Apply Profile to Tiles", icon="FILE_REFRESH")
        if has_custom_profile(settings):
            box.label(text=f"Profile saved ({len(settings.profile_points) + 2} points)", icon="CHECKMARK")
        else:
            box.label(text="No profile saved yet — Generate stays flat", icon="ERROR")


PROFILE_PROPERTY_CLASSES = (MonotileProfilePoint,)

PROFILE_OPERATOR_CLASSES = (
    MONOTILE_OT_create_edge_guide,
    MONOTILE_OT_guide_preset,
    MONOTILE_OT_guide_subdivide,
    MONOTILE_OT_apply_side_profile,
)

PROFILE_CLASSES = PROFILE_PROPERTY_CLASSES + PROFILE_OPERATOR_CLASSES
