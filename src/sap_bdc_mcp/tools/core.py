"""Core tools: ping, diagnostics.

File: src/sap_bdc_mcp/tools/core.py
Version: v1
"""

from __future__ import annotations

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
