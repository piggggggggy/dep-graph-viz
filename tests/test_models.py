from dep_graph.models import Node

def test_node_depth_default():
    node = Node(id="a.js", label="a", category="component", color="#fff", file_size=100)
    assert node.depth == 0

def test_node_depth_in_to_dict():
    node = Node(id="a.js", label="a", category="component", color="#fff", file_size=100, depth=3)
    d = node.to_dict()
    assert d["depth"] == 3
    assert "depth" in d
