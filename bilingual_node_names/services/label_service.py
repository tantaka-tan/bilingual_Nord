import bpy

from ..constants import (
    MANAGEMENT_PROPERTIES,
    PROP_DISPLAY_ENABLED,
    PROP_GENERATED_LABEL,
    PROP_MANAGED,
    PROP_NODE_TYPE,
    PROP_ORIGINAL_LABEL,
    PROP_SCHEMA_VERSION,
    PROP_TRANSLATION_REVISION,
    SCHEMA_VERSION,
)
from ..preferences import get_preferences


class LabelService:
    def __init__(self, translations, diagnostics):
        self.translations = translations
        self.diagnostics = diagnostics

    def build_label(self, node, preferences=None):
        preferences = preferences or get_preferences()
        use_short = getattr(preferences, "use_short_japanese", False)
        use_dynamic = getattr(preferences, "use_dynamic_titles", True)
        english, japanese = self.translations.get_display_names(
            node, use_short, use_dynamic, bpy.app.version
        )
        mode = getattr(preferences, "display_mode", "EN_JA")
        separator = getattr(preferences, "separator", " / ") or " / "
        if mode == "EN_ONLY" or not japanese:
            return english
        if mode == "JA_ONLY":
            return japanese or english
        if mode == "JA_EN":
            return f"{japanese}{separator}{english}"
        return f"{english}{separator}{japanese}"

    def is_readonly(self, node, preferences=None):
        owner = getattr(node, "id_data", None)
        if owner is None:
            return True
        if getattr(owner, "library", None) is not None:
            return True
        override = getattr(owner, "override_library", None)
        return override is not None and not getattr(preferences, "include_library_overrides", False)

    def can_apply(self, node, preferences=None, force=False):
        preferences = preferences or get_preferences()
        if self.is_readonly(node, preferences):
            return False, "READONLY"
        if node.get(PROP_MANAGED):
            display_enabled = bool(node.get(PROP_DISPLAY_ENABLED, True))
            expected = (
                node.get(PROP_GENERATED_LABEL, "")
                if display_enabled
                else node.get(PROP_ORIGINAL_LABEL, "")
            )
            if node.label != expected:
                if not force and getattr(preferences, "release_on_manual_edit", True):
                    self.release_management(node)
                    self.diagnostics.released(node.bl_idname)
                    return False, "USER_EDIT"
            return True, "MANAGED"
        overwrite = force or getattr(preferences, "overwrite_user_labels", False)
        if node.label and not overwrite:
            return False, "USER_LABEL"
        return True, "EMPTY"

    def apply(self, node, preferences=None, force=False):
        preferences = preferences or get_preferences()
        allowed, reason = self.can_apply(node, preferences, force)
        if not allowed:
            if reason == "READONLY":
                self.diagnostics.readonly()
            return False, reason
        generated = self.build_label(node, preferences)
        if PROP_ORIGINAL_LABEL not in node:
            node[PROP_ORIGINAL_LABEL] = node.label
        display_enabled = getattr(preferences, "show_bilingual_labels", True)
        node.label = generated if display_enabled else node.get(PROP_ORIGINAL_LABEL, "")
        node[PROP_MANAGED] = True
        node[PROP_SCHEMA_VERSION] = SCHEMA_VERSION
        node[PROP_NODE_TYPE] = node.bl_idname
        node[PROP_GENERATED_LABEL] = generated
        node[PROP_TRANSLATION_REVISION] = self.translations.revision
        node[PROP_DISPLAY_ENABLED] = display_enabled
        if display_enabled and getattr(preferences, "auto_adjust_width", False):
            estimated = max(140, min(getattr(preferences, "maximum_width", 300), len(generated) * 9))
            node.width = max(node.width, estimated)
        if not self.translations.get_node_entry(node.bl_idname, bpy.app.version):
            self.diagnostics.missing(node.bl_idname)
        return True, "APPLIED"

    def set_display_enabled(self, node, enabled, preferences=None):
        preferences = preferences or get_preferences()
        if not node.get(PROP_MANAGED):
            return False, "UNMANAGED"
        current_enabled = bool(node.get(PROP_DISPLAY_ENABLED, True))
        expected = (
            node.get(PROP_GENERATED_LABEL, "")
            if current_enabled
            else node.get(PROP_ORIGINAL_LABEL, "")
        )
        if node.label != expected:
            if getattr(preferences, "release_on_manual_edit", True):
                self.release_management(node)
                self.diagnostics.released(node.bl_idname)
            return False, "USER_EDIT"
        if enabled:
            generated = self.build_label(node, preferences)
            node.label = generated
            node[PROP_GENERATED_LABEL] = generated
            node[PROP_TRANSLATION_REVISION] = self.translations.revision
        else:
            node.label = node.get(PROP_ORIGINAL_LABEL, "")
        node[PROP_DISPLAY_ENABLED] = bool(enabled)
        return True, "ENABLED" if enabled else "DISABLED"

    def refresh(self, node, preferences=None, force=False):
        if not node.get(PROP_MANAGED) and not force:
            return False, "UNMANAGED"
        return self.apply(node, preferences, force)

    def restore(self, node):
        if not node.get(PROP_MANAGED):
            return False
        node.label = node.get(PROP_ORIGINAL_LABEL, "")
        self._clear_properties(node)
        return True

    def release_management(self, node):
        self._clear_properties(node)

    @staticmethod
    def _clear_properties(node):
        for key in MANAGEMENT_PROPERTIES:
            if key in node:
                del node[key]
