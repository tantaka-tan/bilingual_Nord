import bpy
from bpy.props import BoolProperty, EnumProperty

from ..constants import PROP_MANAGED
from ..preferences import get_preferences
from ..services import labels, scanner


SCOPE_ITEMS = (
    ("SELECTED", "Selected nodes", "Process selected nodes"),
    ("TREE", "Current tree", "Process the current node tree"),
    ("MATERIAL", "Current material", "Process the active material"),
    ("FILE", "Entire file", "Process all supported node trees"),
)


class BN_OT_apply_labels(bpy.types.Operator):
    bl_idname = "node.bn_apply_labels"
    bl_label = "Apply Bilingual Labels"
    bl_options = {"REGISTER", "UNDO"}

    scope: EnumProperty(items=SCOPE_ITEMS, default="SELECTED")
    force: BoolProperty(name="Overwrite user labels", default=False)

    @classmethod
    def poll(cls, context):
        return scanner.current_tree(context) is not None

    def invoke(self, context, event):
        if self.scope == "FILE":
            return context.window_manager.invoke_confirm(self, event)
        return self.execute(context)

    def execute(self, context):
        result = scanner.apply_scope(context, self.scope, get_preferences(context), self.force)
        self.report({"INFO"}, f"Applied {result['changed']}; skipped {result['skipped']}; missing {result['missing']}")
        return {"FINISHED"}


class BN_OT_refresh_labels(bpy.types.Operator):
    bl_idname = "node.bn_refresh_labels"
    bl_label = "Refresh Managed Labels"
    bl_options = {"REGISTER", "UNDO"}

    scope: EnumProperty(items=SCOPE_ITEMS, default="TREE")

    @classmethod
    def poll(cls, context):
        return scanner.current_tree(context) is not None

    def execute(self, context):
        result = scanner.apply_scope(context, self.scope, get_preferences(context), managed_only=True)
        self.report({"INFO"}, f"Updated {result['changed']} managed labels")
        return {"FINISHED"}


class BN_OT_toggle_display(bpy.types.Operator):
    bl_idname = "node.bn_toggle_display"
    bl_label = "Toggle Bilingual Node Display"
    bl_description = "Switch node headers between standard and bilingual display without changing bilingual search"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        preferences = get_preferences(context)
        enabled = not getattr(preferences, "show_bilingual_labels", True)
        preferences.show_bilingual_labels = enabled
        changed = 0
        skipped = 0
        for tree in scanner.iter_all_trees():
            for node in tree.nodes:
                if node.get(PROP_MANAGED):
                    updated, _ = labels.set_display_enabled(node, enabled, preferences)
                elif enabled:
                    updated, _ = labels.apply(node, preferences)
                else:
                    updated = False
                changed += int(updated)
                skipped += int(not updated)
        scanner.rebuild_cache()
        mode = "bilingual" if enabled else "standard"
        self.report({"INFO"}, f"Switched to {mode} display: {changed} nodes; skipped {skipped}")
        return {"FINISHED"}
