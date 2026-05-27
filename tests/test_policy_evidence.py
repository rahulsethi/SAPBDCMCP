"""Policy evidence gate tests.

File: tests/test_policy_evidence.py
Version: v1
"""

from __future__ import annotations

from sap_bdc_mcp.policy_evidence import check_or_block
from sap_bdc_mcp.tools.metadata import APISurface, Mutability, Risk, ToolMetadata


def _meta(mut: Mutability, surface: APISurface, name: str = "t") -> ToolMetadata:
    return ToolMetadata(
        name=name,
        category="x",
        mutability=mut,
        risk=Risk.LOW,
        api_surface=surface,
        api_evidence="t.e",
    )


def test_read_with_unknown_surface_is_allowed_even_strict() -> None:
    r = check_or_block(_meta(Mutability.READ, APISurface.UNKNOWN), strict=True)
    assert r.allowed is True


def test_write_with_unknown_surface_is_blocked_strict() -> None:
    r = check_or_block(_meta(Mutability.WRITE, APISurface.UNKNOWN), strict=True)
    assert r.allowed is False
    assert r.reason is not None
    assert "UNKNOWN" in r.reason


def test_write_with_unknown_surface_allowed_when_not_strict() -> None:
    r = check_or_block(_meta(Mutability.WRITE, APISurface.UNKNOWN), strict=False)
    assert r.allowed is True


def test_admin_with_documented_sdk_is_allowed_strict() -> None:
    r = check_or_block(_meta(Mutability.ADMIN, APISurface.DOCUMENTED_SDK), strict=True)
    assert r.allowed is True


def test_write_with_published_api_is_allowed() -> None:
    r = check_or_block(_meta(Mutability.WRITE, APISurface.PUBLISHED_API), strict=True)
    assert r.allowed is True


def test_reason_mentions_tool_name() -> None:
    r = check_or_block(_meta(Mutability.WRITE, APISurface.UNKNOWN, name="plug_xx"), strict=True)
    assert r.reason is not None
    assert "plug_xx" in r.reason
