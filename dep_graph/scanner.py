"""File discovery for project directories."""

import os
from fnmatch import fnmatch
from typing import Iterator, Tuple


def scan_theme(
    project_dir: str,
    scan_dirs: list,
    exclude_patterns: list,
    file_extensions: tuple = (".liquid", ".json"),
) -> Iterator[Tuple[str, str]]:
    """Walk the project directory, yield (relative_path, absolute_path) pairs.

    Args:
        project_dir: absolute path to the project root
        scan_dirs: list of subdirectories to scan
        exclude_patterns: fnmatch patterns to skip
        file_extensions: tuple of extensions to include

    Yields:
        (relative_path, absolute_path) for each matching file
    """
    project_dir = os.path.abspath(project_dir)

    for scan_dir in scan_dirs:
        abs_dir = os.path.join(project_dir, scan_dir)
        if not os.path.isdir(abs_dir):
            continue

        for root, _dirs, files in os.walk(abs_dir):
            # Skip common heavy directories in-walk
            _dirs[:] = [d for d in _dirs if d not in (
                "node_modules", ".next", ".git", "dist", "build", "__pycache__",
            )]

            for fname in files:
                if not fname.endswith(file_extensions):
                    continue

                abs_path = os.path.join(root, fname)
                rel_path = os.path.relpath(abs_path, project_dir)

                if any(fnmatch(rel_path, pat) for pat in exclude_patterns):
                    continue

                yield rel_path, abs_path
