import argparse
import importlib
import json
import sys
import traceback
from pathlib import Path

import bpy


values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
parser = argparse.ArgumentParser()
parser.add_argument("--result", required=True)
parser.add_argument("--screenshot", required=True)
parser.add_argument("--query", default="set position")
parser.add_argument("--expected", default="Set Position / 位置を設定")
parser.add_argument("--expected-node")
parser.add_argument("--installed", action="store_true")
parser.add_argument("--direct", action="store_true")
arguments = parser.parse_args(values)
result_path = Path(arguments.result).resolve()
screenshot_path = Path(arguments.screenshot).resolve()

if arguments.installed:
    addon_keys = [item.module for item in bpy.context.preferences.addons if "bilingual_node_names" in item.module]
    if not addon_keys:
        raise RuntimeError("Installed Bilingual Node Names extension was not enabled")
    addon = importlib.import_module(addon_keys[0])
else:
    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    addon = importlib.import_module("bilingual_node_names")

state = {}


def write_result(status, **details):
    result_path.write_text(json.dumps({"status": status, **details}, ensure_ascii=False), encoding="utf-8")


def fail(exc):
    traceback.print_exc()
    write_result("failed", error=f"{type(exc).__name__}: {exc}")
    bpy.ops.wm.quit_blender()


def open_add_menu():
    try:
        if not arguments.installed:
            addon.register()
        bpy.context.preferences.view.language = "ja_JP"
        bpy.context.preferences.view.use_translate_interface = True
        mesh = bpy.data.meshes.new("BN_Search_UI_Mesh")
        obj = bpy.data.objects.new("BN_Search_UI_Object", mesh)
        bpy.context.scene.collection.objects.link(obj)
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        tree = bpy.data.node_groups.new("BN_Search_UI_Tree", "GeometryNodeTree")
        tree.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
        tree.nodes.new("NodeGroupOutput")
        modifier = obj.modifiers.new("BN Search UI", "NODES")
        modifier.node_group = tree

        area = next(area for area in bpy.context.screen.areas if area.type == "VIEW_3D")
        area.type = "NODE_EDITOR"
        space = area.spaces.active
        space.tree_type = "GeometryNodeTree"
        if hasattr(space, "geometry_nodes_type"):
            space.geometry_nodes_type = "MODIFIER"
        space.pin = True
        space.node_tree = tree
        region = next(region for region in area.regions if region.type == "WINDOW")
        state.update(tree=tree, area=area, region=region, space=space, obj=obj)
        with bpy.context.temp_override(area=area, region=region, space_data=space, active_object=obj, object=obj):
            if arguments.direct:
                result = bpy.ops.node.bn_search_add_node("INVOKE_DEFAULT")
            else:
                result = bpy.ops.wm.call_menu("INVOKE_DEFAULT", name="NODE_MT_add")
        if result not in ({"RUNNING_MODAL"}, {"INTERFACE"}):
            raise AssertionError(result)
        bpy.app.timers.register(type_query, first_interval=0.3)
    except Exception as exc:
        fail(exc)
    return None


def type_query():
    try:
        window = bpy.context.window
        for character in arguments.query:
            event_type = "SPACE" if character == " " else character.upper()
            window.event_simulate(type=event_type, value="PRESS", unicode=character)
            window.event_simulate(type=event_type, value="RELEASE")
        bpy.app.timers.register(capture_and_accept, first_interval=0.5)
    except Exception as exc:
        fail(exc)
    return None


def capture_and_accept():
    try:
        bpy.ops.screen.screenshot(filepath=str(screenshot_path))
        if arguments.expected_node:
            window = bpy.context.window
            window.event_simulate(type="RET", value="PRESS")
            window.event_simulate(type="RET", value="RELEASE")
            bpy.app.timers.register(verify_added_node, first_interval=0.5)
            return None
        finish()
    except Exception as exc:
        fail(exc)
    return None


def verify_added_node():
    try:
        node = state["tree"].nodes.active
        if node is None or node.bl_idname != arguments.expected_node:
            raise AssertionError({
                "expected": arguments.expected_node,
                "actual": node.bl_idname if node else None,
                "label": node.label if node else None,
            })
        finish(added_node=node.bl_idname, added_label=node.label)
    except Exception as exc:
        fail(exc)
    return None


def finish(**details):
    try:
        if not arguments.installed:
            addon.unregister()
        write_result(
            "ok",
            query=arguments.query,
            expected_result=arguments.expected,
            screenshot=str(screenshot_path),
            **details,
        )
        bpy.ops.wm.quit_blender()
    except Exception as exc:
        fail(exc)


bpy.app.timers.register(open_add_menu, first_interval=0.2)
