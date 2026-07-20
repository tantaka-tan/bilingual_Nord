import importlib
import sys

import bpy


addon_keys = [item.module for item in bpy.context.preferences.addons if "bilingual_node_names" in item.module]
if not addon_keys:
    print("Installed Bilingual Node Names extension was not enabled")
    raise SystemExit(1)

module_name = addon_keys[0]
preferences_module = importlib.import_module(f"{module_name}.preferences")
services = importlib.import_module(f"{module_name}.services")
preferences = preferences_module.get_preferences()
preferences.show_bilingual_labels = True
services.node_registry.rebuild()
services.search.rebuild_index()

new_nodes = (
    ("GeometryNodeMergeLayers", "Merge Layers", "レイヤー統合"),
    ("GeometryNodeSampleSoundFrequencies", "Sample Sound Frequencies", "音声周波数サンプル"),
)
verified_new_nodes = []
for new_node_id, english_name, japanese_name in new_nodes:
    if not hasattr(bpy.types, new_node_id):
        continue
    english = services.search.search(english_name, "GeometryNodeTree")
    japanese = services.search.search(japanese_name, "GeometryNodeTree")
    if not english or not japanese or english[0].node_id != new_node_id or japanese[0].node_id != new_node_id:
        raise SystemExit(1)
    geometry_tree = bpy.data.node_groups.new(f"BN_{new_node_id}_Test", "GeometryNodeTree")
    discovered_node = geometry_tree.nodes.new(new_node_id)
    applied, _ = services.labels.apply(discovered_node, preferences)
    expected_label = f"{english_name} / {japanese_name}"
    if not applied or discovered_node.label != expected_label:
        raise SystemExit(1)
    verified_new_nodes.append(f"{new_node_id}={expected_label}")

tree = bpy.data.node_groups.new("BN_Installed_Toggle_Test", "ShaderNodeTree")
tree.use_fake_user = True
node = tree.nodes.new("ShaderNodeTexNoise")
applied, _ = services.labels.apply(node, preferences)
if not applied or node.label != "Noise Texture / ノイズテクスチャ":
    raise SystemExit(1)

if bpy.ops.node.bn_toggle_display() != {"FINISHED"}:
    raise SystemExit(1)
standard_label = node.label
english_result = services.search.search("Noise Texture", "ShaderNodeTree")
japanese_result = services.search.search("ノイズテクスチャ", "ShaderNodeTree")
if standard_label != "" or not english_result or not japanese_result:
    raise SystemExit(1)
if english_result[0].node_id != "ShaderNodeTexNoise" or japanese_result[0].node_id != "ShaderNodeTexNoise":
    raise SystemExit(1)

if bpy.ops.node.bn_toggle_display() != {"FINISHED"}:
    raise SystemExit(1)
if node.label != "Noise Texture / ノイズテクスチャ":
    raise SystemExit(1)

print("INSTALLED_TOGGLE_OK", bpy.app.version_string, repr(standard_label), node.label)
print("AUTO_DISCOVERY_OK", *verified_new_nodes)
