"""Re-import each GLB and print tri count, bounds (glTF space), objects, materials.

    blender -b -P blender/verify_glb.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import bpy  # noqa: E402
import helpers as H  # noqa: E402

for fn in ["rrr_monolith.glb", "shankha.glb", "urli.glb", "diya.glb", "banyan.glb"]:
    H.reset()
    path = os.path.join(H.MODELS_DIR, fn)
    bpy.ops.import_scene.gltf(filepath=path)
    bpy.context.view_layer.update()
    objs = list(bpy.context.scene.objects)
    meshes = [o for o in objs if o.type == "MESH"]
    tris = 0
    for o in meshes:
        o.data.calc_loop_triangles()
        tris += len(o.data.loop_triangles)
    mn, mx = H.world_bounds(meshes)
    # Blender Z-up -> glTF Y-up: glTF (x, y, z) = (x, z, -y)
    print(f"\n== {fn}  {os.path.getsize(path) / 1024:.0f} KB  tris={tris}")
    print(f"   glTF bbox min=({mn.x:.3f}, {mn.z:.3f}, {-mx.y:.3f}) max=({mx.x:.3f}, {mx.z:.3f}, {-mn.y:.3f})"
          f"  dims=({mx.x - mn.x:.3f}, {mx.z - mn.z:.3f}, {mx.y - mn.y:.3f})")
    print("   objects:", ", ".join(f"{o.name}[{o.type[0]}]" for o in sorted(objs, key=lambda o: o.name)))
    print("   materials:", ", ".join(sorted({m.name for o in meshes for m in o.data.materials if m})))
    for o in objs:
        if o.name.startswith("blade") or o.type == "EMPTY":
            l = o.matrix_world.translation
            print(f"   {o.name} origin glTF=({l.x:.3f}, {l.z:.3f}, {-l.y:.3f})")
