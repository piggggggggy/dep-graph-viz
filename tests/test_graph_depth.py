from dep_graph.graph import _find_entry_points, _compute_depth
from dep_graph.models import Node, Edge
from dep_graph.config import GraphConfig

def _make_nodes(*ids):
    nodes = []
    for nid in ids:
        nodes.append(Node(id=nid, label=nid, category="other", color="#fff", file_size=0))
    return nodes

def _make_edges(*pairs):
    return [Edge(source=s, target=t, ref_type="import") for s, t in pairs]


# --- _find_entry_points tests ---

def test_find_entry_by_patterns():
    """entry_patterns glob이 매칭되면 해당 노드를 반환."""
    nodes = _make_nodes("templates/index.json", "sections/header.liquid", "snippets/logo.liquid")
    edges = _make_edges(("templates/index.json", "sections/header.liquid"))
    config = GraphConfig(entry_patterns=["templates/*.json"])
    result = _find_entry_points(nodes, edges, config)
    assert result == {"templates/index.json"}

def test_find_entry_fallback_in_degree_zero():
    """entry_patterns가 비어있으면 in-degree=0 노드를 반환.
    _find_entry_points는 edges에서 in-degree를 직접 계산한다."""
    nodes = _make_nodes("a", "b", "c")
    edges = _make_edges(("a", "b"), ("b", "c"))  # a는 어디서도 target이 아님 → in-degree=0
    config = GraphConfig()  # entry_patterns = []
    result = _find_entry_points(nodes, edges, config)
    assert result == {"a"}

def test_find_entry_fallback_max_out_degree():
    """모든 노드가 in-degree > 0이면 out-degree 최대 노드를 반환."""
    nodes = _make_nodes("a", "b")
    nodes[0].in_degree = 1; nodes[0].out_degree = 2
    nodes[1].in_degree = 1; nodes[1].out_degree = 1
    edges = _make_edges(("a", "b"), ("b", "a"))
    config = GraphConfig()
    result = _find_entry_points(nodes, edges, config)
    assert result == {"a"}


# --- _compute_depth tests ---

def test_compute_depth_linear_chain():
    """A → B → C 체인에서 depth가 0, 1, 2."""
    nodes = _make_nodes("a", "b", "c")
    edges = _make_edges(("a", "b"), ("b", "c"))
    _compute_depth(nodes, edges, {"a"})
    depth_map = {n.id: n.depth for n in nodes}
    assert depth_map == {"a": 0, "b": 1, "c": 2}

def test_compute_depth_min_path():
    """여러 경로로 도달 가능하면 최소 depth."""
    nodes = _make_nodes("a", "b", "c")
    edges = _make_edges(("a", "b"), ("a", "c"), ("b", "c"))
    _compute_depth(nodes, edges, {"a"})
    depth_map = {n.id: n.depth for n in nodes}
    assert depth_map["c"] == 1  # a→c 직접 경로가 a→b→c보다 짧음

def test_compute_depth_unreachable_node():
    """도달 불가 노드는 max_depth + 1."""
    nodes = _make_nodes("a", "b", "orphan")
    edges = _make_edges(("a", "b"))
    _compute_depth(nodes, edges, {"a"})
    depth_map = {n.id: n.depth for n in nodes}
    assert depth_map["a"] == 0
    assert depth_map["b"] == 1
    assert depth_map["orphan"] == 2  # max_depth(1) + 1

def test_compute_depth_cycle():
    """순환이 있어도 BFS는 최초 도달 depth를 유지."""
    nodes = _make_nodes("a", "b", "c")
    edges = _make_edges(("a", "b"), ("b", "c"), ("c", "a"))
    _compute_depth(nodes, edges, {"a"})
    depth_map = {n.id: n.depth for n in nodes}
    assert depth_map == {"a": 0, "b": 1, "c": 2}


# --- Integration test ---

import os
import tempfile
from dep_graph.graph import build_graph

def test_build_graph_computes_depth():
    """build_graph()가 Node.depth를 올바르게 설정하는지 통합 테스트."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create Shopify-like structure
        os.makedirs(os.path.join(tmpdir, "templates"))
        os.makedirs(os.path.join(tmpdir, "sections"))
        os.makedirs(os.path.join(tmpdir, "snippets"))

        # templates/index.json → sections/header
        with open(os.path.join(tmpdir, "templates", "index.json"), "w") as f:
            f.write('{"sections":{"main":{"type":"header"}}}')

        # sections/header.liquid → snippets/logo
        with open(os.path.join(tmpdir, "sections", "header.liquid"), "w") as f:
            f.write("{% render 'logo' %}")

        with open(os.path.join(tmpdir, "snippets", "logo.liquid"), "w") as f:
            f.write("<svg>logo</svg>")

        config = GraphConfig(
            scan_dirs=["templates", "sections", "snippets"],
            entry_patterns=["templates/*.json"],
        )
        graph = build_graph(tmpdir, config)
        depth_map = {n.id: n.depth for n in graph.nodes}

        assert depth_map["templates/index.json"] == 0
        assert depth_map["sections/header.liquid"] == 1
        assert depth_map["snippets/logo.liquid"] == 2
