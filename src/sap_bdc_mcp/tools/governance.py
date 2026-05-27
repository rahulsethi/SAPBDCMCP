"""Governance tools — risk catalog, policy explain, API policy check, audit tail.

File: src/sap_bdc_mcp/tools/governance.py
Version: v1
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..policy_evidence import check_or_block
from ._gated import ToolContext, gated
from .metadata import APISurface, Mutability, Risk, ToolMetadata


_META = {
    "bdc_tool_risk_catalog": ToolMetadata(
        name="bdc_tool_risk_catalog",
        category="governance",
        mutability=Mutability.READ,
        risk=Risk.LOW,
        api_surface=APISurface.PUBLISHED_API,
        api_evidence="sap-bdc-mcp.governance.risk_catalog",
        description="List all registered tools with their risk metadata.",
    ),
    "bdc_policy_explain": ToolMetadata(
        name="bdc_policy_explain",
        category="governance",
        mutability=Mutability.READ,
        risk=Risk.LOW,
        api_surface=APISurface.PUBLISHED_API,
        api_evidence="sap-bdc-mcp.governance.policy_explain",
        description="Explain how policy gates would evaluate a tool right now.",
    ),
    "bdc_api_policy_check": ToolMetadata(
        name="bdc_api_policy_check",
        category="governance",
        mutability=Mutability.READ,
        risk=Risk.LOW,
        api_surface=APISurface.PUBLISHED_API,
        api_evidence="sap-bdc-mcp.governance.api_policy_check",
        description="Summarize SAP API policy evidence per tool.",
    ),
    "bdc_audit_tail": ToolMetadata(
        name="bdc_audit_tail",
        category="governance",
        mutability=Mutability.READ,
        risk=Risk.LOW,
        api_surface=APISurface.PUBLISHED_API,
        api_evidence="sap-bdc-mcp.governance.audit_tail",
        description="Return recent audit events (redacted).",
    ),
}


def register(server: Any, ctx: ToolContext) -> None:
    config = ctx.config

    @gated(server, ctx, meta=_META["bdc_tool_risk_catalog"])
    def bdc_tool_risk_catalog(category: Optional[str] = None) -> Dict:
        """List tools + risk metadata. Optional `category` filter."""
        items = ctx.metadata.all(category=category)
        return {
            "count": len(items),
            "tools": [m.model_dump(mode="json") for m in items],
        }

    @gated(server, ctx, meta=_META["bdc_policy_explain"])
    def bdc_policy_explain(tool_name: str) -> Dict:
        """Explain whether a tool would be allowed right now and which gates apply."""
        meta = ctx.metadata.get(tool_name)
        if meta is None:
            return {"ok": False, "error": f"Unknown tool: {tool_name}"}

        gates: List[Dict] = []

        ev = check_or_block(meta, strict=config.api_policy_strict)
        gates.append(
            {
                "gate": "policy_evidence",
                "status": "ok" if ev.allowed else "block",
                "reason": ev.reason,
            }
        )

        if meta.mutability == Mutability.WRITE:
            gates.append(
                {
                    "gate": "write_enable",
                    "status": "ok" if config.enable_write_tools else "block",
                    "reason": None if config.enable_write_tools else "BDC_ENABLE_WRITE_TOOLS=0",
                }
            )
        if meta.mutability == Mutability.ADMIN:
            gates.append(
                {
                    "gate": "admin_enable",
                    "status": "ok" if config.enable_admin_tools else "block",
                    "reason": None if config.enable_admin_tools else "BDC_ENABLE_ADMIN_TOOLS=0",
                }
            )
        if meta.requires_dry_run:
            gates.append(
                {
                    "gate": "dry_run_required",
                    "status": "info",
                    "reason": "Call with dry_run=True first; supply correlation_id on real execute.",
                }
            )
        if meta.requires_approval:
            gates.append(
                {
                    "gate": "approval_token",
                    "status": "info",
                    "reason": (
                        "BDC_APPROVAL_TOKEN must be set and supplied as approval_token "
                        "on real execute."
                    ),
                }
            )

        would_allow = all(g["status"] != "block" for g in gates)
        return {
            "tool": tool_name,
            "would_allow": would_allow,
            "gates": gates,
            "metadata": meta.model_dump(mode="json"),
        }

    @gated(server, ctx, meta=_META["bdc_api_policy_check"])
    def bdc_api_policy_check(tool_name: Optional[str] = None) -> Dict:
        """SAP API policy evidence summary per tool (or for one tool)."""
        items = [ctx.metadata.get(tool_name)] if tool_name else ctx.metadata.all()
        items = [m for m in items if m is not None]
        report = []
        unknown_write_count = 0
        for m in items:
            ev = check_or_block(m, strict=config.api_policy_strict)
            entry = {
                "name": m.name,
                "mutability": m.mutability.value,
                "api_surface": m.api_surface.value,
                "api_evidence": m.api_evidence,
                "api_evidence_url": m.api_evidence_url,
                "would_block_under_strict": (not ev.allowed),
            }
            if m.mutability != Mutability.READ and m.api_surface == APISurface.UNKNOWN:
                unknown_write_count += 1
            report.append(entry)
        return {
            "strict_mode": config.api_policy_strict,
            "tools": report,
            "unknown_surface_write_admin_count": unknown_write_count,
        }

    @gated(server, ctx, meta=_META["bdc_audit_tail"])
    def bdc_audit_tail(limit: int = 50, since_timestamp: Optional[str] = None) -> Dict:
        """Return last N audit events. Capped at BDC_MAX_RESULT_ITEMS."""
        cap = config.max_result_items
        effective = max(1, min(int(limit), cap))
        events = ctx.audit.tail(limit=effective, since_timestamp=since_timestamp)
        return {"count": len(events), "events": events}
