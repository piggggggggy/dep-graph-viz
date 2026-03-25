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
