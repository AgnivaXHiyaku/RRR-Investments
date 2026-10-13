"""Sculptural banyan (vata vriksha) -> public/models/banyan.glb

Bronze twisted trunk + spreading branches, aerial prop roots that drop to the
ground (three thicken into secondary trunks: the compounding metaphor), a broad
umbrella canopy of clustered low-poly blobs, and 20 gold "node_XX" spheres on
the canopy surface (the 15-25 stock portfolio).

Objects: trunk, roots, canopy, node_01..node_20
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Vector, noise  # noqa: E402
import helpers as H  # noqa: E402

rng = random.Random(42)
CROWN_Z = 1.05


def tube(name, pts, radii, mat, res=2):
    """Poly-spline tube with per-point radius, converted to mesh."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 1.0
    cu.bevel_resolution = res
    cu.use_fill_caps = True
    cu.twist_mode = "MINIMUM"
    sp = cu.splines.new("NURBS")
    sp.points.add(len(pts) - 1)
    for p, co, r in zip(sp.points, pts, radii):
        p.co = (*co, 1.0)
        p.radius = r
    sp.order_u = 3
    sp.use_endpoint_u = True
    sp.resolution_u = 3
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    ob = H.curve_to_mesh(ob)
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    return ob


def lerp(a, b, t):
    return a + (b - a) * t


def trunk_strands(mat):
    objs = []
    n = 6
    for k in range(n):
        a0 = 2 * math.pi * k / n + rng.uniform(-0.2, 0.2)
        pts, radii = [], []
        steps = 14
        for i in range(steps + 1):
            t = i / steps
            z = t * CROWN_Z
            flare = 0.22 * (1 - t) ** 3 + 0.075        # buttress flare at the foot
            ang = a0 + t * 2.2                         # twist
            wob = 0.018 * noise.noise(Vector((k * 3.1, t * 4, 0)))
            pts.append(Vector((math.cos(ang) * (flare + wob), math.sin(ang) * (flare + wob), z - 0.02)))
            radii.append(lerp(0.075, 0.052, t) * (1 + 0.6 * (1 - t) ** 4))
        objs.append(tube(f"strand_{k}", pts, radii, mat))
    return objs


def branch(origin, direction, length, r0, mat, depth=0, out=None, hangs=None):
    """Recursive, gently arching branch. Collects hang points for prop roots."""
    pts, radii = [], []
    d = Vector(direction).normalized()
    p = Vector(origin)
    steps = 9
    for i in range(steps + 1):
        t = i / steps
        pts.append(p.copy())
        radii.append(lerp(r0, r0 * 0.35, t))
        bend = Vector((0, 0, 0.05 * (1 - t) - 0.05 * t))      # rise, then droop
        jitter = noise.noise_vector(p * 2.3 + Vector((depth, 0, 0))) * 0.25
        jitter.z *= 0.3
        d = (d + bend + jitter * 0.4).normalized()
        p = p + d * (length / steps)
        p.z = min(p.z, CROWN_Z + 0.24)              # stay under the canopy
        if hangs is not None and depth < 2 and 0.35 < t < 0.95 and i % 3 == 0:
            hangs.append((p.copy(), r0 * lerp(1, 0.35, t)))
    out.append(tube(f"branch_{len(out)}", pts, radii, mat))
    if depth < 2:
        for _ in range(2 if depth == 0 else 1):
            k = rng.randint(4, 7)
            side = Vector((-d.y, d.x, 0)) * rng.choice((-1, 1))
            nd = (d + side * rng.uniform(0.5, 0.9)).normalized()
            nd.z = min(nd.z, 0.1)
            branch(pts[k], nd, length * 0.55, radii[k] * 0.8, mat, depth + 1, out, hangs)


def prop_root(top, r_top, thick, idx, mat):
    pts, radii = [], []
    steps = 10
    base = Vector((top.x + rng.uniform(-0.05, 0.05), top.y + rng.uniform(-0.05, 0.05), -0.02))
    for i in range(steps + 1):
        t = i / steps
        p = top.lerp(base, t)
        sway = 0.015 * math.sin(t * math.pi * 2 + idx)
        p.x += sway
        p.y += sway * 0.6
        pts.append(p)
        if thick:
            r = lerp(min(r_top, 0.03), 0.042, t ** 0.7) * (1 + 0.9 * t ** 6)
        else:
            r = lerp(0.006, 0.011, t) * (1 + 1.2 * t ** 8)
        radii.append(r)
    return tube(f"root_{idx}", pts, radii, mat)


def blob(center, radius, mat, seed):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    for v in bm.verts:
        n = v.co.normalized()
        disp = 1 + 0.22 * noise.noise(n * 1.7 + Vector((seed, seed * 0.3, 0)))
        v.co = Vector((n.x * radius * disp, n.y * radius * disp, n.z * radius * 0.62 * disp))
        v.co += center
    me = bpy.data.meshes.new(f"blob_{seed}")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(f"blob_{seed}", me)
    bpy.context.scene.collection.objects.link(ob)
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = False                 # faceted low-poly look
    return ob


def build():
    H.reset()
    bronze = H.material("Bronze", "#8a5a2b", metallic=0.8, roughness=0.4)
    canopy_m = H.material("Canopy", "#0f3b3a", roughness=0.6)
    node_m = H.material("Node", "#f2c14e", metallic=0.3, roughness=0.25,
                        emission="#f2a93b", emission_strength=0.6)

    # trunk + branches
    trunk_parts = trunk_strands(bronze)
    branches, hangs = [], []
    nb = 7
    for k in range(nb):
        ang = 2 * math.pi * k / nb + rng.uniform(-0.25, 0.25)
        d = Vector((math.cos(ang), math.sin(ang), rng.uniform(0.08, 0.22)))
        o = Vector((0, 0, CROWN_Z - rng.uniform(0.0, 0.12)))
        branch(o, d, rng.uniform(0.8, 1.0), 0.055, bronze, 0, branches, hangs)
    trunk = H.join(trunk_parts + branches, "trunk")
    H.shade_smooth(trunk)

    # prop roots: pick well-spread hang points; three become secondary trunks
    rng.shuffle(hangs)
    chosen = []
    for p, r in sorted(hangs, key=lambda h: -Vector((h[0].x, h[0].y)).length):
        if Vector((p.x, p.y)).length < 0.35:
            continue
        if all((Vector((p.x, p.y)) - Vector((q.x, q.y))).length > 0.22 for q, _ in chosen):
            chosen.append((p, r))
        if len(chosen) >= 14:
            break
    thick_idx = set(rng.sample(range(len(chosen)), 3))
    roots = [prop_root(p, r, i in thick_idx, i, bronze) for i, (p, r) in enumerate(chosen)]
    roots = H.join(roots, "roots")
    H.shade_smooth(roots)

    # canopy: umbrella of blobs
    blobs, spheres = [], []
    R = 1.32
    attempts = 0
    while len(blobs) < 58 and attempts < 5000:
        attempts += 1
        r = R * math.sqrt(rng.random())
        a = rng.uniform(0, 2 * math.pi)
        x, y = r * math.cos(a), r * math.sin(a)
        z = CROWN_Z + 0.30 + 0.26 * (1 - (r / R) ** 2) + rng.uniform(-0.06, 0.06)
        rad = rng.uniform(0.2, 0.32) * (1 - 0.25 * (r / R))
        c = Vector((x, y, z))
        if any((c - s[0]).length < (rad + s[1]) * 0.55 for s in spheres):
            continue
        spheres.append((c, rad))
        blobs.append(blob(c, rad, canopy_m, len(blobs)))
    canopy = H.join(blobs, "canopy")

    # portfolio nodes on the exposed canopy surface
    def inside_other(p, skip):
        for k, (c, rad) in enumerate(spheres):
            if k == skip:
                continue
            q = p - c
            if (q.x / rad) ** 2 + (q.y / rad) ** 2 + (q.z / (rad * 0.62)) ** 2 < 1.0:
                return True
        return False

    cands = []
    for k, (c, rad) in enumerate(spheres):
        for _ in range(10):
            el = rng.uniform(0.15, 1.3)            # upper / outer hemisphere only
            az = rng.uniform(0, 2 * math.pi)
            n = Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)))
            p = c + Vector((n.x * rad, n.y * rad, n.z * rad * 0.62)) * 1.02
            if not inside_other(p, k):
                cands.append(p)
    picked = [max(cands, key=lambda p: p.z)]
    while len(picked) < 20:
        picked.append(max(cands, key=lambda p: min((p - q).length for q in picked)))
    nodes = []
    for i, p in enumerate(picked):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.042, location=p)
        o = bpy.context.active_object
        o.name = o.data.name = f"node_{i + 1:02d}"
        o.data.materials.append(node_m)
        H.shade_smooth(o)
        nodes.append(o)

    objs = [trunk, roots, canopy] + nodes
    H.normalize(objs)
    H.export_glb(objs, "banyan.glb")
    return objs


def render(preview=False):
    pd = H.preview_dir()
    H.setup_cycles(samples=16 if preview else 96, res=(500, 500) if preview else (1000, 1000))
    H.world("#141a2c", 0.0, top="#eef2ff", top_strength=0.45)
    c, _ = H.bounds_center()
    H.studio(target=tuple(c), scale=1.1, key_e=320, fill_e=100, rim_e=500, rim="#ffd08a")
    H.frame_camera((0.35, -1, 0.32), lens=50, margin=0.85)
    H.render(os.path.join(pd if preview else H.RENDERS_DIR, "banyan.png"))


if __name__ == "__main__":
    build()
    if not H.flag("--no-render"):
        render(H.flag("--preview"))
