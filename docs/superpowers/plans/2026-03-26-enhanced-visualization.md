# Enhanced Visualization & Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add interactive filtering (depth slider, focus mode), a side analysis panel (stats/unused/cycles tabs), and cycle detection to the dep-graph visualizer.

**Architecture:** Backend adds `entry_points` field + `find_cycles()`/`unused_files()` methods to `DependencyGraph`, renderer injects new JSON data into the template. Frontend handles all interactive features (depth filtering, focus mode, panel rendering, panel-graph interaction) in vanilla JS within the existing single-file HTML output.

**Tech Stack:** Python 3.9+ (backend), Vanilla JavaScript + SVG (frontend), `string.Template` substitution (renderer)

**Security note:** The graph.html template renders data that originates from the user's own local filesystem (file paths, categories). All dynamic content inserted into the DOM should use safe DOM construction methods (createElement, textContent, createTextNode) rather than innerHTML with string concatenation, to follow security best practices. Where innerHTML is used for complex layouts, all values come from the tool's own computed data (node IDs, categories, numeric counts) — never from external/untrusted user input.

---

### Task 1: Add `entry_points` field to DependencyGraph and wire it through `build_graph()`

**Context:** Currently `_find_entry_points()` in `graph.py` computes entry point IDs but discards them after passing to `_compute_depth()`. The renderer needs access to entry points for the Unused tab. We add an `entry_points` field to `DependencyGraph` and store the computed IDs there.

**Files:**
- Modify: `dep_graph/models.py:50-53`
- Modify: `dep_graph/graph.py:164-168`
- Test: `tests/test_models.py`
- Test: `tests/test_graph_depth.py`

- [ ] **Step 1: Write failing test for `entry_points` field**

```python
# tests/test_models.py — append at end of file

def test_dependency_graph_entry_points_default():
    from dep_graph.models import DependencyGraph
    g = DependencyGraph()
    assert g.entry_points == []

def test_dependency_graph_entry_points_set():
    from dep_graph.models import DependencyGraph
    g = DependencyGraph(entry_points=["a.js", "b.js"])
    assert g.entry_points == ["a.js", "b.js"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_models.py::test_dependency_graph_entry_points_default -v`
Expected: FAIL — `TypeError: DependencyGraph.__init__() got an unexpected keyword argument 'entry_points'` or similar

- [ ] **Step 3: Add `entry_points` field to `DependencyGraph`**

In `dep_graph/models.py`, add a new field to the `DependencyGraph` dataclass after `edges`:

```python
@dataclass
class DependencyGraph:
    """The complete graph, ready for serialization or rendering."""
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_models.py -v`
Expected: ALL PASS

- [ ] **Step 5: Write failing test for `build_graph` storing entry_points**

```python
# tests/test_graph_depth.py — append at end of file

def test_build_graph_stores_entry_points():
    """build_graph()가 entry_points를 DependencyGraph에 저장하는지 확인."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "templates"))
        os.makedirs(os.path.join(tmpdir, "sections"))

        with open(os.path.join(tmpdir, "templates", "index.json"), "w") as f:
            f.write('{"sections":{"main":{"type":"header"}}}')
        with open(os.path.join(tmpdir, "sections", "header.liquid"), "w") as f:
            f.write("")

        config = GraphConfig(
            scan_dirs=["templates", "sections"],
            entry_patterns=["templates/*.json"],
        )
        graph = build_graph(tmpdir, config)
        assert "templates/index.json" in graph.entry_points
```

- [ ] **Step 6: Run test to verify it fails**

Run: `python -m pytest tests/test_graph_depth.py::test_build_graph_stores_entry_points -v`
Expected: FAIL — `assert 'templates/index.json' in []`

- [ ] **Step 7: Wire `entry_ids` into `DependencyGraph` in `build_graph()`**

In `dep_graph/graph.py`, change the return statement (line 168) from:

```python
    return DependencyGraph(nodes=nodes, edges=edges)
```

to:

```python
    return DependencyGraph(nodes=nodes, edges=edges, entry_points=sorted(entry_ids))
```

- [ ] **Step 8: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 9: Commit**

```bash
git add dep_graph/models.py dep_graph/graph.py tests/test_models.py tests/test_graph_depth.py
git commit -m "feat: add entry_points field to DependencyGraph"
```

---

### Task 2: Add `find_cycles()` method to DependencyGraph

**Context:** The Cycles tab needs a list of circular dependencies. We implement DFS-based cycle detection on `DependencyGraph`. The algorithm: build adjacency list from `self.edges`, track visit state (unvisited/in-stack/done), extract cycles on back-edges, handle self-loops, normalize cycles by rotating to lexicographically smallest ID for deduplication.

**Files:**
- Modify: `dep_graph/models.py:50-72`
- Create: `tests/test_cycles.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cycles.py

from dep_graph.models import Node, Edge, DependencyGraph


def _make_graph(node_ids, edge_pairs):
    """Helper: create DependencyGraph from node IDs and (source, target) pairs."""
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
    """Cycles are normalized: rotated so lexicographically smallest ID is first."""
    g = _make_graph(["x", "a", "m"], [("x", "a"), ("a", "m"), ("m", "x")])
    cycles = g.find_cycles()
    assert len(cycles) == 1
    assert cycles[0][0] == "a"  # 'a' is lexicographically smallest


def test_overlapping_cycles():
    """Overlapping cycles sharing an edge should all be detected."""
    g = _make_graph(
        ["a", "b", "c", "d"],
        [("a", "b"), ("b", "c"), ("c", "a"), ("b", "d"), ("d", "a")],
    )
    cycles = g.find_cycles()
    assert len(cycles) == 2
    cycle_sets = [set(c) for c in cycles]
    assert {"a", "b", "c"} in cycle_sets
    assert {"a", "b", "d"} in cycle_sets
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_cycles.py -v`
Expected: FAIL — `AttributeError: 'DependencyGraph' object has no attribute 'find_cycles'`

- [ ] **Step 3: Implement `find_cycles()`**

Add this method to `DependencyGraph` in `dep_graph/models.py`, after `filter_by_category()`:

```python
    def find_cycles(self) -> list[list[str]]:
        """Detect all unique cycles using DFS with back-edge detection.

        Returns list of cycles, each an ordered list of node IDs
        normalized so the lexicographically smallest ID is first.
        """
        adj: dict[str, list[str]] = {}
        for e in self.edges:
            adj.setdefault(e.source, []).append(e.target)

        raw_cycles: list[list[str]] = []
        for e in self.edges:
            if e.source == e.target:
                raw_cycles.append([e.source])

        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {n.id: WHITE for n in self.nodes}
        path: list[str] = []

        def dfs(u: str) -> None:
            color[u] = GRAY
            path.append(u)
            for v in adj.get(u, []):
                if v == u:
                    continue
                if color[v] == GRAY:
                    idx = path.index(v)
                    raw_cycles.append(path[idx:])
                elif color[v] == WHITE:
                    dfs(v)
            path.pop()
            color[u] = BLACK

        for n in self.nodes:
            if color[n.id] == WHITE:
                dfs(n.id)

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_cycles.py -v`
Expected: ALL PASS

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add dep_graph/models.py tests/test_cycles.py
git commit -m "feat: add cycle detection to DependencyGraph"
```

---

### Task 3: Add `unused_files()` method to DependencyGraph

**Context:** The Unused tab needs a list of files that are not referenced by anything and are not entry points. Definition: `in_degree == 0 AND id not in self.entry_points`.

**Files:**
- Modify: `dep_graph/models.py`
- Create: `tests/test_unused.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_unused.py

from dep_graph.models import Node, Edge, DependencyGraph


def _node(nid, in_deg=0, out_deg=0):
    return Node(
        id=nid, label=nid, category="other", color="#fff",
        file_size=0, in_degree=in_deg, out_degree=out_deg,
    )


def test_unused_basic():
    """in_degree=0이고 entry point가 아닌 노드만 반환."""
    g = DependencyGraph(
        nodes=[_node("entry", out_deg=2), _node("used", in_deg=1), _node("orphan")],
        edges=[Edge(source="entry", target="used", ref_type="import")],
        entry_points=["entry"],
    )
    unused = g.unused_files()
    assert len(unused) == 1
    assert unused[0].id == "orphan"


def test_unused_excludes_entry_points():
    """in_degree=0이지만 entry point인 노드는 제외."""
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
    """모든 노드가 참조되거나 entry point이면 빈 리스트."""
    g = DependencyGraph(
        nodes=[_node("a", out_deg=1), _node("b", in_deg=1)],
        edges=[Edge(source="a", target="b", ref_type="import")],
        entry_points=["a"],
    )
    assert g.unused_files() == []


def test_unused_uses_self_entry_points():
    """unused_files()는 self.entry_points를 사용, 매개변수 없음."""
    g = DependencyGraph(
        nodes=[_node("a"), _node("b")],
        entry_points=["a"],
    )
    unused = g.unused_files()
    assert len(unused) == 1
    assert unused[0].id == "b"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_unused.py -v`
Expected: FAIL — `AttributeError: 'DependencyGraph' object has no attribute 'unused_files'`

- [ ] **Step 3: Implement `unused_files()`**

Add this method to `DependencyGraph` in `dep_graph/models.py`, after `find_cycles()`:

```python
    def unused_files(self) -> list["Node"]:
        """Return nodes with in_degree == 0 that are not entry points."""
        entry_set = set(self.entry_points)
        return [
            n for n in self.nodes
            if n.in_degree == 0 and n.id not in entry_set
        ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_unused.py -v`
Expected: ALL PASS

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add dep_graph/models.py tests/test_unused.py
git commit -m "feat: add unused_files() method to DependencyGraph"
```

---

### Task 4: Inject `$CYCLES_JSON` and `$ENTRY_POINTS_JSON` in renderer

**Context:** The renderer needs to inject two new template variables so the frontend can use them: `$CYCLES_JSON` (list of cycles) and `$ENTRY_POINTS_JSON` (list of entry point IDs). Also remove the old `.stats` div from the top-right (it will be replaced by the Stats tab in the side panel).

**Files:**
- Modify: `dep_graph/renderer.py:57-74`
- Modify: `dep_graph/templates/graph.html:44-47` (remove old `.stats` div)
- Modify: `dep_graph/templates/graph.html:54-56` (add new JS variables)

- [ ] **Step 1: Add template variables to `render_html()`**

In `dep_graph/renderer.py`, modify the `safe_substitute()` call to add two new variables:

```python
    return tmpl.safe_substitute(
        TITLE=config.title,
        NODES_JSON=json.dumps(data["nodes"]),
        EDGES_JSON=json.dumps(data["edges"]),
        CYCLES_JSON=json.dumps(graph.find_cycles()),
        ENTRY_POINTS_JSON=json.dumps(graph.entry_points),
        HUB_THRESHOLD=str(config.hub_threshold),
        LAYOUT_ITERATIONS=str(config.layout_iterations),
        LEGEND_ITEMS=_build_legend(config),
        CATEGORY_OPTIONS=_build_category_options(graph),
        STATS_ITEMS=_build_stats(graph),
    )
```

- [ ] **Step 2: Add JS variables in `graph.html` template**

In `dep_graph/templates/graph.html`, after line 56 (`var LAYOUT_ITERATIONS = $LAYOUT_ITERATIONS;`), add:

```javascript
  var CYCLES = $CYCLES_JSON;
  var ENTRY_POINTS = $ENTRY_POINTS_JSON;
```

- [ ] **Step 3: Remove old `.stats` div from template**

In `dep_graph/templates/graph.html`, remove lines 44-47 (the old stats section):

```html
<div class="stats">
  <h3>$TITLE</h3>
  $STATS_ITEMS
</div>
```

Also remove the `.stats` CSS class definition from the `<style>` section (lines 17-18):

```css
.stats { position: fixed; top: 16px; right: 16px; ... }
.stats h3 { margin-bottom: 6px; color: #e94560; }
```

- [ ] **Step 4: Run all tests to verify nothing breaks**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add dep_graph/renderer.py dep_graph/templates/graph.html
git commit -m "feat: inject cycles and entry_points data into template"
```

---

### Task 5: Add side panel layout and Stats tab to template

**Context:** The HTML template currently uses a full-viewport SVG. We need to add a collapsible side panel (280px) on the right with 3 tabs. The SVG area adjusts width. The Stats tab is computed entirely from frontend data (nodes/edges arrays). Also adjust the `W` variable to account for panel width, and handle panel toggle by scaling node positions proportionally.

This is the largest task — it modifies `graph.html` extensively. The key structural changes:
1. Wrap the `<svg>` and panel in a flex container
2. Add panel HTML with tabs
3. Adjust `W = window.innerWidth - panelWidth` in JS
4. Add Stats tab rendering logic (summary cards, hotspot list, category breakdown)
5. Panel toggle button with position scaling

**Files:**
- Modify: `dep_graph/templates/graph.html` — major rewrite of HTML structure and JS

- [ ] **Step 1: Restructure HTML layout**

Replace the `<body>` content structure. The new layout wraps everything in a flex container:

```html
<body>
<div id="app" style="display:flex;width:100vw;height:100vh;overflow:hidden;">
  <div id="graphArea" style="flex:1;position:relative;overflow:hidden;">
    <svg id="graph" style="width:100%;height:100%;"></svg>

    <div class="controls">
      <button id="btnReset">Reset View</button>
      <select id="filterCategory">
        <option value="all">All Categories</option>
        $CATEGORY_OPTIONS
      </select>
      <button id="btnOrphans">Show Orphans</button>
      <button id="btnHubs">Show Hubs ($HUB_THRESHOLD+)</button>
      <button id="btnFocus" class="toggle-btn">Focus Mode</button>
      <div class="depth-controls">
        <label style="font-size:11px;color:#888;">Depth</label>
        <input type="range" id="depthMin" min="0" max="0" value="0" style="width:80px;">
        <span id="depthLabel" style="font-size:12px;color:#e94560;">0 ~ 0</span>
        <input type="range" id="depthMax" min="0" max="0" value="0" style="width:80px;">
      </div>
      <div class="focus-controls" id="focusControls" style="display:none;">
        <label style="font-size:11px;color:#888;">Steps</label>
        <input type="number" id="focusSteps" min="1" max="5" value="2" style="width:50px;padding:4px;border:1px solid #444;border-radius:4px;background:#16213e;color:#eee;font-size:12px;">
      </div>
    </div>

    <div class="search"><input type="text" id="searchInput" placeholder="Search files..."></div>

    <div class="legend">
      $LEGEND_ITEMS
      <div style="margin-top:8px;font-size:11px;color:#888">Node size = connection count. Drag nodes, scroll to zoom.</div>
    </div>

    <div class="tooltip" id="tooltip"></div>
  </div>

  <!-- Side Panel -->
  <div id="sidePanel" class="side-panel">
    <div class="panel-toggle" id="panelToggle">&lsaquo;</div>
    <div class="panel-tabs">
      <div class="panel-tab active" data-tab="stats">Stats</div>
      <div class="panel-tab" data-tab="unused">Unused</div>
      <div class="panel-tab" data-tab="cycles">Cycles</div>
    </div>
    <div class="panel-content" id="panelContent"></div>
  </div>
</div>
```

- [ ] **Step 2: Add panel CSS**

Add these styles to the `<style>` section (replacing the removed `.stats` styles):

```css
.side-panel { width: 280px; background: #16213e; border-left: 1px solid #2a2a4a; display: flex; flex-direction: column; overflow: hidden; position: relative; transition: width 0.2s; }
.side-panel.collapsed { width: 0; }
.side-panel.collapsed .panel-tabs, .side-panel.collapsed .panel-content { display: none; }
.panel-toggle { position: absolute; left: -24px; top: 50%; transform: translateY(-50%); width: 24px; height: 48px; background: #16213e; border: 1px solid #2a2a4a; border-right: none; border-radius: 6px 0 0 6px; display: flex; align-items: center; justify-content: center; cursor: pointer; color: #888; font-size: 14px; z-index: 5; }
.panel-toggle:hover { background: #0f3460; color: #eee; }
.panel-tabs { display: flex; border-bottom: 1px solid #2a2a4a; flex-shrink: 0; }
.panel-tab { flex: 1; padding: 10px 8px; text-align: center; font-size: 11px; color: #888; cursor: pointer; }
.panel-tab.active { color: #e94560; border-bottom: 2px solid #e94560; background: #1a1a2e; }
.panel-content { flex: 1; overflow-y: auto; padding: 14px; }
.toggle-btn { transition: background 0.2s; }
.toggle-btn.active { background: #e94560 !important; border-color: #e94560 !important; }
.depth-controls { display: flex; align-items: center; gap: 4px; padding: 4px 8px; background: #16213e; border: 1px solid #444; border-radius: 6px; }
.depth-controls input[type="range"] { -webkit-appearance: none; height: 4px; background: #2a2a4a; border-radius: 2px; outline: none; }
.depth-controls input[type="range"]::-webkit-slider-thumb { -webkit-appearance: none; width: 12px; height: 12px; background: #e94560; border-radius: 50%; cursor: pointer; }
.focus-controls { display: flex; align-items: center; gap: 6px; padding: 4px 8px; background: #16213e; border: 1px solid #444; border-radius: 6px; }
.stat-card { background: #1a1a2e; border-radius: 6px; padding: 10px; text-align: center; }
.stat-value { font-size: 20px; font-weight: bold; }
.stat-label { font-size: 10px; color: #888; }
.hotspot-item, .unused-item, .cycle-item { background: #1a1a2e; border-radius: 4px; padding: 8px 10px; cursor: pointer; margin-bottom: 4px; }
.hotspot-item:hover, .unused-item:hover, .cycle-item:hover { background: #0f3460; }
.section-title { font-size: 10px; color: #666; text-transform: uppercase; margin-bottom: 8px; margin-top: 12px; }
.cat-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.cat-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.cat-bar-fill { height: 4px; background: #2a2a4a; border-radius: 2px; flex: 2; overflow: hidden; }
.badge { display: inline-block; font-size: 10px; background: #2a2a4a; border-radius: 10px; padding: 2px 8px; color: #888; }
.highlight-btn { display: inline-block; background: rgba(233,69,96,0.2); border: 1px solid #e94560; border-radius: 6px; padding: 8px 20px; font-size: 11px; color: #e94560; cursor: pointer; margin-top: 12px; }
.highlight-btn:hover { background: rgba(233,69,96,0.35); }
.chip { display: inline-block; border-radius: 12px; padding: 3px 10px; font-size: 10px; cursor: pointer; margin: 2px; }
.chip.active { background: #e94560; color: white; }
.chip:not(.active) { background: #2a2a4a; color: #aaa; }
```

- [ ] **Step 3: Update JS — adjust W for panel, add panel state variables**

In the JS section, update the initialization of `W` and add panel state. Replace:

```javascript
  var W = window.innerWidth, H = window.innerHeight;
```

with:

```javascript
  var panelWidth = 280;
  var panelOpen = true;
  var W = window.innerWidth - panelWidth, H = window.innerHeight;
```

- [ ] **Step 4: Add panel toggle logic**

Add this code after the existing controls section (after the search input event listener, before the closing `})();`):

```javascript
  // Panel toggle
  var panel = document.getElementById("sidePanel");
  var panelToggle = document.getElementById("panelToggle");
  panelToggle.addEventListener("click", function() {
    panelOpen = !panelOpen;
    panel.classList.toggle("collapsed", !panelOpen);
    panelToggle.textContent = panelOpen ? "\u2039" : "\u203a";
    var newW = panelOpen ? window.innerWidth - panelWidth : window.innerWidth;
    var ratio = newW / W;
    nodes.forEach(function(n) { n.x *= ratio; });
    W = newW;
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    nodeEls.forEach(function(c) {
      var nd = nodeMap[c.dataset.id];
      c.setAttribute("cx", nd.x);
    });
    edgeEls.forEach(function(l) {
      var src = nodeMap[l.dataset.source], tgt = nodeMap[l.dataset.target];
      if (src) l.setAttribute("x1", src.x);
      if (tgt) l.setAttribute("x2", tgt.x);
    });
    gLabels.querySelectorAll("text").forEach(function(t) {
      var nd = nodeMap[t.dataset.id];
      if (nd) t.setAttribute("x", nd.x);
    });
  });

  // Panel tabs
  var tabs = document.querySelectorAll(".panel-tab");
  var panelContent = document.getElementById("panelContent");
  var currentTab = "stats";
  tabs.forEach(function(tab) {
    tab.addEventListener("click", function() {
      tabs.forEach(function(t) { t.classList.remove("active"); });
      tab.classList.add("active");
      currentTab = tab.dataset.tab;
      renderPanel();
    });
  });
```

- [ ] **Step 5: Add Stats tab rendering function**

Add the `renderPanel()` function and Stats tab logic. The Stats tab uses safe DOM construction — all displayed values are computed numeric counts and node properties from the tool's own data:

```javascript
  function renderPanel() {
    if (currentTab === "stats") renderStats();
    else if (currentTab === "unused") renderUnused();
    else if (currentTab === "cycles") renderCycles();
  }

  function renderStats() {
    var totalNodes = nodes.length;
    var totalEdges = edges.length;
    var avgDeps = totalNodes > 0 ? (edges.length / totalNodes).toFixed(1) : "0";

    var container = document.createElement("div");

    // Summary cards
    var grid = document.createElement("div");
    grid.style.cssText = "display:grid;grid-template-columns:1fr 1fr;gap:8px;";
    var stats = [
      { value: totalNodes, label: "Files", color: "#e94560" },
      { value: totalEdges, label: "Edges", color: "#4ea8de" },
      { value: avgDeps, label: "Avg Deps", color: "#FF9800" },
      { value: maxDepth, label: "Max Depth", color: "#9C27B0" },
    ];
    stats.forEach(function(s) {
      var card = document.createElement("div");
      card.className = "stat-card";
      var val = document.createElement("div");
      val.className = "stat-value";
      val.style.color = s.color;
      val.textContent = s.value;
      var lbl = document.createElement("div");
      lbl.className = "stat-label";
      lbl.textContent = s.label;
      card.appendChild(val);
      card.appendChild(lbl);
      grid.appendChild(card);
    });
    container.appendChild(grid);

    // Hotspot title
    var hotTitle = document.createElement("div");
    hotTitle.className = "section-title";
    hotTitle.textContent = "Most Referenced (Top 5)";
    container.appendChild(hotTitle);

    // Hotspot list
    var sorted = nodes.slice().sort(function(a, b) { return b.inDegree - a.inDegree; });
    sorted.slice(0, 5).forEach(function(n) {
      var item = document.createElement("div");
      item.className = "hotspot-item";
      item.dataset.nodeId = n.id;
      var row = document.createElement("div");
      row.style.cssText = "display:flex;justify-content:space-between;align-items:center;";
      var name = document.createElement("span");
      name.style.cssText = "font-size:11px;color:#ccc;";
      name.textContent = n.id;
      var count = document.createElement("span");
      count.style.cssText = "font-size:11px;color:#e94560;font-weight:bold;";
      count.textContent = n.inDegree;
      row.appendChild(name);
      row.appendChild(count);
      item.appendChild(row);
      item.addEventListener("click", function() { activateFocus(n.id); });
      container.appendChild(item);
    });

    // Category title
    var catTitle = document.createElement("div");
    catTitle.className = "section-title";
    catTitle.textContent = "Categories";
    container.appendChild(catTitle);

    // Category breakdown
    var catCounts = {};
    var catColors = {};
    nodes.forEach(function(n) {
      catCounts[n.category] = (catCounts[n.category] || 0) + 1;
      catColors[n.category] = n.color;
    });
    var maxCount = Math.max.apply(null, Object.values(catCounts));
    Object.keys(catCounts).sort().forEach(function(cat) {
      var pct = (catCounts[cat] / maxCount * 100).toFixed(0);
      var bar = document.createElement("div");
      bar.className = "cat-bar";
      var dot = document.createElement("div");
      dot.className = "cat-dot";
      dot.style.background = catColors[cat];
      var label = document.createElement("span");
      label.style.cssText = "font-size:11px;color:#aaa;flex:1;";
      label.textContent = cat;
      var fill = document.createElement("div");
      fill.className = "cat-bar-fill";
      var inner = document.createElement("div");
      inner.style.cssText = "width:" + pct + "%;height:100%;background:" + catColors[cat] + ";border-radius:2px;";
      fill.appendChild(inner);
      var num = document.createElement("span");
      num.style.cssText = "font-size:10px;color:#888;";
      num.textContent = catCounts[cat];
      bar.appendChild(dot);
      bar.appendChild(label);
      bar.appendChild(fill);
      bar.appendChild(num);
      container.appendChild(bar);
    });

    panelContent.textContent = "";
    panelContent.appendChild(container);
  }
```

- [ ] **Step 6: Add placeholder functions for Unused and Cycles tabs**

These will be filled in subsequent tasks. Add stubs:

```javascript
  function renderUnused() {
    var placeholder = document.createElement("div");
    placeholder.style.cssText = "color:#888;text-align:center;padding:40px;";
    placeholder.textContent = "Unused tab — coming soon";
    panelContent.textContent = "";
    panelContent.appendChild(placeholder);
  }

  function renderCycles() {
    var placeholder = document.createElement("div");
    placeholder.style.cssText = "color:#888;text-align:center;padding:40px;";
    placeholder.textContent = "Cycles tab — coming soon";
    panelContent.textContent = "";
    panelContent.appendChild(placeholder);
  }

  function activateFocus(nodeId) {
    // Stub — implemented in Task 6
  }
```

- [ ] **Step 7: Call `renderPanel()` on load**

Add this at the end of the script (before the closing `})();`):

```javascript
  renderPanel();
```

- [ ] **Step 8: Manually test in browser**

Run dep-graph on any available project directory, open the HTML output, and verify:
1. Side panel is visible on the right with 3 tabs
2. Stats tab shows summary cards, hotspot list, and category breakdown
3. Panel toggle button collapses/expands the panel
4. SVG graph area adjusts when panel toggles
5. Unused/Cycles tabs show placeholder text

Run: `python -m pytest tests/ -v`
Expected: ALL PASS (no backend changes)

- [ ] **Step 9: Commit**

```bash
git add dep_graph/templates/graph.html
git commit -m "feat: add side panel layout with Stats tab"
```

---

### Task 6: Implement Focus Mode

**Context:** Focus Mode lets users click a node to see N-step dependencies in both directions. Upstream (files that depend on this node) shown in blue, downstream (files this node depends on) shown in orange. Opacity decreases per step. Toggle via button, deactivate with Escape or background click.

**Files:**
- Modify: `dep_graph/templates/graph.html` — JS section

- [ ] **Step 1: Implement `activateFocus()` function**

Replace the `activateFocus()` stub with the full implementation:

```javascript
  var focusModeEnabled = false;
  var focusedNodeId = null;

  // Build reverse adjacency for upstream traversal
  var adjDown = {};  // source -> [targets] (downstream)
  var adjUp = {};    // target -> [sources] (upstream)
  edges.forEach(function(e) {
    if (!adjDown[e.source]) adjDown[e.source] = [];
    adjDown[e.source].push(e.target);
    if (!adjUp[e.target]) adjUp[e.target] = [];
    adjUp[e.target].push(e.source);
  });

  function bfsSteps(startId, adj, maxSteps) {
    var visited = {};
    visited[startId] = 0;
    var queue = [startId];
    while (queue.length > 0) {
      var curr = queue.shift();
      var currStep = visited[curr];
      if (currStep >= maxSteps) continue;
      var neighbors = adj[curr] || [];
      for (var i = 0; i < neighbors.length; i++) {
        if (!(neighbors[i] in visited)) {
          visited[neighbors[i]] = currStep + 1;
          queue.push(neighbors[i]);
        }
      }
    }
    delete visited[startId];
    return visited;  // { nodeId: stepDistance }
  }

  function activateFocus(nodeId) {
    focusedNodeId = nodeId;
    var steps = parseInt(document.getElementById("focusSteps").value) || 2;
    var downstream = bfsSteps(nodeId, adjDown, steps);
    var upstream = bfsSteps(nodeId, adjUp, steps);

    var stepOpacity = [1, 0.9, 0.5, 0.3, 0.2, 0.15];

    nodeEls.forEach(function(c) {
      var nid = c.dataset.id;
      var nd = nodeMap[nid];
      if (nid === nodeId) {
        c.setAttribute("fill-opacity", "1");
        c.setAttribute("stroke", "#fff");
        c.setAttribute("stroke-width", "3");
        c.setAttribute("r", nd.radius * 1.3);
      } else if (nid in downstream) {
        var op = stepOpacity[downstream[nid]] || 0.15;
        c.setAttribute("fill-opacity", String(op));
        c.setAttribute("stroke", "#FF9800");
        c.setAttribute("stroke-width", "2");
        c.setAttribute("r", nd.radius);
      } else if (nid in upstream) {
        var op2 = stepOpacity[upstream[nid]] || 0.15;
        c.setAttribute("fill-opacity", String(op2));
        c.setAttribute("stroke", "#4ea8de");
        c.setAttribute("stroke-width", "2");
        c.setAttribute("r", nd.radius);
      } else {
        c.setAttribute("fill-opacity", "0.08");
        c.setAttribute("stroke", "#fff");
        c.setAttribute("stroke-width", "0.3");
        c.setAttribute("r", nd.radius);
      }
    });

    edgeEls.forEach(function(l) {
      var src = l.dataset.source, tgt = l.dataset.target;
      var isDown = (src === nodeId && tgt in downstream) || (src in downstream && tgt in downstream && downstream[tgt] === downstream[src] + 1);
      var isUp = (tgt === nodeId && src in upstream) || (tgt in upstream && src in upstream && upstream[src] === upstream[tgt] + 1);
      if (isDown) {
        var dStep = downstream[tgt] || 1;
        l.setAttribute("stroke", "#FF9800");
        l.setAttribute("stroke-width", dStep === 1 ? "2" : "1.2");
        l.setAttribute("stroke-opacity", String(stepOpacity[dStep] || 0.15));
      } else if (isUp) {
        var uStep = upstream[src] || 1;
        l.setAttribute("stroke", "#4ea8de");
        l.setAttribute("stroke-width", uStep === 1 ? "2" : "1.2");
        l.setAttribute("stroke-opacity", String(stepOpacity[uStep] || 0.15));
      } else {
        l.setAttribute("stroke", "#334");
        l.setAttribute("stroke-width", "0.5");
        l.setAttribute("stroke-opacity", "0.06");
      }
      l.setAttribute("stroke-dasharray", "");
    });
  }

  function deactivateFocus() {
    focusedNodeId = null;
    resetAll();
  }
```

- [ ] **Step 2: Wire Focus Mode toggle button and node clicks**

Add event listeners:

```javascript
  // Focus mode toggle
  var btnFocus = document.getElementById("btnFocus");
  var focusControls = document.getElementById("focusControls");
  btnFocus.addEventListener("click", function() {
    focusModeEnabled = !focusModeEnabled;
    btnFocus.classList.toggle("active", focusModeEnabled);
    focusControls.style.display = focusModeEnabled ? "flex" : "none";
    if (!focusModeEnabled) deactivateFocus();
  });

  // Escape to deactivate
  document.addEventListener("keydown", function(e) {
    if (e.key === "Escape") {
      if (focusedNodeId) deactivateFocus();
      if (focusModeEnabled) {
        focusModeEnabled = false;
        btnFocus.classList.remove("active");
        focusControls.style.display = "none";
      }
    }
  });

  // SVG background click to deactivate
  svg.addEventListener("click", function(e) {
    if (e.target === svg && focusedNodeId) deactivateFocus();
  });
```

- [ ] **Step 3: Add focus click handler to node circles**

In the existing node creation loop (where circles get mousedown for drag), add a click handler. Insert this after the drag `mouseup` listener, before the hover `mouseenter` listener:

```javascript
    // Focus mode click
    circle.addEventListener("click", function(e) {
      if (!focusModeEnabled) return;
      e.stopPropagation();
      activateFocus(n.id);
    });
```

- [ ] **Step 4: Add step depth change re-trigger**

```javascript
  document.getElementById("focusSteps").addEventListener("change", function() {
    if (focusedNodeId) activateFocus(focusedNodeId);
  });
```

- [ ] **Step 5: Manually test Focus Mode**

Open graph in browser, verify:
1. Focus Mode button toggles on/off (red highlight when active)
2. Clicking a node shows upstream (blue) and downstream (orange) connections
3. Step depth input changes how many levels are shown
4. Escape and background click deactivate focus
5. Opacity decreases for distant steps

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add dep_graph/templates/graph.html
git commit -m "feat: implement Focus Mode with upstream/downstream coloring"
```

---

### Task 7: Implement Depth Range Slider

**Context:** Two native range sliders (min/max) filter nodes by depth. Nodes outside the range fade to near-invisible. The sliders constrain each other (min <= max).

**Files:**
- Modify: `dep_graph/templates/graph.html` — JS section

- [ ] **Step 1: Initialize depth slider values**

After the `maxDepth` computation (line 76 area), add slider initialization:

```javascript
  var depthMinEl = document.getElementById("depthMin");
  var depthMaxEl = document.getElementById("depthMax");
  var depthLabelEl = document.getElementById("depthLabel");
  depthMinEl.max = maxDepth; depthMinEl.value = 0;
  depthMaxEl.max = maxDepth; depthMaxEl.value = maxDepth;
  depthLabelEl.textContent = "0 ~ " + maxDepth;
```

- [ ] **Step 2: Add depth filter function**

```javascript
  function applyDepthFilter() {
    var dMin = parseInt(depthMinEl.value);
    var dMax = parseInt(depthMaxEl.value);
    depthLabelEl.textContent = dMin + " ~ " + dMax;

    if (focusedNodeId) return;  // Don't override focus mode

    nodeEls.forEach(function(c) {
      var nd = nodeMap[c.dataset.id];
      var inRange = nd.depth >= dMin && nd.depth <= dMax;
      c.setAttribute("fill-opacity", inRange ? "0.85" : "0.08");
      c.setAttribute("stroke-width", inRange ? "0.5" : "0.3");
      c.style.pointerEvents = inRange ? "auto" : "none";
    });
    edgeEls.forEach(function(l) {
      var src = nodeMap[l.dataset.source], tgt = nodeMap[l.dataset.target];
      var srcIn = src && src.depth >= dMin && src.depth <= dMax;
      var tgtIn = tgt && tgt.depth >= dMin && tgt.depth <= dMax;
      l.setAttribute("stroke-opacity", (srcIn && tgtIn) ? "0.4" : "0.03");
    });
  }
```

- [ ] **Step 3: Wire slider events with mutual constraints**

```javascript
  depthMinEl.addEventListener("input", function() {
    if (parseInt(depthMinEl.value) > parseInt(depthMaxEl.value)) {
      depthMaxEl.value = depthMinEl.value;
    }
    applyDepthFilter();
  });
  depthMaxEl.addEventListener("input", function() {
    if (parseInt(depthMaxEl.value) < parseInt(depthMinEl.value)) {
      depthMinEl.value = depthMaxEl.value;
    }
    applyDepthFilter();
  });
```

- [ ] **Step 4: Update `resetAll()` to also reset depth sliders**

In the existing `resetAll()` function, add at the end:

```javascript
    depthMinEl.value = 0;
    depthMaxEl.value = maxDepth;
    depthLabelEl.textContent = "0 ~ " + maxDepth;
    nodeEls.forEach(function(c) { c.style.pointerEvents = "auto"; });
```

- [ ] **Step 5: Manually test depth slider**

Open graph, verify:
1. Sliders show correct range (0 to maxDepth)
2. Moving min slider fades nodes below that depth
3. Moving max slider fades nodes above that depth
4. Min can't exceed max and vice versa
5. Reset button restores full range

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add dep_graph/templates/graph.html
git commit -m "feat: add depth range slider for filtering by depth level"
```

---

### Task 8: Implement Unused tab in side panel

**Context:** The Unused tab shows files with `inDegree === 0` that are not entry points. Uses the `ENTRY_POINTS` array injected in Task 4. Features: summary badge, category filter chips, file list with click-to-focus.

**Files:**
- Modify: `dep_graph/templates/graph.html` — JS section (replace `renderUnused` stub)

- [ ] **Step 1: Implement `renderUnused()`**

Replace the stub with the full implementation using safe DOM construction:

```javascript
  function renderUnused() {
    var entrySet = {};
    ENTRY_POINTS.forEach(function(id) { entrySet[id] = true; });

    var unused = nodes.filter(function(n) {
      return n.inDegree === 0 && !entrySet[n.id];
    });

    var container = document.createElement("div");

    // Summary badge
    var badge = document.createElement("div");
    badge.style.cssText = "background:rgba(233,69,96,0.15);border:1px solid rgba(233,69,96,0.3);border-radius:8px;padding:12px;margin-bottom:14px;text-align:center;";
    var badgeNum = document.createElement("div");
    badgeNum.style.cssText = "font-size:28px;color:#e94560;font-weight:bold;";
    badgeNum.textContent = unused.length;
    var badgeLabel = document.createElement("div");
    badgeLabel.style.cssText = "font-size:11px;color:#888;";
    badgeLabel.textContent = "unused files detected";
    badge.appendChild(badgeNum);
    badge.appendChild(badgeLabel);
    container.appendChild(badge);

    // Category filter chips
    var catCounts = {};
    unused.forEach(function(n) { catCounts[n.category] = (catCounts[n.category] || 0) + 1; });
    var chipContainer = document.createElement("div");
    chipContainer.style.cssText = "margin-bottom:12px;display:flex;gap:6px;flex-wrap:wrap;";

    function makeChip(label, catFilter) {
      var chip = document.createElement("div");
      chip.className = "chip" + (catFilter === "all" ? " active" : "");
      chip.textContent = label;
      chip.addEventListener("click", function() {
        chipContainer.querySelectorAll(".chip").forEach(function(c) { c.classList.remove("active"); });
        chip.classList.add("active");
        listContainer.querySelectorAll(".unused-item").forEach(function(item) {
          item.style.display = (catFilter === "all" || item.dataset.cat === catFilter) ? "block" : "none";
        });
      });
      return chip;
    }

    chipContainer.appendChild(makeChip("All (" + unused.length + ")", "all"));
    Object.keys(catCounts).sort().forEach(function(cat) {
      chipContainer.appendChild(makeChip(cat + " (" + catCounts[cat] + ")", cat));
    });
    container.appendChild(chipContainer);

    // File list
    var listContainer = document.createElement("div");
    unused.forEach(function(n) {
      var item = document.createElement("div");
      item.className = "unused-item";
      item.dataset.nodeId = n.id;
      item.dataset.cat = n.category;
      var nameEl = document.createElement("div");
      nameEl.style.cssText = "font-size:11px;color:#ccc;";
      nameEl.textContent = n.id;
      var metaEl = document.createElement("div");
      metaEl.style.cssText = "font-size:10px;color:#666;margin-top:3px;";
      var sizeStr = n.size > 1024 ? (n.size / 1024).toFixed(1) + " KB" : n.size + " B";
      metaEl.textContent = n.category + " \u00B7 " + sizeStr + " \u00B7 out: " + n.outDegree;
      item.appendChild(nameEl);
      item.appendChild(metaEl);
      item.addEventListener("click", function() { activateFocus(n.id); });
      listContainer.appendChild(item);
    });
    container.appendChild(listContainer);

    // Highlight all button
    if (unused.length > 0) {
      var btnWrap = document.createElement("div");
      btnWrap.style.textAlign = "center";
      var btn = document.createElement("div");
      btn.className = "highlight-btn";
      btn.textContent = "Highlight All in Graph";
      btn.addEventListener("click", function() {
        var unusedIds = {};
        unused.forEach(function(n2) { unusedIds[n2.id] = true; });
        nodeEls.forEach(function(c) {
          var nid = c.dataset.id;
          if (unusedIds[nid]) {
            c.setAttribute("fill", "#e94560"); c.setAttribute("fill-opacity", "1");
            c.setAttribute("stroke", "#ff0"); c.setAttribute("stroke-width", "2");
          } else {
            c.setAttribute("fill", nodeMap[nid].color); c.setAttribute("fill-opacity", "0.15");
            c.setAttribute("stroke", "#fff"); c.setAttribute("stroke-width", "0.3");
          }
        });
        edgeEls.forEach(function(l) { l.setAttribute("stroke-opacity", "0.03"); });
      });
      btnWrap.appendChild(btn);
      container.appendChild(btnWrap);
    }

    panelContent.textContent = "";
    panelContent.appendChild(container);
  }
```

- [ ] **Step 2: Manually test Unused tab**

Open graph, verify:
1. Unused tab shows count of unused files
2. Category chips filter the list
3. Clicking a file activates focus mode on that node
4. "Highlight All" makes all unused files glow red

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add dep_graph/templates/graph.html
git commit -m "feat: implement Unused tab in side panel"
```

---

### Task 9: Implement Cycles tab in side panel

**Context:** The Cycles tab shows circular dependencies detected by the backend. Each cycle is displayed as a chain (A -> B -> C -> loop-back). Clicking a cycle highlights its edges as red dashed lines in the graph. Uses the `CYCLES` array injected in Task 4.

**Files:**
- Modify: `dep_graph/templates/graph.html` — JS section (replace `renderCycles` stub)

- [ ] **Step 1: Implement `renderCycles()`**

Replace the stub with the full implementation using safe DOM construction:

```javascript
  function renderCycles() {
    var container = document.createElement("div");

    // Summary badge
    var badge = document.createElement("div");
    badge.style.cssText = "background:rgba(233,69,96,0.15);border:1px solid rgba(233,69,96,0.3);border-radius:8px;padding:12px;margin-bottom:14px;text-align:center;";
    var badgeNum = document.createElement("div");
    badgeNum.style.cssText = "font-size:28px;color:#e94560;font-weight:bold;";
    badgeNum.textContent = CYCLES.length;
    var badgeLabel = document.createElement("div");
    badgeLabel.style.cssText = "font-size:11px;color:#888;";
    badgeLabel.textContent = "circular dependencies found";
    badge.appendChild(badgeNum);
    badge.appendChild(badgeLabel);
    container.appendChild(badge);

    if (CYCLES.length === 0) {
      var noIssue = document.createElement("div");
      noIssue.style.cssText = "color:#4CAF50;text-align:center;padding:20px;font-size:13px;";
      noIssue.textContent = "No circular dependencies detected!";
      container.appendChild(noIssue);
      panelContent.textContent = "";
      panelContent.appendChild(container);
      return;
    }

    // Cycle list
    CYCLES.forEach(function(cycle, idx) {
      var item = document.createElement("div");
      item.className = "cycle-item";

      // Header row
      var header = document.createElement("div");
      header.style.cssText = "display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;";
      var title = document.createElement("span");
      title.style.cssText = "font-size:11px;color:#e94560;font-weight:bold;";
      title.textContent = "Cycle #" + (idx + 1);
      var countBadge = document.createElement("span");
      countBadge.className = "badge";
      countBadge.textContent = cycle.length + " files";
      header.appendChild(title);
      header.appendChild(countBadge);
      item.appendChild(header);

      // Path chain
      var chain = document.createElement("div");
      chain.style.cssText = "display:flex;align-items:center;gap:6px;flex-wrap:wrap;";
      cycle.forEach(function(nodeId, i) {
        var label = (nodeMap[nodeId] || {}).label || nodeId.split("/").pop();
        var tag = document.createElement("span");
        tag.style.cssText = "font-size:10px;color:#ccc;background:#2a2a4a;border-radius:4px;padding:3px 8px;";
        tag.textContent = label;
        chain.appendChild(tag);
        if (i < cycle.length - 1) {
          var arrow = document.createElement("span");
          arrow.style.cssText = "font-size:10px;color:#e94560;";
          arrow.textContent = "\u2192";
          chain.appendChild(arrow);
        }
      });
      var loopBack = document.createElement("span");
      loopBack.style.cssText = "font-size:10px;color:#e94560;";
      loopBack.textContent = "\u21BA";
      chain.appendChild(loopBack);
      item.appendChild(chain);

      item.addEventListener("click", function() { highlightCycle(cycle); });
      container.appendChild(item);
    });

    // Highlight all button
    var btnWrap = document.createElement("div");
    btnWrap.style.textAlign = "center";
    var btn = document.createElement("div");
    btn.className = "highlight-btn";
    btn.textContent = "Highlight All Cycles";
    btn.addEventListener("click", highlightAllCycles);
    btnWrap.appendChild(btn);
    container.appendChild(btnWrap);

    panelContent.textContent = "";
    panelContent.appendChild(container);
  }

  function highlightCycle(cycle) {
    var cycleSet = {};
    cycle.forEach(function(id) { cycleSet[id] = true; });

    var cycleEdges = {};
    for (var i = 0; i < cycle.length; i++) {
      var src = cycle[i];
      var tgt = cycle[(i + 1) % cycle.length];
      cycleEdges[src + "|" + tgt] = true;
    }

    nodeEls.forEach(function(c) {
      var nid = c.dataset.id;
      if (cycleSet[nid]) {
        c.setAttribute("fill-opacity", "1");
        c.setAttribute("stroke", "#e94560");
        c.setAttribute("stroke-width", "2.5");
      } else {
        c.setAttribute("fill-opacity", "0.08");
        c.setAttribute("stroke", "#fff");
        c.setAttribute("stroke-width", "0.3");
      }
    });

    edgeEls.forEach(function(l) {
      var key = l.dataset.source + "|" + l.dataset.target;
      if (cycleEdges[key]) {
        l.setAttribute("stroke", "#e94560");
        l.setAttribute("stroke-width", "2.5");
        l.setAttribute("stroke-opacity", "1");
        l.setAttribute("stroke-dasharray", "6,3");
      } else {
        l.setAttribute("stroke", "#334");
        l.setAttribute("stroke-width", "0.5");
        l.setAttribute("stroke-opacity", "0.03");
        l.setAttribute("stroke-dasharray", "");
      }
    });
  }

  function highlightAllCycles() {
    var cycleNodes = {};
    var cycleEdges = {};
    CYCLES.forEach(function(cycle) {
      cycle.forEach(function(id) { cycleNodes[id] = true; });
      for (var i = 0; i < cycle.length; i++) {
        cycleEdges[cycle[i] + "|" + cycle[(i + 1) % cycle.length]] = true;
      }
    });

    nodeEls.forEach(function(c) {
      var nid = c.dataset.id;
      if (cycleNodes[nid]) {
        c.setAttribute("fill-opacity", "1");
        c.setAttribute("stroke", "#e94560");
        c.setAttribute("stroke-width", "2.5");
      } else {
        c.setAttribute("fill-opacity", "0.08");
        c.setAttribute("stroke", "#fff");
        c.setAttribute("stroke-width", "0.3");
      }
    });

    edgeEls.forEach(function(l) {
      var key = l.dataset.source + "|" + l.dataset.target;
      if (cycleEdges[key]) {
        l.setAttribute("stroke", "#e94560");
        l.setAttribute("stroke-width", "2.5");
        l.setAttribute("stroke-opacity", "1");
        l.setAttribute("stroke-dasharray", "6,3");
      } else {
        l.setAttribute("stroke", "#334");
        l.setAttribute("stroke-width", "0.5");
        l.setAttribute("stroke-opacity", "0.03");
        l.setAttribute("stroke-dasharray", "");
      }
    });
  }
```

- [ ] **Step 2: Update `resetAll()` to clear dasharray**

In `resetAll()`, update the edge reset line to also clear dasharray:

```javascript
    edgeEls.forEach(function(l) {
      l.setAttribute("stroke", "#334");
      l.setAttribute("stroke-opacity", "0.4");
      l.setAttribute("stroke-width", "0.5");
      l.setAttribute("stroke-dasharray", "");
    });
```

- [ ] **Step 3: Manually test Cycles tab**

Open graph, verify:
1. Cycles tab shows count (likely 0 for simple projects)
2. If cycles exist, clicking a cycle highlights its path with red dashed edges
3. "Highlight All Cycles" shows all cycle edges
4. Reset button clears cycle highlights

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add dep_graph/templates/graph.html
git commit -m "feat: implement Cycles tab in side panel"
```

---

### Task 10: Final integration and cleanup

**Context:** Remove dead code from the old `.stats` section, verify all features work together end-to-end.

**Files:**
- Modify: `dep_graph/renderer.py` — remove `_build_stats` helper
- Modify: `dep_graph/templates/graph.html` — minor cleanup if needed

- [ ] **Step 1: Remove `_build_stats` dead code**

After removing the `.stats` div in Task 5, the `$STATS_ITEMS` variable is no longer in the template. Remove the `_build_stats` function from `dep_graph/renderer.py` (lines 45-54) and remove the `STATS_ITEMS=_build_stats(graph)` line from `safe_substitute()`.

- [ ] **Step 2: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 3: Run dep-graph on a test project and verify all features work end-to-end**

Run: `cd <some-project-dir> && dep-graph . --title "Test"` (or `python -m dep_graph <project-dir>`)

Verify:
1. Graph renders with side panel
2. Stats tab shows correct numbers
3. Unused tab lists files with inDegree=0 (excluding entry points)
4. Cycles tab shows any detected cycles
5. Focus Mode works with upstream/downstream colors
6. Depth slider filters by depth
7. Panel toggle collapses/expands
8. Reset button clears all highlights
9. Search still works
10. Orphans/Hubs buttons still work

- [ ] **Step 4: Commit**

```bash
git add dep_graph/renderer.py dep_graph/templates/graph.html
git commit -m "refactor: clean up dead stats code, finalize integration"
```
