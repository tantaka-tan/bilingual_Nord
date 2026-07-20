import os
import sys
from contextlib import contextmanager

import bpy


@contextmanager
def suppress_native_output():
    saved_descriptors = []
    null_descriptor = None
    suppression_enabled = False
    try:
        for stream in (sys.stdout, sys.stderr):
            if stream is not None:
                stream.flush()
        null_descriptor = os.open(os.devnull, os.O_WRONLY)
        for descriptor in (1, 2):
            saved_descriptors.append((descriptor, os.dup(descriptor)))
            os.dup2(null_descriptor, descriptor)
        suppression_enabled = True
    except OSError:
        for descriptor, saved in reversed(saved_descriptors):
            try:
                os.dup2(saved, descriptor)
                os.close(saved)
            except OSError:
                pass
        saved_descriptors.clear()
        if null_descriptor is not None:
            try:
                os.close(null_descriptor)
            except OSError:
                pass
            null_descriptor = None
    try:
        yield
    finally:
        if suppression_enabled:
            for descriptor, saved in reversed(saved_descriptors):
                try:
                    os.dup2(saved, descriptor)
                    os.close(saved)
                except OSError:
                    pass
        if null_descriptor is not None:
            try:
                os.close(null_descriptor)
            except OSError:
                pass


class NodeRegistry:
    def __init__(self, diagnostics):
        self.diagnostics = diagnostics
        self.registered = set()
        self.entries = {}
        self.discovered = False

    @staticmethod
    def candidate_ids():
        node_types = {}
        for name in dir(bpy.types):
            node_type = getattr(bpy.types, name, None)
            try:
                if isinstance(node_type, type) and node_type is not bpy.types.Node and issubclass(node_type, bpy.types.Node):
                    node_types[node_type] = name
            except TypeError:
                continue

        pending = [bpy.types.Node]
        visited = set(pending)
        while pending:
            parent = pending.pop()
            try:
                subclasses = parent.__subclasses__()
            except TypeError:
                continue
            for node_type in subclasses:
                if node_type in visited:
                    continue
                visited.add(node_type)
                pending.append(node_type)
                try:
                    if node_type.is_registered_node_type():
                        node_types.setdefault(node_type, node_type.__name__)
                except (AttributeError, RuntimeError):
                    continue

        candidates = set()
        for node_type, fallback_name in node_types.items():
            node_id = getattr(getattr(node_type, "bl_rna", None), "identifier", "")
            if not node_id:
                node_id = node_type.__dict__.get("bl_idname", "")
            if isinstance(node_id, str) and node_id:
                candidates.add(node_id)
            else:
                candidates.add(fallback_name)
        return candidates

    def is_stale(self):
        return self.registered != self.candidate_ids()

    def rebuild(self):
        candidates = self.candidate_ids()
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
            with suppress_native_output():
                for node_id in sorted(candidates):
                    tree_types = []
                    english = ""
                    for tree_type, tree in trees.items():
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
