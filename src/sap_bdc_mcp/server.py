"""Server construction.

File: src/sap_bdc_mcp/server.py
Version: v1
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .config import BDCConfig
from .plugin_loader import load_plugins
from .tools.registry import register_all_tools


def build_server() -> FastMCP:
    config = BDCConfig.from_env()

    mcp = FastMCP(
        "SAP Business Data Cloud MCP",
        instructions=(
            "Expose BDC discovery + contract validation tools with safe defaults. "
            "Write tools are gated and disabled by default."
        ),
        json_response=True,
    )

    plugin_status = load_plugins(mcp, config)
    register_all_tools(mcp, config, plugin_status)

    return mcp
