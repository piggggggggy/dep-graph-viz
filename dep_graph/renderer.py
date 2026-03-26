"""HTML renderer: injects graph data into the HTML template."""

import json
import os
from string import Template
from typing import Optional

from .config import GraphConfig
from .models import DependencyGraph


def _load_template() -> str:
    template_path = os.path.join(os.path.dirname(__file__), "templates", "graph.html")
    with open(template_path, encoding="utf-8") as f:
        return f.read()


def _build_legend(config: GraphConfig) -> str:
    labels = {
        "template": "Template (.json)",
        "layout": "Layout",
        "section": "Section",
        "snippet": "Snippet",
        "block": "Block",
    }
    items = []
    for cat, color in config.category_colors.items():
        if cat == "other":
            continue
        label = labels.get(cat, cat.capitalize())
        items.append(
            f'<div class="legend-item">'
            f'<div class="legend-dot" style="background:{color}"></div> {label}'
            f'</div>'
        )
    return "\n  ".join(items)


def _build_category_options(graph: DependencyGraph) -> str:
    cats = sorted({n.category for n in graph.nodes})
    return "\n    ".join(
        f'<option value="{c}">{c.capitalize()}s</option>' for c in cats
    )



def render_html(graph: DependencyGraph, config: Optional[GraphConfig] = None) -> str:
    """Render the DependencyGraph into a self-contained interactive HTML string."""
    if config is None:
        config = GraphConfig()

    data = graph.to_dict()
    tmpl = Template(_load_template())

    return tmpl.safe_substitute(
        TITLE=config.title,
        NODES_JSON=json.dumps(data["nodes"]),
        EDGES_JSON=json.dumps(data["edges"]),
        HUB_THRESHOLD=str(config.hub_threshold),
        LAYOUT_ITERATIONS=str(config.layout_iterations),
        LEGEND_ITEMS=_build_legend(config),
        CATEGORY_OPTIONS=_build_category_options(graph),

        CYCLES_JSON=json.dumps(graph.find_cycles()),
        ENTRY_POINTS_JSON=json.dumps(graph.entry_points),
    )


def render_json(graph: DependencyGraph) -> str:
    """Render the DependencyGraph as a JSON string (for piping to other tools)."""
    return json.dumps(graph.to_dict(), indent=2)
