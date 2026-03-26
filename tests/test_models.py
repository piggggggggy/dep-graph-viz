from dep_graph.models import Node

def test_node_depth_default():
    node = Node(id="a.js", label="a", category="component", color="#fff", file_size=100)
    assert node.depth == 0

def test_node_depth_in_to_dict():
    node = Node(id="a.js", label="a", category="component", color="#fff", file_size=100, depth=3)
    d = node.to_dict()
    assert d["depth"] == 3
    assert "depth" in d


def test_dependency_graph_entry_points_default():
    from dep_graph.models import DependencyGraph
    g = DependencyGraph()
    assert g.entry_points == []

def test_dependency_graph_entry_points_set():
    from dep_graph.models import DependencyGraph
    g = DependencyGraph(entry_points=["a.js", "b.js"])
    assert g.entry_points == ["a.js", "b.js"]
