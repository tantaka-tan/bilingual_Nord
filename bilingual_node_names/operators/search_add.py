import bpy
from bpy.props import EnumProperty, StringProperty

from ..preferences import get_preferences
from ..services import labels, node_registry, scanner, search


_enum_items_cache = {}
_enum_cache_generation = None
_enum_values = {}


def enum_value(node_id):
    value = _enum_values.get(node_id)
    if value is None:
        value = len(_enum_values) + 1
        _enum_values[node_id] = value
    return value


def search_items(self, context):
    global _enum_cache_generation
    tree = scanner.current_tree(context)
    tree_type = tree.bl_idname if tree else None
    space = getattr(context, "space_data", None)
    shader_type = getattr(space, "shader_type", "")
    object_type = getattr(getattr(context, "object", None), "type", "")
    if _enum_cache_generation != search.generation:
        _enum_items_cache.clear()
        _enum_cache_generation = search.generation
    cache_key = (tree_type, shader_type, object_type)
    cached = _enum_items_cache.get(cache_key)
    if cached is not None:
        return cached

    results = search.search(tree_type=tree_type, limit=5000)
    if tree_type == "ShaderNodeTree":
        excluded = set()
        if shader_type != "WORLD":
            excluded.add("ShaderNodeOutputWorld")
        if shader_type == "WORLD":
            excluded.update(("ShaderNodeOutputMaterial", "ShaderNodeOutputLight"))
        elif object_type == "LIGHT":
            excluded.add("ShaderNodeOutputMaterial")
        else:
            excluded.add("ShaderNodeOutputLight")
        results = [result for result in results if result.node_id not in excluded]
    items = [
        (result.node_id, result.label, result.description or result.node_id, "NONE", enum_value(result.node_id))
        for result in results
    ]
    _enum_items_cache[cache_key] = items
    return items


class BN_OT_search_add_node(bpy.types.Operator):
    bl_idname = "node.bn_search_add_node"
    bl_label = "Bilingual Node Search"
    bl_description = "Search nodes using English, Japanese, or aliases"
    bl_options = {"REGISTER", "UNDO"}
    bl_property = "search_selection"

    node_type: StringProperty(name="Node Type", options={"HIDDEN"})
    search_selection: EnumProperty(name="Node", items=search_items)

    @classmethod
    def poll(cls, context):
        return scanner.current_tree(context) is not None

    def invoke(self, context, event):
        self.node_type = ""
        context.window_manager.invoke_search_popup(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        tree = scanner.current_tree(context)
        node_id = self.node_type or self.search_selection
        if not tree or not node_id:
            return {"CANCELLED"}
        entry = search.get_entry(node_id)
        if not entry or tree.bl_idname not in entry.get("tree_types", [tree.bl_idname]):
            self.report({"ERROR"}, "Node is not available in this node tree")
            return {"CANCELLED"}
        try:
            node = node_registry.create_node(tree, node_id)
        except (OSError, RuntimeError) as exc:
            self.report({"ERROR"}, f"Could not add node: {exc}")
            return {"CANCELLED"}
        for existing in tree.nodes:
            existing.select = False
        node.select = True
        tree.nodes.active = node
        node.location = getattr(tree, "view_center", (0.0, 0.0))
        preferences = get_preferences(context)
        if entry.get("kind") == "ASSET":
            labels.apply_names(
                node,
                entry["english"],
                entry.get("japanese", ""),
                preferences,
                force=True,
            )
        else:
            labels.apply(node, preferences, force=True)
        self.report({"INFO"}, f"Added {node.label}")
        return {"FINISHED"}
