"""Graph builder: wires scanner + parsers into a DependencyGraph."""

import os
from collections import defaultdict, deque
from fnmatch import fnmatch
from typing import Optional

from .config import GraphConfig
from .models import DependencyGraph, Node, Edge, FileRef
from .scanner import scan_theme
from .parsers import ParserRegistry, default_registry


def _find_entry_points(
    nodes: list,
    edges: list,
    config: GraphConfig,
) -> set:
    """Determine entry point node IDs using 3-stage fallback."""
    node_ids = {n.id for n in nodes}

    # 1. entry_patterns glob matching
    if config.entry_patterns:
        matched = set()
        for nid in node_ids:
            for pat in config.entry_patterns:
                if fnmatch(nid, pat):
                    matched.add(nid)
                    break
        if matched:
            return matched

    # 2. in-degree = 0
    targets = {e.target for e in edges}
    zero_in = {n.id for n in nodes if n.id not in targets}
    if zero_in:
        return zero_in

    # 3. max out-degree
    if nodes:
        max_node = max(nodes, key=lambda n: n.out_degree)
        return {max_node.id}

    return set()


def _compute_depth(
    nodes: list,
    edges: list,
    entry_ids: set,
) -> None:
    """Set depth on each node via BFS from entry points. Mutates nodes in place."""
    # Build adjacency list (source → targets)
    adj: dict = {}
    for e in edges:
        adj.setdefault(e.source, []).append(e.target)

    # BFS
    depth_map: dict = {}
    queue = deque()
    for eid in entry_ids:
        depth_map[eid] = 0
        queue.append(eid)

    while queue:
        current = queue.popleft()
        for neighbor in adj.get(current, []):
            if neighbor not in depth_map:
                depth_map[neighbor] = depth_map[current] + 1
                queue.append(neighbor)

    # Assign depths — unreachable nodes get max_depth + 1
    max_depth = max(depth_map.values()) if depth_map else 0
    for node in nodes:
        if node.id in depth_map:
            node.depth = depth_map[node.id]
        else:
            node.depth = max_depth + 1


def build_graph(
    project_dir: str,
    config: Optional[GraphConfig] = None,
    registry: Optional[ParserRegistry] = None,
) -> DependencyGraph:
    """Scan a project and build a complete dependency graph.

    Args:
        project_dir: path to the project root directory
        config: optional GraphConfig (uses defaults if None)
        registry: optional ParserRegistry (uses default parsers if None)

    Returns:
        A DependencyGraph with nodes and deduplicated edges.
    """
    if config is None:
        config = GraphConfig()
    if registry is None:
        registry = default_registry()

    project_dir = os.path.abspath(project_dir)
    file_sizes = {}
    all_refs = []

    # 1. Scan and parse
    for rel_path, abs_path in scan_theme(
        project_dir, config.scan_dirs, config.exclude_patterns, config.file_extensions,
    ):
        file_sizes[rel_path] = os.path.getsize(abs_path)
        with open(abs_path, encoding="utf-8", errors="replace") as f:
            content = f.read()
        refs = registry.parse_file(rel_path, content)

        # Apply exclude patterns to targets too
        for ref in refs:
            if not any(fnmatch(ref.target, pat) for pat in config.exclude_patterns):
                all_refs.append(ref)

    # 2. Collect all node IDs
    all_node_ids = set()
    for ref in all_refs:
        all_node_ids.add(ref.source)
        all_node_ids.add(ref.target)

    # 3. Compute degrees
    in_degree = defaultdict(int)
    out_degree = defaultdict(int)
    for ref in all_refs:
        out_degree[ref.source] += 1
        in_degree[ref.target] += 1

    # 4. Deduplicate edges
    seen_edges = set()
    edges = []
    for ref in all_refs:
        key = (ref.source, ref.target)
        if key not in seen_edges:
            seen_edges.add(key)
            edges.append(Edge(source=ref.source, target=ref.target, ref_type=ref.ref_type))

    # 5. Build nodes — strip known extensions for label
    strip_exts = (".liquid", ".json", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
    nodes = []
    for node_id in sorted(all_node_ids):
        cat = config.get_category(node_id)
        label = node_id.split("/")[-1]
        for ext in strip_exts:
            if label.endswith(ext):
                label = label[: -len(ext)]
                break
        degree = in_degree[node_id] + out_degree[node_id]
        radius = max(4.0, min(20.0, degree * 1.5))
        nodes.append(Node(
            id=node_id,
            label=label,
            category=cat,
            color=config.get_color(cat),
            file_size=file_sizes.get(node_id, 0),
            in_degree=in_degree[node_id],
            out_degree=out_degree[node_id],
            radius=radius,
        ))

    # 6. Compute depth from entry points
    entry_ids = _find_entry_points(nodes, edges, config)
    _compute_depth(nodes, edges, entry_ids)

    return DependencyGraph(nodes=nodes, edges=edges)
