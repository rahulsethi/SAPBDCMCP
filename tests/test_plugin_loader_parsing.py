"""Plugin loader entry-parsing tests (Phase 6 / TestPlan §8.1).

File: tests/test_plugin_loader_parsing.py
Version: v1
"""

from __future__ import annotations

import pytest

from sap_bdc_mcp.plugin_loader import (
    PluginParseError,
    PluginSpec,
    parse_plugin_entry,
)


def test_bare_module_path_is_python_scheme() -> None:
    spec = parse_plugin_entry("sap_bdc_mcp.plugins.databricks_extra")
    assert spec.scheme == "python"
    assert spec.target == "sap_bdc_mcp.plugins.databricks_extra"
    assert spec.alias == "databricks_extra"
    assert spec.args == []


def test_explicit_python_scheme() -> None:
    spec = parse_plugin_entry("python:module.path")
    assert spec.scheme == "python"
    assert spec.target == "module.path"
    assert spec.alias == "path"


def test_npx_scheme_with_alias_and_args() -> None:
    spec = parse_plugin_entry("gh=npx:@modelcontextprotocol/server-github@0.5.0 -- --flag")
    assert spec.scheme == "npx"
    assert spec.alias == "gh"
    assert spec.target == "@modelcontextprotocol/server-github@0.5.0"
    assert spec.args == ["--flag"]


def test_npx_scheme_without_alias_derives_alias() -> None:
    spec = parse_plugin_entry("npx:@modelcontextprotocol/server-github@0.5.0")
    assert spec.scheme == "npx"
    assert spec.alias == "server-github"


def test_uvx_scheme_with_version_pin() -> None:
    spec = parse_plugin_entry("uvx:mcp-server-sentry==0.1.4")
    assert spec.scheme == "uvx"
    assert spec.target == "mcp-server-sentry==0.1.4"
    assert spec.alias == "mcp-server-sentry"
    assert spec.args == []


def test_uvx_with_alias_and_args() -> None:
    spec = parse_plugin_entry("sentry=uvx:mcp-server-sentry==0.1.4 -- --token=xyz")
    assert spec.scheme == "uvx"
    assert spec.alias == "sentry"
    assert spec.target == "mcp-server-sentry==0.1.4"
    assert spec.args == ["--token=xyz"]


def test_cmd_scheme_with_path_and_args() -> None:
    spec = parse_plugin_entry("cmd:/usr/local/bin/my-mcp-server -- --config=/etc/mcp.yaml")
    assert spec.scheme == "cmd"
    assert spec.target == "/usr/local/bin/my-mcp-server"
    assert spec.args == ["--config=/etc/mcp.yaml"]
    assert spec.alias == "my-mcp-server"


def test_cmd_scheme_with_inline_args_in_target() -> None:
    # The convenience form ``cmd:python script.py`` keeps the inline tokens
    # together; _resolve_subprocess_command splits them later.
    spec = parse_plugin_entry("cmd:python tests/_helpers/dummy_mcp_server.py")
    assert spec.scheme == "cmd"
    assert "dummy_mcp_server.py" in spec.target


def test_unknown_scheme_raises_parse_error() -> None:
    with pytest.raises(PluginParseError):
        parse_plugin_entry("something:invalid")


def test_empty_entry_raises() -> None:
    with pytest.raises(PluginParseError):
        parse_plugin_entry("")


def test_whitespace_only_entry_raises() -> None:
    with pytest.raises(PluginParseError):
        parse_plugin_entry("   ")


def test_alias_with_dashes_and_underscores() -> None:
    spec = parse_plugin_entry("my-alias_1=npx:pkg")
    assert spec.alias == "my-alias_1"
    assert spec.scheme == "npx"
    assert spec.target == "pkg"


def test_python_scheme_preserved_in_spec_dataclass() -> None:
    spec = parse_plugin_entry("python:a.b.c")
    assert isinstance(spec, PluginSpec)


def test_load_plugins_does_not_raise_on_bad_entry(tmp_path) -> None:
    """Top-level loader surfaces parse errors as PluginLoadResult."""
    from sap_bdc_mcp.audit import AuditWriter
    from sap_bdc_mcp.config import BDCConfig, DatabricksConfig, SnowflakeConfig
    from sap_bdc_mcp.plugin_loader import load_plugins
    from sap_bdc_mcp.tools._gated import ToolContext
    from sap_bdc_mcp.tools.metadata import MetadataRegistry

    config = BDCConfig(
        mode="local",
        mock_mode=True,
        verify_tls=False,
        max_doc_kb=512,
        ord_sources=[],
        plugins=["something:invalid"],
        enable_write_tools=False,
        databricks=DatabricksConfig(),
        snowflake=SnowflakeConfig(),
        audit_log_path=str(tmp_path / "audit.jsonl"),
    )
    ctx = ToolContext(
        config=config,
        audit=AuditWriter(config.audit_log_path, enabled=False),
        metadata=MetadataRegistry(),
        plugin_status=[],
    )

    class _Srv:
        def tool(self):
            def deco(fn):
                return fn

            return deco

    results = load_plugins(_Srv(), ctx)
    assert len(results) == 1
    assert results[0].ok is False
    assert "unknown plugin scheme" in (results[0].error or "")
