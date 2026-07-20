import bpy
from bpy.app.handlers import persistent

from ..preferences import get_preferences
from ..services import labels, node_registry, scanner, search


_timer_running = False


@persistent
def on_load_post(_):
    scanner.cache.clear()
    node_registry.rebuild()
    search.rebuild_index()
    preferences = get_preferences()
    for tree in scanner.iter_all_trees():
        for node in tree.nodes:
            if node.get("_bn_managed"):
                labels.refresh(node, preferences)
            elif getattr(preferences, "apply_on_load", True):
                labels.apply(node, preferences)
    scanner.rebuild_cache()


@persistent
def on_undo_redo(_):
    scanner.rebuild_cache()


def monitor_timer():
    global _timer_running
    if not _timer_running:
        return None
    preferences = get_preferences()
    interval = getattr(preferences, "monitor_interval", 0.75)
    if not node_registry.discovered or node_registry.is_stale():
        node_registry.rebuild()
        search.rebuild_index()
    if getattr(preferences, "monitor_enabled", True) and getattr(preferences, "auto_apply_new_nodes", True):
        scanner.scan_new_nodes(preferences)
    return max(0.5, interval)


def register_handlers():
    global _timer_running
    for collection, handler in (
        (bpy.app.handlers.load_post, on_load_post),
        (bpy.app.handlers.undo_post, on_undo_redo),
        (bpy.app.handlers.redo_post, on_undo_redo),
    ):
        if handler not in collection:
            collection.append(handler)
    _timer_running = True
    if not bpy.app.timers.is_registered(monitor_timer):
        bpy.app.timers.register(monitor_timer, first_interval=0.75, persistent=True)


def unregister_handlers():
    global _timer_running
    _timer_running = False
    for collection, handler in (
        (bpy.app.handlers.load_post, on_load_post),
        (bpy.app.handlers.undo_post, on_undo_redo),
        (bpy.app.handlers.redo_post, on_undo_redo),
    ):
        if handler in collection:
            collection.remove(handler)
    if bpy.app.timers.is_registered(monitor_timer):
        bpy.app.timers.unregister(monitor_timer)
