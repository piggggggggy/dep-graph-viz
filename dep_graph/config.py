"""Configuration for the dependency graph generator."""

from dataclasses import dataclass, field


@dataclass
class GraphConfig:
    """All user-configurable settings."""

    # Directories to scan (relative to project root)
    scan_dirs: list = field(default_factory=lambda: [
        "templates", "layout", "sections", "snippets", "blocks",
    ])

    # fnmatch patterns to exclude (matched against relative paths)
    exclude_patterns: list = field(default_factory=lambda: [
        "*/pf-*", "*/.pf-*",
    ])

    # Glob patterns to identify entry point files
    entry_patterns: list = field(default_factory=list)

    # File extensions to include
    file_extensions: tuple = (".liquid", ".json")

    # Path prefix -> category name
    category_rules: dict = field(default_factory=lambda: {
        "templates/": "template",
        "layout/": "layout",
        "sections/": "section",
        "snippets/": "snippet",
        "blocks/": "block",
    })

    # Category -> hex color
    category_colors: dict = field(default_factory=lambda: {
        "template": "#4CAF50",
        "layout": "#FF5722",
        "section": "#2196F3",
        "snippet": "#FF9800",
        "block": "#9C27B0",
        "other": "#607D8B",
    })

    title: str = "Dependency Graph"
    hub_threshold: int = 5
    layout_iterations: int = 200

    def get_category(self, path: str) -> str:
        # Longer prefixes first for specificity (e.g., "src/components/" before "src/")
        for prefix in sorted(self.category_rules.keys(), key=len, reverse=True):
            if path.startswith(prefix):
                return self.category_rules[prefix]
        return "other"

    def get_color(self, category: str) -> str:
        return self.category_colors.get(category, self.category_colors.get("other", "#607D8B"))
