"""Brass urli bowl with water and floating marigolds -> public/models/urli.glb"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
import bpy  # noqa: E402
import helpers as H  # noqa: E402

# Closed lathe profile (r, z): outer wall from the foot up, rolled rim, inner wall back down.
PROFILE = [
    (0.0, 0.0), (0.16, 0.0), (0.195, 0.008), (0.205, 0.025), (0.19, 0.05), (0.17, 0.065),
    (0.24, 0.075), (0.40, 0.105), (0.58, 0.155), (0.72, 0.205), (0.84, 0.262), (0.915, 0.305),
    (0.955, 0.33),
    # rolled rim (roughly a torus section)
    (0.985, 0.340), (1.000, 0.356), (0.998, 0.374), (0.983, 0.388), (0.962, 0.392),
    (0.940, 0.386), (0.925, 0.372),
    # inner wall
    (0.895, 0.345), (0.80, 0.293), (0.66, 0.232), (0.50, 0.180), (0.32, 0.140),
    (0.15, 0.122), (0.0, 0.118),
]
Z_SCALE = 1.45
PROFILE = [(r, z * Z_SCALE) for r, z in PROFILE]
WATER_Z = 0.30 * Z_SCALE
N_FLOWERS = 5


def marigold(name, mat, radius, rng):
    """Marigold head: three rings of cupped, ruffled petals around a domed centre."""
    verts, faces = [], []

    def petal(ph, elev, length, width, base_r, z0):
        nu, nv = 5, 4
        start = len(verts)
        ce, se = math.cos(elev), math.sin(elev)
        for i in range(nu + 1):
            u = i / nu
            w = width * math.sin(math.pi * (0.12 + 0.88 * u) ** 0.8) * (1 if u < 1 else 0.35)
            for j in range(nv + 1):
                v = -1 + 2 * j / nv
                cup = 0.25 * width * (v * v)                     # cupped across
                ruffle = 0.08 * width * math.sin(9 * v + u * 5) * u
                rr = base_r + length * u * ce                    # radial distance
                zz = z0 + length * u * se + cup + ruffle - 0.15 * length * u * u
                lx, ly = rr, w * v
                x = lx * math.cos(ph) - ly * math.sin(ph)
                y = lx * math.sin(ph) + ly * math.cos(ph)
                verts.append((x, y, zz))
        W = nv + 1
        for i in range(nu):
            for j in range(nv):
                a = start + i * W + j
                faces.append((a, a + W, a + W + 1, a + 1))

    rings = [  # (count, elevation deg, length, width, base radius, z0)
        (16, 12, 0.95, 0.30, 0.10, 0.00),
        (13, 38, 0.72, 0.30, 0.08, 0.12),
        (10, 68, 0.48, 0.28, 0.04, 0.24),
    ]
    for k, (n, el, ln, wd, br, z0) in enumerate(rings):
        off = rng.uniform(0, 6.28)
        for m in range(n):
            ph = off + 2 * math.pi * m / n + rng.uniform(-0.08, 0.08)
            petal(ph, math.radians(el + rng.uniform(-6, 6)), ln * radius, wd * radius,
                  br * radius, z0 * radius)
    ob = H.mesh_object(name, verts, faces, mat)
    sol = ob.modifiers.new("t", "SOLIDIFY")
    sol.thickness = 0.03 * radius
    H.apply_modifiers(ob)
    H.shade_smooth(ob)
    ob.rotation_euler = (rng.uniform(-0.12, 0.12), rng.uniform(-0.12, 0.12), rng.uniform(0, 6.28))
    return ob


def build():
    H.reset()
    rng = random.Random(7)
    brass = H.material("Brass", "#c9973a", metallic=1.0, roughness=0.28)
    water_m = H.material("Water", "#0b1a3a", metallic=0.0, roughness=0.05, specular=0.8)
    mari = H.material("Marigold", "#f39c12", roughness=0.6)

    bowl = H.lathe("urli", PROFILE, segments=128, mat=brass)
    H.shade_smooth(bowl, angle=55)

    water = H.lathe("water", [(0.0, WATER_Z), (0.83, WATER_Z)], segments=128, mat=water_m)
    H.shade_smooth(water)

    flowers = []
    spots = [(0.04, 0.02), (0.44, 0.22), (-0.36, 0.34), (0.14, -0.45), (-0.38, -0.22)]
    for k, (x, y) in enumerate(spots[:N_FLOWERS]):
        rad = 0.15 + rng.uniform(-0.015, 0.02)
        f = marigold(f"petal_{k + 1}", mari, rad, rng)
        f.location = (x, y, WATER_Z - 0.004)               # floating on the surface
        flowers.append(f)
    for f in flowers:
        H.select_only([f])
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

    objs = [bowl, water] + flowers
    H.normalize(objs)
    H.export_glb(objs, "urli.glb")
    return objs


def render(preview=False):
    pd = H.preview_dir()
    H.setup_cycles(samples=16 if preview else 96, res=(500, 500) if preview else (1000, 1000))
    H.world("#1b2033", 0.0, top="#f4f6ff", top_strength=0.5)
    c, _ = H.bounds_center()
    H.studio(target=tuple(c), scale=1.0, key_e=320, fill_e=90, rim_e=420, rim="#ffd9a0")
    H.frame_camera((0.25, -1, 0.45), lens=55, margin=0.95)
    H.render(os.path.join(pd if preview else H.RENDERS_DIR, "urli.png"))


if __name__ == "__main__":
    build()
    if not H.flag("--no-render"):
        render(H.flag("--preview"))
