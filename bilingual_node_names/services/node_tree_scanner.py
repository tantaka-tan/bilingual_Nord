import time

import bpy

from ..constants import PROP_MANAGED, SUPPORTED_TREE_TYPES


class NodeTreeScanner:
    def __init__(self, labels, translations, diagnostics):
        self.labels = labels
        self.translations = translations
        self.diagnostics = diagnostics
        self.cache = {}

    @staticmethod
    def current_tree(context):
        space = getattr(context, "space_data", None)
        tree = getattr(space, "edit_tree", None) or getattr(space, "node_tree", None)
        return tree if tree and tree.bl_idname in SUPPORTED_TREE_TYPES else None

    def iter_all_trees(self):
        seen = set()
        owners = [*bpy.data.materials, *bpy.data.worlds, *bpy.data.lights, *bpy.data.node_groups]
        for owner in owners:
            tree = owner if isinstance(owner, bpy.types.NodeTree) else getattr(owner, "node_tree", None)
            if not tree or tree.bl_idname not in SUPPORTED_TREE_TYPES:
                continue
            pointer = tree.as_pointer()
            if pointer not in seen:
                seen.add(pointer)
                yield tree

    @staticmethod
    def selected_nodes(context):
        tree = NodeTreeScanner.current_tree(context)
        return [node for node in tree.nodes if node.select] if tree else []

    def material_tree(self, context):
        material = getattr(getattr(context, "object", None), "active_material", None)
        tree = getattr(material, "node_tree", None)
        return tree if tree and tree.bl_idname == "ShaderNodeTree" else None

    def nodes_for_scope(self, context, scope):
        if scope == "SELECTED":
            return self.selected_nodes(context)
        if scope == "MATERIAL":
            tree = self.material_tree(context)
            return list(tree.nodes) if tree else []
        if scope == "FILE":
            return [node for tree in self.iter_all_trees() for node in tree.nodes]
        tree = self.current_tree(context)
        return list(tree.nodes) if tree else []

    def apply_scope(self, context, scope, preferences=None, force=False, managed_only=False):
        result = {"changed": 0, "skipped": 0, "readonly": 0, "missing": 0}
        for node in self.nodes_for_scope(context, scope):
            if managed_only and not node.get(PROP_MANAGED):
                result["skipped"] += 1
                continue
            changed, reason = self.labels.apply(node, preferences, force)
            if changed:
                result["changed"] += 1
                if not self.translations.get_node_entry(node.bl_idname, bpy.app.version):
                    result["missing"] += 1
            else:
                result["skipped"] += 1
                if reason == "READONLY":
                    result["readonly"] += 1
        self.diagnostics.last_scan_time = time.time()
        self.rebuild_cache()
        return result

    def restore_scope(self, context, scope):
        changed = sum(self.labels.restore(node) for node in self.nodes_for_scope(context, scope))
        self.rebuild_cache()
        return changed

    def rebuild_cache(self):
        self.cache = {
            tree.as_pointer(): {node.as_pointer() for node in tree.nodes}
            for tree in self.iter_all_trees()
        }

    def scan_new_nodes(self, preferences=None, limit=500):
        changed = 0
        processed = 0
        for tree in self.iter_all_trees():
            pointer = tree.as_pointer()
            known = self.cache.setdefault(pointer, set())
            current = {node.as_pointer() for node in tree.nodes}
            for node in tree.nodes:
                if node.as_pointer() not in known and processed < limit:
                    applied, _ = self.labels.apply(node, preferences)
                    changed += int(applied)
                    processed += 1
            self.cache[pointer] = current
        self.diagnostics.last_scan_time = time.time()
        return changed
