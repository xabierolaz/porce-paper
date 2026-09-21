"""Ryan scan -> FBX listo para UE: escala a 1.78 m, pie en Z=0, textura junto al FBX.
Uso: blender -b -P ryan_to_fbx.py -- <obj> <out_dir>
"""
import bpy, sys, os, mathutils

argv = sys.argv
args = argv[argv.index("--") + 1:] if "--" in argv else []
obj, out_dir = args[0], args[1]
os.makedirs(out_dir, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.obj_import(filepath=obj)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]


def bbox(objs):
    pts = []
    for o in objs:
        for c in o.bound_box:
            pts.append(o.matrix_world @ mathutils.Vector(c))
    xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)


x0, x1, y0, y1, z0, z1 = bbox(meshes)
height = z1 - z0
s = 1.78 / height
for o in meshes:
    o.scale = (o.scale.x * s, o.scale.y * s, o.scale.z * s)
bpy.context.view_layer.update()

x0, x1, y0, y1, z0, z1 = bbox(meshes)
for o in meshes:
    o.location.z -= z0
bpy.context.view_layer.update()

x0, x1, y0, y1, z0, z1 = bbox(meshes)
print("FINAL height=%.3f m  bbox x %.2f..%.2f y %.2f..%.2f z %.2f..%.2f" % (z1 - z0, x0, x1, y0, y1, z0, z1))

bpy.ops.object.select_all(action="DESELECT")
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.export_scene.fbx(filepath=os.path.join(out_dir, "Ryan.fbx"),
                         path_mode="COPY", embed_textures=False,
                         use_selection=True, add_leaf_bones=False)
print("DONE")
