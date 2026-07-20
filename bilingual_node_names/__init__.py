from .addon_info import bl_info
from .handlers import register_handlers, unregister_handlers
from .keymaps import register_keymaps, unregister_keymaps
from .operators import CLASSES as OPERATOR_CLASSES
from .preferences import CLASSES as PREFERENCE_CLASSES, get_preferences
from .services import diagnostics, node_registry, search, translations
from .ui import CLASSES as UI_CLASSES
from .ui import register_menus, unregister_menus


CLASSES = (*PREFERENCE_CLASSES, *OPERATOR_CLASSES, *UI_CLASSES)


def register():
    import bpy

    for cls in CLASSES:
        bpy.utils.register_class(cls)
    preferences = get_preferences()
    user_path = getattr(preferences, "user_translation_path", "")
    translations.reload(user_path or None, bpy.app.version)
    node_registry.rebuild()
    search.rebuild_index()
    diagnostics.reset_runtime()
    register_menus()
    register_keymaps()
    register_handlers()


def unregister():
    import bpy

    unregister_handlers()
    unregister_keymaps()
    unregister_menus()
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
