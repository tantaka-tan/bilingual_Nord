import argparse
import json
import sys
import traceback
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bilingual_node_names as addon


values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
parser = argparse.ArgumentParser()
parser.add_argument("--result", required=True)
result_path = Path(parser.parse_args(values).result).resolve()


def write_result(status, **details):
    result_path.write_text(json.dumps({"status": status, **details}, ensure_ascii=False), encoding="utf-8")


def run_test():
    try:
        addon.register()
        mesh = bpy.data.meshes.new("BN_GUI_Undo_Mesh")
        obj = bpy.data.objects.new("BN_GUI_Undo_Object", mesh)
        bpy.context.scene.collection.objects.link(obj)
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        material = bpy.data.materials.new("BN_GUI_Undo_Material")
        material_name = material.name
        material.use_nodes = True
        obj.data.materials.append(material)
        tree = material.node_tree
        tree.nodes.clear()
        tree.nodes.new("ShaderNodeBsdfPrincipled")

        area = next(area for area in bpy.context.screen.areas if area.type == "VIEW_3D")
        area.type = "NODE_EDITOR"
        space = area.spaces.active
        space.tree_type = "ShaderNodeTree"
        space.shader_type = "OBJECT"
        space.pin = True
        space.node_tree = tree
        region = next(region for region in area.regions if region.type == "WINDOW")

        before = len(tree.nodes)
        with bpy.context.temp_override(area=area, region=region, space_data=space, active_object=obj, object=obj):
            initialized = bpy.ops.ed.undo_push(message="Initialize bilingual node undo test")
            pushed = bpy.ops.ed.undo_push(message="Before bilingual node addition")
            added = bpy.ops.node.bn_search_add_node("EXEC_DEFAULT", node_type="ShaderNodeTexImage")
            after_add = len(tree.nodes)
            undone = bpy.ops.ed.undo()
        restored_tree = bpy.data.materials[material_name].node_tree
        after_undo = len(restored_tree.nodes)
        if initialized != {"FINISHED"} or pushed != {"FINISHED"} or added != {"FINISHED"} or undone != {"FINISHED"}:
            raise AssertionError((initialized, pushed, added, undone))
        if after_add != before + 1 or after_undo != before:
            raise AssertionError((before, after_add, after_undo))
        addon.unregister()
        write_result("ok", before=before, after_add=after_add, after_undo=after_undo)
    except Exception as exc:
        traceback.print_exc()
        write_result("failed", error=f"{type(exc).__name__}: {exc}")
    finally:
        bpy.ops.wm.quit_blender()
    return None


bpy.app.timers.register(run_test, first_interval=0.2)
