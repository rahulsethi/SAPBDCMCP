"""Share planning tools — plan + validate (v0.1) + execute (v0.2 high-risk).

File: src/sap_bdc_mcp/tools/share_tools.py
Version: v5
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Dict, List, Optional

from ..models.share_plan import ShareAsset, SharePlan
from ..policy import RiskLevel, ToolPermission, ToolPolicy, approval_token_valid
from ..providers.base import ProviderCapabilityError, ProviderContext
from ._gated import ToolContext, gated
from .metadata import (
    APISurface,
    BulkDataBehavior,
    Mutability,
    Risk,
    ToolMetadata,
    v01_metadata_list,
)


_V01_META = {m.name: m for m in v01_metadata_list()}

# Retained from v0.1 for backward-compat with anything that may import it.
SHARE_VALIDATE_POLICY = ToolPolicy(permission=ToolPermission.READ, risk=RiskLevel.MEDIUM)


def _validate_contract(plan: Dict) -> Dict:
    """Pure validation — used by both the gated tool and by execute_plan.

    Returning a plain dict avoids writing a second audit event when
    ``bdc_share_execute_plan`` needs the same checks during its gate chain.
    """
    issues: List[Dict] = []
    try:
        parsed = SharePlan.model_validate(plan)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "issues": [{"code": "INVALID_PLAN", "message": str(e)}]}

    if len(parsed.assets) > 50:
        issues.append(
            {
                "code": "TOO_MANY_ASSETS",
                "message": "Share plan has > 50 assets; split into multiple shares.",
            }
        )

    for i, asset in enumerate(parsed.assets):
        if not asset.name or not asset.name.strip():
            issues.append(
                {
                    "code": "INVALID_ASSET_NAME",
                    "asset_index": i,
                    "message": f"Asset at index {i} has empty or invalid name",
                }
            )
        asset_key = (asset.schema_name or "", asset.name)
        if i > 0:
            prev_assets = [(a.schema_name or "", a.name) for a in parsed.assets[:i]]
            if asset_key in prev_assets:
                issues.append(
                    {
                        "code": "DUPLICATE_ASSET",
                        "asset_index": i,
                        "asset": asset.name,
                        "message": f"Duplicate asset '{asset.name}' in share plan",
                    }
                )

    return {"ok": len(issues) == 0, "issues": issues}


# In-memory map: correlation_id -> {"provider": str, "plan_name": str}.
# Populated by a successful dry-run; required for a subsequent real execute.
_DRY_RUN_CORRELATIONS: Dict[str, Dict[str, Any]] = {}


_EXECUTE_PLAN_META = ToolMetadata(
    name="bdc_share_execute_plan",
    category="sharing",
    mutability=Mutability.WRITE,
    risk=Risk.HIGH,
    api_surface=APISurface.DOCUMENTED_SDK,
    api_evidence="bdc-connect-sdk.share.execute_v1",
    requires_dry_run=True,
    requires_approval=True,
    requires_write_enable=True,
    bulk_data_behavior=BulkDataBehavior.METADATA_ONLY,
    description="Execute a validated share plan against a provider (dry-run by default).",
)


def _new_correlation_id() -> str:
    return str(uuid.uuid4())


def _record_dry_run(correlation_id: str, provider: str, plan_name: str) -> None:
    _DRY_RUN_CORRELATIONS[correlation_id] = {
        "provider": provider,
        "plan_name": plan_name,
    }


def _consume_dry_run(correlation_id: str) -> Optional[Dict[str, Any]]:
    return _DRY_RUN_CORRELATIONS.get(correlation_id)


def _provider_surface_blocks_strict(provider: Any, strict: bool) -> Optional[str]:
    """Return a block reason if the provider's surface is UNKNOWN under strict.

    Mirrors the per-tool policy-evidence check, but at the provider level —
    matches §7.1 row #9 for synthetic plugin providers.
    """
    if not strict:
        return None
    surface = getattr(provider, "api_surface", "documented_sdk")
    # Accept either an APISurface enum or its string value.
    surface_value = getattr(surface, "value", surface)
    if str(surface_value).lower() == APISurface.UNKNOWN.value:
        return (
            f"Provider '{provider.name}' has api_surface=UNKNOWN; refusing "
            f"under BDC_API_POLICY_STRICT=1. Promote via BDC_PLUGIN_TRUST."
        )
    return None


def register(server: Any, ctx: ToolContext) -> None:
    @gated(server, ctx, meta=_V01_META["bdc_share_plan"])
    def bdc_share_plan(
        share_name: str,
        assets: List[Dict],
        description: str = "",
        provider: str = "sap-bdc",
    ) -> Dict:
        """Create a share plan object (no mutation)."""
        plan = SharePlan(
            name=share_name,
            description=description,
            provider=provider,
            assets=[ShareAsset(**a) for a in assets],
        )
        return plan.model_dump(by_alias=True)

    @gated(server, ctx, meta=_V01_META["bdc_share_validate_contract"])
    def bdc_share_validate_contract(plan: Dict) -> Dict:
        """Validate a share plan against safety limits + basic contract structure."""
        return _validate_contract(plan)

    @gated(server, ctx, meta=_EXECUTE_PLAN_META)
    def bdc_share_execute_plan(
        plan: Dict,
        provider: str,
        dry_run: bool = True,
        approval_token: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Dict:
        """Execute a share plan against a provider (dry-run by default).

        Gate chain (top to bottom):
          1. api_policy + write_enable — handled by ``gated()`` wrapper.
          2. provider registered.
          3. provider surface (UNKNOWN + strict -> block).
          4. plan schema validation (re-runs bdc_share_validate_contract).
          5. provider.validate_plan() -> issues block.
          6. provider capability for the requested action.
          7. For dry_run=False: prior dry-run correlation required.
          8. For dry_run=False: approval token must compare-equal.
          9. Provider call (dry_run -> dry_run_execute, real -> execute).
        """
        registry = ctx.providers
        if registry is None:
            return {"ok": False, "blocked_reason": "provider registry not initialized"}
        prov = registry.get(provider)
        if prov is None:
            return {
                "ok": False,
                "blocked_reason": (
                    f"provider '{provider}' is not registered; available: "
                    f"{registry.list_names() if registry else []}"
                ),
            }

        # Provider-surface policy evidence gate.
        block = _provider_surface_blocks_strict(prov, ctx.config.api_policy_strict)
        if block is not None:
            return {"ok": False, "blocked_reason": block}

        # Plan schema validation (uses the same logic as
        # bdc_share_validate_contract, but called as a pure function so no
        # second audit event is written for this single tool invocation).
        validation_result = _validate_contract(plan)
        if not validation_result.get("ok"):
            return {
                "ok": False,
                "blocked_reason": "share_validate_contract: plan invalid",
                "issues": validation_result.get("issues", []),
            }

        try:
            parsed_plan = SharePlan.model_validate(plan)
        except Exception as e:  # noqa: BLE001
            return {
                "ok": False,
                "blocked_reason": f"plan parse failed: {e}",
            }

        # Provider-specific plan validation.
        pctx = ProviderContext(
            mock_mode=ctx.config.mock_mode,
            config_snapshot={"mock_mode": ctx.config.mock_mode, "mode": ctx.config.mode},
            correlation_id=correlation_id,
        )
        try:
            plan_validation = asyncio.run(prov.validate_plan(parsed_plan, pctx))
        except ProviderCapabilityError as e:
            return {"ok": False, "blocked_reason": f"provider capability: {e}"}
        if not plan_validation.ok:
            return {
                "ok": False,
                "blocked_reason": "provider.validate_plan: issues found",
                "issues": plan_validation.issues,
            }

        caps = prov.capabilities()
        if dry_run:
            if not caps.supports_dry_run:
                return {
                    "ok": False,
                    "blocked_reason": (
                        f"provider capability: '{provider}' does not support "
                        f"dry-run execute (notes: {caps.notes})"
                    ),
                }
            try:
                preview = asyncio.run(prov.dry_run_execute(parsed_plan, pctx))
            except ProviderCapabilityError as e:
                return {"ok": False, "blocked_reason": f"provider capability: {e}"}
            if not preview.ok:
                return {
                    "ok": False,
                    "blocked_reason": "provider.dry_run_execute: preview failed",
                    "warnings": preview.warnings,
                }
            cid = correlation_id or _new_correlation_id()
            _record_dry_run(cid, provider, parsed_plan.name)
            return {
                "ok": True,
                "dry_run": True,
                "provider": provider,
                "correlation_id": cid,
                "planned_operations": preview.planned_operations,
                "warnings": preview.warnings,
                "estimated_impact": preview.estimated_impact,
            }

        # Real execute path.
        if not caps.supports_execute:
            return {
                "ok": False,
                "blocked_reason": (
                    f"provider capability: '{provider}' does not support "
                    f"execute (notes: {caps.notes})"
                ),
            }
        if ctx.config.require_dry_run:
            if correlation_id is None or _consume_dry_run(correlation_id) is None:
                return {
                    "ok": False,
                    "blocked_reason": (
                        "dry-run required: supply correlation_id from a prior "
                        "successful dry-run call against this provider."
                    ),
                }
            recorded = _consume_dry_run(correlation_id)
            assert recorded is not None  # mypy-friendly; just verified above
            if recorded["provider"] != provider or recorded["plan_name"] != parsed_plan.name:
                return {
                    "ok": False,
                    "blocked_reason": (
                        "correlation_id does not match the prior dry-run "
                        "(provider or plan name mismatch)."
                    ),
                }

        if ctx.config.require_approval_token:
            if approval_token is None:
                return {
                    "ok": False,
                    "blocked_reason": (
                        "approval token required: BDC_APPROVAL_TOKEN must be "
                        "set and supplied as `approval_token`."
                    ),
                }
            if not approval_token_valid(approval_token, ctx.config.approval_token):
                return {"ok": False, "blocked_reason": "approval token invalid"}

        try:
            result = asyncio.run(prov.execute(parsed_plan, pctx, approval_token or ""))
        except ProviderCapabilityError as e:
            return {"ok": False, "blocked_reason": f"provider capability: {e}"}
        return {
            "ok": result.ok,
            "dry_run": False,
            "provider": provider,
            "correlation_id": correlation_id,
            "status": result.status,
            "summary": result.summary,
            "next_steps": result.next_steps,
        }
