"""Headless Cycles render: periodic hexagons (left) vs aperiodic Spectre tiles (right).

One continuous glazed-ceramic floor split down the center seam. The left half
is a regular hexagonal grid in cool slate tones; the right half is a real
Spectre / Tile(1,1) patch (from generator JSON) in the site's warm coral/gold
palette. Same material, same light — only the geometry differs.

Run:
    blender --background --python blender_periodic_vs_aperiodic.py -- \
        --width 2048 --height 1152 --samples 128 \
        --out ../../outputs/periodic_vs_aperiodic.png
"""

import colorsys
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
import mathutils
import numpy as np

SQRT3 = math.sqrt(3.0)

PROTOTILE_RING = [
    (0.0, 0.0),
    (1.0, 0.0),
    (1.5, -SQRT3 / 2.0),
    (1.5 + SQRT3 / 2.0, 0.5 - SQRT3 / 2.0),
    (1.5 + SQRT3 / 2.0, 1.5 - SQRT3 / 2.0),
    (2.5 + SQRT3 / 2.0, 1.5 - SQRT3 / 2.0),
    (3.0 + SQRT3 / 2.0, 1.5),
    (3.0, 2.0),
    (3.0 - SQRT3 / 2.0, 1.5),
    (2.5 - SQRT3 / 2.0, 1.5 + SQRT3 / 2.0),
    (1.5 - SQRT3 / 2.0, 1.5 + SQRT3 / 2.0),
    (0.5 - SQRT3 / 2.0, 1.5 + SQRT3 / 2.0),
    (-SQRT3 / 2.0, 1.5),
    (0.0, 1.0),
]
# Tile(1,1) area with unit edges ~= 4 + 2*sqrt(3); match hexagon area to it.
TILE_AREA = 4.0 + 2.0 * SQRT3
HEX_R = math.sqrt(TILE_AREA * 2.0 / (3.0 * SQRT3))  # circumradius, equal area


def apply_affine(affine6, points):
    a, b, c, d, e, f = affine6
    return [(a * x + b * y + c, d * x + e * y + f) for x, y in points]


def expand_ring(ring, factor):
    cx = sum(p[0] for p in ring) / len(ring)
    cy = sum(p[1] for p in ring) / len(ring)
    return [(cx + (x - cx) * factor, cy + (y - cy) * factor) for x, y in ring]


def signed_area(ring):
    s = 0.0
    n = len(ring)
    for i in range(n):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % n]
        s += x0 * y1 - x1 * y0
    return 0.5 * s


def hbytes(seed, salt=""):
    return hashlib.sha256((seed + salt).encode("utf-8")).digest()


def median(values):
    s = sorted(values)
    n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def parse_args(argv):
    import argparse

    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser()
    parser.add_argument("--tile-json", default=str(root / "outputs" / "monotile_vertical_rectangle_max_labels.json"))
    parser.add_argument("--out", default=str(root / "outputs" / "periodic_vs_aperiodic.png"))
    parser.add_argument("--width", type=int, default=2048)
    parser.add_argument("--height", type=int, default=1152)
    parser.add_argument("--samples", type=int, default=128)
    parser.add_argument("--half-w", type=float, default=70.0)
    parser.add_argument("--half-h", type=float, default=55.0)
    parser.add_argument("--seam", type=float, default=0.9, help="half-gap at the center seam")
    parser.add_argument("--grout-inset", type=float, default=0.955)
    parser.add_argument("--thickness", type=float, default=0.34)
    parser.add_argument("--tilt-deg", type=float, default=3.2)
    idx = argv.index("--") if "--" in argv else len(argv)
    return parser.parse_args(argv[idx + 1:])


def color_slate(seed):
    """Cool desaturated steel-blue: deliberately calm and repetitive-feeling."""
    b = hbytes(seed, "col")
    hue = 0.58 + (b[0] / 255.0 - 0.5) * 0.03
    sat = 0.22 + (b[1] / 255.0) * 0.10
    val = 0.18 + (b[2] / 255.0) ** 1.6 * 0.42
    return colorsys.hsv_to_rgb(hue % 1.0, sat, val)


def color_ember(seed):
    """Warm coral -> gold, the site accent family."""
    b = hbytes(seed, "col")
    hue = (0.02 + (b[0] / 255.0) * 0.085) % 1.0
    sat = 0.80 + (b[1] / 255.0) * 0.2
    val = 0.16 + (b[2] / 255.0) ** 1.35 * 0.62
    return colorsys.hsv_to_rgb(hue, min(sat, 1.0), val)


def hexagon_rings(half_w, half_h, seam):
    """Pointy-top hexagonal grid filling x in [-half_w, -seam]."""
    r = HEX_R
    w = SQRT3 * r          # horizontal pitch
    h = 1.5 * r            # vertical pitch
    rings = []
    row = 0
    y = -half_h - r
    while y < half_h + r:
        offset = (w / 2.0 if row % 2 else 0.0)
        x = -half_w - w + offset
        while x < -seam + w:
            ring = [
                (x + r * math.sin(a), y + r * math.cos(a))
                for a in [math.pi / 3.0 * k for k in range(6)]
            ]
            cx = sum(p[0] for p in ring) / 6.0
            if cx <= -seam - r * 0.25:
                rings.append((ring, f"hex_{row}_{round(x, 2)}"))
            x += w
        y += h
        row += 1
    return rings


def spectre_rings(path, half_w, half_h, seam):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    raw = payload["tiles"]
    ox = median([t["centroid_canonical_xy"][0] for t in raw])
    oy = median([t["centroid_canonical_xy"][1] for t in raw])
    rings = []
    for t in raw:
        cx, cy = t["centroid_canonical_xy"]
        x, y = cx - ox, cy - oy
        # shift patch so it fills the right half
        x += half_w / 2.0 + seam
        if seam + 1.2 <= x <= half_w + 4 and abs(y) <= half_h + 4:
            ring = apply_affine(t["generator_affine6"], PROTOTILE_RING)
            ring = [(px - ox + half_w / 2.0 + seam, py - oy) for px, py in ring]
            rings.append((ring, str(t.get("id") or "tile")))
    return rings


def build_tiles(rings_with_seeds, color_fn, args, name):
    verts, faces, face_colors = [], [], []
    for ring, seed in rings_with_seeds:
        ring = expand_ring(ring, args.grout_inset)
        if signed_area(ring) < 0.0:
            ring.reverse()
        n = len(ring)
        cx = sum(p[0] for p in ring) / n
        cy = sum(p[1] for p in ring) / n

        rgb = color_fn(seed)
        side = tuple(c * 0.55 for c in rgb)

        b = hbytes(seed, "tilt")
        ang = math.radians(args.tilt_deg) * (b[0] / 255.0)
        axis = mathutils.Vector((math.cos(b[1] / 255.0 * 2 * math.pi),
                                 math.sin(b[1] / 255.0 * 2 * math.pi), 0.0))
        rot = mathutils.Matrix.Rotation(ang, 3, axis)
        lift = args.thickness * (0.9 + 0.2 * (b[2] / 255.0))
        centroid = mathutils.Vector((cx, cy, lift * 0.5))

        start = len(verts)
        local = [mathutils.Vector((x, y, 0.0)) for x, y in ring]
        local += [mathutils.Vector((x, y, lift)) for x, y in ring]
        for v in local:
            p = rot @ (v - centroid) + centroid
            verts.append((p.x, p.y, p.z))

        faces.append(tuple(range(start + n, start + 2 * n)))
        face_colors.append((*rgb, 1.0))
        for i in range(n):
            j = (i + 1) % n
            faces.append((start + i, start + j, start + n + j, start + n + i))
            face_colors.append((*side, 1.0))

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    attr = mesh.color_attributes.new(name="Col", type="BYTE_COLOR", domain="FACE")
    attr.data.foreach_set("color", np.array(face_colors, dtype=np.float32).ravel())
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def add_grout_plane(half_w, half_h):
    mesh = bpy.data.meshes.new("Grout")
    m = 10.0
    mesh.from_pydata(
        [(-half_w - m, -half_h - m, 0.0), (half_w + m, -half_h - m, 0.0),
         (half_w + m, half_h + m, 0.0), (-half_w - m, half_h + m, 0.0)],
        [], [(0, 1, 2, 3)])
    mesh.update()
    obj = bpy.data.objects.new("Grout", mesh)
    bpy.context.scene.collection.objects.link(obj)
    mat = bpy.data.materials.new("GroutMat")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.06, 0.055, 0.05, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.92
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 18.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.3
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    mesh.materials.append(mat)


def mat_glaze(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_name = "Col"
    nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.10
    try:
        bsdf.inputs["Coat Weight"].default_value = 0.55
        bsdf.inputs["Coat Roughness"].default_value = 0.08
    except KeyError:
        pass
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.9
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.07
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def setup_sky_world(sun_elev_deg, sun_rot_deg, strength):
    world = bpy.data.worlds.new("SkyWorld")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes["Background"]
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    sky.sun_elevation = math.radians(sun_elev_deg)
    sky.sun_rotation = math.radians(sun_rot_deg)
    sky.sun_intensity = 0.6
    sky.sun_size = math.radians(2.0)
    sky.altitude = 400.0
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    bg.inputs[1].default_value = strength


def add_area(loc, size, energy, color, aim=(0.0, 0.0, 0.0)):
    light = bpy.data.lights.new("Area", type="AREA")
    light.energy = energy
    light.size = size
    light.color = color
    obj = bpy.data.objects.new("Area", light)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = loc
    d = mathutils.Vector(aim) - mathutils.Vector(loc)
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def setup_camera(dist, elev_deg, lens, target=(0.0, 0.0, 0.2), yaw_deg=0.0):
    cam_data = bpy.data.cameras.new("Cam")
    cam_data.sensor_width = 36.0
    cam_data.lens = lens
    cam = bpy.data.objects.new("Cam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    elev = math.radians(elev_deg)
    yaw = math.radians(yaw_deg)
    tv = mathutils.Vector(target)
    loc = tv + mathutils.Vector((
        dist * math.cos(elev) * math.sin(yaw),
        -dist * math.cos(elev) * math.cos(yaw),
        dist * math.sin(elev),
    ))
    cam.location = loc
    cam.rotation_euler = (tv - loc).to_track_quat("-Z", "Y").to_euler()


def configure_cycles(scene, args):
    scene.render.engine = "CYCLES"
    scene.render.resolution_x = args.width
    scene.render.resolution_y = args.height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    try:
        scene.view_settings.view_transform = "Khronos PBR Neutral"
    except TypeError:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Punchy"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type != "CPU"
        scene.cycles.device = "GPU"
        print("Cycles: OPTIX GPU enabled", flush=True)
    except Exception as e:
        print(f"Cycles: GPU setup failed ({e}), using CPU", flush=True)


def main():
    args = parse_args(sys.argv)
    bpy.ops.wm.read_factory_settings(use_empty=True)

    hex_tiles = hexagon_rings(args.half_w, args.half_h, args.seam)
    spec_tiles = spectre_rings(args.tile_json, args.half_w, args.half_h, args.seam)
    print(f"hexagons: {len(hex_tiles)}, spectres: {len(spec_tiles)}", flush=True)

    left = build_tiles(hex_tiles, color_slate, args, "PeriodicHexFloor")
    right = build_tiles(spec_tiles, color_ember, args, "AperiodicSpectreFloor")
    glaze = mat_glaze("Glaze")
    left.data.materials.append(glaze)
    right.data.materials.append(glaze)
    add_grout_plane(args.half_w, args.half_h)

    setup_sky_world(10.0, 235.0, 0.55)
    add_area((30.0, -30.0, 34.0), 42.0, 900.0, (1.0, 0.9, 0.8))

    setup_camera(dist=72.0, elev_deg=38.0, lens=42.0, target=(0.0, 6.0, 0.2), yaw_deg=0.0)

    scene = bpy.context.scene
    configure_cycles(scene, args)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out)
    bpy.ops.render.render(write_still=True)
    print(f"Done -> {out}", flush=True)


if __name__ == "__main__":
    main()
