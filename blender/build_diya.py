"""Clay diya (oil lamp) with oil, wick and a flame anchor -> public/models/diya.glb

The bowl is lofted from a teardrop outline (the point becomes the spout), with
the spout lip lifted. Empty "flame_anchor" marks the wick tip for the web flame.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import bpy  # noqa: E402
import helpers as H  # noqa: E402

NT = 120                       # samples around the outline
WIDTH = 1.0                   # roundness of the bowl (y stretch)
LIFT = 0.10                    # spout lift at the rim
WALL = 0.045
# (outline scale, z) from the foot to the rim
PROFILE = [
    (0.00, 0.000), (0.26, 0.000), (0.300, 0.012), (0.305, 0.035), (0.27, 0.060),
    (0.42, 0.085), (0.62, 0.120), (0.80, 0.175), (0.92, 0.240), (0.985, 0.300), (1.00, 0.335),
]
Z_SCALE = 1.45
PROFILE = [(sc, z * Z_SCALE) for sc, z in PROFILE]
OIL_Z = 0.20 * Z_SCALE


def teardrop(t):
    """Round bowl with a short pinched spout, point at +X (t = 0). Max x = 1."""
    d = math.atan2(math.sin(t), math.cos(t))
    w = math.exp(-(d / 0.62) ** 2)
    r = 0.60 + 0.40 * w ** 1.4
    pinch = 1 - 0.55 * math.exp(-(d / 0.5) ** 2)
    return r * math.cos(t), WIDTH * r * math.sin(t) * pinch


def tip_weight(t):
    d = math.atan2(math.sin(t), math.cos(t))
    return math.exp(-(d / 0.55) ** 2)


def build():
    H.reset()
    clay = H.material("Terracotta", "#a4502a", roughness=0.85)
    oil_m = H.material("Oil", "#d8a13a", roughness=0.1, specular=0.35)
    wick_m = H.material("Wick", "#efe6d2", roughness=0.95, sheen=0.5)

    verts, faces = [], []
    nprof = len(PROFILE)
    for k, (sc, z) in enumerate(PROFILE):
        s = k / (nprof - 1)
        for i in range(NT):
            t = 2 * math.pi * i / NT
            x, y = teardrop(t)
            up = LIFT * max(0.0, (s - 0.55) / 0.45) ** 2 * tip_weight(t)
            # pull the spout slightly outward so the lip has a channel
            stretch = 1 + 0.06 * tip_weight(t) * s
            verts.append((x * sc * stretch, y * sc, z + up))
    for k in range(nprof - 1):
        for i in range(NT):
            a = k * NT + i
            b = k * NT + (i + 1) % NT
            faces.append((a, b, b + NT, a + NT))
    bowl = H.mesh_object("diya", verts, faces, clay)
    H.merge_doubles(bowl, 1e-6)
    sub = bowl.modifiers.new("s", "SUBSURF")
    sub.levels = 1
    sol = bowl.modifiers.new("wall", "SOLIDIFY")
    sol.thickness = WALL
    sol.offset = -1
    sol.use_even_offset = True
    H.apply_modifiers(bowl)
    H.shade_smooth(bowl)

    # oil surface: inner outline at OIL_Z, tucked slightly into the wall
    sc = 0.80
    ov = [(0, 0, OIL_Z)]
    for i in range(NT):
        t = 2 * math.pi * i / NT
        x, y = teardrop(t)
        shrink = 1 - 0.18 * tip_weight(t)
        ov.append((x * sc * shrink, y * sc, OIL_Z))
    of = [(0, 1 + i, 1 + (i + 1) % NT) for i in range(NT)]
    oil = H.mesh_object("oil", ov, of, oil_m)

    # cotton wick lying in the spout, tip curling up
    cu = bpy.data.curves.new("wick", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.032
    cu.bevel_resolution = 3
    cu.use_fill_caps = True
    sp = cu.splines.new("BEZIER")
    pts = [(0.60, 0.0, OIL_Z + 0.004), (0.78, 0.0, 0.47), (0.95, 0.0, 0.62)]
    sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    sp.bezier_points[-1].radius = 0.6
    wick = bpy.data.objects.new("wick", cu)
    bpy.context.scene.collection.objects.link(wick)
    wick = H.curve_to_mesh(wick)
    wick.name = "wick"
    wick.data.materials.clear()
    wick.data.materials.append(wick_m)
    H.shade_smooth(wick)

    anchor = bpy.data.objects.new("flame_anchor", None)
    anchor.empty_display_type = "SPHERE"
    anchor.empty_display_size = 0.05
    bpy.context.scene.collection.objects.link(anchor)
    anchor.location = (0.955, 0.0, 0.635)

    objs = [bowl, oil, wick, anchor]
    H.normalize(objs)
    H.export_glb(objs, "diya.glb")
    return objs


def render(preview=False):
    pd = H.preview_dir()
    H.setup_cycles(samples=16 if preview else 96, res=(500, 500) if preview else (1000, 1000))
    H.world("#1b1a24", 0.0, top="#d9dcef", top_strength=0.3)
    c, _ = H.bounds_center()
    H.studio(target=tuple(c), scale=1.0, key_e=300, fill_e=80, rim_e=380, rim="#ffcf8a")
    # small warm point light where the flame will be
    a = bpy.data.objects["flame_anchor"]
    ld = bpy.data.lights.new("Flame", "POINT")
    ld.energy = 12
    ld.color = (1.0, 0.62, 0.25)
    ld.shadow_soft_size = 0.03
    lo = bpy.data.objects.new("Flame", ld)
    bpy.context.scene.collection.objects.link(lo)
    lo.location = a.matrix_world.translation + H.Vector((0, 0, 0.08))
    H.frame_camera((-0.55, -1, 0.6), lens=55, margin=0.95)
    H.render(os.path.join(pd if preview else H.RENDERS_DIR, "diya.png"))


if __name__ == "__main__":
    build()
    if not H.flag("--no-render"):
        render(H.flag("--preview"))
