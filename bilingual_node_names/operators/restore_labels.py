import bpy
from bpy.props import EnumProperty

from ..services import labels, scanner
from .apply_labels import SCOPE_ITEMS


class BN_OT_restore_labels(bpy.types.Operator):
    bl_idname = "node.bn_restore_labels"
    bl_label = "Restore Original Labels"
    bl_options = {"REGISTER", "UNDO"}

    scope: EnumProperty(items=SCOPE_ITEMS, default="SELECTED")

    @classmethod
    def poll(cls, context):
        return scanner.current_tree(context) is not None

    def invoke(self, context, event):
        if self.scope == "FILE":
            return context.window_manager.invoke_confirm(self, event)
        return self.execute(context)

    def execute(self, context):
        changed = scanner.restore_scope(context, self.scope)
        self.report({"INFO"}, f"Restored {changed} labels")
        return {"FINISHED"}


class BN_OT_release_selected(bpy.types.Operator):
    bl_idname = "node.bn_release_selected"
    bl_label = "Release Label Management"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return bool(scanner.selected_nodes(context))

    def execute(self, context):
        nodes = scanner.selected_nodes(context)
        for node in nodes:
            labels.release_management(node)
        self.report({"INFO"}, f"Released {len(nodes)} nodes")
        return {"FINISHED"}
