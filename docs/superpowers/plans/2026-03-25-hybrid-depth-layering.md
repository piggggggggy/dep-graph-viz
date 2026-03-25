# Hybrid Depth Layering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace category-based node positioning with BFS depth-based layering, using auto-detected or user-specified entry points.

**Architecture:** Add `entry_patterns` to config/presets, compute BFS depth in `graph.py` after building nodes/edges, pass depth to the HTML template for x-coordinate positioning. 4-stage fallback: CLI `--entry` → preset `entry_patterns` → in-degree=0 → max out-degree.

**Tech Stack:** Python stdlib only (collections.deque for BFS, fnmatch for glob matching)

**Spec:** `docs/superpowers/specs/2026-03-25-hybrid-depth-layering-design.md`

---

### Task 1: Add `depth` field to Node model

**Files:**
- Modify: `models.py:19-35`
- Create: `tests/test_models.py`

- [ ] **Step 1: Create tests directory and test file**

```bash
mkdir -p tests
touch tests/__init__.py
```

- [ ] **Step 2: Write failing test for Node.depth and to_dict()**

```python
# tests/test_models.py
from dep_graph.models import Node

def test_node_depth_default():
    node = Node(id="a.js", label="a", category="component", color="#fff", file_size=100)
    assert node.depth == 0

def test_node_depth_in_to_dict():
    node = Node(id="a.js", label="a", category="component", color="#fff", file_size=100, depth=3)
    d = node.to_dict()
    assert d["depth"] == 3
    assert "depth" in d
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /Users/parkyong-tae/Dev/lib/dep_graph && python -m pytest tests/test_models.py -v`
Expected: FAIL — Node has no `depth` parameter

- [ ] **Step 4: Add depth field to Node and update to_dict()**

In `models.py`, add `depth: int = 0` after `radius` field, and add `"depth": self.depth` to `to_dict()`:

```python
# models.py Node dataclass — add field after radius
    radius: float = 4.0
    depth: int = 0

# models.py Node.to_dict() — add depth key
    def to_dict(self) -> dict:
        return {
            "id": self.id, "label": self.label, "category": self.category,
            "color": self.color, "size": self.file_size,
            "inDegree": self.in_degree, "outDegree": self.out_degree,
            "radius": self.radius, "depth": self.depth,
        }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /Users/parkyong-tae/Dev/lib/dep_graph && python -m pytest tests/test_models.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add models.py tests/
git commit -m "feat: add depth field to Node model"
```

---

### Task 2: Add `entry_patterns` to GraphConfig and presets

**Files:**
- Modify: `config.py:6-44`
- Modify: `presets.py:6-111`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_config.py
from dep_graph.config import GraphConfig
from dep_graph.presets import PRESETS

def test_config_entry_patterns_default_empty():
    config = GraphConfig()
    assert config.entry_patterns == []

def test_shopify_preset_has_entry_patterns():
    config = PRESETS["shopify"]()
    assert "templates/*.json" in config.entry_patterns
    assert "layout/theme.liquid" in config.entry_patterns

def test_nextjs_preset_has_entry_patterns():
    config = PRESETS["nextjs"]()
    assert any("layout" in p for p in config.entry_patterns)

def test_react_preset_has_entry_patterns():
    config = PRESETS["react"]()
    assert any("index" in p for p in config.entry_patterns)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/parkyong-tae/Dev/lib/dep_graph && python -m pytest tests/test_config.py -v`
Expected: FAIL — GraphConfig has no `entry_patterns`

- [ ] **Step 3: Add entry_patterns to GraphConfig**

In `config.py`, add after `exclude_patterns`:

```python
    # Glob patterns to identify entry point files
    entry_patterns: list = field(default_factory=list)
```

- [ ] **Step 4: Add entry_patterns to each preset**

In `presets.py`, add `entry_patterns` to each function:

shopify():
```python
        entry_patterns=["templates/*.json", "templates/*.liquid", "layout/theme.liquid"],
```

nextjs():
```python
        entry_patterns=[
            "app/layout.tsx", "app/layout.ts", "app/page.tsx", "app/page.ts",
            "pages/_app.tsx", "pages/_app.ts", "pages/index.tsx", "pages/index.ts",
            "src/app/layout.tsx", "src/app/page.tsx",
            "src/pages/_app.tsx", "src/pages/index.tsx",
        ],
```

react():
```python
        entry_patterns=[
            "src/index.tsx", "src/index.ts", "src/index.jsx", "src/index.js",
            "src/App.tsx", "src/App.ts", "src/App.jsx", "src/App.js",
        ],
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /Users/parkyong-tae/Dev/lib/dep_graph && python -m pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add config.py presets.py tests/test_config.py
git commit -m "feat: add entry_patterns to GraphConfig and presets"
```

---

### Task 3: Implement `_find_entry_points()` and `_compute_depth()`

**Files:**
- Modify: `graph.py`
- Create: `tests/test_graph_depth.py`

- [ ] **Step 1: Write failing tests for _find_entry_points()**

```python
# tests/test_graph_depth.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/parkyong-tae/Dev/lib/dep_graph && python -m pytest tests/test_graph_depth.py -v`
Expected: FAIL — `_find_entry_points` and `_compute_depth` not importable

- [ ] **Step 3: Implement _find_entry_points()**

Add to `graph.py` (before `build_graph`):

```python
from collections import deque
from fnmatch import fnmatch

def _find_entry_points(
    nodes: list[Node],
    edges: list[Edge],
    config: GraphConfig,
) -> set[str]:
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
```

- [ ] **Step 4: Implement _compute_depth()**

Add to `graph.py` (after `_find_entry_points`):

```python
def _compute_depth(
    nodes: list[Node],
    edges: list[Edge],
    entry_ids: set[str],
) -> None:
    """Set depth on each node via BFS from entry points. Mutates nodes in place."""
    # Build adjacency list (source → targets)
    adj: dict[str, list[str]] = {}
    for e in edges:
        adj.setdefault(e.source, []).append(e.target)

    # BFS
    depth_map: dict[str, int] = {}
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /Users/parkyong-tae/Dev/lib/dep_graph && python -m pytest tests/test_graph_depth.py -v`
Expected: PASS (all 7 tests)

- [ ] **Step 6: Commit**

```bash
git add graph.py tests/test_graph_depth.py
git commit -m "feat: implement BFS depth calculation with entry point detection"
```

---

### Task 4: Wire depth computation into build_graph()

**Files:**
- Modify: `graph.py:14-97` (build_graph function)

- [ ] **Step 1: Write integration test**

Add to `tests/test_graph_depth.py`:

```python
import os
import tempfile
from dep_graph.graph import build_graph
from dep_graph.config import GraphConfig

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/parkyong-tae/Dev/lib/dep_graph && python -m pytest tests/test_graph_depth.py::test_build_graph_computes_depth -v`
Expected: FAIL — depth not computed in build_graph yet

- [ ] **Step 3: Add depth computation call to build_graph()**

In `graph.py`, at the end of `build_graph()`, before `return DependencyGraph(...)`, add:

```python
    # 6. Compute depth from entry points
    entry_ids = _find_entry_points(nodes, edges, config)
    _compute_depth(nodes, edges, entry_ids)
```

- [ ] **Step 4: Run all tests**

Run: `cd /Users/parkyong-tae/Dev/lib/dep_graph && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add graph.py tests/test_graph_depth.py
git commit -m "feat: wire depth computation into build_graph"
```

---

### Task 5: Add `--entry` CLI option

**Files:**
- Modify: `cli.py:15-123`

- [ ] **Step 1: Write test**

Add to `tests/test_config.py`:

```python
def test_cli_entry_option_is_accepted(tmp_path):
    """--entry 옵션이 argparse에 등록되어 에러 없이 파싱되는지 확인."""
    from dep_graph.cli import main
    import os

    os.makedirs(tmp_path / "templates")
    (tmp_path / "templates" / "index.json").write_text('{}')

    # --entry 옵션이 인식되어야 함 (SystemExit(1)은 no-nodes, SystemExit(2)는 parse error)
    try:
        main([str(tmp_path), "--entry", "custom/*.liquid", "--no-open", "--json"])
    except SystemExit as e:
        assert e.code != 2, "--entry argument was not recognized by argparse"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/parkyong-tae/Dev/lib/dep_graph && python -m pytest tests/test_config.py::test_cli_entry_overrides_preset -v`
Expected: FAIL — unrecognized argument `--entry`

- [ ] **Step 3: Add --entry argument to CLI**

In `cli.py`, add after `--exclude` argument:

```python
    parser.add_argument(
        "--entry",
        nargs="+",
        default=None,
        help="Glob patterns for entry point files (overrides preset entry_patterns)",
    )
```

And in the CLI overrides section (after `config.hub_threshold = args.hub_threshold`):

```python
    if args.entry is not None:
        config.entry_patterns = args.entry
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/parkyong-tae/Dev/lib/dep_graph && python -m pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add cli.py tests/test_config.py
git commit -m "feat: add --entry CLI option for custom entry points"
```

---

### Task 6: Update HTML template for depth-based positioning

**Files:**
- Modify: `templates/graph.html:75-114`

- [ ] **Step 1: Replace catOrder-based x positioning with depth-based**

In `templates/graph.html`, replace the node initialization block (lines 75-83):

Old:
```js
  var catOrder = {template: 0, layout: 1, section: 2, snippet: 3, block: 4};

  nodes.forEach(function(n) {
    var layer = catOrder[n.category] !== undefined ? catOrder[n.category] : 2;
    n.x = W * 0.12 + layer * (W * 0.19) + (Math.random() - 0.5) * 120;
    n.y = H * 0.1 + Math.random() * H * 0.8;
    n.vx = 0; n.vy = 0;
    nodeMap[n.id] = n;
  });
```

New:
```js
  var maxDepth = 0;
  nodes.forEach(function(n) { if (n.depth > maxDepth) maxDepth = n.depth; });
  var depthSpacing = maxDepth > 0 ? (W * 0.76) / maxDepth : W * 0.76;

  nodes.forEach(function(n) {
    n.x = W * 0.12 + n.depth * depthSpacing + (Math.random() - 0.5) * 120;
    n.y = H * 0.1 + Math.random() * H * 0.8;
    n.vx = 0; n.vy = 0;
    nodeMap[n.id] = n;
  });
```

- [ ] **Step 2: Update force-directed category pull to depth pull**

In `templates/graph.html`, replace the category pull in the force loop (line 108):

Old:
```js
      var targetX = W * 0.12 + (catOrder[n.category] !== undefined ? catOrder[n.category] : 2) * (W * 0.19);
```

New:
```js
      var targetX = W * 0.12 + n.depth * depthSpacing;
```

- [ ] **Step 3: Verify by running the tool on a test project**

Run: `cd /Users/parkyong-tae/Dev/lib/dep_graph && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add templates/graph.html
git commit -m "feat: use BFS depth for node x-coordinate positioning"
```

---

### Task 7: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update CLI options table**

Add `--entry` row to the CLI options table.

- [ ] **Step 2: Update visualization section**

Replace category-based layer description with depth-based description. Mention 3-stage entry point fallback.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: update README with --entry option and depth-based layering"
```
