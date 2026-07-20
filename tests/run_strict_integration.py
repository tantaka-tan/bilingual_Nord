import argparse
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bilingual_node_names as addon
from bilingual_node_names.constants import (
    MANAGEMENT_PROPERTIES,
    PROP_GENERATED_LABEL,
    PROP_MANAGED,
    PROP_ORIGINAL_LABEL,
)
from bilingual_node_names.services import labels, node_registry, scanner, search, translations
from bilingual_node_names.services.node_registry import suppress_native_output
from bilingual_node_names.handlers import runtime_handlers


class BNTestRuntimeNode(bpy.types.Node):
    bl_idname = "BNTestRuntimeNodeType"
    bl_label = "Runtime Discovered Node"

    @classmethod
    def poll(cls, node_tree):
        return node_tree.bl_idname == "GeometryNodeTree"


def parse_arguments():
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=("core", "create-library", "link-append", "create-save", "verify-save"), default="core")
    parser.add_argument("--path")
    return parser.parse_args(values)


def reset_file():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def register_addon():
    addon.register()
    translations.reload(blender_version=bpy.app.version)
    node_registry.rebuild()
    search.rebuild_index()


def unregister_addon():
    try:
        addon.unregister()
    except RuntimeError:
        pass


def create_shader_context():
    mesh = bpy.data.meshes.new("BN_Strict_Mesh")
    obj = bpy.data.objects.new("BN_Strict_Object", mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    material = bpy.data.materials.new("BN_Strict_Material")
    material.use_nodes = True
    obj.data.materials.append(material)
    tree = material.node_tree
    area = next(area for area in bpy.context.screen.areas if area.type == "VIEW_3D")
    area.type = "NODE_EDITOR"
    space = area.spaces.active
    space.tree_type = "ShaderNodeTree"
    space.shader_type = "OBJECT"
    space.pin = True
    space.node_tree = tree
    region = next(region for region in area.regions if region.type == "WINDOW")
    return obj, material, tree, area, region


def create_geometry_context(area):
    mesh = bpy.data.meshes.new("BN_Geometry_Mesh")
    obj = bpy.data.objects.new("BN_Geometry_Object", mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    for existing in bpy.context.selected_objects:
        existing.select_set(False)
    obj.select_set(True)
    tree = bpy.data.node_groups.new("BN_Geometry_Tree", "GeometryNodeTree")
    tree.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    tree.nodes.new("NodeGroupOutput")
    modifier = obj.modifiers.new("BN Geometry", "NODES")
    modifier.node_group = tree
    space = area.spaces.active
    space.tree_type = "GeometryNodeTree"
    if hasattr(space, "geometry_nodes_type"):
        space.geometry_nodes_type = "MODIFIER"
    space.pin = True
    space.node_tree = tree
    region = next(region for region in area.regions if region.type == "WINDOW")
    return obj, tree, region


class StrictCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reset_file()
        register_addon()

    @classmethod
    def tearDownClass(cls):
        unregister_addon()

    def setUp(self):
        reset_file()
        unregister_addon()
        register_addon()

    def test_repeated_register_unregister(self):
        for _ in range(3):
            unregister_addon()
            register_addon()
        self.assertTrue(hasattr(bpy.ops.node, "bn_search_add_node"))

    def test_real_shader_operator_and_data_integrity(self):
        obj, material, tree, area, region = create_shader_context()
        tree.nodes.clear()
        output = tree.nodes.new("ShaderNodeOutputMaterial")
        principled = tree.nodes.new("ShaderNodeBsdfPrincipled")
        noise = tree.nodes.new("ShaderNodeTexNoise")
        noise.label = "Artist Label"
        link = tree.links.new(principled.outputs[0], output.inputs[0])
        roughness = principled.inputs.get("Roughness")
        roughness_value = roughness.default_value
        identities = {node.as_pointer(): (node.name, node.bl_idname) for node in tree.nodes}

        with bpy.context.temp_override(area=area, region=region, space_data=area.spaces.active, active_object=obj, object=obj):
            self.assertIs(scanner.current_tree(bpy.context), tree)
            result = bpy.ops.node.bn_apply_labels(scope="TREE")
            self.assertEqual(result, {"FINISHED"})
            self.assertEqual(principled.label, "Principled BSDF / プリンシプルBSDF")
            self.assertEqual(noise.label, "Artist Label")
            self.assertEqual(len(tree.links), 1)
            self.assertEqual(link.from_node.as_pointer(), principled.as_pointer())
            self.assertEqual(roughness.default_value, roughness_value)
            for node in tree.nodes:
                self.assertEqual((node.name, node.bl_idname), identities[node.as_pointer()])

            before = len(tree.nodes)
            result = bpy.ops.node.bn_search_add_node("EXEC_DEFAULT", node_type="ShaderNodeTexImage")
            self.assertEqual(result, {"FINISHED"})
            self.assertEqual(len(tree.nodes), before + 1)
            added = tree.nodes.active
            self.assertEqual(added.bl_idname, "ShaderNodeTexImage")
            self.assertEqual(added.label, "Image Texture / 画像テクスチャ")
            self.assertTrue(added.select)

    def test_real_geometry_operator_and_auto_detection(self):
        _, _, _, area, _ = create_shader_context()
        obj, tree, region = create_geometry_context(area)
        with bpy.context.temp_override(area=area, region=region, space_data=area.spaces.active, active_object=obj, object=obj):
            self.assertIs(scanner.current_tree(bpy.context), tree)
            result = bpy.ops.node.bn_search_add_node("EXEC_DEFAULT", node_type="GeometryNodeSetPosition")
            self.assertEqual(result, {"FINISHED"})
            self.assertEqual(tree.nodes.active.label, "Set Position / 位置を設定")
            sound_node_id = "GeometryNodeSampleSoundFrequencies"
            if hasattr(bpy.types, sound_node_id):
                result = bpy.ops.node.bn_search_add_node("EXEC_DEFAULT", node_type=sound_node_id)
                self.assertEqual(result, {"FINISHED"})
                self.assertEqual(tree.nodes.active.bl_idname, sound_node_id)
                self.assertEqual(
                    tree.nodes.active.label,
                    "Sample Sound Frequencies / 音声周波数サンプル",
                )
            cross_tree_node_id = "ShaderNodeClamp"
            self.assertNotIn(cross_tree_node_id, translations.nodes)
            self.assertEqual(
                set(node_registry.entries[cross_tree_node_id]["tree_types"]),
                {"GeometryNodeTree", "ShaderNodeTree"},
            )
            self.assertEqual(
                search.search("Clamp", "GeometryNodeTree")[0].node_id,
                cross_tree_node_id,
            )
            result = bpy.ops.node.bn_search_add_node("EXEC_DEFAULT", node_type=cross_tree_node_id)
            self.assertEqual(result, {"FINISHED"})
            self.assertEqual(tree.nodes.active.bl_idname, cross_tree_node_id)
            scanner.rebuild_cache()
            new_node = tree.nodes.new("GeometryNodeJoinGeometry")
            self.assertEqual(new_node.label, "")
            self.assertEqual(scanner.scan_new_nodes(limit=100), 1)
            self.assertEqual(new_node.label, "Join Geometry / ジオメトリを統合")

    def test_every_indexed_node_can_be_created_in_declared_tree(self):
        failures = []
        for tree_type in ("GeometryNodeTree", "ShaderNodeTree"):
            tree = bpy.data.node_groups.new(f"BN_All_{tree_type}", tree_type)
            for node_id, entry in node_registry.entries.items():
                if tree_type not in entry.get("tree_types", []):
                    continue
                if not node_registry.exists(node_id):
                    continue
                try:
                    node = tree.nodes.new(node_id)
                    labels.apply(node, force=True)
                    self.assertTrue(node.label)
                    tree.nodes.remove(node)
                except Exception as exc:
                    failures.append(f"{tree_type}:{node_id}:{type(exc).__name__}:{exc}")
            bpy.data.node_groups.remove(tree)
        self.assertEqual(failures, [], "\n".join(failures))

    def test_registry_matches_every_constructible_node_subclass(self):
        candidates = node_registry.candidate_ids()

        expected = set()
        with suppress_native_output():
            for tree_type in ("GeometryNodeTree", "ShaderNodeTree"):
                tree = bpy.data.node_groups.new(f"BN_Audit_{tree_type}", tree_type)
                try:
                    for node_id in sorted(candidates):
                        try:
                            node = tree.nodes.new(node_id)
                        except (RuntimeError, TypeError):
                            continue
                        expected.add((node_id, tree_type))
                        tree.nodes.remove(node)
                finally:
                    bpy.data.node_groups.remove(tree)

        actual = {
            (node_id, tree_type)
            for node_id, entry in node_registry.entries.items()
            for tree_type in entry.get("tree_types", [])
        }
        print(json.dumps({
            "metric": "node_discovery_coverage",
            "subclasses": len(candidates),
            "constructible_pairs": len(expected),
            "registered_pairs": len(actual),
        }))
        self.assertEqual(actual, expected)

    def test_runtime_custom_node_registration_is_detected(self):
        node_id = BNTestRuntimeNode.bl_idname
        self.assertNotIn(node_id, node_registry.entries)
        bpy.utils.register_class(BNTestRuntimeNode)
        try:
            self.assertTrue(node_registry.is_stale())
            self.assertIsNotNone(runtime_handlers.monitor_timer())
            self.assertFalse(node_registry.is_stale())
            self.assertEqual(
                node_registry.entries[node_id]["tree_types"],
                ["GeometryNodeTree"],
            )
            self.assertEqual(
                search.search("Runtime Discovered Node", "GeometryNodeTree")[0].node_id,
                node_id,
            )
        finally:
            bpy.utils.unregister_class(BNTestRuntimeNode)
            node_registry.rebuild()
            search.rebuild_index()

    def test_malformed_user_dictionary_isolated(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as stream:
            stream.write("{not valid json")
            path = Path(stream.name)
        try:
            self.assertFalse(translations.reload(path, bpy.app.version))
            self.assertTrue(translations.errors)
            self.assertIsNotNone(translations.get_node_entry("ShaderNodeBsdfPrincipled", bpy.app.version))
        finally:
            path.unlink(missing_ok=True)
            translations.reload(blender_version=bpy.app.version)

    def test_manual_edit_and_exact_property_cleanup(self):
        tree = bpy.data.node_groups.new("BN_Manual_Edit", "ShaderNodeTree")
        node = tree.nodes.new("ShaderNodeTexNoise")
        labels.apply(node)
        original_generated = node.get(PROP_GENERATED_LABEL)
        node.label = "Artist Override"
        changed, reason = labels.apply(node)
        self.assertFalse(changed)
        self.assertEqual(reason, "USER_EDIT")
        self.assertEqual(node.label, "Artist Override")
        self.assertNotEqual(node.label, original_generated)
        for key in MANAGEMENT_PROPERTIES:
            self.assertNotIn(key, node)

    def test_one_thousand_node_apply_performance(self):
        tree = bpy.data.node_groups.new("BN_Performance", "ShaderNodeTree")
        for _ in range(1000):
            tree.nodes.new("ShaderNodeValue")
        started = time.perf_counter()
        changed = 0
        for node in tree.nodes:
            applied, _ = labels.apply(node)
            changed += int(applied)
        elapsed = time.perf_counter() - started
        print(json.dumps({"metric": "apply_1000_nodes_seconds", "value": elapsed}))
        self.assertEqual(changed, 1000)
        self.assertLess(elapsed, 2.0)


def run_core():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(StrictCoreTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)


def create_library(path):
    reset_file()
    tree = bpy.data.node_groups.new("BN_Linked_Geometry", "GeometryNodeTree")
    tree.use_fake_user = True
    node = tree.nodes.new("GeometryNodeSetPosition")
    node.label = "Library Original"
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    print(json.dumps({"scenario": "create-library", "path": str(path)}))


def link_append(path):
    reset_file()
    register_addon()
    with bpy.data.libraries.load(str(path), link=True) as (source, target):
        target.node_groups = ["BN_Linked_Geometry"]
    linked_tree = bpy.data.node_groups["BN_Linked_Geometry"]
    linked_node = linked_tree.nodes[0]
    changed, reason = labels.apply(linked_node, force=True)
    if changed or reason != "READONLY" or linked_node.label != "Library Original":
        raise AssertionError((changed, reason, linked_node.label))

    with bpy.data.libraries.load(str(path), link=False) as (source, target):
        target.node_groups = ["BN_Linked_Geometry"]
    appended = [tree for tree in bpy.data.node_groups if tree.library is None and tree.name.startswith("BN_Linked_Geometry")][0]
    appended_node = appended.nodes[0]
    changed, reason = labels.apply(appended_node, force=True)
    if not changed or reason != "APPLIED" or not appended_node.get(PROP_MANAGED):
        raise AssertionError((changed, reason, appended_node.label))
    unregister_addon()
    print(json.dumps({"scenario": "link-append", "linked": "skipped", "append": "applied"}))


def create_save(path):
    reset_file()
    register_addon()
    material = bpy.data.materials.new("BN_Persistence_Material")
    material.use_fake_user = True
    material.use_nodes = True
    node = material.node_tree.nodes.new("ShaderNodeTexNoise")
    labels.apply(node)
    if node.get(PROP_ORIGINAL_LABEL) != "":
        raise AssertionError("Original empty label was not saved")
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    unregister_addon()
    print(json.dumps({"scenario": "create-save", "label": node.label}))


def verify_save():
    register_addon()
    material = bpy.data.materials["BN_Persistence_Material"]
    node = next(node for node in material.node_tree.nodes if node.bl_idname == "ShaderNodeTexNoise")
    if node.label != "Noise Texture / ノイズテクスチャ" or not node.get(PROP_MANAGED):
        raise AssertionError((node.label, node.get(PROP_MANAGED)))
    addon.unregister()
    if node.label != "Noise Texture / ノイズテクスチャ":
        raise AssertionError("Disabling the add-on changed the persisted display label")
    print(json.dumps({"scenario": "verify-save", "persisted": True, "disabled_label_retained": True}))


def main():
    arguments = parse_arguments()
    if arguments.scenario == "core":
        run_core()
    elif arguments.scenario == "create-library":
        create_library(Path(arguments.path).resolve())
    elif arguments.scenario == "link-append":
        link_append(Path(arguments.path).resolve())
    elif arguments.scenario == "create-save":
        create_save(Path(arguments.path).resolve())
    elif arguments.scenario == "verify-save":
        verify_save()


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    raise SystemExit(1)
