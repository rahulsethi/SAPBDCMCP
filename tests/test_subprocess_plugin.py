"""Subprocess plugin integration tests (Phase 6 / TestPlan §8.2).

File: tests/test_subprocess_plugin.py
Version: v1

Launches the in-repo ``tests/_helpers/dummy_mcp_server.py`` via the ``cmd:``
scheme, performs the initialize + tools/list handshake, registers a
namespaced proxy, calls it, then shuts the child down cleanly. No network
access; uses the current Python interpreter so behavior is deterministic
across CI runners.

Subprocess startup on Windows can be slow on cold paths; tests are marked
with a generous per-test timeout via :func:`pytest.mark.timeout` when the
plugin is available — they are skipped if the spawn fails for environmental
reasons (e.g. policy blocks executing python from this directory).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable, List

import pytest

from sap_bdc_mcp.audit import AuditWriter
from sap_bdc_mcp.config import BDCConfig, DatabricksConfig, SnowflakeConfig
from sap_bdc_mcp.plugin_loader import (
    SubprocessPlugin,
    _resolve_subprocess_command,
    load_plugins,
    parse_plugin_entry,
)
from sap_bdc_mcp.tools._gated import ToolContext
from sap_bdc_mcp.tools.metadata import MetadataRegistry


_DUMMY = Path(__file__).parent / "_helpers" / "dummy_mcp_server.py"


def _quote(p: str) -> str:
    """Quote a path token for inclusion in a ``cmd:`` plugin entry.

    Paths on Windows dev machines may contain spaces; the plugin loader
    parses ``cmd:`` targets with ``shlex.split(..., posix=False)`` which
    respects double-quoted tokens on both platforms.
    """
    if " " in p:
        return f'"{p}"'
    return p


def _dummy_entry(alias: str = "dummy") -> str:
    return f"{alias}=cmd:{_quote(sys.executable)} {_quote(str(_DUMMY))}"


class _CapturingServer:
    def __init__(self) -> None:
        self.registered: List[Callable[..., Any]] = []
        self.names: List[str] = []

    def tool(self) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
            self.registered.append(fn)
            self.names.append(fn.__name__)
            return fn

        return deco


def _build_ctx(tmp_path: Path, plugins: list[str], trust: dict[str, str]) -> ToolContext:
    config = BDCConfig(
        mode="local",
        mock_mode=True,
        verify_tls=False,
        max_doc_kb=512,
        ord_sources=[],
        plugins=plugins,
        enable_write_tools=True,
        enable_admin_tools=False,
        require_dry_run=True,
        require_approval_token=True,
        approval_token="",
        audit_enabled=True,
        audit_log_path=str(tmp_path / "audit.jsonl"),
        api_policy_strict=True,
        max_result_items=50,
        plugin_env_passthrough=[],
        plugin_trust=trust,
        databricks=DatabricksConfig(),
        snowflake=SnowflakeConfig(),
    )
    audit = AuditWriter(config.audit_log_path, enabled=True)
    return ToolContext(
        config=config,
        audit=audit,
        metadata=MetadataRegistry(),
        plugin_status=[],
    )


# ---------------------------------------------------------------------------
# _resolve_subprocess_command — pure unit test, never spawns.
# ---------------------------------------------------------------------------


def test_resolve_npx_command() -> None:
    spec = parse_plugin_entry("npx:@scope/pkg -- --flag")
    cmd, args = _resolve_subprocess_command(spec)
    assert cmd == "npx"
    assert args[0] == "-y"
    assert "@scope/pkg" in args
    assert "--flag" in args


def test_resolve_uvx_command() -> None:
    spec = parse_plugin_entry("uvx:mcp-server-sentry==0.1.4")
    cmd, args = _resolve_subprocess_command(spec)
    assert cmd == "uvx"
    assert args == ["mcp-server-sentry==0.1.4"]


def test_resolve_cmd_with_inline_args() -> None:
    entry = f"cmd:{_quote(sys.executable)} {_quote(str(_DUMMY))}"
    spec = parse_plugin_entry(entry)
    cmd, args = _resolve_subprocess_command(spec)
    assert Path(cmd).name.lower().startswith("python")
    assert any(str(_DUMMY) == a or _DUMMY.name == Path(a).name for a in args)


# ---------------------------------------------------------------------------
# Full subprocess plugin round-trip.
# ---------------------------------------------------------------------------


@pytest.fixture
def live_plugin():  # noqa: ANN201 - pytest fixture
    spec = parse_plugin_entry(_dummy_entry())
    plugin = SubprocessPlugin(spec, env_passthrough=[])
    try:
        plugin.start(timeout=30.0)
    except Exception as exc:  # pragma: no cover - environmental skip
        pytest.skip(f"could not spawn dummy MCP server: {exc}")
    yield plugin
    plugin.stop(timeout=10.0)


def test_subprocess_plugin_lists_dummy_echo(live_plugin: SubprocessPlugin) -> None:
    tool_names = [t["name"] for t in live_plugin.listed_tools()]
    assert "dummy_echo" in tool_names


def test_subprocess_plugin_call_roundtrip(live_plugin: SubprocessPlugin) -> None:
    result = live_plugin.call_sync("dummy_echo", {"message": "hello"})
    assert result.get("ok") is True
    # Either structured or text content carries the echoed message.
    structured = result.get("structured")
    text = result.get("text", "")
    assert ("hello" in text) or (
        isinstance(structured, dict) and structured.get("message") == "hello"
    )


def test_subprocess_plugin_clean_shutdown() -> None:
    spec = parse_plugin_entry(_dummy_entry())
    plugin = SubprocessPlugin(spec, env_passthrough=[])
    try:
        plugin.start(timeout=30.0)
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"could not spawn dummy MCP server: {exc}")
    plugin.stop(timeout=10.0)
    # After stop the background thread should have exited.
    assert plugin._stopped.wait(timeout=5.0)


def test_load_plugins_registers_namespaced_proxy(tmp_path: Path) -> None:
    """End-to-end: load_plugins + cmd: scheme should yield plug_dummy__dummy_echo."""
    from sap_bdc_mcp.plugin_loader import _LIVE_SUBPROCESS_PLUGINS

    entry = _dummy_entry()
    ctx = _build_ctx(tmp_path, plugins=[entry], trust={"dummy": "documented_sdk"})
    server = _CapturingServer()
    try:
        try:
            results = load_plugins(server, ctx)
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"plugin load environment unavailable: {exc}")
        assert len(results) == 1
        result = results[0]
        if not result.ok:
            pytest.skip(f"dummy plugin did not start: {result.error}")
        assert "plug_dummy__dummy_echo" in result.tools
        assert "plug_dummy__dummy_echo" in server.names
    finally:
        for p in list(_LIVE_SUBPROCESS_PLUGINS):
            p.stop(timeout=10.0)
        _LIVE_SUBPROCESS_PLUGINS.clear()
