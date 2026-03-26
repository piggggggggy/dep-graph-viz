from dep_graph.models import Node, Edge, DependencyGraph


def _make_graph(node_ids, edge_pairs):
    nodes = [
        Node(id=nid, label=nid, category="other", color="#fff", file_size=0)
        for nid in node_ids
    ]
    edges = [Edge(source=s, target=t, ref_type="import") for s, t in edge_pairs]
    return DependencyGraph(nodes=nodes, edges=edges)


def test_no_cycles():
    g = _make_graph(["a", "b", "c"], [("a", "b"), ("b", "c")])
    assert g.find_cycles() == []


def test_self_loop():
    g = _make_graph(["a", "b"], [("a", "b"), ("b", "b")])
    cycles = g.find_cycles()
    assert [["b"]] == cycles


def test_two_node_cycle():
    g = _make_graph(["a", "b"], [("a", "b"), ("b", "a")])
    cycles = g.find_cycles()
    assert len(cycles) == 1
    assert set(cycles[0]) == {"a", "b"}


def test_three_node_cycle():
    g = _make_graph(["a", "b", "c"], [("a", "b"), ("b", "c"), ("c", "a")])
    cycles = g.find_cycles()
    assert len(cycles) == 1
    assert set(cycles[0]) == {"a", "b", "c"}


def test_multiple_cycles():
    g = _make_graph(
        ["a", "b", "c", "d"],
        [("a", "b"), ("b", "a"), ("c", "d"), ("d", "c")],
    )
    cycles = g.find_cycles()
    assert len(cycles) == 2


def test_cycle_normalized_order():
    g = _make_graph(["x", "a", "m"], [("x", "a"), ("a", "m"), ("m", "x")])
    cycles = g.find_cycles()
    assert len(cycles) == 1
    assert cycles[0][0] == "a"


def test_overlapping_cycles():
    g = _make_graph(
        ["a", "b", "c", "d"],
        [("a", "b"), ("b", "c"), ("c", "a"), ("b", "d"), ("d", "a")],
    )
    cycles = g.find_cycles()
    assert len(cycles) == 2
    cycle_sets = [set(c) for c in cycles]
    assert {"a", "b", "c"} in cycle_sets
    assert {"a", "b", "d"} in cycle_sets
