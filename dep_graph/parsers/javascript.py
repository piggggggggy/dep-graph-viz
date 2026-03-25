"""Parser for JavaScript/TypeScript/JSX/TSX files.

Handles:
  - ES module: import X from './path'
  - ES module: import('./path')
  - ES module: export { X } from './path'
  - CommonJS:  require('./path')
  - Re-exports: export * from './path'
"""

import os
import re
from . import BaseParser
from ..models import FileRef

# Static imports/exports:
#   import X from './foo'
#   import { X } from '../bar'
#   import './side-effect'
#   export { X } from './foo'
#   export * from './foo'
_STATIC_IMPORT_RE = re.compile(
    r"""(?:import|export)\s+"""
    r"""(?:[\w*{}\s,]+\s+from\s+)?"""  # optional binding clause
    r"""['"]([^'"]+)['"]""",
)

# Dynamic imports: import('./foo')
_DYNAMIC_IMPORT_RE = re.compile(
    r"""import\s*\(\s*['"]([^'"]+)['"]\s*\)""",
)

# CommonJS: require('./foo')
_REQUIRE_RE = re.compile(
    r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)""",
)

_JS_EXTENSIONS = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")

# Extensions to try when resolving bare paths
_RESOLVE_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")


def _is_relative(path: str) -> bool:
    """True if the import is a relative path (not a package)."""
    return path.startswith(".") or path.startswith("/")


def _resolve_target(source: str, raw_import: str, project_root: str) -> str:
    """Resolve an import specifier to a relative file path.

    Handles:
      - './foo'       -> same dir
      - '../foo'      -> parent dir
      - '@/foo'       -> src/foo (Next.js alias)
      - '~/foo'       -> src/foo (common alias)

    Returns relative path from project root, or the raw import if unresolvable.
    """
    source_dir = os.path.dirname(source)

    # Handle common aliases
    if raw_import.startswith("@/") or raw_import.startswith("~/"):
        # Try src/ first, then project root
        stripped = raw_import[2:]
        for base in ("src", "app", ""):
            candidate = os.path.join(base, stripped) if base else stripped
            resolved = _try_resolve(candidate, project_root)
            if resolved:
                return resolved
        return os.path.join("src", stripped)

    if not _is_relative(raw_import):
        # External package (e.g., 'react', 'next/link') — skip
        return ""

    joined = os.path.normpath(os.path.join(source_dir, raw_import))
    resolved = _try_resolve(joined, project_root)
    return resolved if resolved else joined


def _try_resolve(candidate: str, project_root: str) -> str:
    """Try to resolve a candidate path to an actual file.

    Tries: exact match, +extension, /index+extension.
    """
    abs_root = os.path.abspath(project_root)

    # Exact match (already has extension)
    if os.path.isfile(os.path.join(abs_root, candidate)):
        return candidate

    # Try adding extensions
    for ext in _RESOLVE_EXTENSIONS:
        attempt = candidate + ext
        if os.path.isfile(os.path.join(abs_root, attempt)):
            return attempt

    # Try index files (directory import)
    for ext in _RESOLVE_EXTENSIONS:
        attempt = os.path.join(candidate, "index" + ext)
        if os.path.isfile(os.path.join(abs_root, attempt)):
            return attempt

    return ""


class JavaScriptParser(BaseParser):
    """Parses JS/TS/JSX/TSX files for import/require references."""

    def __init__(self, project_root: str = ""):
        self._project_root = project_root

    def can_parse(self, relative_path: str) -> bool:
        return relative_path.endswith(_JS_EXTENSIONS)

    def parse(self, relative_path: str, content: str) -> list[FileRef]:
        refs: list[FileRef] = []
        seen: set[str] = set()

        for pattern, ref_type in [
            (_STATIC_IMPORT_RE, "import"),
            (_DYNAMIC_IMPORT_RE, "dynamic_import"),
            (_REQUIRE_RE, "require"),
        ]:
            for i, line in enumerate(content.splitlines(), 1):
                for m in pattern.finditer(line):
                    raw = m.group(1)

                    # Skip external packages
                    if not _is_relative(raw) and not raw.startswith("@/") and not raw.startswith("~/"):
                        continue

                    target = _resolve_target(
                        relative_path, raw, self._project_root,
                    )
                    if not target or target in seen:
                        continue
                    seen.add(target)

                    refs.append(FileRef(
                        source=relative_path,
                        target=target,
                        ref_type=ref_type,
                        line_number=i,
                    ))

        return refs
