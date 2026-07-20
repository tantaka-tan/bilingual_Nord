import json
import gettext
from copy import deepcopy
from pathlib import Path

import bpy


class TranslationService:
    def __init__(self, diagnostics):
        self.diagnostics = diagnostics
        self.nodes = {}
        self.revision = "unloaded"
        self.errors = []
        self.official_japanese = None

    @property
    def translation_dir(self):
        return Path(__file__).resolve().parent.parent / "translations"

    def reload(self, user_path=None, blender_version=None):
        self.nodes = {}
        self.errors = []
        self._load_official_japanese()
        revisions = []
        paths = [
            self.translation_dir / "geometry_nodes_ja.json",
            self.translation_dir / "shader_nodes_ja.json",
            self.translation_dir / "dynamic_operations_ja.json",
        ]
        if blender_version:
            major, minor = blender_version[:2]
            paths.append(self.translation_dir / "overrides" / f"blender_{major}_{minor}.json")
            paths.append(self.translation_dir / "overrides" / f"blender_{major}_x.json")
        if user_path:
            paths.append(Path(user_path).expanduser())

        for path in paths:
            if not path.exists():
                if user_path and path == paths[-1]:
                    self.errors.append(f"Dictionary not found: {path}")
                continue
            data = self._load_file(path)
            if not data:
                continue
            revisions.append(str(data.get("translation_revision", "unknown")))
            for node_id, entry in data.get("nodes", {}).items():
                if not self._valid_entry(node_id, entry, path):
                    continue
                current = self.nodes.setdefault(node_id, {})
                current.update(deepcopy(entry))

        self.revision = revisions[-1] if revisions else "none"
        self.diagnostics.set_dictionary_errors(self.errors)
        return not self.errors

    def _load_official_japanese(self):
        self.official_japanese = None
        for resource_type in ("LOCAL", "SYSTEM"):
            resource_path = bpy.utils.resource_path(resource_type)
            if not resource_path:
                continue
            path = Path(resource_path) / "datafiles" / "locale" / "ja" / "LC_MESSAGES" / "blender.mo"
            if not path.exists():
                continue
            try:
                with path.open("rb") as stream:
                    self.official_japanese = gettext.GNUTranslations(stream)
                return
            except (OSError, UnicodeError):
                continue

    def translate_japanese(self, english):
        if not english or self.official_japanese is None:
            return ""
        translated = self.official_japanese.gettext(english)
        return translated if translated and translated != english else ""

    def _load_file(self, path):
        try:
            with path.open("r", encoding="utf-8") as stream:
                data = json.load(stream)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            self.errors.append(f"{path.name}: {exc}")
            return None
        if data.get("schema_version") != 1 or not isinstance(data.get("nodes"), dict):
            self.errors.append(f"{path.name}: invalid schema")
            return None
        return data

    def _valid_entry(self, node_id, entry, path):
        if not isinstance(node_id, str) or not node_id or not isinstance(entry, dict):
            self.errors.append(f"{path.name}: invalid node entry")
            return False
        for key in ("english", "japanese"):
            if key in entry and not isinstance(entry[key], str):
                self.errors.append(f"{path.name}: {node_id}.{key} must be text")
                return False
        tree_types = entry.get("tree_types")
        if tree_types is not None and not isinstance(tree_types, list):
            self.errors.append(f"{path.name}: {node_id}.tree_types must be a list")
            return False
        return True

    def validate(self):
        return list(self.errors)

    def get_node_entry(self, bl_idname, blender_version=None):
        entry = self.nodes.get(bl_idname)
        if not entry or not self._version_matches(entry, blender_version):
            return None
        return entry

    @staticmethod
    def _version_matches(entry, version):
        if not version:
            return True
        version = tuple(version[:3])
        minimum = entry.get("min_version")
        maximum = entry.get("max_version")
        return (not minimum or version >= tuple(minimum)) and (not maximum or version <= tuple(maximum))

    def get_display_names(self, node, use_short=False, use_dynamic=True, blender_version=None):
        entry = self.get_node_entry(node.bl_idname, blender_version)
        english = (entry or {}).get("english") or getattr(node, "bl_label", "") or node.bl_idname
        japanese_key = "japanese_short" if use_short and (entry or {}).get("japanese_short") else "japanese"
        japanese = (entry or {}).get(japanese_key, "") or self.translate_japanese(english)
        if use_dynamic and entry and entry.get("dynamic_title"):
            dynamic = entry["dynamic_title"]
            value = getattr(node, dynamic.get("property", ""), None)
            operation = dynamic.get("values", {}).get(str(value))
            if operation:
                english = operation.get("english", english)
                japanese = operation.get("japanese", japanese)
        return english, japanese

    def get_aliases(self, bl_idname):
        entry = self.nodes.get(bl_idname, {})
        return [*entry.get("aliases_en", []), *entry.get("aliases_ja", [])]
