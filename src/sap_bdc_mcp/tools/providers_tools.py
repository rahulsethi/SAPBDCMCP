"""Provider-introspection tools.

File: src/sap_bdc_mcp/tools/providers_tools.py
Version: v1

Three READ tools that surface the provider registry without exposing secrets:

  - ``bdc_connect_list_providers`` — names + capabilities + configured-bit.
  - ``bdc_connect_diagnostics``    — config-shape health, redacted.
  - ``bdc_connect_preflight``      — calls ``provider.preflight()``.

api_evidence values cite ``sap-bdc-mcp.providers.<x>`` — these tools are
sap-bdc-mcp's own published surface, not a wrapped SDK call.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from ..providers.base import ProviderContext
from ..redaction import redact
from ._gated import ToolContext, gated
from .metadata import APISurface, Mutability, Risk, ToolMetadata


_META = {
    "bdc_connect_list_providers": ToolMetadata(
        name="bdc_connect_list_providers",
        category="providers",
        mutability=Mutability.READ,
        risk=Risk.LOW,
        api_surface=APISurface.PUBLISHED_API,
        api_evidence="sap-bdc-mcp.providers.list",
        description="List registered BDC Connect providers + capability flags.",
    ),
    "bdc_connect_diagnostics": ToolMetadata(
        name="bdc_connect_diagnostics",
        category="providers",
        mutability=Mutability.READ,
        risk=Risk.LOW,
        api_surface=APISurface.PUBLISHED_API,
        api_evidence="sap-bdc-mcp.providers.diagnostics",
        description="Provider configuration health (redacted; no secrets exposed).",
    ),
    "bdc_connect_preflight": ToolMetadata(
        name="bdc_connect_preflight",
        category="providers",
        mutability=Mutability.READ,
        risk=Risk.LOW,
        api_surface=APISurface.PUBLISHED_API,
        api_evidence="sap-bdc-mcp.providers.preflight",
        description="Run a provider's preflight() probe and return the structured result.",
    ),
}


def _redacted_config_snapshot(ctx: ToolContext) -> Dict[str, Any]:
    """Return a small, redacted snapshot of operator-relevant config flags."""
    cfg = ctx.config
    return redact(
        {
            "mode": cfg.mode,
            "mock_mode": cfg.mock_mode,
            "verify_tls": cfg.verify_tls,
            "api_policy_strict": cfg.api_policy_strict,
            "audit_enabled": cfg.audit_enabled,
        }
    )


def _run(coro: Any) -> Any:
    """Run an awaitable from sync code. Server tool callbacks are sync."""
    return asyncio.run(coro)


def register(server: Any, ctx: ToolContext) -> None:
    registry = ctx.providers

    @gated(server, ctx, meta=_META["bdc_connect_list_providers"])
    def bdc_connect_list_providers() -> Dict:
        """List provider names + capabilities + whether the provider is configured."""
        if registry is None:
            return {"providers": [], "note": "provider registry not initialized"}
        out = []
        for name in registry.list_names():
            provider = registry.get(name)
            if provider is None:  # pragma: no cover — defensive
                continue
            caps = provider.capabilities()
            configured = _is_configured(name, ctx)
            out.append(
                {
                    "name": name,
                    "configured": configured,
                    "capabilities": {
                        "supports_preflight": caps.supports_preflight,
                        "supports_validate_plan": caps.supports_validate_plan,
                        "supports_dry_run": caps.supports_dry_run,
                        "supports_execute": caps.supports_execute,
                        "notes": caps.notes,
                    },
                }
            )
        return {"providers": out}

    @gated(server, ctx, meta=_META["bdc_connect_diagnostics"])
    def bdc_connect_diagnostics(provider_name: Optional[str] = None) -> Dict:
        """Report configuration health for one or all providers (no secrets)."""
        if registry is None:
            return {"ok": False, "error": "provider registry not initialized"}
        names = [provider_name] if provider_name else registry.list_names()
        reports = []
        for name in names:
            if name is None:
                continue
            provider = registry.get(name)
            if provider is None:
                reports.append({"name": name, "ok": False, "error": "provider not registered"})
                continue
            reports.append(
                {
                    "name": name,
                    "configured": _is_configured(name, ctx),
                    "config_shape": _redact_provider_config(name, ctx),
                }
            )
        return {"providers": reports, "server_config": _redacted_config_snapshot(ctx)}

    @gated(server, ctx, meta=_META["bdc_connect_preflight"])
    def bdc_connect_preflight(provider_name: str) -> Dict:
        """Run ``provider.preflight()`` and return the structured result."""
        if registry is None:
            return {"ok": False, "error": "provider registry not initialized"}
        provider = registry.get(provider_name)
        if provider is None:
            return {
                "ok": False,
                "error": f"provider '{provider_name}' is not registered",
                "available_providers": registry.list_names(),
            }
        pctx = ProviderContext(
            mock_mode=ctx.config.mock_mode,
            config_snapshot=_redacted_config_snapshot(ctx),
        )
        result = _run(provider.preflight(pctx))
        return {
            "provider": provider_name,
            "ok": result.ok,
            "checks": result.checks,
            "blockers": result.blockers,
        }


def _is_configured(name: str, ctx: ToolContext) -> bool:
    """Return True if the provider has any of its env vars set."""
    cfg = ctx.config
    if name == "databricks":
        d = cfg.databricks
        return bool(d.host or d.token or d.recipient or d.warehouse)
    if name == "snowflake":
        s = cfg.snowflake
        return bool(s.account or s.role or s.warehouse)
    return False


def _redact_provider_config(name: str, ctx: ToolContext) -> Dict[str, Any]:
    """Return a redacted view of a provider's configured fields.

    Boolean ``present`` flags only — never the values themselves.
    """
    cfg = ctx.config
    if name == "databricks":
        d = cfg.databricks
        return {
            "host_present": bool(d.host),
            "token_present": bool(d.token),
            "recipient_present": bool(d.recipient),
            "warehouse_present": bool(d.warehouse),
        }
    if name == "snowflake":
        s = cfg.snowflake
        return {
            "account_present": bool(s.account),
            "role_present": bool(s.role),
            "warehouse_present": bool(s.warehouse),
        }
    return {}
