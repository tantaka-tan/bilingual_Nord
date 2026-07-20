import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, StringProperty

from .constants import ADDON_ID


class BN_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_ID

    display_mode: EnumProperty(
        name="Display order",
        items=(
            ("EN_JA", "English / 日本語", "Show English followed by Japanese"),
            ("JA_EN", "日本語 / English", "Show Japanese followed by English"),
            ("EN_ONLY", "English only", "Show only English"),
            ("JA_ONLY", "日本語のみ", "Show only Japanese"),
        ),
        default="EN_JA",
    )
    show_bilingual_labels: BoolProperty(name="Show bilingual labels", default=True)
    separator: StringProperty(name="Separator", default=" / ", maxlen=16)
    use_short_japanese: BoolProperty(name="Use short Japanese names", default=False)
    use_dynamic_titles: BoolProperty(name="Use dynamic operation names", default=True)
    auto_adjust_width: BoolProperty(name="Adjust node width", default=False)
    maximum_width: IntProperty(name="Maximum width", default=300, min=140, max=1000)

    auto_apply_new_nodes: BoolProperty(name="Apply to new nodes", default=True)
    apply_on_load: BoolProperty(name="Apply after loading a file", default=True)
    monitor_enabled: BoolProperty(name="Monitor standard node additions", default=True)
    monitor_interval: FloatProperty(name="Monitor interval", default=0.75, min=0.5, max=10.0)
    overwrite_user_labels: BoolProperty(name="Overwrite user labels", default=False)
    release_on_manual_edit: BoolProperty(name="Release manually edited labels", default=True)
    include_library_overrides: BoolProperty(name="Include library overrides", default=False)

    enable_english_search: BoolProperty(name="Search English", default=True)
    enable_japanese_search: BoolProperty(name="Search Japanese", default=True)
    enable_alias_search: BoolProperty(name="Search aliases", default=True)
    add_to_menu: BoolProperty(name="Add to Shift+A menu", default=True)
    user_translation_path: StringProperty(name="User dictionary", subtype="FILE_PATH")

    def draw(self, context):
        layout = self.layout
        display = layout.box()
        display.label(text="Display / 表示")
        display.label(text=f"Bilingual labels: {'ON' if self.show_bilingual_labels else 'OFF'}")
        display.operator("node.bn_toggle_display", icon="ARROW_LEFTRIGHT")
        display.prop(self, "display_mode")
        display.prop(self, "separator")
        display.prop(self, "use_short_japanese")
        display.prop(self, "use_dynamic_titles")
        row = display.row(align=True)
        row.prop(self, "auto_adjust_width")
        row.prop(self, "maximum_width")

        automatic = layout.box()
        automatic.label(text="Automatic application / 自動適用")
        automatic.prop(self, "auto_apply_new_nodes")
        automatic.prop(self, "apply_on_load")
        automatic.prop(self, "monitor_enabled")
        automatic.prop(self, "monitor_interval")
        automatic.prop(self, "overwrite_user_labels")
        automatic.prop(self, "release_on_manual_edit")
        automatic.prop(self, "include_library_overrides")

        search = layout.box()
        search.label(text="Search / 検索")
        search.prop(self, "enable_english_search")
        search.prop(self, "enable_japanese_search")
        search.prop(self, "enable_alias_search")
        search.prop(self, "add_to_menu")

        translation = layout.box()
        translation.label(text="Translations / 翻訳")
        translation.prop(self, "user_translation_path")
        translation.operator("node.bn_reload_translations", icon="FILE_REFRESH")


def get_preferences(context=None):
    context = context or bpy.context
    addon = context.preferences.addons.get(ADDON_ID) if context and context.preferences else None
    return addon.preferences if addon else None


CLASSES = (BN_AddonPreferences,)
