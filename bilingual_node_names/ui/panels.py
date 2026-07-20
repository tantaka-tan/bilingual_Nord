import datetime

import bpy

from ..constants import PROP_MANAGED, PROP_ORIGINAL_LABEL
from ..preferences import get_preferences
from ..services import diagnostics, scanner, translations


class BN_PT_bilingual_nodes(bpy.types.Panel):
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Bilingual Nodes"
    bl_label = "Bilingual Nodes / 二言語ノード"

    @classmethod
    def poll(cls, context):
        return scanner.current_tree(context) is not None

    def draw(self, context):
        layout = self.layout
        tree = scanner.current_tree(context)
        selected = scanner.selected_nodes(context)
        preferences = get_preferences(context)

        enabled = getattr(preferences, "show_bilingual_labels", True)
        layout.operator(
            "node.bn_toggle_display",
            text=("Use Standard Display / 通常表示へ" if enabled else "Use Bilingual Display / 日英表示へ"),
            icon=("HIDE_ON" if enabled else "HIDE_OFF"),
        )

        box = layout.box()
        box.label(text="Selected node / 選択ノード")
        if len(selected) == 1:
            node = selected[0]
            entry = translations.get_node_entry(node.bl_idname, bpy.app.version) or {}
            box.label(text=f"English: {entry.get('english', node.bl_label or node.bl_idname)}")
            box.label(text=f"日本語: {entry.get('japanese', '未登録')}")
            box.label(text=f"ID: {node.bl_idname}")
            box.label(text=f"Label: {node.label or '(empty)'}")
            box.label(text=f"Managed: {'Yes' if node.get(PROP_MANAGED) else 'No'}")
            if PROP_ORIGINAL_LABEL in node:
                box.label(text=f"Original: {node.get(PROP_ORIGINAL_LABEL) or '(empty)'}")
        else:
            box.label(text=f"{len(selected)} nodes selected")
        row = box.row(align=True)
        operator = row.operator("node.bn_apply_labels", text="Apply")
        operator.scope = "SELECTED"
        operator = row.operator("node.bn_restore_labels", text="Restore")
        operator.scope = "SELECTED"
        box.operator("node.bn_release_selected", text="Release management")

        box = layout.box()
        box.label(text="Current tree / 現在のツリー")
        managed = sum(bool(node.get(PROP_MANAGED)) for node in tree.nodes)
        missing = sum(not translations.get_node_entry(node.bl_idname, bpy.app.version) for node in tree.nodes)
        box.label(text=f"Nodes: {len(tree.nodes)}  Managed: {managed}  Missing: {missing}")
        box.operator("node.bn_search_add_node", icon="VIEWZOOM")
        row = box.row(align=True)
        operator = row.operator("node.bn_apply_labels", text="Apply tree")
        operator.scope = "TREE"
        operator = row.operator("node.bn_refresh_labels", text="Refresh")
        operator.scope = "TREE"
        operator = box.operator("node.bn_restore_labels", text="Restore tree")
        operator.scope = "TREE"

        box = layout.box()
        box.label(text="Diagnostics / 診断")
        box.label(text=f"Missing types: {len(diagnostics.missing_nodes)}")
        box.label(text=f"Dictionary errors: {len(diagnostics.dictionary_errors)}")
        box.label(text=f"Read-only skips: {diagnostics.readonly_skips}")
        if diagnostics.last_scan_time:
            stamp = datetime.datetime.fromtimestamp(diagnostics.last_scan_time).strftime("%H:%M:%S")
            box.label(text=f"Last scan: {stamp}")
        box.operator("node.bn_rebuild_diagnostics", icon="FILE_REFRESH")
