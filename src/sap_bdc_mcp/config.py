"""Configuration loading and validation.

File: src/sap_bdc_mcp/config.py
Version: v2
"""

from __future__ import annotations

from dataclasses import dataclass, field
from os import getenv
from typing import Dict, List

from dotenv import load_dotenv


_TRUTHY = {"1", "true", "TRUE", "yes", "YES", "on", "ON"}


def _bool_env(name: str, default: str) -> bool:
    return getenv(name, default).strip() in _TRUTHY


def _csv_env(name: str, default: str = "") -> List[str]:
    raw = getenv(name, default).strip()
    return [s.strip() for s in raw.split(",") if s.strip()]


def _int_env(name: str, default: str) -> int:
    raw = getenv(name, default).strip()
    try:
        return int(raw)
    except ValueError as e:
        raise ValueError(f"{name} must be an integer, got: {raw}") from e


@dataclass(frozen=True)
class DatabricksConfig:
    host: str = ""
    token: str = ""
    recipient: str = ""
    warehouse: str = ""

    @staticmethod
    def from_env() -> "DatabricksConfig":
        return DatabricksConfig(
            host=getenv("BDC_DATABRICKS_HOST", "").strip(),
            token=getenv("BDC_DATABRICKS_TOKEN", "").strip(),
            recipient=getenv("BDC_DATABRICKS_RECIPIENT", "").strip(),
            warehouse=getenv("BDC_DATABRICKS_WAREHOUSE", "").strip(),
        )


@dataclass(frozen=True)
class SnowflakeConfig:
    account: str = ""
    role: str = ""
    warehouse: str = ""

    @staticmethod
    def from_env() -> "SnowflakeConfig":
        return SnowflakeConfig(
            account=getenv("BDC_SNOWFLAKE_ACCOUNT", "").strip(),
            role=getenv("BDC_SNOWFLAKE_ROLE", "").strip(),
            warehouse=getenv("BDC_SNOWFLAKE_WAREHOUSE", "").strip(),
        )


def _parse_plugin_trust(raw: str) -> Dict[str, str]:
    """Parse `BDC_PLUGIN_TRUST=alias1:surface,alias2:surface` into a dict."""
    out: Dict[str, str] = {}
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry or ":" not in entry:
            continue
        alias, _, surface = entry.partition(":")
        alias = alias.strip()
        surface = surface.strip()
        if alias and surface:
            out[alias] = surface
    return out


@dataclass(frozen=True)
class BDCConfig:
    """Configuration for the BDC MCP server.

    Values are loaded from env (.env supported).
    Keep this small and explicit — it becomes a contract for deployments.
    """

    # v0.1 fields (unchanged semantics):
    mode: str
    mock_mode: bool
    verify_tls: bool
    max_doc_kb: int
    ord_sources: List[str]
    plugins: List[str]
    enable_write_tools: bool

    # v0.2 additions (defaults are safe):
    enable_admin_tools: bool = False
    require_dry_run: bool = True
    require_approval_token: bool = True
    approval_token: str = ""
    audit_enabled: bool = True
    audit_log_path: str = ".sap_bdc_mcp/audit.jsonl"
    api_policy_strict: bool = True
    max_result_items: int = 50
    plugin_env_passthrough: List[str] = field(default_factory=list)
    plugin_trust: Dict[str, str] = field(default_factory=dict)
    databricks: DatabricksConfig = field(default_factory=DatabricksConfig)
    snowflake: SnowflakeConfig = field(default_factory=SnowflakeConfig)

    @staticmethod
    def from_env() -> "BDCConfig":
        load_dotenv()

        return BDCConfig(
            mode=getenv("BDC_MODE", "local").strip(),
            mock_mode=_bool_env("BDC_MOCK_MODE", "0"),
            verify_tls=_bool_env("BDC_VERIFY_TLS", "1"),
            max_doc_kb=_int_env("BDC_MAX_DOC_KB", "512"),
            ord_sources=_csv_env("BDC_ORD_SOURCES"),
            plugins=_csv_env("BDC_PLUGINS"),
            enable_write_tools=_bool_env("BDC_ENABLE_WRITE_TOOLS", "0"),
            enable_admin_tools=_bool_env("BDC_ENABLE_ADMIN_TOOLS", "0"),
            require_dry_run=_bool_env("BDC_REQUIRE_DRY_RUN", "1"),
            require_approval_token=_bool_env("BDC_REQUIRE_APPROVAL_TOKEN", "1"),
            approval_token=getenv("BDC_APPROVAL_TOKEN", "").strip(),
            audit_enabled=_bool_env("BDC_AUDIT_ENABLED", "1"),
            audit_log_path=getenv("BDC_AUDIT_LOG_PATH", ".sap_bdc_mcp/audit.jsonl").strip(),
            api_policy_strict=_bool_env("BDC_API_POLICY_STRICT", "1"),
            max_result_items=_int_env("BDC_MAX_RESULT_ITEMS", "50"),
            plugin_env_passthrough=_csv_env("BDC_PLUGIN_ENV_PASSTHROUGH"),
            plugin_trust=_parse_plugin_trust(getenv("BDC_PLUGIN_TRUST", "")),
            databricks=DatabricksConfig.from_env(),
            snowflake=SnowflakeConfig.from_env(),
        )
