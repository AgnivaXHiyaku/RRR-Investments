"""RRR logo as a 3-blade sculpture -> public/models/rrr_monolith.glb

blade_1 = left / shortest / front, blade_3 = right / tallest / back.
Each blade keeps its own origin at its bottom-centre so the web can animate them.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import bpy  # noqa: E402
import helpers as H  # noqa: E402

# Blade layout measured from the 2D logo (px, y up from the tallest blade's foot).
BLADES = [
    # name,     x0,  y0,   w,   h
    ("blade_1",   8,  93, 127, 382),
    ("blade_2",  63,  50, 142, 478),
    ("blade_3", 113,   0, 167, 578),
]
THICK = 24.0   # px  (~0.083 final units)
GAP = 12.0     # px between blades in depth
BEVEL = 4.5    # px


def outline(w, h):
    """Sail/shield outline, CCW, starting at the bottom-left tip (0, 0)."""
    r_tl = 0.06 * w
    r_tr = 0.30 * w
    yb = 1.1 * w                      # height where the right edge starts to sweep
    cx = -0.25 * w                     # ellipse centre left of the blade => angled tip
    rx = w - cx
    t0 = -math.acos(-cx / rx)          # parameter where the sweep meets x = 0
    ry = -yb / math.sin(t0)
    pts = []
    n = 70
    for i in range(n + 1):             # bottom sweep: tip -> right edge
        t = t0 + (0 - t0) * i / n
        pts.append((cx + rx * math.cos(t), yb + ry * math.sin(t)))
    for i in range(1, 6):              # right edge
        pts.append((w, yb + (h - r_tr - yb) * i / 5))
    for i in range(1, 25):             # top-right round
        a = math.pi / 2 * i / 24
        pts.append((w - r_tr + r_tr * math.cos(a), h - r_tr + r_tr * math.sin(a)))
    for i in range(1, 6):              # top edge
        pts.append((w - r_tr - (w - r_tr - r_tl) * i / 5, h))
    for i in range(1, 9):              # top-left round
        a = math.pi / 2 + math.pi / 2 * i / 8
        pts.append((r_tl + r_tl * math.cos(a), h - r_tl + r_tl * math.sin(a)))
    for i in range(1, 12):             # left edge back down (tip excluded: cyclic)
        y = (h - r_tl) * (1 - i / 12)
        pts.append((0, y))
    return pts


def blade(name, x0, y0, w, h, depth_y, mat):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "2D"
    cu.fill_mode = "BOTH"
    cu.extrude = THICK / 2 - BEVEL
    cu.bevel_depth = BEVEL
    cu.bevel_resolution = 4
    cu.offset = 0.0
    sp = cu.splines.new("POLY")
    pts = outline(w, h)
    sp.points.add(len(pts) - 1)
    for p, (x, y) in zip(sp.points, pts):
        p.co = (x, y, 0, 1)
    sp.use_cyclic_u = True
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.rotation_euler = (math.radians(90), 0, 0)
    ob.location = (x0, depth_y, y0)
    ob = H.curve_to_mesh(ob)
    H.select_only([ob])
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    H.merge_doubles(ob, 1e-3)
    H.shade_smooth(ob, angle=40)
    H.set_origin_bottom_center(ob)
    return ob


def build():
    H.reset()
    navy = H.material("RRR_Navy", "#1a40b0", metallic=0.35, roughness=0.22, coat=0.7, coat_roughness=0.06)
    step = THICK + GAP
    objs = []
    for i, (name, x0, y0, w, h) in enumerate(BLADES):
        # blade_1 at the front (-Y in Blender == +Z toward the viewer in glTF)
        objs.append(blade(name, x0, y0, w, h, (i - 1) * step, navy))
    H.normalize(objs)
    H.export_glb(objs, "rrr_monolith.glb")
    return objs


def render_hero(objs, preview=False):
    pd = H.preview_dir()
    H.setup_cycles(samples=16 if preview else 96, res=(800, 500) if preview else (1600, 1000))
    H.world("#0b1530", 0.0, top="#c9d6ff", top_strength=0.35)
    t = (0, 0, 1.0)
    H.area_light("Key", (-3.4, -2.6, 3.8), t, 420, 2.0, "#fff1e0")
    H.area_light("Fill", (3.6, -2.6, 0.8), t, 60, 4.0, "#dfe8ff")
    H.area_light("RimWarm", (3.4, 1.6, 2.2), t, 1100, 1.2, "#ff8a1f")
    H.area_light("RimCool", (-2.8, 3.2, 1.2), t, 500, 1.6, "#8fb2ff")
    H.area_light("Top", (0, 0, 5.0), t, 150, 3.0, "#ffffff")
    H.camera((2.9, -4.6, 1.75), (0.05, 0, 1.0), lens=50)
    H.render(os.path.join(pd if preview else H.RENDERS_DIR, "monolith_hero.png"))


def render_og(objs, preview=False):
    pd = H.preview_dir()
    out_dir = pd if preview else H.RENDERS_DIR
    for o in list(bpy.data.objects):
        if o.type in ("LIGHT", "CAMERA"):
            bpy.data.objects.remove(o)
    H.setup_cycles(samples=16 if preview else 96, res=(1200, 630))
    H.world("#050b1f", 0.25)
    t = (0, 0, 1.0)
    H.area_light("Key", (-3.2, -3.0, 3.0), t, 300, 2.5, "#e6ecff")
    H.area_light("RimSaffron", (3.4, 1.2, 2.0), t, 1500, 1.2, "#ff7a0a")
    H.area_light("RimSaffron2", (2.2, -0.6, 3.6), t, 260, 1.0, "#ffb15c")
    H.area_light("Back", (-2.4, 3.4, 1.6), t, 380, 1.4, "#6f8fff")
    cam = H.camera((3.6, -5.6, 1.4), (-0.75, 0, 0.98), lens=50)
    tmp = os.path.join(pd, "og_alpha.png")
    H.render(tmp)
    H.composite_over(tmp, os.path.join(out_dir, "og.jpg"), "#050b1f", vignette=0.35,
                     glow=(0.66, 0.5, 0.55, "#1b2f66", 0.9))


if __name__ == "__main__":
    objs = build()
    if not H.flag("--no-render"):
        pv = H.flag("--preview")
        render_hero(objs, pv)
        render_og(objs, pv)
