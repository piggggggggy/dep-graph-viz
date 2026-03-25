"""Pre-built configurations for common project types."""

from .config import GraphConfig


def shopify() -> GraphConfig:
    """Shopify Liquid theme."""
    return GraphConfig(
        scan_dirs=["templates", "layout", "sections", "snippets", "blocks"],
        exclude_patterns=["*/pf-*", "*/.pf-*"],
        file_extensions=(".liquid", ".json"),
        category_rules={
            "templates/": "template",
            "layout/": "layout",
            "sections/": "section",
            "snippets/": "snippet",
            "blocks/": "block",
        },
        category_colors={
            "template": "#4CAF50",
            "layout": "#FF5722",
            "section": "#2196F3",
            "snippet": "#FF9800",
            "block": "#9C27B0",
            "other": "#607D8B",
        },
        title="Shopify Theme Dependency Graph",
        entry_patterns=["templates/*.json", "templates/*.liquid", "layout/theme.liquid"],
    )


def nextjs() -> GraphConfig:
    """Next.js (App Router + Pages Router)."""
    return GraphConfig(
        scan_dirs=["src", "app", "pages", "components", "lib", "utils", "hooks", "store", "styles", "public"],
        exclude_patterns=["*/node_modules/*", "*/.next/*", "*/dist/*", "*/__tests__/*", "*/*.test.*", "*/*.spec.*"],
        file_extensions=(".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"),
        category_rules={
            "app/": "route",
            "pages/": "page",
            "src/app/": "route",
            "src/pages/": "page",
            "components/": "component",
            "src/components/": "component",
            "lib/": "lib",
            "src/lib/": "lib",
            "utils/": "util",
            "src/utils/": "util",
            "hooks/": "hook",
            "src/hooks/": "hook",
            "store/": "store",
            "src/store/": "store",
            "styles/": "style",
            "src/styles/": "style",
        },
        category_colors={
            "route": "#FF5722",
            "page": "#FF5722",
            "component": "#2196F3",
            "lib": "#FF9800",
            "util": "#FF9800",
            "hook": "#9C27B0",
            "store": "#E91E63",
            "style": "#00BCD4",
            "other": "#607D8B",
        },
        title="Next.js Dependency Graph",
        entry_patterns=[
            "app/layout.tsx", "app/layout.ts", "app/page.tsx", "app/page.ts",
            "pages/_app.tsx", "pages/_app.ts", "pages/index.tsx", "pages/index.ts",
            "src/app/layout.tsx", "src/app/page.tsx",
            "src/pages/_app.tsx", "src/pages/index.tsx",
        ],
    )


def react() -> GraphConfig:
    """React (CRA / Vite / custom)."""
    return GraphConfig(
        scan_dirs=["src", "components", "lib", "utils", "hooks", "store", "pages", "features", "services"],
        exclude_patterns=["*/node_modules/*", "*/dist/*", "*/build/*", "*/__tests__/*", "*/*.test.*", "*/*.spec.*"],
        file_extensions=(".ts", ".tsx", ".js", ".jsx"),
        category_rules={
            "src/pages/": "page",
            "src/features/": "feature",
            "src/components/": "component",
            "components/": "component",
            "src/lib/": "lib",
            "lib/": "lib",
            "src/utils/": "util",
            "utils/": "util",
            "src/hooks/": "hook",
            "hooks/": "hook",
            "src/store/": "store",
            "store/": "store",
            "src/services/": "service",
            "services/": "service",
        },
        category_colors={
            "page": "#FF5722",
            "feature": "#E91E63",
            "component": "#2196F3",
            "lib": "#FF9800",
            "util": "#FF9800",
            "hook": "#9C27B0",
            "store": "#E91E63",
            "service": "#4CAF50",
            "other": "#607D8B",
        },
        title="React Dependency Graph",
        entry_patterns=[
            "src/index.tsx", "src/index.ts", "src/index.jsx", "src/index.js",
            "src/App.tsx", "src/App.ts", "src/App.jsx", "src/App.js",
        ],
    )


PRESETS = {
    "shopify": shopify,
    "nextjs": nextjs,
    "react": react,
}
