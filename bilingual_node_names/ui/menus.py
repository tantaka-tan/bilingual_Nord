import bpy

from ..operators.search_add import search_items


class BN_MT_bilingual_add(bpy.types.Menu):
    bl_idname = "NODE_MT_bn_bilingual_add"
    bl_label = "Bilingual Nodes / 二言語ノード"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = "EXEC_DEFAULT"
        items = search_items(None, context)
        if not items:
            layout.label(text="No compatible nodes / 候補なし")
            return
        for node_id, label, description in items:
            operator = layout.operator(
                "node.bn_search_add_node",
                text=label,
                icon="NONE",
            )
            operator.node_type = node_id


def draw_add_menu(self, context):
    from ..preferences import get_preferences

    preferences = get_preferences(context)
    if preferences and not preferences.add_to_menu:
        return
    self.layout.separator()
    self.layout.menu("NODE_MT_bn_bilingual_add", icon="NODETREE")
    self.layout.operator("node.bn_search_add_node", text="Bilingual Search / 二言語検索", icon="VIEWZOOM")


def register_menus():
    import bpy
    bpy.types.NODE_MT_add.append(draw_add_menu)


def unregister_menus():
    import bpy
    try:
        bpy.types.NODE_MT_add.remove(draw_add_menu)
    except ValueError:
        pass
