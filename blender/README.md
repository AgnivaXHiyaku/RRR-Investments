# RRR Investments: Blender assets

Every 3D asset on the site is generated procedurally by these scripts, so nothing is a binary-only source file. Tested with Blender 5.2 (headless).

| Script | Output (public/models) | Render (public/renders) |
| --- | --- | --- |
| `build_monolith.py` | `rrr_monolith.glb` (blade_1..3) | `monolith_hero.png`, `og.jpg` |
| `build_shankha.py` | `shankha.glb` | `shankha.png` |
| `build_urli.py` | `urli.glb` (urli, water, petal_1..5) | `urli.png` |
| `build_diya.py` | `diya.glb` (diya, oil, wick, empty `flame_anchor`) | `diya.png` |
| `build_banyan.py` | `banyan.glb` (trunk, roots, canopy, node_01..20) | `banyan.png` |

```bash
# rebuild one model + its final render
blender -b -P blender/build_banyan.py
# export only
blender -b -P blender/build_banyan.py -- --no-render
# fast low-sample preview render to $RRR_PREVIEW_DIR (default: system temp)
RRR_PREVIEW_DIR=/tmp/pv blender -b -P blender/build_banyan.py -- --preview
# rebuild everything
for m in monolith shankha urli diya banyan; do blender -b -P blender/build_$m.py; done
# sanity-check the exported GLBs (tris, bbox, node + material names)
blender -b -P blender/verify_glb.py
```

Conventions the web code relies on:
- binary GLB, +Y up, modifiers applied, no Draco, no cameras or lights
- centred on X/Z, base at Y = 0, largest dimension = 2.0
- Principled BSDF materials only (clearcoat and emission export as glTF extensions)
- every blade in `rrr_monolith.glb` has its origin at its own bottom-centre, so it can be animated on its own

`helpers.py` holds the shared scene, material, normalise, export and render utilities.
