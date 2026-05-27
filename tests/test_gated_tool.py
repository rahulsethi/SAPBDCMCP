"""Tests for the gated-tool wrapper.

File: tests/test_gated_tool.py
Version: v1
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, List


from sap_bdc_mcp.audit import AuditWriter
from sap_bdc_mcp.config import BDCConfig, DatabricksConfig, SnowflakeConfig
from sap_bdc_mcp.tools._gated import ToolContext, gated
from sap_bdc_mcp.tools.metadata import APISurface, MetadataRegistry, Mutability, Risk, ToolMetadata


class FakeServer:
    """Minimal stand-in for a FastMCP server — captures registered tools."""

    def __init__(self) -> None:
        self.registered: List[Callable] = []

    def tool(self) -> Callable:
        def decorator(fn: Callable) -> Callable:
            self.registered.append(fn)
            return fn

        return decorator


def _build_ctx(tmp_path: Path, *, write_enabled: bool = False, strict: bool = True) -> ToolContext:
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
        plugin_trust={},
        databricks=DatabricksConfig(),
        snowflake=SnowflakeConfig(),
    )
    audit = AuditWriter(config.audit_log_path, enabled=True)
    return ToolContext(config=config, audit=audit, metadata=MetadataRegistry(), plugin_status=[])


def _meta(
    *,
    name: str = "t",
    mut: Mutability = Mutability.READ,
    surface: APISurface = APISurface.PUBLISHED_API,
) -> ToolMetadata:
    return ToolMetadata(
        name=name,
        category="x",
        mutability=mut,
        risk=Risk.LOW,
        api_surface=surface,
        api_evidence="t.e",
    )


def test_success_writes_audit_event(tmp_path: Path) -> None:
    ctx = _build_ctx(tmp_path)
    server = FakeServer()

    @gated(server, ctx, meta=_meta())
    def t() -> dict:
        return {"ok": True}

    result = t()
    assert result == {"ok": True}
    events = ctx.audit.tail()
    assert len(events) == 1
    assert events[0]["result_status"] == "ok"
    assert events[0]["allowed"] is True


def test_registration_calls_server_tool(tmp_path: Path) -> None:
    ctx = _build_ctx(tmp_path)
    server = FakeServer()

    @gated(server, ctx, meta=_meta(name="reg"))
    def fn() -> dict:
        return {}

    assert len(server.registered) == 1
    assert ctx.metadata.get("reg") is not None


def test_write_disabled_blocks(tmp_path: Path) -> None:
    ctx = _build_ctx(tmp_path, write_enabled=False)
    server = FakeServer()

    @gated(server, ctx, meta=_meta(name="w", mut=Mutability.WRITE))
    def t() -> dict:
        return {"ok": True}

    result = t()
    assert result["ok"] is False
    assert "BDC_ENABLE_WRITE_TOOLS" in result["blocked_reason"]
    events = ctx.audit.tail()
    assert events[-1]["result_status"] == "blocked"


def test_admin_disabled_blocks(tmp_path: Path) -> None:
    ctx = _build_ctx(tmp_path, write_enabled=True)
    server = FakeServer()

    @gated(server, ctx, meta=_meta(name="a", mut=Mutability.ADMIN))
    def t() -> dict:
        return {"ok": True}

    result = t()
    assert result["ok"] is False
    assert "BDC_ENABLE_ADMIN_TOOLS" in result["blocked_reason"]


def test_api_policy_strict_blocks_write_unknown(tmp_path: Path) -> None:
    ctx = _build_ctx(tmp_path, write_enabled=True, strict=True)
    server = FakeServer()

    @gated(server, ctx, meta=_meta(name="u", mut=Mutability.WRITE, surface=APISurface.UNKNOWN))
    def t() -> dict:
        return {"ok": True}

    result = t()
    assert result["ok"] is False
    assert "UNKNOWN" in result["blocked_reason"]


def test_read_with_unknown_surface_allowed_even_strict(tmp_path: Path) -> None:
    ctx = _build_ctx(tmp_path, strict=True)
    server = FakeServer()

    @gated(server, ctx, meta=_meta(name="ru", surface=APISurface.UNKNOWN))
    def t() -> dict:
        return {"ok": True}

    result = t()
    assert result == {"ok": True}


def test_exception_is_caught_and_audited(tmp_path: Path) -> None:
    ctx = _build_ctx(tmp_path)
    server = FakeServer()

    @gated(server, ctx, meta=_meta(name="boom"))
    def t() -> dict:
        raise RuntimeError("explode")

    result = t()
    assert result["ok"] is False
    assert "explode" in result["error"]
    events = ctx.audit.tail()
    assert events[-1]["result_status"] == "error"


def test_exception_message_is_redacted(tmp_path: Path) -> None:
    ctx = _build_ctx(tmp_path)
    server = FakeServer()

    @gated(server, ctx, meta=_meta(name="bn"))
    def t() -> dict:
        raise RuntimeError("Bearer abc123secrettoken")

    result = t()
    assert "abc123secrettoken" not in result["error"]


def test_result_redaction_applied_on_dict(tmp_path: Path) -> None:
    ctx = _build_ctx(tmp_path)
    server = FakeServer()

    @gated(server, ctx, meta=_meta(name="rd"))
    def t() -> dict:
        return {"token": "abc", "ok": True}

    result = t()
    assert result["token"] == "***"
    assert result["ok"] is True


def test_metadata_is_registered(tmp_path: Path) -> None:
    ctx = _build_ctx(tmp_path)
    server = FakeServer()
    m = _meta(name="mr")

    @gated(server, ctx, meta=m)
    def t() -> dict:
        return {}

    assert ctx.metadata.get("mr") is m


def test_dry_run_argument_captured_in_audit(tmp_path: Path) -> None:
    ctx = _build_ctx(tmp_path)
    server = FakeServer()

    @gated(server, ctx, meta=_meta(name="dr"))
    def t(dry_run: bool = True) -> dict:
        return {"ok": True}

    t(dry_run=False)
    events = ctx.audit.tail()
    assert events[-1]["dry_run"] is False
