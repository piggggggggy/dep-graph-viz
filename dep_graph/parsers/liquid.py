"""Parser for Shopify Liquid template files."""

import re
from . import BaseParser
from ..models import FileRef

# render 'name' / include 'name'
_RENDER_INCLUDE_RE = re.compile(r"""(?:render|include)\s+['"]([^'"]+)['"]""")

# section 'name' (inside liquid files)
_SECTION_RE = re.compile(r"""section\s+['"]([^'"]+)['"]""")


class LiquidParser(BaseParser):

    def can_parse(self, relative_path: str) -> bool:
        return relative_path.endswith(".liquid")

    def parse(self, relative_path: str, content: str) -> list[FileRef]:
        refs: list[FileRef] = []

        for i, line in enumerate(content.splitlines(), 1):
            for m in _RENDER_INCLUDE_RE.finditer(line):
                name = m.group(1)
                ref_type = "render" if "render" in m.group(0) else "include"
                refs.append(FileRef(
                    source=relative_path,
                    target=f"snippets/{name}.liquid",
                    ref_type=ref_type,
                    line_number=i,
                ))

            for m in _SECTION_RE.finditer(line):
                name = m.group(1)
                refs.append(FileRef(
                    source=relative_path,
                    target=f"sections/{name}.liquid",
                    ref_type="section",
                    line_number=i,
                ))

        return refs
