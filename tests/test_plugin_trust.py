"""Plugin trust gating tests (Phase 6 / TestPlan §8.3).

File: tests/test_plugin_trust.py
Version: v1

These tests exercise the metadata synthesis + gating logic for subprocess
plugin tools WITHOUT spawning an actual subprocess. They prove:

* Synthetic plugin tool defaults to ``mutability=WRITE`` + ``api_surface=UNKNOWN``.
* Under ``BDC_API_POLICY_STRICT=1`` such a tool is blocked on call.
* When the operator promotes the alias via ``BDC_PLUGIN_TRUST=alias:documented_sdk``
  the synthesized metadata becomes evidenced and the gate allows the call
  (subject to ``BDC_ENABLE_WRITE_TOOLS``).
* A READ tool with UNKNOWN surface is always allowed (audit still written).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, List

from sap_bdc_mcp.audit import AuditWriter
from sap_bdc_mcp.config import BDCConfig, DatabricksConfig, SnowflakeConfig
from sap_bdc_mcp.plugin_loader import _make_proxy, _synthesize_metadata
from sap_bdc_mcp.tools._gated import ToolContext, gated
from sap_bdc_mcp.tools.metadata import (
    APISurface,
    BulkDataBehavior,
    MetadataRegistry,
    Mutability,
    Risk,
)


class _FakeServer:
    def __init__(self) -> None:
        self.registered: List[Callable[..., Any]] = []

    def tool(self) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
            self.registered.append(fn)
            return fn

        return deco


class _FakePlugin:
    """Stand-in for ``SubprocessPlugin`` that records calls instead of forwarding."""

    def __init__(self) -> None:
        self.calls: List[tuple[str, dict]] = []

    def call_sync(self, name: str, args: dict) -> dict:
        self.calls.append((name, dict(args)))
        return {"ok": True, "echoed": dict(args)}


def _build_ctx(
    tmp_path: Path,
    *,
    write_enabled: bool = True,
    strict: bool = True,
    trust: dict[str, str] | None = None,
) -> ToolContext:
    config = BDCConfig(
        mode="local",
        mock_mode=True,
        verify_tls=False,
        max_doc_kb=512,
        ord_sources=[],
        plugins=[],
        enable_write_tools=write_enabled,
        enable_admin_tools=False,
        require_dry_run=True,
        require_approval_token=True,
        approval_token="",
        audit_enabled=True,
        audit_log_path=str(tmp_path / "audit.jsonl"),
        api_policy_strict=strict,
        max_result_items=50,
        plugin_env_passthrough=[],
        plugin_trust=trust or {},
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
# Metadata synthesis defaults
# ---------------------------------------------------------------------------


def test_synthesized_metadata_defaults_are_distrusted() -> None:
    meta = _synthesize_metadata(
        "dummy",
        {"name": "echo", "description": "Echo it"},
        trust={},
    )
    assert meta.name == "plug_dummy__echo"
    assert meta.category == "plugin"
    assert meta.mutability == Mutability.WRITE
    assert meta.risk == Risk.MEDIUM
    assert meta.api_surface == APISurface.UNKNOWN
    assert meta.bulk_data_behavior == BulkDataBehavior.BLOCKED
    assert meta.requires_write_enable is True


def test_synthesized_metadata_honors_operator_trust() -> None:
    meta = _synthesize_metadata(
        "dummy",
        {"name": "echo", "description": "Echo"},
        trust={"dummy": "documented_sdk"},
    )
    assert meta.api_surface == APISurface.DOCUMENTED_SDK
    # Operator trust implicitly flips the bulk classification to NONE.
    assert meta.bulk_data_behavior == BulkDataBehavior.NONE


def test_unknown_trust_value_falls_back_to_unknown_surface() -> None:
    meta = _synthesize_metadata(
        "dummy",
        {"name": "echo"},
        trust={"dummy": "totally_made_up"},
    )
    assert meta.api_surface == APISurface.UNKNOWN


# ---------------------------------------------------------------------------
# Gate behavior on synthesized metadata
# ---------------------------------------------------------------------------


def test_default_write_unknown_plugin_call_is_blocked(tmp_path: Path) -> None:
    ctx = _build_ctx(tmp_path, write_enabled=True, strict=True, trust={})
    server = _FakeServer()
    plugin = _FakePlugin()

    meta = _synthesize_metadata("dummy", {"name": "echo"}, trust={})
    proxy = _make_proxy(plugin, "echo", meta.name)
    gated(server, ctx, meta=meta)(proxy)

    # gated() returns the same wrapper that FakeServer captured.
    wrapper = server.registered[0]
    result = wrapper(arguments={"message": "hi"})
    assert result["ok"] is False
    assert "UNKNOWN" in result["blocked_reason"]
    assert plugin.calls == []  # forward never happened
    assert ctx.audit.tail()[-1]["result_status"] == "blocked"


def test_trusted_plugin_call_is_forwarded(tmp_path: Path) -> None:
    ctx = _build_ctx(
        tmp_path,
        write_enabled=True,
        strict=True,
        trust={"dummy": "documented_sdk"},
    )
    server = _FakeServer()
    plugin = _FakePlugin()

    meta = _synthesize_metadata("dummy", {"name": "echo"}, trust=ctx.config.plugin_trust)
    proxy = _make_proxy(plugin, "echo", meta.name)
    gated(server, ctx, meta=meta)(proxy)

    wrapper = server.registered[0]
    result = wrapper(arguments={"message": "hi"})
    assert result.get("ok") is True
    assert plugin.calls == [("echo", {"message": "hi"})]
    assert ctx.audit.tail()[-1]["result_status"] == "ok"


def test_trusted_plugin_blocked_when_write_tools_disabled(tmp_path: Path) -> None:
    ctx = _build_ctx(
        tmp_path,
        write_enabled=False,
        strict=True,
        trust={"dummy": "documented_sdk"},
    )
    server = _FakeServer()
    plugin = _FakePlugin()

    meta = _synthesize_metadata("dummy", {"name": "echo"}, trust=ctx.config.plugin_trust)
    proxy = _make_proxy(plugin, "echo", meta.name)
    gated(server, ctx, meta=meta)(proxy)

    wrapper = server.registered[0]
    result = wrapper(arguments={"message": "hi"})
    assert result["ok"] is False
    assert "BDC_ENABLE_WRITE_TOOLS" in result["blocked_reason"]
    assert plugin.calls == []


def test_read_plugin_with_unknown_surface_is_allowed(tmp_path: Path) -> None:
    """READ tools bypass the api_surface gate even under strict mode."""
    ctx = _build_ctx(tmp_path, write_enabled=False, strict=True, trust={})
    server = _FakeServer()
    plugin = _FakePlugin()

    # Hand-built READ metadata using the synthesized name shape.
    from sap_bdc_mcp.tools.metadata import ToolMetadata

    meta = ToolMetadata(
        name="plug_dummy__lookup",
        category="plugin",
        mutability=Mutability.READ,
        risk=Risk.LOW,
        api_surface=APISurface.UNKNOWN,
        api_evidence="plugin.dummy.lookup",
        bulk_data_behavior=BulkDataBehavior.METADATA_ONLY,
        description="Read proxy",
    )
    proxy = _make_proxy(plugin, "lookup", meta.name)
    gated(server, ctx, meta=meta)(proxy)

    wrapper = server.registered[0]
    result = wrapper(arguments={"q": "x"})
    assert result.get("ok") is True
    assert plugin.calls == [("lookup", {"q": "x"})]
    assert ctx.audit.tail()[-1]["result_status"] == "ok"
