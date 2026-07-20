import hashlib
import os
import sys
from contextlib import contextmanager
from pathlib import Path

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
        self.asset_signature = ()
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
        return self.registered != self.candidate_ids() or self.asset_signature != self.current_asset_signature()

    @staticmethod
    def asset_libraries():
        libraries = {}
        for resource_type in ("LOCAL", "SYSTEM"):
            root = Path(bpy.utils.resource_path(resource_type)) / "datafiles" / "assets" / "nodes"
            if not root.is_dir():
                continue
            for path in root.glob("*.blend"):
                filename = path.name.casefold()
                if filename.startswith("geometry_nodes"):
                    tree_type = "GeometryNodeTree"
                elif filename.startswith("shading_nodes"):
                    tree_type = "ShaderNodeTree"
                else:
                    continue
                libraries[str(path.resolve())] = tree_type
        return libraries

    @classmethod
    def current_asset_signature(cls):
        signature = []
        for path in cls.asset_libraries():
            try:
                stat = Path(path).stat()
            except OSError:
                continue
            signature.append((path, stat.st_mtime_ns, stat.st_size))
        return tuple(sorted(signature))

    def discover_assets(self):
        for library_path, tree_type in self.asset_libraries().items():
            try:
                with bpy.data.libraries.load(library_path, assets_only=True) as (source, _target):
                    names = list(source.node_groups)
            except (OSError, RuntimeError):
                continue
            for asset_name in names:
                digest = hashlib.sha1(f"{library_path}\0{asset_name}".encode("utf-8")).hexdigest()[:20]
                asset_id = f"BNAsset_{digest}"
                self.entries[asset_id] = {
                    "english": asset_name,
                    "tree_types": [tree_type],
                    "kind": "ASSET",
                    "asset_library": library_path,
                    "asset_name": asset_name,
                }

    @staticmethod
    def _existing_asset_group(entry):
        for node_group in bpy.data.node_groups:
            if (
                node_group.get("_bn_asset_library") == entry["asset_library"]
                and node_group.get("_bn_asset_name") == entry["asset_name"]
            ):
                return node_group
        return None

    def load_asset_group(self, entry):
        node_group = self._existing_asset_group(entry)
        if node_group is not None:
            return node_group
        library_path = entry["asset_library"]
        asset_name = entry["asset_name"]
        with bpy.data.libraries.load(library_path, link=False, assets_only=True) as (source, target):
            if asset_name not in source.node_groups:
                raise RuntimeError(f"Node asset is no longer available: {asset_name}")
            target.node_groups = [asset_name]
        node_group = target.node_groups[0]
        if node_group is None or node_group.bl_idname not in entry["tree_types"]:
            if node_group is not None:
                bpy.data.node_groups.remove(node_group)
            raise RuntimeError(f"Node asset has an incompatible tree type: {asset_name}")
        node_group["_bn_asset_library"] = library_path
        node_group["_bn_asset_name"] = asset_name
        return node_group

    def create_node(self, tree, node_id):
        entry = self.entries.get(node_id, {})
        if entry.get("kind") != "ASSET":
            return tree.nodes.new(node_id)
        node_group = self.load_asset_group(entry)
        group_node_type = "GeometryNodeGroup" if tree.bl_idname == "GeometryNodeTree" else "ShaderNodeGroup"
        node = tree.nodes.new(group_node_type)
        node.node_tree = node_group
        return node

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
            self.discover_assets()
            self.asset_signature = self.current_asset_signature()
            self.discovered = True
        finally:
            for tree in trees.values():
                if tree.name in node_groups:
                    node_groups.remove(tree)
        return self.registered

    def exists(self, bl_idname):
        return bl_idname in self.entries or bl_idname in self.registered or hasattr(bpy.types, bl_idname)
