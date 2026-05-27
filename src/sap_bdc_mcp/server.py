"""Server construction.

File: src/sap_bdc_mcp/server.py
Version: v4
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .audit import AuditWriter
from .config import BDCConfig
from .plugin_loader import load_plugins
from .providers import default_registry
from .providers.databricks import DatabricksProvider
from .providers.snowflake import SnowflakeProvider
from .tools._gated import ToolContext
from .tools.metadata import MetadataRegistry
from .tools.registry import register_all_tools


def build_server() -> FastMCP:
    config = BDCConfig.from_env()

    mcp = FastMCP(
        "SAP Business Data Cloud MCP",
        instructions=(
            "Expose BDC discovery + contract validation + governed execution tools "
            "with safe defaults. Write/admin tools are gated and disabled by default."
        ),
        json_response=True,
    )

    # Build the runtime context first so plugin proxies can hook into the
    # same metadata + audit registries as first-party tools (Phase 6).
    audit = AuditWriter(config.audit_log_path, enabled=config.audit_enabled)
    metadata = MetadataRegistry()

    # Provider registry (Phase 3): built-in providers are registered before
    # tool registration so ctx.providers is populated when share/databricks/
    # snowflake tools register.
    providers = default_registry()
    providers.register(DatabricksProvider(config))
    providers.register(SnowflakeProvider(config))

    ctx = ToolContext(
        config=config,
        audit=audit,
        metadata=metadata,
        plugin_status=[],
        providers=providers,
    )

    # First-party tools register against ctx; then subprocess plugin proxies
    # are added so their namespaced names cannot collide with built-ins.
    register_all_tools(mcp, ctx)

    plugin_status = load_plugins(mcp, ctx)
    ctx.plugin_status.extend(plugin_status)

    return mcp
