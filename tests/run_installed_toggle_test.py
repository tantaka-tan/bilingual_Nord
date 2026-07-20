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
