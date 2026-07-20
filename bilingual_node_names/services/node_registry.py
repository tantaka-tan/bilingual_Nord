import bpy


class NodeRegistry:
    def __init__(self, diagnostics):
        self.diagnostics = diagnostics
        self.registered = set()
        self.entries = {}
        self.discovered = False

    def rebuild(self):
        candidates = {
            name for name in dir(bpy.types)
            if name.startswith(("GeometryNode", "ShaderNode", "FunctionNode", "NodeGroup"))
            and isinstance(getattr(bpy.types, name, None), type)
        }
        candidates.update(name for name in ("NodeFrame", "NodeReroute") if hasattr(bpy.types, name))
        candidates.difference_update({
            "FunctionNode",
            "GeometryNode",
            "GeometryNodeTree",
            "NodeGroup",
            "ShaderNode",
            "ShaderNodeTree",
        })
        self.registered = candidates
        self.entries = {}
        self.discovered = False
        try:
            node_groups = bpy.data.node_groups
        except AttributeError:
            return self.registered

        trees = {}
        try:
            for tree_type in ("GeometryNodeTree", "ShaderNodeTree"):
                trees[tree_type] = node_groups.new(f".BN_Discovery_{tree_type}", tree_type)
            for node_id in sorted(candidates):
                if node_id.endswith("CustomGroup"):
                    continue
                if node_id.startswith(("GeometryNode", "FunctionNode")):
                    target_tree_types = ("GeometryNodeTree",)
                elif node_id.startswith("ShaderNode"):
                    target_tree_types = ("ShaderNodeTree",)
                else:
                    target_tree_types = tuple(trees)
                tree_types = []
                english = ""
                for tree_type in target_tree_types:
                    tree = trees[tree_type]
                    try:
                        node = tree.nodes.new(node_id)
                    except (RuntimeError, TypeError):
                        continue
                    english = english or node.bl_label or node.name or node_id
                    tree_types.append(tree_type)
                    tree.nodes.remove(node)
                if tree_types:
                    self.entries[node_id] = {
                        "english": english,
                        "tree_types": tree_types,
                    }
            self.discovered = True
        finally:
            for tree in trees.values():
                if tree.name in node_groups:
                    node_groups.remove(tree)
        return self.registered

    def exists(self, bl_idname):
        return bl_idname in self.registered or hasattr(bpy.types, bl_idname)
