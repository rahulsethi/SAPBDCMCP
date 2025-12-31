"""Core tools: ping, diagnostics, tenant info, whoami.

File: src/sap_bdc_mcp/tools/core.py
Version: v2
"""

from __future__ import annotations

import os
from typing import Any, List

from ..config import BDCConfig
from ..plugin_loader import PluginLoadResult
from ..redaction import redact


def register(server: Any, config: BDCConfig, plugin_status: List[PluginLoadResult]) -> None:
    @server.tool()
    def bdc_ping() -> dict:
        """Lightweight health check for config & wiring."""
        return {
            "ok": True,
            "server": "sap-bdc-mcp",
            "version": "0.1.0",
            "mode": config.mode,
            "mock_mode": config.mock_mode,
            "write_enabled": config.enable_write_tools,
        }

    @server.tool()
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
        }
        return redact(data)

    @server.tool()
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

    @server.tool()
    def bdc_whoami() -> dict:
        """Get current user/identity information (where supported, redacted)."""
        identity = {
            "mode": config.mode,
            "mock_mode": config.mock_mode,
            "user": os.getenv("BDC_USER"),
            "service_account": os.getenv("BDC_SERVICE_ACCOUNT"),
        }
        # In mock mode, return a mock identity
        if config.mock_mode:
            identity["user"] = "mock_user"
            identity["mock"] = True
        
        return redact(identity)
