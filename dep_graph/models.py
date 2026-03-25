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
        )
