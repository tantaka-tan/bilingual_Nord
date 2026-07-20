addon_keymaps = []


def register_keymaps():
    import bpy
    keyconfig = bpy.context.window_manager.keyconfigs.addon
    if not keyconfig:
        return
    keymap = keyconfig.keymaps.new(name="Node Editor", space_type="NODE_EDITOR")
    item = keymap.keymap_items.new("node.bn_search_add_node", "A", "PRESS", ctrl=True, shift=True)
    addon_keymaps.append((keymap, item))


def unregister_keymaps():
    for keymap, item in addon_keymaps:
        keymap.keymap_items.remove(item)
    addon_keymaps.clear()
