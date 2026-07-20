import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import bpy


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bilingual_node_names as addon
from bilingual_node_names.constants import PROP_MANAGED, PROP_ORIGINAL_LABEL
from bilingual_node_names.services import labels, node_registry, search, translations


class BilingualNodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        addon.register()

    @classmethod
    def tearDownClass(cls):
        addon.unregister()

    def setUp(self):
        translations.reload(blender_version=bpy.app.version)
        node_registry.rebuild()
        search.rebuild_index()
        self.tree = bpy.data.node_groups.new("BN_Test_Tree", "ShaderNodeTree")

    def tearDown(self):
        bpy.data.node_groups.remove(self.tree)

    def test_translation_and_dynamic_title(self):
        node = self.tree.nodes.new("ShaderNodeMath")
        node.operation = "MULTIPLY"
        self.assertEqual(labels.build_label(node), "Multiply / 乗算")

    def test_apply_preserves_identity_and_restores(self):
        node = self.tree.nodes.new("ShaderNodeBsdfPrincipled")
        original_name = node.name
        original_id = node.bl_idname
        changed, _ = labels.apply(node)
        self.assertTrue(changed)
        self.assertEqual(node.label, "Principled BSDF / プリンシプルBSDF")
        self.assertEqual(node.name, original_name)
        self.assertEqual(node.bl_idname, original_id)
        self.assertTrue(node.get(PROP_MANAGED))
        self.assertEqual(node.get(PROP_ORIGINAL_LABEL), "")
        self.assertTrue(labels.restore(node))
        self.assertEqual(node.label, "")

    def test_user_label_is_not_overwritten(self):
        node = self.tree.nodes.new("ShaderNodeTexNoise")
        node.label = "My procedural texture"
        changed, reason = labels.apply(node)
        self.assertFalse(changed)
        self.assertEqual(reason, "USER_LABEL")
        self.assertEqual(node.label, "My procedural texture")

    def test_manual_edit_releases_management(self):
        node = self.tree.nodes.new("ShaderNodeTexNoise")
        labels.apply(node)
        node.label = "Custom"
        changed, reason = labels.apply(node)
        self.assertFalse(changed)
        self.assertEqual(reason, "USER_EDIT")
        self.assertNotIn(PROP_MANAGED, node)
        self.assertEqual(node.label, "Custom")

    def test_search_languages_alias_and_context(self):
        self.assertEqual(search.search("Principled BSDF", "ShaderNodeTree")[0].node_id, "ShaderNodeBsdfPrincipled")
        self.assertEqual(search.search("プリンシプル", "ShaderNodeTree")[0].node_id, "ShaderNodeBsdfPrincipled")
        self.assertEqual(search.search("標準マテリアル", "ShaderNodeTree")[0].node_id, "ShaderNodeBsdfPrincipled")
        self.assertFalse(any(result.node_id == "GeometryNodeSetPosition" for result in search.search("位置を設定", "ShaderNodeTree")))

    def test_invalid_dictionary_does_not_break_standard_data(self):
        entry = translations.get_node_entry("ShaderNodeBsdfPrincipled", bpy.app.version)
        self.assertIsNotNone(entry)
        self.assertGreater(len(translations.nodes), 20)

    def test_display_toggle_keeps_bilingual_search(self):
        preferences = SimpleNamespace(
            show_bilingual_labels=True,
            use_short_japanese=False,
            use_dynamic_titles=True,
            display_mode="EN_JA",
            separator=" / ",
            release_on_manual_edit=True,
            include_library_overrides=False,
            overwrite_user_labels=False,
            auto_adjust_width=False,
        )
        node = self.tree.nodes.new("ShaderNodeTexNoise")
        changed, _ = labels.apply(node, preferences)
        self.assertTrue(changed)
        self.assertEqual(node.label, "Noise Texture / ノイズテクスチャ")

        changed, _ = labels.set_display_enabled(node, False, preferences)
        self.assertTrue(changed)
        self.assertEqual(node.label, "")
        self.assertTrue(node.get(PROP_MANAGED))
        self.assertEqual(search.search("Noise Texture", "ShaderNodeTree")[0].node_id, "ShaderNodeTexNoise")
        self.assertEqual(search.search("ノイズテクスチャ", "ShaderNodeTree")[0].node_id, "ShaderNodeTexNoise")

        changed, _ = labels.set_display_enabled(node, True, preferences)
        self.assertTrue(changed)
        self.assertEqual(node.label, "Noise Texture / ノイズテクスチャ")


suite = unittest.defaultTestLoader.loadTestsFromTestCase(BilingualNodeTests)
result = unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)
