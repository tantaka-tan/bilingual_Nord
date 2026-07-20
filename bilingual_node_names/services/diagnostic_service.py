from collections import deque
from dataclasses import dataclass, field


@dataclass
class DiagnosticService:
    dictionary_errors: list[str] = field(default_factory=list)
    missing_nodes: set[str] = field(default_factory=set)
    readonly_skips: int = 0
    manually_released: int = 0
    last_scan_time: float = 0.0
    events: deque = field(default_factory=lambda: deque(maxlen=100))

    def reset_runtime(self):
        self.missing_nodes.clear()
        self.readonly_skips = 0
        self.manually_released = 0
        self.last_scan_time = 0.0
        self.events.clear()

    def set_dictionary_errors(self, errors):
        self.dictionary_errors = list(errors)

    def record(self, level, message):
        self.events.append((level, message))

    def missing(self, bl_idname):
        self.missing_nodes.add(bl_idname)

    def readonly(self):
        self.readonly_skips += 1

    def released(self, bl_idname):
        self.manually_released += 1
        self.record("INFO", f"Manual edit released: {bl_idname}")
