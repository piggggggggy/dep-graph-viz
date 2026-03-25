"""CLI interface for dep-graph."""

import argparse
import os
import sys
import webbrowser
from typing import Optional

from .config import GraphConfig
from .graph import build_graph
from .renderer import render_html, render_json
from .presets import PRESETS


def main(argv: Optional[list] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="dep-graph",
        description="Generate an interactive dependency graph for any project.",
    )
    parser.add_argument(
        "project_dir",
        help="Path to the project root directory",
    )
    parser.add_argument(
        "-o", "--output",
        default="dependency-graph.html",
        help="Output file path (default: dependency-graph.html)",
    )
    parser.add_argument(
        "-p", "--preset",
        choices=list(PRESETS.keys()),
        default=None,
        help="Use a preset configuration: " + ", ".join(PRESETS.keys()),
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Graph title displayed in the HTML",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=None,
        help="fnmatch patterns to exclude",
    )
    parser.add_argument(
        "--entry",
        nargs="+",
        default=None,
        help="Glob patterns for entry point files (overrides preset entry_patterns)",
    )
    parser.add_argument(
        "--hub-threshold",
        type=int,
        default=5,
        help="Minimum in-degree to count as a hub (default: 5)",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Don't auto-open the HTML file in browser",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output graph data as JSON instead of HTML",
    )

    args = parser.parse_args(argv)

    project_dir = os.path.abspath(args.project_dir)
    if not os.path.isdir(project_dir):
        print("Error: '{}' is not a directory".format(project_dir), file=sys.stderr)
        sys.exit(1)

    # Auto-detect preset if not specified
    preset_name = args.preset
    if preset_name is None:
        preset_name = _detect_preset(project_dir)
        if preset_name:
            print("Auto-detected preset: {}".format(preset_name))

    # Build config from preset or defaults
    if preset_name and preset_name in PRESETS:
        config = PRESETS[preset_name]()
    else:
        config = GraphConfig()

    # CLI overrides
    if args.title:
        config.title = args.title
    if args.exclude is not None:
        config.exclude_patterns = args.exclude
    config.hub_threshold = args.hub_threshold
    if args.entry is not None:
        config.entry_patterns = args.entry

    # Select parser registry based on file types
    registry = None
    js_exts = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
    if any(ext in config.file_extensions for ext in js_exts):
        from .parsers import javascript_registry
        registry = javascript_registry(project_root=project_dir)
    else:
        from .parsers import default_registry
        registry = default_registry()

    print("Scanning: {}".format(project_dir))
    graph = build_graph(project_dir, config, registry)
    print("Found: {} nodes, {} edges".format(len(graph.nodes), len(graph.edges)))

    if not graph.nodes:
        print("No files found. Check --preset or scan_dirs configuration.", file=sys.stderr)
        sys.exit(1)

    if args.json:
        output = render_json(graph)
        out_path = args.output
        if out_path.endswith(".html"):
            out_path = out_path.replace(".html", ".json")
    else:
        output = render_html(graph, config)
        out_path = args.output

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(output)
    print("Output: {}".format(out_path))

    if not args.json and not args.no_open:
        abs_path = os.path.abspath(out_path)
        webbrowser.open("file://{}".format(abs_path))


def _detect_preset(project_dir: str) -> Optional[str]:
    """Try to auto-detect the project type from common marker files."""
    markers = {
        "nextjs": ["next.config.js", "next.config.mjs", "next.config.ts"],
        "react": ["package.json"],  # fallback: check for react dependency
        "shopify": ["layout/theme.liquid", "config/settings_schema.json"],
    }

    # Shopify first (most specific markers)
    for f in markers["shopify"]:
        if os.path.isfile(os.path.join(project_dir, f)):
            return "shopify"

    # Next.js
    for f in markers["nextjs"]:
        if os.path.isfile(os.path.join(project_dir, f)):
            return "nextjs"

    # React (check package.json for react dependency)
    pkg_json = os.path.join(project_dir, "package.json")
    if os.path.isfile(pkg_json):
        try:
            import json
            with open(pkg_json) as fh:
                pkg = json.load(fh)
            all_deps = {}
            all_deps.update(pkg.get("dependencies", {}))
            all_deps.update(pkg.get("devDependencies", {}))
            if "react" in all_deps:
                return "react"
        except Exception:
            pass

    return None


if __name__ == "__main__":
    main()
