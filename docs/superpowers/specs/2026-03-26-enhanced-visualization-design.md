# Enhanced Visualization & Analysis Design

## Goal

Improve dep-graph visualization to handle complex dependency graphs by adding interactive filtering, a side analysis panel, and circular dependency detection — all integrated into the existing HTML output.

## Problem

When a project has many files and dependencies, the current graph is visually overwhelming and hard to navigate. Users need ways to:
1. **Reduce noise** — show only relevant parts of the graph
2. **Trace dependencies** — explore what a specific file depends on and what depends on it
3. **Find issues** — detect unused files and circular dependencies
4. **Understand structure** — see summary statistics and hotspots at a glance

## Architecture

Three independent feature groups, all integrated into the existing single-file HTML output:

1. **Interactive Filtering** (frontend-only) — depth slider + focus mode
2. **Analysis Panel** (frontend + backend) — side panel with Stats/Unused/Cycles tabs
3. **Cycle Detection** (backend) — DFS-based circular dependency detection

The backend computes analysis data (cycles, unused files, stats) and injects it as JSON into the HTML template. The frontend renders the panel and handles all interactivity.

## Tech Stack

- Python (backend analysis logic)
- Vanilla JavaScript + SVG (frontend, no dependencies — same as current)
- HTML template with `string.Template` substitution (same as current)

---

## Feature 1: Interactive Filtering

### 1A. Depth Range Slider

**Purpose:** Show only nodes within a specific depth range, hiding deeper or shallower layers.

**UI:** Two native `<input type="range">` sliders (min/max) in the top control bar, displaying `min ~ max` values. Native range inputs avoid the complexity of a custom dual-handle widget while providing the same functionality.

**Behavior:**
- Slider range: `0` to `maxDepth` (computed from graph data)
- Min slider constrains max slider's minimum; max slider constrains min slider's maximum
- Nodes outside the selected range: `fill-opacity: 0.08`, non-interactive
- Edges where either endpoint is outside range: `stroke-opacity: 0.03`
- Nodes/edges inside range: normal opacity
- Default: full range (all nodes visible)

**Implementation:** Frontend-only. Reads `node.depth` (already available in data) and filters SVG elements by `data-id` lookup.

### 1B. Focus Mode

**Purpose:** Click a node to see only its N-step dependencies in both directions, with visual direction encoding.

**Activation:**
- Click any node while Focus Mode toggle is active, OR
- Click a node from the side panel (Unused/Cycles tab)

**Visual encoding:**
- **Focused node:** full opacity, white stroke (3px), slightly enlarged
- **Upstream nodes** (files that depend on focused node): blue edge (`#4ea8de`), blue ring on node
- **Downstream nodes** (files that focused node depends on): orange edge (`#FF9800`), orange ring on node
- **Step distance:** opacity decreases per step (step 1: 0.9, step 2: 0.5, step 3: 0.3)
- **Unrelated nodes:** `fill-opacity: 0.08`, edges `stroke-opacity: 0.06`

**Controls:**
- Step depth: number input (default: 2, range: 1-5)
- Deactivate: click background or press Escape

**Implementation:** Frontend-only. BFS traversal from clicked node in both edge directions, using the edges array already in the template data.

---

## Feature 2: Analysis Side Panel

### Layout

A collapsible side panel (280px width) on the right side of the graph area. Panel has 3 tabs: **Stats**, **Unused**, **Cycles**.

**SVG viewport handling:** The current template computes `W = window.innerWidth` for layout positioning. When the panel is open, `W` should be `window.innerWidth - 280`. On panel toggle, the force layout does NOT re-run — instead, all node positions are scaled proportionally to the new width (`node.x *= newW / oldW`), and the SVG viewBox is updated. This avoids expensive re-computation while maintaining spatial relationships.

**Toggle:** A small button on the panel edge to collapse/expand. When collapsed, the graph takes full width (positions scale back).

### 2A. Stats Tab

**Summary cards (2x2 grid):**
- Total files (node count)
- Total edges (edge count)
- Average dependencies (mean out_degree, 1 decimal)
- Max depth

**Hotspot list (Top 5 most referenced):**
- Sorted by `in_degree` descending
- Each row: file path + in_degree count
- Click → activates Focus Mode on that node

**Category breakdown:**
- Each category with color dot, name, horizontal bar (proportional), count
- Click → applies category filter (same as existing dropdown)

**Implementation:** Frontend-only. All data is already available in the nodes/edges JSON.

### 2B. Unused Tab

**Definition:** A file is "unused" if `in_degree === 0` AND it is NOT an entry point.

**Summary badge:** Count of unused files with explanation.

**Category filter chips:** Quick filter by category (e.g., "components (5)", "hooks (4)").

**File list:**
- Each item shows: file path, category, file size (KB), out_degree
- Click → pans graph to node, activates Focus Mode
- "Highlight All in Graph" button → all unused files glow red simultaneously

**Backend data needed:** List of entry point node IDs (already computed by `_find_entry_points()`). The frontend filters nodes where `inDegree === 0` and ID not in entry points set.

**Implementation:** Entry point IDs injected as new template variable `$ENTRY_POINTS_JSON`. Frontend computes unused list from nodes data + entry points.

### 2C. Cycles Tab

**Summary badge:** Count of circular dependencies.

**Cycle list:**
- Each cycle shows its path as a chain: `A → B → C → ↻`
- File count badge per cycle
- Click → highlights the cycle path in the graph:
  - Cycle edges: red (`#e94560`), dashed (`stroke-dasharray: 6,3`), `stroke-width: 2.5`
  - Cycle nodes: pulsing red ring
  - Other elements: faded
- "Highlight All Cycles" button → all cycle edges shown as dashed red

**Color distinction:** Cycle highlights use red (`#e94560`) to avoid confusion with Focus Mode's downstream orange (`#FF9800`).

**Backend data needed:** List of cycles, each cycle being an ordered list of node IDs.

**Implementation:** Backend detects cycles via DFS in `graph.py`, injects as `$CYCLES_JSON` template variable. Frontend renders the list and handles highlight interaction.

---

## Feature 3: Cycle Detection (Backend)

### Algorithm

Johnson's algorithm or simple DFS-based cycle detection on the directed graph.

For simplicity and given typical project sizes (<1000 nodes), use **DFS with back-edge detection**:

1. Build adjacency list from edges (source → targets)
2. Track visit state per node: unvisited / in-stack / done
3. When a back-edge is found (target is in-stack), extract the cycle path
4. Handle self-loops (`A → A`) as a special case — check if any edge has `source === target`
5. Collect all unique cycles (normalize by rotating to lexicographically smallest ID first to deduplicate)

### Data Model Changes

**`DependencyGraph` — new method:**
```python
def find_cycles(self) -> list[list[str]]:
    """Returns list of cycles. Each cycle is an ordered list of node IDs."""
```

**`DependencyGraph` — new method:**
```python
def unused_files(self) -> list[Node]:
    """Returns nodes with in_degree == 0 that are not in self.entry_points."""
```

### Renderer Changes

New template variables injected by `render_html()`:
- `$CYCLES_JSON` — `json.dumps(graph.find_cycles())`
- `$ENTRY_POINTS_JSON` — `json.dumps(graph.entry_points)`

**Data flow:** `build_graph()` stores entry_ids in `DependencyGraph.entry_points` → `render_html()` reads `graph.entry_points` and `graph.find_cycles()` → injects as template variables → frontend uses them for Unused and Cycles tabs.

**Stats:** Computed frontend-only from the existing nodes/edges JSON (no backend method needed — avoids duplicating data already in `$NODES_JSON`).

### Graph Builder Changes

`build_graph()` needs to return or store entry point IDs so the renderer can access them. Options:
- Add `entry_points: list[str]` field to `DependencyGraph`
- Or compute in renderer (call `_find_entry_points` again — not ideal, duplicate logic)

**Chosen approach:** Add `entry_points: list[str] = field(default_factory=list)` to `DependencyGraph`. Set it in `build_graph()` after computing entry points.

---

## File Changes Summary

### Backend (Python)
- **`dep_graph/models.py`** — Add `entry_points` field to `DependencyGraph`, add `find_cycles()`, `unused_files()` methods. Existing `orphan_snippets()` kept as-is (different semantics: snippet-specific vs. all categories). Existing top-right `.stats` section in template will be removed in favor of the new Stats tab.
- **`dep_graph/graph.py`** — Store entry_ids in DependencyGraph after computation
- **`dep_graph/renderer.py`** — Inject `$CYCLES_JSON`, `$ENTRY_POINTS_JSON` into template

### Frontend (HTML/JS)
- **`dep_graph/templates/graph.html`** — Major changes:
  - Layout: flex container with graph area + side panel
  - New controls: depth range slider, focus mode toggle, step depth input
  - Side panel: 3 tabs with content rendering
  - Focus mode logic: BFS traversal, upstream/downstream coloring
  - Depth filtering logic
  - Panel-graph interaction handlers
  - Cycle highlight rendering (dashed edges, pulsing nodes)

### Tests
- **`tests/test_cycles.py`** — Tests for `find_cycles()`: no cycles, simple 2-node cycle, 3-node cycle, multiple cycles, self-loops
- **`tests/test_unused.py`** — Tests for `unused_files()`: entry points excluded, in_degree > 0 excluded
- **`tests/test_unused.py`** — also tests that `unused_files()` uses `self.entry_points` (no parameter needed)

---

## Scope Boundaries

**In scope:**
- Depth range slider
- Focus mode with upstream/downstream visual distinction
- Side panel with Stats/Unused/Cycles tabs
- Cycle detection (DFS)
- Panel-graph click interaction
- Panel collapse/expand

**Out of scope (future):**
- Export unused file list to file
- CLI subcommands for analysis (e.g., `dep-graph analyze`)
- Cycle severity scoring
- Auto-fix suggestions for cycles
- Persistence of panel state across sessions
