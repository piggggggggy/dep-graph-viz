from dep_graph.models import Node, Edge, DependencyGraph

def _node(nid, in_deg=0, out_deg=0):
    return Node(id=nid, label=nid, category="other", color="#fff", file_size=0, in_degree=in_deg, out_degree=out_deg)

def test_unused_basic():
    g = DependencyGraph(
        nodes=[_node("entry", out_deg=2), _node("used", in_deg=1), _node("orphan")],
        edges=[Edge(source="entry", target="used", ref_type="import")],
        entry_points=["entry"],
    )
    unused = g.unused_files()
    assert len(unused) == 1
    assert unused[0].id == "orphan"

def test_unused_excludes_entry_points():
    g = DependencyGraph(
        nodes=[_node("entry_a"), _node("entry_b"), _node("orphan")],
        edges=[],
        entry_points=["entry_a", "entry_b"],
    )
    unused = g.unused_files()
    ids = [n.id for n in unused]
    assert "entry_a" not in ids
    assert "entry_b" not in ids
    assert "orphan" in ids

def test_unused_none_when_all_referenced():
    g = DependencyGraph(
        nodes=[_node("a", out_deg=1), _node("b", in_deg=1)],
        edges=[Edge(source="a", target="b", ref_type="import")],
        entry_points=["a"],
    )
    assert g.unused_files() == []

def test_unused_uses_self_entry_points():
    g = DependencyGraph(
        nodes=[_node("a"), _node("b")],
        entry_points=["a"],
    )
    unused = g.unused_files()
    assert len(unused) == 1
    assert unused[0].id == "b"
