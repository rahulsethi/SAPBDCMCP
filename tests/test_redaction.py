"""Redaction tests — including v0.2 additions.

File: tests/test_redaction.py
Version: v1
"""

from __future__ import annotations

from sap_bdc_mcp.redaction import redact, redact_str


def test_basic_auth_url_redacted() -> None:
    s = "https://user:pw@example.com/x"
    assert "user:pw@" not in redact_str(s)
    assert "***:***@" in redact_str(s)


def test_bearer_token_redacted() -> None:
    s = "Authorization: Bearer abcDEF123_xyz"
    out = redact_str(s)
    assert "abcDEF123_xyz" not in out
    assert "Bearer ***" in out


def test_sensitive_dict_key_redacted() -> None:
    d = {"token": "secret-1", "name": "ok"}
    out = redact(d)
    assert out["token"] == "***"
    assert out["name"] == "ok"


def test_approval_token_dict_key_redacted() -> None:
    d = {"approval_token": "letmein"}
    assert redact(d)["approval_token"] == "***"


def test_signed_url_redacted() -> None:
    s = "https://share.databricks.example/path/share?token=abc123def&other=keep"
    out = redact_str(s)
    assert "abc123def" not in out
    assert "token=***" in out
    assert "other=keep" in out
    # Host/path remain visible
    assert "share.databricks.example/path/share" in out


def test_signature_query_redacted() -> None:
    s = "https://x.example/y?signature=AABBCCDD&z=1"
    assert "AABBCCDD" not in redact_str(s)
    assert "signature=***" in redact_str(s)


def test_jwt_redacted() -> None:
    s = "got header eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c here"
    out = redact_str(s)
    assert "eyJ" not in out
    assert "***" in out


def test_nested_structures_redacted() -> None:
    obj = {
        "outer": {"token": "x", "url": "https://u:p@h"},
        "list": ["Bearer abc", {"secret": "s"}],
    }
    out = redact(obj)
    assert out["outer"]["token"] == "***"
    assert "u:p@" not in out["outer"]["url"]
    assert out["list"][0] == "Bearer ***"
    assert out["list"][1]["secret"] == "***"


def test_non_string_values_pass_through() -> None:
    assert redact(42) == 42
    assert redact(None) is None
    assert redact(True) is True
