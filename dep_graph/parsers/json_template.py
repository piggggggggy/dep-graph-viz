"""Parser for Shopify JSON template files."""

import json
from . import BaseParser
from ..models import FileRef


class JsonTemplateParser(BaseParser):

    def can_parse(self, relative_path: str) -> bool:
        return relative_path.startswith("templates/") and relative_path.endswith(".json")

    def parse(self, relative_path: str, content: str) -> list[FileRef]:
        refs: list[FileRef] = []
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, ValueError):
            return refs

        # Layout reference
        if "layout" in data:
            layout = data["layout"]
            refs.append(FileRef(
                source=relative_path,
                target=f"layout/{layout}.liquid",
                ref_type="layout",
            ))

        # Section references
        if "sections" in data and isinstance(data["sections"], dict):
            for _sid, sdata in data["sections"].items():
                if isinstance(sdata, dict) and "type" in sdata:
                    stype = sdata["type"]
                    # Skip app blocks (shopify://apps/...)
                    if not stype.startswith("shopify://"):
                        refs.append(FileRef(
                            source=relative_path,
                            target=f"sections/{stype}.liquid",
                            ref_type="section",
                        ))

        return refs
