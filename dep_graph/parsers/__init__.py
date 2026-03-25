"""Parser registry and base class."""

from abc import ABC, abstractmethod
from ..models import FileRef


class BaseParser(ABC):
    """Base class for file parsers."""

    @abstractmethod
    def can_parse(self, relative_path: str) -> bool:
        ...

    @abstractmethod
    def parse(self, relative_path: str, content: str) -> list:
        ...


class ParserRegistry:
    """Holds registered parsers and dispatches files to them."""

    def __init__(self):
        self._parsers = []

    def register(self, parser: BaseParser) -> None:
        self._parsers.append(parser)

    def parse_file(self, relative_path: str, content: str) -> list:
        refs = []
        for parser in self._parsers:
            if parser.can_parse(relative_path):
                refs.extend(parser.parse(relative_path, content))
        return refs


def default_registry() -> ParserRegistry:
    """Pre-configured registry with Liquid + JSON parsers (Shopify)."""
    from .liquid import LiquidParser
    from .json_template import JsonTemplateParser

    registry = ParserRegistry()
    registry.register(LiquidParser())
    registry.register(JsonTemplateParser())
    return registry


def javascript_registry(project_root: str = "") -> ParserRegistry:
    """Pre-configured registry with JS/TS parser (React/Next.js)."""
    from .javascript import JavaScriptParser

    registry = ParserRegistry()
    registry.register(JavaScriptParser(project_root=project_root))
    return registry
