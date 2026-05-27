"""Audit writer tests.

File: tests/test_audit.py
Version: v1
"""

from __future__ import annotations

import json
from pathlib import Path

from sap_bdc_mcp.audit import EVENT_VERSION, AuditWriter, hash_inputs


def test_hash_inputs_redacts_before_hashing() -> None:
    # Same hash whether or not the secret is present in the dict —
    # because redact() replaces the value before hashing.
    h1 = hash_inputs({"token": "abc123"})
    h2 = hash_inputs({"token": "different-secret"})
    assert h1 == h2  # both redacted to {"token": "***"}
    assert h1.startswith("sha256:")
    assert len(h1) == len("sha256:") + 64


def test_hash_inputs_is_deterministic_for_same_payload() -> None:
    assert hash_inputs({"a": 1, "b": [2, 3]}) == hash_inputs({"b": [2, 3], "a": 1})


def test_hash_inputs_distinguishes_different_payloads() -> None:
    assert hash_inputs({"a": 1}) != hash_inputs({"a": 2})


def test_writer_creates_parent_dir(tmp_path: Path) -> None:
    log = tmp_path / "deep" / "audit.jsonl"
    AuditWriter(str(log), enabled=True)
    assert log.parent.exists()


def test_writer_roundtrip(tmp_path: Path) -> None:
    log = tmp_path / "audit.jsonl"
    w = AuditWriter(str(log), enabled=True)
    cid = w.write(
        tool_name="bdc_ping",
        mutability="READ",
        risk="low",
        provider=None,
        dry_run=True,
        allowed=True,
        blocked_reason=None,
        inputs={"x": 1},
        result_status="ok",
    )
    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    ev = json.loads(lines[0])
    assert ev["tool_name"] == "bdc_ping"
    assert ev["event_version"] == EVENT_VERSION
    assert ev["correlation_id"] == cid
    assert ev["input_hash"].startswith("sha256:")
    assert ev["redaction_applied"] is True


def test_writer_uses_supplied_correlation_id(tmp_path: Path) -> None:
    log = tmp_path / "audit.jsonl"
    w = AuditWriter(str(log), enabled=True)
    cid = w.write(
        tool_name="t",
        mutability="WRITE",
        risk="high",
        provider="databricks",
        dry_run=False,
        allowed=True,
        blocked_reason=None,
        inputs={},
        result_status="ok",
        correlation_id="given-cid",
    )
    assert cid == "given-cid"


def test_writer_disabled_does_not_write(tmp_path: Path) -> None:
    log = tmp_path / "audit.jsonl"
    w = AuditWriter(str(log), enabled=False)
    cid = w.write(
        tool_name="t",
        mutability="READ",
        risk="low",
        provider=None,
        dry_run=True,
        allowed=True,
        blocked_reason=None,
        inputs={},
        result_status="ok",
    )
    assert cid  # still returns an id
    assert not log.exists()


def test_writer_tail_filters_by_timestamp(tmp_path: Path) -> None:
    log = tmp_path / "audit.jsonl"
    w = AuditWriter(str(log), enabled=True)
    # Write three events
    for i in range(3):
        w.write(
            tool_name=f"t{i}",
            mutability="READ",
            risk="low",
            provider=None,
            dry_run=True,
            allowed=True,
            blocked_reason=None,
            inputs={"i": i},
            result_status="ok",
        )
    all_events = w.tail(limit=10)
    assert len(all_events) == 3
    last = w.tail(limit=1)
    assert len(last) == 1
    assert last[0]["tool_name"] == "t2"


def test_writer_tail_empty_when_no_file(tmp_path: Path) -> None:
    log = tmp_path / "audit.jsonl"
    w = AuditWriter(str(log), enabled=False)
    assert w.tail() == []


def test_event_has_all_required_fields(tmp_path: Path) -> None:
    log = tmp_path / "audit.jsonl"
    w = AuditWriter(str(log), enabled=True)
    w.write(
        tool_name="bdc_share_execute_plan",
        mutability="WRITE",
        risk="high",
        provider="databricks",
        dry_run=True,
        allowed=True,
        blocked_reason=None,
        inputs={"plan": {"name": "s"}},
        result_status="ok",
    )
    ev = json.loads(log.read_text(encoding="utf-8").strip())
    for field in (
        "timestamp",
        "event_version",
        "tool_name",
        "mutability",
        "risk",
        "provider",
        "plugin",
        "upstream_tool",
        "dry_run",
        "allowed",
        "blocked_reason",
        "input_hash",
        "redaction_applied",
        "result_status",
        "correlation_id",
    ):
        assert field in ev, f"missing {field}"
