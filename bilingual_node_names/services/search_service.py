import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class SearchResult:
    node_id: str
    label: str
    description: str
    score: int


class SearchService:
    def __init__(self, translations, registry):
        self.translations = translations
        self.registry = registry
        self.index = []
        self.generation = 0

    @staticmethod
    def normalize_query(text):
        text = unicodedata.normalize("NFKC", text or "").lower()
        text = re.sub(r"[/_\-]+", " ", text)
        text = " ".join(text.split())
        return "".join(chr(ord(char) - 0x60) if "ァ" <= char <= "ヶ" else char for char in text)

    def rebuild_index(self):
        self.index = []
        node_ids = set(self.registry.entries)
        for node_id in node_ids:
            entry = self.get_entry(node_id)
            english = entry.get("english", node_id)
            japanese = entry.get("japanese", "")
            aliases = [*entry.get("aliases_en", []), *entry.get("aliases_ja", [])]
            names = [english, japanese, entry.get("japanese_short", ""), node_id]
            searchable = [self.normalize_query(value) for value in [*names, *aliases, entry.get("description_ja", "")]]
            self.index.append({
                "node_id": node_id,
                "entry": entry,
                "label": f"{english} / {japanese}" if japanese else english,
                "names": [self.normalize_query(value) for value in names if value],
                "aliases": [self.normalize_query(value) for value in aliases if value],
                "searchable": searchable,
            })
        self.generation += 1
        return self.index

    def get_entry(self, node_id):
        registry_entry = self.registry.entries.get(node_id)
        if registry_entry is None:
            return None
        entry = dict(self.translations.nodes.get(node_id, {}))
        entry.update(registry_entry)
        english = entry.get("english", node_id)
        entry["english"] = english
        entry["japanese"] = entry.get("japanese", "") or self.translations.translate_japanese(english)
        return entry

    def search(self, query="", tree_type=None, limit=100):
        normalized = self.normalize_query(query)
        results = []
        for item in self.index:
            tree_types = item["entry"].get("tree_types", [])
            if tree_type and tree_types and tree_type not in tree_types:
                continue
            score = self._score(normalized, item)
            if normalized and not score:
                continue
            aliases = [*item["entry"].get("aliases_en", []), *item["entry"].get("aliases_ja", [])]
            results.append(SearchResult(
                item["node_id"], item["label"], ", ".join(aliases), score
            ))
        results.sort(key=lambda result: (-result.score, result.label.casefold()))
        return results[:limit]

    @staticmethod
    def _score(query, item):
        if not query:
            return 1
        if query in item["names"]:
            return 1000
        if any(name.startswith(query) for name in item["names"]):
            return 800
        if any(query in name.split() for name in item["names"]):
            return 650
        if query in item["aliases"]:
            return 600
        if any(alias.startswith(query) for alias in item["aliases"]):
            return 500
        if any(query in value for value in item["searchable"]):
            return 350
        return 0
