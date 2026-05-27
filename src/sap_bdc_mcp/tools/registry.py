"""Tool registration orchestrator.

File: src/sap_bdc_mcp/tools/registry.py
Version: v3

v0.2: every tool is registered through the gated wrapper (see _gated.py).
ToolContext is built by server.py and passed in here. Phase 3 adds the
provider-introspection + Databricks tools; Phase 4 adds Snowflake.
"""

from __future__ import annotations

from typing import Any

from . import (
    core,
    csn_tools,
    databricks_tools,
    governance,
    ord_tools,
    providers_tools,
    share_tools,
    snowflake_tools,
)
from ._gated import ToolContext


def register_all_tools(server: Any, ctx: ToolContext) -> None:
    core.register(server, ctx)
    ord_tools.register(server, ctx)
    csn_tools.register(server, ctx)
    share_tools.register(server, ctx)
    governance.register(server, ctx)
    providers_tools.register(server, ctx)
    databricks_tools.register(server, ctx)
    snowflake_tools.register(server, ctx)
