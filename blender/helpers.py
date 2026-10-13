"""Shared helpers for the RRR Investments Blender asset scripts.

Run any build script headless, e.g.:
    blender -b -P blender/build_monolith.py -- [--preview] [--no-render]
"""
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODELS_DIR = os.path.join(ROOT, "public", "models")
RENDERS_DIR = os.path.join(ROOT, "public", "renders")


def argv():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def flag(name):
    return name in argv()


def opt(name, default=None):
    a = argv()
    if name in a and a.index(name) + 1 < len(a):
        return a[a.index(name) + 1]
    return default


# ---------------------------------------------------------------- scene

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def hex_rgb(h):
    h = h.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    return (*lin, 1.0)


def material(name, color, metallic=0.0, roughness=0.5, coat=0.0, coat_roughness=0.08,
             emission=None, emission_strength=0.0, specular=0.5, sheen=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = hex_rgb(color)
    p.inputs["Metallic"].default_value = metallic
    p.inputs["Roughness"].default_value = roughness
    if "Specular IOR Level" in p.inputs:
        p.inputs["Specular IOR Level"].default_value = specular
    if coat:
        p.inputs["Coat Weight"].default_value = coat
        p.inputs["Coat Roughness"].default_value = coat_roughness
    if sheen:
        p.inputs["Sheen Weight"].default_value = sheen
    if emission:
        p.inputs["Emission Color"].default_value = hex_rgb(emission)
        p.inputs["Emission Strength"].default_value = emission_strength
    return m


def mesh_object(name, verts, faces, mat=None, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.validate()
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if mat:
        me.materials.append(mat)
    if smooth:
        shade_smooth(ob)
    return ob


def shade_smooth(ob, angle=None):
    me = ob.data
    for p in me.polygons:
        p.use_smooth = True
    if angle is not None:
        me.set_sharp_from_angle(angle=math.radians(angle))


def select_only(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]


def apply_modifiers(ob):
    select_only([ob])
    for m in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def curve_to_mesh(ob):
    select_only([ob])
    bpy.ops.object.convert(target="MESH")
    return bpy.context.view_layer.objects.active


def join(objs, name):
    select_only(objs)
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    ob.data.name = name
    return ob


def set_origin_bottom_center(ob):
    """Move object origin to bottom-center of its mesh bounds (world Z min)."""
    me = ob.data
    mw = ob.matrix_world
    pts = [mw @ v.co for v in me.vertices]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    target = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
    inv = mw.inverted()
    local_t = inv @ target
    for v in me.vertices:
        v.co -= local_t
    ob.location = target


# ---------------------------------------------------------------- normalisation

def world_bounds(objs):
    pts = []
    for o in objs:
        if o.type == "MESH":
            pts += [o.matrix_world @ v.co for v in o.data.vertices]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def normalize(objs, size=2.0):
    """Centre X/Y, base on Z=0 (glTF Y=0), largest dimension = size. Bakes scale."""
    bpy.context.view_layer.update()
    mn, mx = world_bounds(objs)
    dims = mx - mn
    s = size / max(dims)
    off = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
    for o in objs:
        if o.parent is None:
            o.location = (o.location - off) * s
            o.scale = o.scale * s
    bpy.context.view_layer.update()
    meshes = [o for o in objs if o.type == "MESH"]
    select_only(meshes)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for o in objs:
        if o.type == "EMPTY":
            o.scale = (1, 1, 1)
    bpy.context.view_layer.update()


def export_glb(objs, filename):
    os.makedirs(MODELS_DIR, exist_ok=True)
    path = os.path.join(MODELS_DIR, filename)
    select_only(objs)
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_cameras=False,
        export_lights=False,
        export_draco_mesh_compression_enable=False,
        export_extras=False,
    )
    print(f"[export] {path} {os.path.getsize(path) / 1024:.0f} KB")
    return path


# ---------------------------------------------------------------- rendering

def setup_cycles(samples=64, res=(1000, 1000), transparent=True, look="AgX - Medium High Contrast"):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        sc.cycles.device = "GPU"
    except Exception as e:  # noqa
        print("GPU unavailable, using CPU", e)
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = look
    except TypeError:
        pass
    return sc


def world(color="#1a2238", strength=0.35, top="#dfe6ff", top_strength=0.0):
    sc = bpy.context.scene
    w = bpy.data.worlds.new("World")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    if top_strength:
        # simple vertical gradient: brighter sky above, dim floor below
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        nt.links.new(tc.outputs["Generated"], sep.inputs[0])
        nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
        ramp.color_ramp.elements[0].position = 0.45
        ramp.color_ramp.elements[0].color = hex_rgb(color)
        ramp.color_ramp.elements[1].position = 0.75
        ramp.color_ramp.elements[1].color = hex_rgb(top)
        nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
        bg.inputs["Strength"].default_value = top_strength
    else:
        bg.inputs["Color"].default_value = hex_rgb(color)
        bg.inputs["Strength"].default_value = strength
    return w


def area_light(name, loc, target, energy, size=2.0, color="#ffffff"):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy
    ld.size = size
    ld.color = hex_rgb(color)[:3]
    lo = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(lo)
    lo.location = loc
    look_at(lo, target)
    return lo


def look_at(ob, target):
    d = Vector(target) - Vector(ob.location)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def camera(loc, target, lens=50):
    cd = bpy.data.cameras.new("Camera")
    cd.lens = lens
    co = bpy.data.objects.new("Camera", cd)
    bpy.context.scene.collection.objects.link(co)
    co.location = loc
    look_at(co, target)
    bpy.context.scene.camera = co
    return co


def studio(target=(0, 0, 0.8), scale=1.0, key="#fff4e6", rim="#cfe0ff", key_e=400, fill_e=120, rim_e=500):
    t = Vector(target)
    s = scale
    area_light("Key", t + Vector((-3.2, -3.6, 3.4)) * s, t, key_e * s * s, 3.0 * s, key)
    area_light("Fill", t + Vector((4.0, -2.5, 1.2)) * s, t, fill_e * s * s, 4.0 * s, "#e8eeff")
    area_light("Rim", t + Vector((1.5, 4.2, 3.0)) * s, t, rim_e * s * s, 2.0 * s, rim)


def shadow_catcher(size=20):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, 0))
    p = bpy.context.active_object
    p.name = "ShadowCatcher"
    p.is_shadow_catcher = True
    return p


def render(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sc = bpy.context.scene
    if path.lower().endswith((".jpg", ".jpeg")):
        sc.render.image_settings.file_format = "JPEG"
        sc.render.image_settings.quality = 90
        sc.render.image_settings.color_mode = "RGB"
    else:
        sc.render.image_settings.file_format = "PNG"
        sc.render.image_settings.color_mode = "RGBA" if sc.render.film_transparent else "RGB"
        sc.render.image_settings.compression = 90
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"[render] {path}")


def preview_dir():
    d = opt("--preview-dir") or os.environ.get("RRR_PREVIEW_DIR") or os.path.join(__import__("tempfile").gettempdir(), "rrr_previews")
    os.makedirs(d, exist_ok=True)
    return d


# ---------------------------------------------------------------- geometry

def lathe(name, profile, segments=96, mat=None, close_bottom=False):
    """Revolve a (r, z) profile around Z. Profile is an open polyline."""
    verts, faces = [], []
    n = len(profile)
    for i in range(segments):
        a = 2 * math.pi * i / segments
        ca, sa = math.cos(a), math.sin(a)
        for r, z in profile:
            verts.append((r * ca, r * sa, z))
    for i in range(segments):
        j = (i + 1) % segments
        for k in range(n - 1):
            a, b = i * n + k, j * n + k
            faces.append((a, b, b + 1, a + 1))
    ob = mesh_object(name, verts, faces, mat)
    merge_doubles(ob)
    return ob


def merge_doubles(ob, dist=1e-5):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=dist)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def composite_over(png_path, out_path, bg_hex, vignette=0.0, glow=None):
    """Composite a transparent PNG (display-referred) over a flat colour, save JPEG/PNG."""
    import numpy as np
    img = bpy.data.images.load(png_path)
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)
    hx = bg_hex.lstrip("#")
    bg = np.array([int(hx[i:i + 2], 16) / 255 for i in (0, 2, 4)], dtype=np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    base = np.broadcast_to(bg, (h, w, 3)).copy()
    if glow:
        gx, gy, gr, ghex, gs = glow
        gh = ghex.lstrip("#")
        gc = np.array([int(gh[i:i + 2], 16) / 255 for i in (0, 2, 4)], dtype=np.float32)
        d = np.sqrt(((xx / w - gx) * w / h) ** 2 + (yy / h - gy) ** 2)
        f = np.clip(1 - d / gr, 0, 1) ** 2 * gs
        base = base + (gc - base) * f[..., None]
    if vignette:
        d = np.sqrt(((xx / w - 0.5) * 1.6) ** 2 + (yy / h - 0.5) ** 2)
        base = base * (1 - vignette * np.clip(d, 0, 1)[..., None])
    a = px[..., 3:4]
    rgb = px[..., :3] * a + base * (1 - a)
    out = np.concatenate([rgb, np.ones((h, w, 1), np.float32)], axis=2)
    oimg = bpy.data.images.new("comp", w, h, alpha=False)
    oimg.pixels.foreach_set(out.ravel())
    oimg.filepath_raw = out_path
    oimg.file_format = "JPEG" if out_path.lower().endswith((".jpg", ".jpeg")) else "PNG"
    oimg.save(quality=90) if oimg.file_format == "JPEG" else oimg.save()
    print(f"[composite] {out_path}")


def bounds_center(objs=None):
    objs = objs or [o for o in bpy.context.scene.objects if o.type == "MESH" and o.name != "ShadowCatcher"]
    mn, mx = world_bounds(objs)
    return (mn + mx) / 2, (mx - mn)


def frame_camera(direction, lens=55, margin=1.25, objs=None, target_offset=(0, 0, 0)):
    """Place a camera looking at the bounds centre from `direction`, far enough to fit."""
    c, dims = bounds_center(objs)
    c = c + Vector(target_offset)
    radius = dims.length / 2
    fov = 2 * math.atan(36 / 2 / lens)
    dist = radius * margin / math.sin(fov / 2)
    d = Vector(direction).normalized()
    return camera(c + d * dist, c, lens), c
