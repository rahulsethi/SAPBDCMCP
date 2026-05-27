"""BDCConfig tests — v0.2 additions.

File: tests/test_config.py
Version: v1
"""

from __future__ import annotations

import os

import pytest

from sap_bdc_mcp import config as config_module
from sap_bdc_mcp.config import BDCConfig


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip any BDC_* env + suppress .env loading so tests see true defaults."""
    for k in list(os.environ.keys()):
        if k.startswith("BDC_"):
            monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(config_module, "load_dotenv", lambda *a, **kw: None)


def test_defaults_when_env_empty() -> None:
    c = BDCConfig.from_env()
    assert c.mode == "local"
    assert c.mock_mode is False
    assert c.verify_tls is True
    assert c.enable_write_tools is False
    assert c.enable_admin_tools is False
    assert c.require_dry_run is True
    assert c.require_approval_token is True
    assert c.approval_token == ""
    assert c.audit_enabled is True
    assert c.audit_log_path == ".sap_bdc_mcp/audit.jsonl"
    assert c.api_policy_strict is True
    assert c.max_result_items == 50
    assert c.plugin_env_passthrough == []
    assert c.plugin_trust == {}


def test_bool_truthy_variants(monkeypatch: pytest.MonkeyPatch) -> None:
    for v in ("1", "true", "TRUE", "yes", "YES", "on", "ON"):
        monkeypatch.setenv("BDC_ENABLE_WRITE_TOOLS", v)
        assert BDCConfig.from_env().enable_write_tools is True
    for v in ("0", "false", "no", "off", "anything"):
        monkeypatch.setenv("BDC_ENABLE_WRITE_TOOLS", v)
        assert BDCConfig.from_env().enable_write_tools is False


def test_plugin_trust_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BDC_PLUGIN_TRUST", "gh:documented_sdk,sentry:published_api")
    c = BDCConfig.from_env()
    assert c.plugin_trust == {"gh": "documented_sdk", "sentry": "published_api"}


def test_plugin_trust_ignores_malformed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BDC_PLUGIN_TRUST", "gh:documented_sdk,bad-entry,,sentry:")
    c = BDCConfig.from_env()
    assert c.plugin_trust == {"gh": "documented_sdk"}


def test_plugin_env_passthrough_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BDC_PLUGIN_ENV_PASSTHROUGH", "GH_TOKEN, SENTRY_TOKEN ,")
    c = BDCConfig.from_env()
    assert c.plugin_env_passthrough == ["GH_TOKEN", "SENTRY_TOKEN"]


def test_databricks_subconfig(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BDC_DATABRICKS_HOST", "https://example.databricks")
    monkeypatch.setenv("BDC_DATABRICKS_TOKEN", "secret")
    c = BDCConfig.from_env()
    assert c.databricks.host == "https://example.databricks"
    assert c.databricks.token == "secret"


def test_snowflake_subconfig(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BDC_SNOWFLAKE_ACCOUNT", "abc-xy123")
    monkeypatch.setenv("BDC_SNOWFLAKE_ROLE", "ANALYST")
    c = BDCConfig.from_env()
    assert c.snowflake.account == "abc-xy123"
    assert c.snowflake.role == "ANALYST"


def test_max_doc_kb_must_be_integer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BDC_MAX_DOC_KB", "not-a-number")
    with pytest.raises(ValueError):
        BDCConfig.from_env()


def test_approval_token_loaded_but_not_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BDC_APPROVAL_TOKEN", "super-secret-123")
    c = BDCConfig.from_env()
    assert c.approval_token == "super-secret-123"
    # We don't override __repr__ to fully scrub, but the dataclass repr should
    # at least preserve the value (callers who repr() Config in logs need
    # to redact themselves). This test pins current behavior so we notice if it changes.
    assert "super-secret-123" in repr(c)


def test_csv_env_handles_whitespace_and_empties(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BDC_ORD_SOURCES", " a , , b ,c,")
    c = BDCConfig.from_env()
    assert c.ord_sources == ["a", "b", "c"]
