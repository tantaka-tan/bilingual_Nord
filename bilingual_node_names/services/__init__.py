from .diagnostic_service import DiagnosticService
from .label_service import LabelService
from .node_registry import NodeRegistry
from .node_tree_scanner import NodeTreeScanner
from .search_service import SearchService
from .translation_service import TranslationService

diagnostics = DiagnosticService()
translations = TranslationService(diagnostics)
node_registry = NodeRegistry(diagnostics)
labels = LabelService(translations, diagnostics)
scanner = NodeTreeScanner(labels, translations, diagnostics)
search = SearchService(translations, node_registry)
