"""Data models for the dependency graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FileRef:
    """A single reference from one file to another."""
    source: str       # relative path, e.g. "sections/header.liquid"
    target: str       # relative path, e.g. "snippets/logo.liquid"
    ref_type: str     # "render", "include", "section", "layout"
    line_number: Optional[int] = None


@dataclass
class Node:
    id: str           # relative path (unique key)
    label: str        # display name (filename without extension)
    category: str     # "template", "layout", "section", "snippet", etc.
    color: str        # hex color
    file_size: int    # bytes, 0 if file not found on disk
    in_degree: int = 0
    out_degree: int = 0
    radius: float = 4.0
    depth: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id, "label": self.label, "category": self.category,
            "color": self.color, "size": self.file_size,
            "inDegree": self.in_degree, "outDegree": self.out_degree,
            "radius": self.radius, "depth": self.depth,
        }


@dataclass
class Edge:
    source: str
    target: str
    ref_type: str

    def to_dict(self) -> dict:
        return {"source": self.source, "target": self.target, "type": self.ref_type}


@dataclass
class DependencyGraph:
    """The complete graph, ready for serialization or rendering."""
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }

    def orphan_snippets(self) -> list[Node]:
        return [n for n in self.nodes if n.category == "snippet" and n.in_degree == 0]

    def hubs(self, threshold: int = 5) -> list[Node]:
        return [n for n in self.nodes if n.in_degree >= threshold]

    def filter_by_category(self, category: str) -> "DependencyGraph":
        ids = {n.id for n in self.nodes if n.category == category}
        return DependencyGraph(
            nodes=[n for n in self.nodes if n.id in ids],
            edges=[e for e in self.edges if e.source in ids or e.target in ids],
            entry_points=[ep for ep in self.entry_points if ep in ids],
        )

    def find_cycles(self) -> list[list[str]]:
        """Detect all unique cycles using iterative DFS with back-edge detection."""
        node_ids = {n.id for n in self.nodes}
        adj: dict[str, list[str]] = {}
        for e in self.edges:
            if e.source in node_ids and e.target in node_ids:
                adj.setdefault(e.source, []).append(e.target)

        raw_cycles: list[list[str]] = []
        for e in self.edges:
            if e.source == e.target and e.source in node_ids:
                raw_cycles.append([e.source])

        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {nid: WHITE for nid in node_ids}
        path: list[str] = []
        path_set: set[str] = set()

        for n in self.nodes:
            if color[n.id] != WHITE:
                continue
            stack: list[tuple[str, int]] = [(n.id, 0)]
            while stack:
                u, idx = stack[-1]
                if color[u] == WHITE:
                    color[u] = GRAY
                    path.append(u)
                    path_set.add(u)
                neighbors = adj.get(u, [])
                found_next = False
                while idx < len(neighbors):
                    v = neighbors[idx]
                    idx += 1
                    if v == u:
                        continue
                    if color[v] == GRAY and v in path_set:
                        cycle_start = path.index(v)
                        raw_cycles.append(path[cycle_start:])
                    elif color[v] == WHITE:
                        stack[-1] = (u, idx)
                        stack.append((v, 0))
                        found_next = True
                        break
                if not found_next:
                    stack.pop()
                    path.pop()
                    path_set.discard(u)
                    color[u] = BLACK

        seen: set[tuple[str, ...]] = set()
        result: list[list[str]] = []
        for cycle in raw_cycles:
            min_idx = cycle.index(min(cycle))
            normalized = cycle[min_idx:] + cycle[:min_idx]
            key = tuple(normalized)
            if key not in seen:
                seen.add(key)
                result.append(normalized)

        return sorted(result, key=lambda c: (len(c), c))

    def unused_files(self) -> list["Node"]:
        """Return nodes with in_degree == 0 that are not entry points."""
        entry_set = set(self.entry_points)
        return [
            n for n in self.nodes
            if n.in_degree == 0 and n.id not in entry_set
        ]
