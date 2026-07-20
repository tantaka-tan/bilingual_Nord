from .apply_labels import BN_OT_apply_labels, BN_OT_refresh_labels, BN_OT_toggle_display
from .diagnostics import BN_OT_rebuild_diagnostics
from .restore_labels import BN_OT_release_selected, BN_OT_restore_labels
from .search_add import BN_OT_search_add_node
from .translation_io import BN_OT_reload_translations

CLASSES = (
    BN_OT_search_add_node,
    BN_OT_apply_labels,
    BN_OT_restore_labels,
    BN_OT_refresh_labels,
    BN_OT_toggle_display,
    BN_OT_release_selected,
    BN_OT_reload_translations,
    BN_OT_rebuild_diagnostics,
)
