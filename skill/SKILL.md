---
name: dep-graph
description: 프로젝트의 파일 의존성을 분석하고 인터랙티브 HTML 시각화를 생성. 순환 의존성 탐지, 미사용 파일 탐색, 의존성 구조 파악에 사용. Shopify Liquid, Next.js, React 프리셋 지원.
argument-hint: [project-dir] [options]
disable-model-invocation: false
allowed-tools: Bash, Read, Glob, Grep
---

# dep-graph: 의존성 분석 도구

프로젝트의 파일 간 의존성을 분석하여 인터랙티브 HTML 그래프를 생성한다.

## 실행

```bash
python3 -m dep_graph <project-dir> [options]
```

`<project-dir>`이 생략되면 현재 작업 디렉토리(`.`)를 사용한다.

## CLI 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `project_dir` | 프로젝트 루트 경로 | (필수) |
| `-o, --output FILE` | 출력 파일 경로 | `dependency-graph.html` |
| `-p, --preset NAME` | 프리셋 설정 (`shopify`, `nextjs`, `react`) | 자동 감지 |
| `--title TEXT` | 그래프 제목 | `Dependency Graph` |
| `--exclude PATTERN...` | 제외할 fnmatch 패턴 | 프리셋 기본값 |
| `--entry PATTERN...` | 진입점 glob 패턴 | 프리셋 기본값 |
| `--hub-threshold N` | 허브로 간주할 최소 in-degree | `5` |
| `--no-open` | 브라우저 자동 열기 비활성화 | `false` |
| `--json` | HTML 대신 JSON 출력 | `false` |

## 프리셋

- **shopify** — Liquid 테마 (templates, layout, sections, snippets, blocks)
- **nextjs** — Next.js App/Pages Router (routes, components, hooks, lib, utils)
- **react** — React CRA/Vite (pages, features, components, hooks, services)

프리셋은 자동 감지된다 (marker 파일 기반). `--preset`으로 강제 지정 가능.

## 출력 기능

생성된 HTML에는 다음 기능이 포함된다:

- **사이드 패널** — Stats/Unused/Cycles 3개 탭
- **Focus Mode** — 노드 클릭 시 상류(파란색)/하류(주황색) 의존성 시각화
- **Depth 슬라이더** — 의존성 깊이별 필터링
- **순환 의존성 탐지** — 빨간 점선으로 사이클 하이라이트
- **미사용 파일 탐지** — in_degree=0이면서 진입점이 아닌 파일 표시
- **검색, 카테고리 필터, 허브/고아 노드 하이라이트**

## 사용 예시

```
/dep-graph .
/dep-graph /path/to/project --preset nextjs
/dep-graph . --title "My Project" --no-open
/dep-graph . --json -o graph.json
/dep-graph . --entry "src/index.tsx" --exclude "*/test/*"
```

## 동작

1. `$ARGUMENTS`가 있으면 그대로 CLI 인수로 전달
2. 없으면 현재 작업 디렉토리를 대상으로 실행
3. `--no-open` 플래그가 없으면 브라우저에서 결과를 자동으로 연다
4. 결과 분석이 필요하면 `--json` 출력을 사용한다

인수가 주어졌을 때:
```bash
python3 -m dep_graph $ARGUMENTS
```

인수가 없을 때:
```bash
python3 -m dep_graph . --no-open
```
실행 후 출력 파일 경로를 사용자에게 알려준다.
