import json
from pathlib import Path

class AutoComplete:
    def __init__(self, root: Path):
        self.brands = json.loads((root/"assets"/"brands.json").read_text(encoding='utf-8'))
        self.models = json.loads((root/"assets"/"models.json").read_text(encoding='utf-8'))
    def suggest(self, q: str, kind: str = 'brand'):
        if len(q) < 2:
            return []
        arr = self.brands if kind=='brand' else self.models
        ql = q.lower()
        return [x for x in arr if ql in x.lower()][:10]