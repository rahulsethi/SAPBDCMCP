"""Snowflake MCP tool tests.

File: tests/test_snowflake_tools.py
Version: v1

Covers 06_TestPlan §6.2.
"""

from __future__ import annotations

import os

import pytest

from sap_bdc_mcp.server import build_server


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    for k in list(os.environ.keys()):
        if k.startswith("BDC_"):
            monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("BDC_MOCK_MODE", "1")
    monkeypatch.setenv("BDC_AUDIT_LOG_PATH", str(tmp_path / "audit.jsonl"))


def _get_tool_fn(server, name: str):
    tm = getattr(server, "_tool_manager", None)
    if tm is not None and hasattr(tm, "_tools"):
        tools = tm._tools  # type: ignore[attr-defined]
        entry = tools.get(name)
        if entry is not None:
            return getattr(entry, "fn", None) or getattr(entry, "func", None) or entry
    return None


def test_snowflake_preflight_mock_mode_passes() -> None:
    server = build_server()
    fn = _get_tool_fn(server, "bdc_snowflake_preflight")
    assert fn is not None
    out = fn()
    assert out["ok"] is True
    assert out["mock_mode"] is True


def test_snowflake_explain_flow_returns_documentation() -> None:
    server = build_server()
    fn = _get_tool_fn(server, "bdc_snowflake_explain_flow")
    out = fn()
    assert out["ok"] is True
    assert "CREATE SHARE" in out["flow"]
    assert out["execution_status"] == "deferred_to_v0.3"
    assert "v0.3" in out["note"]


def test_snowflake_tools_appear_in_risk_catalog() -> None:
    server = build_server()
    fn = _get_tool_fn(server, "bdc_tool_risk_catalog")
    out = fn()
    names = {t["name"] for t in out["tools"]}
    assert "bdc_snowflake_preflight" in names
    assert "bdc_snowflake_explain_flow" in names
    # All snowflake tools are READ — verify no mutators leaked.
    sf_tools = [t for t in out["tools"] if t["category"] == "snowflake"]
    for t in sf_tools:
        assert t["mutability"] == "READ"
