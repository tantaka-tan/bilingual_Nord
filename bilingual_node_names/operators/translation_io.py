import bpy

from ..preferences import get_preferences
from ..services import node_registry, search, translations


class BN_OT_reload_translations(bpy.types.Operator):
    bl_idname = "node.bn_reload_translations"
    bl_label = "Reload Translation Dictionaries"

    def execute(self, context):
        preferences = get_preferences(context)
        user_path = getattr(preferences, "user_translation_path", "")
        translations.reload(user_path or None, bpy.app.version)
        node_registry.rebuild()
        search.rebuild_index()
        level = {"WARNING"} if translations.errors else {"INFO"}
        self.report(level, f"Loaded {len(translations.nodes)} entries; {len(translations.errors)} errors")
        return {"FINISHED"}
