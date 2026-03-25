# dep-graph

프로젝트의 파일 간 의존성을 분석하고 인터랙티브 그래프로 시각화하는 CLI 도구.

- **Zero dependency** — Python 3.10+ 표준 라이브러리만 사용
- **Self-contained output** — 생성된 HTML 파일 하나로 완결 (외부 CDN 없음)
- **Preset auto-detection** — 프로젝트 타입을 자동 감지하여 적절한 파서/설정 적용

## Quick Start

```bash
# 프로젝트 디렉토리를 인자로 전달 (프리셋 자동 감지)
PYTHONPATH=/path/to/dep-graph/parent python3 -m dep_graph /path/to/project

# 브라우저에서 인터랙티브 그래프가 자동으로 열림
```

## 지원 프로젝트 타입

| 프리셋 | 자동 감지 기준 | 파싱 대상 |
|--------|---------------|----------|
| `shopify` | `layout/theme.liquid` 또는 `config/settings_schema.json` 존재 | Liquid `render`/`include`/`section` 태그, JSON template의 `layout`/`sections` 참조 |
| `nextjs` | `next.config.js`/`.mjs`/`.ts` 존재 | ES `import`/`export from`, `require()`, dynamic `import()`, `@/`·`~/` alias |
| `react` | `package.json`의 dependencies에 `react` 포함 | 동일 (alias 포함) |

## CLI 옵션

```bash
python3 -m dep_graph <project_dir> [options]
```

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `project_dir` | *(필수)* | 프로젝트 루트 경로 |
| `-o`, `--output` | `dependency-graph.html` | 출력 파일 경로 |
| `-p`, `--preset` | 자동 감지 | `shopify` / `nextjs` / `react` |
| `--title` | 프리셋 기본값 | 그래프 제목 |
| `--exclude` | 프리셋 기본값 | 제외할 fnmatch 패턴 (복수 가능) |
| `--entry` | 프리셋 기본값 | Entry point glob 패턴 (프리셋 값 대체, 복수 가능) |
| `--hub-threshold` | `5` | 허브 노드로 간주할 최소 in-degree |
| `--no-open` | — | 브라우저 자동 열기 비활성화 |
| `--json` | — | HTML 대신 JSON으로 출력 |

### 사용 예시

```bash
# 프리셋 명시
python3 -m dep_graph ./my-shop --preset shopify

# JSON으로 출력 (다른 도구에 파이프)
python3 -m dep_graph ./my-app --json --no-open -o deps.json

# 특정 패턴 제외 + 허브 기준 변경
python3 -m dep_graph ./my-app --exclude "*/test/*" "*/*.spec.*" --hub-threshold 3
```

## 라이브러리 API

CLI 외에 Python 코드에서 직접 사용할 수 있습니다.

```python
from dep_graph import build_graph, render_html, render_json, GraphConfig, PRESETS

# 프리셋으로 그래프 생성
config = PRESETS["nextjs"]()
graph = build_graph("/path/to/nextjs-app", config)

# 그래프 분석
print(f"노드: {len(graph.nodes)}, 엣지: {len(graph.edges)}")
print(f"허브: {[n.label for n in graph.hubs(threshold=5)]}")
print(f"미참조 스니펫: {[n.label for n in graph.orphan_snippets()]}")

# 카테고리 필터링
components_only = graph.filter_by_category("component")

# HTML / JSON 렌더링
html = render_html(graph, config)
json_str = render_json(graph)
```

### Public API

| 모듈 | 내보내기 | 설명 |
|------|---------|------|
| `dep_graph` | `GraphConfig` | 스캔 디렉토리, 확장자, 카테고리 규칙, 색상 등 설정 |
| | `DependencyGraph` | 노드/엣지 컨테이너. `to_dict()`, `hubs()`, `orphan_snippets()`, `filter_by_category()` |
| | `Node`, `Edge`, `FileRef` | 그래프 구성 데이터클래스 |
| | `build_graph(dir, config, registry)` | 프로젝트 스캔 → `DependencyGraph` 반환 |
| | `render_html(graph, config)` | 인터랙티브 HTML 문자열 반환 |
| | `render_json(graph)` | JSON 문자열 반환 |
| | `PRESETS` | `{"shopify": fn, "nextjs": fn, "react": fn}` 딕셔너리 |

## 시각화 기능

생성된 HTML은 SVG 기반 force-directed 그래프입니다.

- **드래그** — 노드를 끌어서 위치 이동
- **스크롤** — 줌 인/아웃
- **호버** — 의존 관계 엣지 하이라이트 + 상세 정보 툴팁 (카테고리, 파일 크기, in/out degree, 의존 목록)
- **검색** — 상단 검색창으로 파일명 필터링
- **카테고리 필터** — 드롭다운으로 특정 카테고리만 표시
- **Show Orphans** — 어디서도 참조되지 않는 snippet 강조 (빨간색)
- **Show Hubs** — in-degree가 임계값 이상인 핵심 파일 강조 (빨간색)

노드는 의존 depth 기반으로 왼→오 방향으로 자동 배치됩니다:

- Entry point (depth 0)가 왼쪽, leaf 파일이 오른쪽
- Entry point 결정: `--entry` 옵션 → 프리셋 `entry_patterns` → in-degree=0 자동 탐지
- 도달 불가 노드는 가장 오른쪽에 배치

## 아키텍처

```
project_dir (입력)
    │
    ▼
scanner.py ─────── 파일 탐색 (scan_dirs + 확장자 + exclude 필터)
    │
    ▼
parsers/ ──────── 파일 내용 파싱 → FileRef[] 반환
    │                ├─ liquid.py        render/include/section 태그
    │                ├─ json_template.py  JSON template의 layout/sections
    │                └─ javascript.py     import/export/require 구문
    ▼
graph.py ──────── FileRef[] → DependencyGraph (Node + Edge, 중복 제거)
    │
    ▼
renderer.py ───── DependencyGraph → HTML (templates/graph.html) 또는 JSON
```

### 핵심 데이터 흐름

1. `scanner.scan_theme()` — 설정된 디렉토리를 순회하며 `(상대경로, 절대경로)` 쌍을 yield
2. `ParserRegistry.parse_file()` — 등록된 파서 중 `can_parse()`가 true인 파서로 `FileRef` 목록 추출
3. `build_graph()` — 모든 FileRef를 모아 Node/Edge로 변환, degree 계산, 엣지 중복 제거
4. `render_html()` — `string.Template`으로 HTML 템플릿에 JSON 데이터 주입

## 커스텀 파서 추가

새로운 언어/프레임워크를 지원하려면 4단계를 거칩니다.

### 1. 파서 작성 — `parsers/<name>.py`

```python
import re
from . import BaseParser
from ..models import FileRef

class MyParser(BaseParser):
    def can_parse(self, relative_path: str) -> bool:
        return relative_path.endswith(".py")

    def parse(self, relative_path: str, content: str) -> list[FileRef]:
        # content를 파싱하여 FileRef 목록 반환
        ...
```

**규칙:**
- `can_parse()` — 확장자로만 빠르게 판단 (I/O 없음)
- `parse()` — 순수 함수: 문자열 → FileRef 리스트
- `target`은 프로젝트 루트 기준 상대 경로
- 외부 패키지 의존은 무시 (프로젝트 내부만 추적)

### 2. 레지스트리 등록 — `parsers/__init__.py`

```python
def my_registry() -> ParserRegistry:
    from .my_parser import MyParser
    registry = ParserRegistry()
    registry.register(MyParser())
    return registry
```

### 3. 프리셋 추가 — `presets.py`

```python
def my_preset() -> GraphConfig:
    return GraphConfig(
        scan_dirs=["src", "lib"],
        file_extensions=(".py",),
        category_rules={"src/models/": "model", "src/views/": "view"},
        category_colors={"model": "#FF5722", "view": "#2196F3", "other": "#607D8B"},
        title="My Project Dependency Graph",
    )

PRESETS["my_preset"] = my_preset
```

### 4. CLI 자동 감지 *(선택)* — `cli.py`의 `_detect_preset()`

```python
if os.path.isfile(os.path.join(project_dir, "pyproject.toml")):
    return "my_preset"
```

## 파일 구조

```
dep_graph/
├── __init__.py           # Public API exports
├── __main__.py           # python -m dep_graph 진입점
├── cli.py                # argparse CLI + 프리셋 자동 감지
├── config.py             # GraphConfig 데이터클래스
├── models.py             # FileRef, Node, Edge, DependencyGraph
├── graph.py              # 스캐너 + 파서 → 그래프 조립
├── scanner.py            # 디렉토리 순회 (fnmatch 필터)
├── renderer.py           # HTML/JSON 렌더링
├── presets.py            # shopify, nextjs, react 프리셋
├── parsers/
│   ├── __init__.py       # BaseParser, ParserRegistry, 레지스트리 팩토리
│   ├── liquid.py         # Shopify Liquid 파서
│   ├── json_template.py  # Shopify JSON template 파서
│   └── javascript.py     # JS/TS import/require/export 파서
└── templates/
    └── graph.html        # SVG force-directed 시각화 템플릿
```
