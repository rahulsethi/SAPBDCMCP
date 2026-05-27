"""Snowflake-specific MCP tools.

File: src/sap_bdc_mcp/tools/snowflake_tools.py
Version: v1

Two READ tools — no mutation paths (Snowflake is readiness-only at v0.2):

  - ``bdc_snowflake_preflight``     — config-shape probe.
  - ``bdc_snowflake_explain_flow``  — documented flow text + v0.3 deferral note.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from ..providers.base import ProviderContext
from ..providers.snowflake import EXPLAIN_FLOW_TEXT
from ._gated import ToolContext, gated
from .metadata import APISurface, Mutability, Risk, ToolMetadata


_META = {
    "bdc_snowflake_preflight": ToolMetadata(
        name="bdc_snowflake_preflight",
        category="snowflake",
        mutability=Mutability.READ,
        risk=Risk.LOW,
        provider="snowflake",
        api_surface=APISurface.DOCUMENTED_SDK,
        api_evidence="bdc-connect-sdk.snowflake.preflight",
        description="Probe Snowflake configuration shape (readiness only at v0.2).",
    ),
    "bdc_snowflake_explain_flow": ToolMetadata(
        name="bdc_snowflake_explain_flow",
        category="snowflake",
        mutability=Mutability.READ,
        risk=Risk.LOW,
        provider="snowflake",
        api_surface=APISurface.DOCUMENTED_SDK,
        api_evidence="bdc-connect-sdk.snowflake.flow_documentation",
        description="Return the documented Snowflake sharing flow text.",
    ),
}


def register(server: Any, ctx: ToolContext) -> None:
    registry = ctx.providers

    @gated(server, ctx, meta=_META["bdc_snowflake_preflight"])
    def bdc_snowflake_preflight(mock_mode: Optional[bool] = None) -> Dict:
        """Run the Snowflake provider's preflight probes."""
        if registry is None:
            return {"ok": False, "error": "provider registry not initialized"}
        provider = registry.get("snowflake")
        if provider is None:
            return {"ok": False, "error": "snowflake provider not registered"}
        effective = ctx.config.mock_mode if mock_mode is None else bool(mock_mode)
        pctx = ProviderContext(
            mock_mode=effective,
            config_snapshot={"mock_mode": effective, "mode": ctx.config.mode},
        )
        result = asyncio.run(provider.preflight(pctx))
        return {
            "ok": result.ok,
            "mock_mode": effective,
            "checks": result.checks,
            "blockers": result.blockers,
        }

    @gated(server, ctx, meta=_META["bdc_snowflake_explain_flow"])
    def bdc_snowflake_explain_flow() -> Dict:
        """Return the documented Snowflake sharing flow + v0.3 deferral note."""
        return {
            "ok": True,
            "flow": EXPLAIN_FLOW_TEXT,
            "execution_status": "deferred_to_v0.3",
            "note": (
                "Snowflake share execution is deferred to v0.3. v0.2 only "
                "documents the prerequisites and verifies configuration "
                "shape via bdc_snowflake_preflight."
            ),
        }
