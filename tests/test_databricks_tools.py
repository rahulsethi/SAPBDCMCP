"""Databricks tool tests — happy + blocked + edge.

File: tests/test_databricks_tools.py
Version: v1

Covers 06_TestPlan §5.3.
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


def test_databricks_preflight_happy_mock(tmp_path) -> None:
    server = build_server()
    fn = _get_tool_fn(server, "bdc_databricks_preflight")
    assert fn is not None
    out = fn()
    assert out["ok"] is True
    assert out["mock_mode"] is True
    assert out["blockers"] == []


def test_databricks_preflight_missing_host_blocks_in_real_mode(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("BDC_MOCK_MODE", "0")
    server = build_server()
    fn = _get_tool_fn(server, "bdc_databricks_preflight")
    out = fn(mock_mode=False)
    assert out["ok"] is False
    assert any("BDC_DATABRICKS_HOST" in b for b in out["blockers"])


def test_databricks_validate_share_readiness_known_share() -> None:
    server = build_server()
    fn = _get_tool_fn(server, "bdc_databricks_validate_share_readiness")
    out = fn(share_name="simple_share")
    assert out["ok"] is True
    assert out["recipient_registered"] is True
    assert out["schema_count"] >= 1


def test_databricks_validate_share_readiness_missing_share_is_structured() -> None:
    server = build_server()
    fn = _get_tool_fn(server, "bdc_databricks_validate_share_readiness")
    out = fn(share_name="no_such_share")
    assert out["ok"] is False
    assert out["reason"] == "share_not_found"
    assert out["share_name"] == "no_such_share"


def test_databricks_generate_csn_from_share_simple_returns_csn() -> None:
    server = build_server()
    fn = _get_tool_fn(server, "bdc_databricks_generate_csn_from_share")
    out = fn(share_name="simple_share")
    assert out["ok"] is True
    assert "csn" in out
    assert "disclaimer" in out
    # Type mapping spot-check.
    defs = out["csn"]["definitions"]
    keys = list(defs.keys())
    assert any("sales" in k for k in keys)


def test_databricks_generate_csn_from_share_complex_refuses() -> None:
    server = build_server()
    fn = _get_tool_fn(server, "bdc_databricks_generate_csn_from_share")
    out = fn(share_name="complex_share")
    assert out["ok"] is False
    assert out["reason"] == "complex_types_not_supported"
    assert out["disclaimer"]
    assert out["unsupported_columns"]


def test_databricks_tools_show_in_risk_catalog() -> None:
    server = build_server()
    fn = _get_tool_fn(server, "bdc_tool_risk_catalog")
    out = fn()
    names = {t["name"] for t in out["tools"]}
    assert "bdc_databricks_preflight" in names
    assert "bdc_databricks_validate_share_readiness" in names
    assert "bdc_databricks_generate_csn_from_share" in names
