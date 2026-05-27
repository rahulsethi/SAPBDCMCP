"""Core tools: ping, diagnostics, tenant info, whoami.

File: src/sap_bdc_mcp/tools/core.py
Version: v3
"""

from __future__ import annotations

import os
from typing import Any

from .. import __version__
from ..redaction import redact
from ._gated import ToolContext, gated
from .metadata import v01_metadata_list


_META = {m.name: m for m in v01_metadata_list()}


def register(server: Any, ctx: ToolContext) -> None:
    config = ctx.config
    plugin_status = ctx.plugin_status

    @gated(server, ctx, meta=_META["bdc_ping"])
    def bdc_ping() -> dict:
        """Lightweight health check for config & wiring."""
        return {
            "ok": True,
            "server": "sap-bdc-mcp",
            "version": __version__,
            "mode": config.mode,
            "mock_mode": config.mock_mode,
            "write_enabled": config.enable_write_tools,
            "admin_enabled": config.enable_admin_tools,
            "audit_enabled": config.audit_enabled,
        }

    @gated(server, ctx, meta=_META["bdc_diagnostics"])
    def bdc_diagnostics() -> dict:
        """Structured environment + readiness report (no secrets)."""
        data = {
            "mode": config.mode,
            "mock_mode": config.mock_mode,
            "verify_tls": config.verify_tls,
            "max_doc_kb": config.max_doc_kb,
            "ord_sources": config.ord_sources,
            "plugins": [p.__dict__ for p in plugin_status],
            "write_enabled": config.enable_write_tools,
            "admin_enabled": config.enable_admin_tools,
            "audit_enabled": config.audit_enabled,
            "audit_log_path": config.audit_log_path,
            "api_policy_strict": config.api_policy_strict,
            "tool_count": len(ctx.metadata),
        }
        return redact(data)

    @gated(server, ctx, meta=_META["bdc_get_tenant_info"])
    def bdc_get_tenant_info() -> dict:
        """Get tenant information from environment/config (redacted)."""
        tenant_info = {
            "mode": config.mode,
            "mock_mode": config.mock_mode,
            "tenant_id": os.getenv("BDC_TENANT_ID"),
            "region": os.getenv("BDC_REGION"),
            "base_url": os.getenv("BDC_BASE_URL"),
        }
        return redact(tenant_info)

    @gated(server, ctx, meta=_META["bdc_whoami"])
    def bdc_whoami() -> dict:
        """Get current user/identity information (where supported, redacted)."""
        identity: dict = {
            "mode": config.mode,
            "mock_mode": config.mock_mode,
            "user": os.getenv("BDC_USER"),
            "service_account": os.getenv("BDC_SERVICE_ACCOUNT"),
        }
        if config.mock_mode:
            identity["user"] = "mock_user"
            identity["mock"] = True
        return redact(identity)
