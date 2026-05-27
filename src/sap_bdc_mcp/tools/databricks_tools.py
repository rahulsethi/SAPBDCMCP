"""Databricks-specific MCP tools.

File: src/sap_bdc_mcp/tools/databricks_tools.py
Version: v1

Three READ tools:

  - ``bdc_databricks_preflight``
  - ``bdc_databricks_validate_share_readiness``
  - ``bdc_databricks_generate_csn_from_share``

All cite ``bdc-connect-sdk.databricks.<x>`` evidence — the SDK is the
documented surface even though v0.2 calls the mock fixture path.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from ..providers.base import ProviderContext
from ..providers.databricks import (
    generate_csn_from_share,
    lookup_recipient,
    lookup_share,
)
from ._gated import ToolContext, gated
from .metadata import APISurface, Mutability, Risk, ToolMetadata


_META = {
    "bdc_databricks_preflight": ToolMetadata(
        name="bdc_databricks_preflight",
        category="databricks",
        mutability=Mutability.READ,
        risk=Risk.LOW,
        provider="databricks",
        api_surface=APISurface.DOCUMENTED_SDK,
        api_evidence="bdc-connect-sdk.databricks.preflight",
        description="Probe Databricks configuration shape (mock-aware).",
    ),
    "bdc_databricks_validate_share_readiness": ToolMetadata(
        name="bdc_databricks_validate_share_readiness",
        category="databricks",
        mutability=Mutability.READ,
        risk=Risk.LOW,
        provider="databricks",
        api_surface=APISurface.DOCUMENTED_SDK,
        api_evidence="bdc-connect-sdk.databricks.share_readiness",
        description="Check whether a Databricks share is ready to publish.",
    ),
    "bdc_databricks_generate_csn_from_share": ToolMetadata(
        name="bdc_databricks_generate_csn_from_share",
        category="databricks",
        mutability=Mutability.READ,
        risk=Risk.LOW,
        provider="databricks",
        api_surface=APISurface.DOCUMENTED_SDK,
        api_evidence="bdc-connect-sdk.databricks.csn_from_share",
        description="Generate CSN-ish artifact from a Databricks share (D-006).",
    ),
}


def register(server: Any, ctx: ToolContext) -> None:
    registry = ctx.providers

    @gated(server, ctx, meta=_META["bdc_databricks_preflight"])
    def bdc_databricks_preflight(mock_mode: Optional[bool] = None) -> Dict:
        """Run the Databricks provider's preflight probes.

        ``mock_mode`` overrides the server-level flag for this call only —
        useful when an operator wants to test the real-mode failure surface
        without restarting the server.
        """
        if registry is None:
            return {"ok": False, "error": "provider registry not initialized"}
        provider = registry.get("databricks")
        if provider is None:
            return {"ok": False, "error": "databricks provider not registered"}
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

    @gated(server, ctx, meta=_META["bdc_databricks_validate_share_readiness"])
    def bdc_databricks_validate_share_readiness(share_name: str) -> Dict:
        """Verify a Databricks share is present + has a registered recipient.

        Mock-mode driven at v0.2 — fixture lookup only. Returns a structured
        "not found" result instead of raising when the share is missing.
        """
        share = lookup_share(share_name)
        if share is None:
            return {
                "ok": False,
                "share_name": share_name,
                "reason": "share_not_found",
                "hint": "Add the share to fixtures/databricks_share_mock.json (mock mode).",
            }
        recipient = lookup_recipient(share.recipient) if share.recipient else None
        ready = recipient is not None
        return {
            "ok": ready,
            "share_name": share_name,
            "recipient": share.recipient,
            "recipient_registered": recipient is not None,
            "schema_count": len(share.schemas),
            "comment": share.comment,
            "next_steps": (
                ["Share is ready to publish (mock)."]
                if ready
                else [
                    f"Recipient '{share.recipient}' is not registered. Add it via "
                    "BDC_DATABRICKS_RECIPIENT or fixtures/databricks_recipient_mock.json."
                ]
            ),
        }

    @gated(server, ctx, meta=_META["bdc_databricks_generate_csn_from_share"])
    def bdc_databricks_generate_csn_from_share(share_name: str, format: str = "json") -> Dict:
        """Generate a CSN artifact from a Databricks share (D-006).

        ``format`` is one of ``"json"`` (default), ``"cds"``, ``"draft"``.
        Returns a refusal dict for shares containing complex columns.
        """
        return generate_csn_from_share(share_name, format=format)
