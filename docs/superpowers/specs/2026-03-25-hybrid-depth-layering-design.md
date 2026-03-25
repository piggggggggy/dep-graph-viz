# Hybrid Depth Layering Design

## Problem

현재 시각화는 카테고리 이름(`catOrder`)으로 노드의 x 좌표를 결정한다.
실제 의존 depth와 무관하게 배치되므로, 같은 카테고리 내 체인(snippet → snippet)이나
프리셋에 정의되지 않은 카테고리는 의미 있는 위치를 갖지 못한다.

또한 `catOrder`는 Shopify 카테고리만 정의되어 있어, Next.js/React 프리셋에서는
모든 노드가 fallback 값(레이어 2)에 몰리는 문제가 있다.

## Solution

Entry point 기반 BFS depth 계산 + 3단계 fallback으로 entry point 결정.

### Entry Point 결정 (우선순위)

1. `--entry` CLI 옵션 (glob 패턴, 복수 가능) — 프리셋 `entry_patterns`를 **대체**
2. 프리셋의 `entry_patterns` 필드
3. 자동 탐지: 그래프 내 in-degree = 0인 노드
4. **모든 fallback이 빈 결과일 때** (순환 의존만 있는 그래프): 전체 노드 중 out-degree가 가장 높은 노드를 entry로 선택

### Depth 계산

- Entry point = depth 0
- BFS로 `source → target` 방향(caller → callee)의 edge를 따라가며 depth 증가
- 여러 경로로 도달 가능한 노드는 **최소 depth** 사용
- Entry point에서 도달 불가능한 고립 노드는 `depth = max_depth + 1` (가장 오른쪽 레이어)

### 시각화 배치

- x 좌표: `왼쪽 여백 + depth * 간격` (왼→오: entry → leaf)
- y 좌표: 같은 depth 내에서 force-directed로 결정 (기존 방식 유지)

### 프리셋별 Entry Patterns

| 프리셋 | entry_patterns |
|--------|---------------|
| shopify | `["templates/*.json", "templates/*.liquid", "layout/theme.liquid"]` |
| nextjs | `["app/layout.tsx", "app/layout.ts", "app/page.tsx", "app/page.ts", "pages/_app.tsx", "pages/_app.ts", "pages/index.tsx", "pages/index.ts", "src/app/layout.tsx", "src/app/page.tsx", "src/pages/_app.tsx", "src/pages/index.tsx"]` |
| react | `["src/index.tsx", "src/index.ts", "src/index.jsx", "src/index.js", "src/App.tsx", "src/App.ts", "src/App.jsx", "src/App.js"]` |

## Changes

| File | Change |
|------|--------|
| `models.py` | `Node.depth: int = 0` 필드 추가, `to_dict()`에 `"depth"` 키 추가 |
| `config.py` | `entry_patterns: list = field(default_factory=list)` 필드 추가 |
| `presets.py` | 각 프리셋에 `entry_patterns` 값 추가 |
| `cli.py` | `--entry` 옵션 추가, 지정 시 `config.entry_patterns`를 대체 |
| `graph.py` | `_find_entry_points()` + `_compute_depth()` 함수 추가, `build_graph()`에서 호출하여 Node.depth 설정 |
| `templates/graph.html` | `catOrder` 기반 x좌표 → `node.depth` 기반 x좌표로 변경, force-directed의 category pull을 depth pull로 변경 |

## Data Flow

```
build_graph()
  1. scan + parse → all_refs (기존)
  2. build nodes + edges (기존)
  3. _find_entry_points(nodes, edges, config) → entry_node_ids
     - config.entry_patterns로 노드 ID에 대해 fnmatch glob 매칭
     - 매칭 없으면 in-degree=0 노드
     - 그래도 없으면 out-degree 최대 노드
  4. _compute_depth(nodes, edges, entry_node_ids)
     - BFS: source → target 방향으로 탐색
     - unreachable nodes → max_depth + 1
  5. Node.depth 설정, Node.to_dict()에 "depth" 포함
```

## Node.to_dict() Output

```json
{
  "id": "templates/index.json",
  "label": "index",
  "category": "template",
  "color": "#4CAF50",
  "size": 1234,
  "inDegree": 0,
  "outDegree": 5,
  "radius": 7.5,
  "depth": 0
}
```
