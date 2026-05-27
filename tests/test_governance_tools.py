"""Governance tools tests (bdc_tool_risk_catalog / policy_explain / api_policy_check / audit_tail).

File: tests/test_governance_tools.py
Version: v1
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


def test_server_builds_with_governance() -> None:
    server = build_server()
    assert server is not None


def _get_tool_fn(server, name: str):
    """Find the underlying Python function for a registered tool by name.

    FastMCP exposes a `_tool_manager` (private but stable enough for tests in
    this repo). Falls back to a method-based lookup if available.
    """
    tm = getattr(server, "_tool_manager", None)
    if tm is not None and hasattr(tm, "_tools"):
        tools = tm._tools  # type: ignore[attr-defined]
        entry = tools.get(name)
        if entry is not None:
            return getattr(entry, "fn", None) or getattr(entry, "func", None) or entry
    return None


def test_risk_catalog_returns_v01_plus_governance() -> None:
    server = build_server()
    fn = _get_tool_fn(server, "bdc_tool_risk_catalog")
    assert fn is not None
    out = fn()
    assert out["count"] >= 12 + 4  # 12 v0.1 + 4 governance
    names = {t["name"] for t in out["tools"]}
    assert "bdc_ping" in names
    assert "bdc_tool_risk_catalog" in names
    assert "bdc_policy_explain" in names
    assert "bdc_api_policy_check" in names
    assert "bdc_audit_tail" in names


def test_risk_catalog_filter_by_category() -> None:
    server = build_server()
    fn = _get_tool_fn(server, "bdc_tool_risk_catalog")
    out = fn(category="ord")
    cats = {t["category"] for t in out["tools"]}
    assert cats == {"ord"}


def test_policy_explain_known_tool() -> None:
    server = build_server()
    fn = _get_tool_fn(server, "bdc_policy_explain")
    out = fn(tool_name="bdc_ping")
    assert out["tool"] == "bdc_ping"
    assert out["would_allow"] is True
    gate_names = {g["gate"] for g in out["gates"]}
    assert "policy_evidence" in gate_names


def test_policy_explain_unknown_tool() -> None:
    server = build_server()
    fn = _get_tool_fn(server, "bdc_policy_explain")
    out = fn(tool_name="no_such_tool")
    assert out["ok"] is False
    assert "no_such_tool" in out["error"]


def test_api_policy_check_summarizes_all() -> None:
    server = build_server()
    fn = _get_tool_fn(server, "bdc_api_policy_check")
    out = fn()
    assert "tools" in out
    assert out["unknown_surface_write_admin_count"] == 0  # no UNKNOWN-surface mutators in v0.1


def test_api_policy_check_single_tool() -> None:
    server = build_server()
    fn = _get_tool_fn(server, "bdc_api_policy_check")
    out = fn(tool_name="bdc_ping")
    assert len(out["tools"]) == 1
    assert out["tools"][0]["name"] == "bdc_ping"


def test_audit_tail_returns_events(tmp_path) -> None:
    server = build_server()
    # Invoke a couple of tools to populate audit.
    ping = _get_tool_fn(server, "bdc_ping")
    ping()
    ping()
    tail = _get_tool_fn(server, "bdc_audit_tail")
    out = tail(limit=10)
    assert out["count"] >= 2
    assert any(ev["tool_name"] == "bdc_ping" for ev in out["events"])


def test_audit_tail_respects_max_result_items(monkeypatch) -> None:
    monkeypatch.setenv("BDC_MAX_RESULT_ITEMS", "3")
    server = build_server()
    ping = _get_tool_fn(server, "bdc_ping")
    for _ in range(10):
        ping()
    tail = _get_tool_fn(server, "bdc_audit_tail")
    out = tail(limit=100)
    assert out["count"] <= 3
