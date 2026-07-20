import importlib
import sys

import bpy


addon_keys = [item.module for item in bpy.context.preferences.addons if "bilingual_node_names" in item.module]
if not addon_keys:
    print("Installed Bilingual Node Names extension was not enabled")
    raise SystemExit(1)

module_name = addon_keys[0]
services = importlib.import_module(f"{module_name}.services")
services.node_registry.rebuild()
services.search.rebuild_index()

node_id = "GeometryNodeSampleSoundFrequencies"
if not hasattr(bpy.types, node_id):
    print("Sample Sound Frequencies is unavailable in this Blender version")
    raise SystemExit(1)

bpy.context.preferences.view.language = "ja_JP"
bpy.context.preferences.view.use_translate_interface = True

mesh = bpy.data.meshes.new("BN_Installed_Sound_Mesh")
obj = bpy.data.objects.new("BN_Installed_Sound_Object", mesh)
bpy.context.scene.collection.objects.link(obj)
bpy.context.view_layer.objects.active = obj
obj.select_set(True)

tree = bpy.data.node_groups.new("BN_Installed_Sound_Tree", "GeometryNodeTree")
tree.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
tree.nodes.new("NodeGroupOutput")
modifier = obj.modifiers.new("BN Installed Sound", "NODES")
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

with bpy.context.temp_override(area=area, region=region, space_data=space, active_object=obj, object=obj):
    result = bpy.ops.node.bn_search_add_node("EXEC_DEFAULT", node_type=node_id)

node = tree.nodes.active
expected_label = "Sample Sound Frequencies / 音声周波数サンプル"
if result != {"FINISHED"}:
    raise SystemExit(1)
if node is None or node.bl_idname != node_id or node.label != expected_label:
    raise SystemExit(1)

print("INSTALLED_OPERATOR_ADD_OK", node.bl_idname, node.label)
