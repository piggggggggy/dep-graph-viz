"""dep_graph - Interactive dependency graph for any project."""

from .config import GraphConfig
from .models import DependencyGraph, Node, Edge, FileRef
from .graph import build_graph
from .renderer import render_html, render_json
from .presets import PRESETS

__all__ = [
    "GraphConfig",
    "DependencyGraph",
    "Node",
    "Edge",
    "FileRef",
    "build_graph",
    "render_html",
    "render_json",
    "PRESETS",
]
