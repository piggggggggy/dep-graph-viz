"""Parser for Shopify JSON template files."""

import json
import re
from . import BaseParser
from ..models import FileRef

# Shopify CLI prepends /* ... */ block comments to template JSON files
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


class JsonTemplateParser(BaseParser):

    def can_parse(self, relative_path: str) -> bool:
        return relative_path.startswith("templates/") and relative_path.endswith(".json")

    @staticmethod
    def _strip_json_comments(text: str) -> str:
        """Remove block comments (/* ... */) that Shopify CLI adds."""
        return _BLOCK_COMMENT_RE.sub("", text)

    def parse(self, relative_path: str, content: str) -> list[FileRef]:
        refs: list[FileRef] = []
        try:
            data = json.loads(self._strip_json_comments(content))
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
