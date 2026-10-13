"""Procedural conch (shankha) -> public/models/shankha.glb

Built as a spindle (Turbinella pyrum silhouette: siphonal canal, broad body
whorl, knobbed shoulder, stepped spire). The spire whorls are carved by a
log-spaced helical suture so the spiral reads clearly. A long aperture is cut
into the body whorl, its outer lip flared, and a solidify shell exposes the
pink interior (Pearl_Inner) through the opening.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import bpy  # noqa: E402
import helpers as H  # noqa: E402

NZ = 112         # samples along the axis (canal tip -> spire apex)
NP = 84          # samples around
SHOULDER = 0.64  # axial position of the shoulder (top of the body whorl)
APEX = 1.0
GROWTH = 1.9     # whorl height ratio


def lerp_profile(z, pts):
    for (z0, r0), (z1, r1) in zip(pts, pts[1:]):
        if z0 <= z <= z1:
            t = (z - z0) / (z1 - z0)
            t = t * t * (3 - 2 * t)
            return r0 + (r1 - r0) * t
    return pts[-1][1]


# (z, radius) control profile of the spindle
PROFILE = [
    (0.00, 0.035), (0.10, 0.060), (0.22, 0.120), (0.36, 0.215),
    (0.50, 0.270), (0.60, 0.285), (SHOULDER, 0.270), (0.70, 0.185),
    (0.80, 0.115), (0.90, 0.055), (0.97, 0.018), (APEX, 0.004),
]


def whorl_coord(z):
    """Continuous whorl index above the shoulder (0 at shoulder, grows to apex)."""
    d0 = APEX - SHOULDER + 0.02
    d = APEX - z + 0.02
    return math.log(d0 / d) / math.log(GROWTH) * 1.6


def radius(z, phi):
    r = lerp_profile(z, PROFILE)
    turn = phi / (2 * math.pi)
    if z > SHOULDER - 0.03:
        q = whorl_coord(max(z, SHOULDER - 0.03)) + turn
        f = q - math.floor(q)
        # each whorl bulges; suture groove where f ~ 0
        bulge = 0.78 + 0.22 * math.sin(math.pi * f) ** 0.6
        blend = min(1.0, (z - (SHOULDER - 0.03)) / 0.06)
        r *= 1 - blend * (1 - bulge)
    # knobs around the shoulder and the next whorl up
    k = math.exp(-((z - SHOULDER) / 0.035) ** 2)
    r += 0.032 * k * max(0.0, math.cos(phi * 9)) ** 3
    # fine spiral cords over the body
    r *= 1 + 0.006 * math.sin(z * 120)
    return r


def aperture_halfwidth(z):
    """Angular half-width of the aperture opening at height z (0 = closed)."""
    z0, z1 = 0.0, SHOULDER - 0.01
    if z <= z0 or z >= z1:
        return 0.0
    t = (z - z0) / (z1 - z0)
    return 0.46 * math.sin(math.pi * t ** 0.8) ** 0.7


def build():
    H.reset()
    pearl = H.material("Pearl", "#f3ece0", roughness=0.3, coat=0.4, coat_roughness=0.15, sheen=0.15)
    inner = H.material("Pearl_Inner", "#e9b9a8", roughness=0.2, coat=0.6, coat_roughness=0.05)

    PHI0 = 0.0     # aperture centred on +X
    # Each ring spans the shell wall only: from the outer lip (PHI0 + hw) round to
    # the inner lip (PHI0 + 2pi - hw). Where hw == 0 the two ends coincide and are
    # merged, so the aperture edge follows the grid exactly (no stair-steps).
    verts, faces = [], []
    W = NP + 1
    for i in range(NZ + 1):
        z = APEX * i / NZ
        hw = aperture_halfwidth(z)
        for j in range(W):
            phi = PHI0 + hw + (2 * math.pi - 2 * hw) * j / NP
            r = radius(z, phi)
            edge = phi - PHI0 - hw                 # 0 at the outer lip
            r *= 1 + 0.30 * math.exp(-(edge / 0.28) ** 2) * min(1.0, hw / 0.3)
            verts.append((r * math.cos(phi), r * math.sin(phi), z))
    for i in range(NZ):
        for j in range(NP):
            a = i * W + j
            faces.append((a, a + 1, a + 1 + W, a + W))
    faces.append(tuple(reversed(range(NP))))       # cap the canal tip
    ob = H.mesh_object("shankha", verts, faces, None)
    ob.data.materials.append(pearl)
    ob.data.materials.append(inner)
    H.merge_doubles(ob, 1e-6)
    H.select_only([ob])
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.delete_loose()
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    sol = ob.modifiers.new("shell", "SOLIDIFY")
    sol.thickness = 0.012
    sol.offset = -1
    sol.material_offset = 1
    sol.material_offset_rim = 0
    sol.use_even_offset = True
    sol.use_rim = True
    H.apply_modifiers(ob)
    H.shade_smooth(ob)
    # lay it down: aperture toward the viewer (-Y) and tipped up, spire -> +X
    for rot in ((0, 0, math.radians(-90)), (0, math.radians(90), 0), (math.radians(-35), 0, 0)):
        ob.rotation_euler = rot
        H.select_only([ob])
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    H.normalize([ob])
    H.export_glb([ob], "shankha.glb")
    return [ob]


def render(preview=False):
    pd = H.preview_dir()
    H.setup_cycles(samples=16 if preview else 96, res=(500, 500) if preview else (1000, 1000))
    H.world("#141a2c", 0.0, top="#e9eeff", top_strength=0.3)
    c, _ = H.bounds_center()
    H.studio(target=tuple(c), scale=0.9, key_e=260, fill_e=70, rim_e=320)
    H.frame_camera((0.12, -1, 0.55), lens=60, margin=1.05)
    H.render(os.path.join(pd if preview else H.RENDERS_DIR, "shankha.png"))


if __name__ == "__main__":
    build()
    if not H.flag("--no-render"):
        render(H.flag("--preview"))
