import bpy

from ..services import diagnostics, scanner, translations


class BN_OT_rebuild_diagnostics(bpy.types.Operator):
    bl_idname = "node.bn_rebuild_diagnostics"
    bl_label = "Rebuild Bilingual Node Diagnostics"

    def execute(self, context):
        diagnostics.missing_nodes.clear()
        for tree in scanner.iter_all_trees():
            for node in tree.nodes:
                if not translations.get_node_entry(node.bl_idname, bpy.app.version):
                    diagnostics.missing(node.bl_idname)
        scanner.rebuild_cache()
        self.report({"INFO"}, f"Found {len(diagnostics.missing_nodes)} unregistered node types")
        return {"FINISHED"}
