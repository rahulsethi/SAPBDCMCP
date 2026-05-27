"""Snowflake BDC Connect provider — readiness only at v0.2.

File: src/sap_bdc_mcp/providers/snowflake.py
Version: v1

Capabilities at v0.2 (per ADR-002 / Plan/04):

  - supports_preflight = True
  - supports_validate_plan = True
  - supports_dry_run = False  -> raises ProviderCapabilityError
  - supports_execute = False  -> raises ProviderCapabilityError

The share-execute wrapper catches :class:`ProviderCapabilityError` and emits
a structured block so no raise reaches the MCP caller.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..config import BDCConfig
from ..models.share_plan import SharePlan
from .base import (
    BDCConnectProvider,
    ExecutionPreview,
    ExecutionResult,
    PlanValidation,
    PreflightResult,
    ProviderCapabilities,
    ProviderCapabilityError,
    ProviderContext,
)


# Plain-English description of the documented sharing flow, surfaced by
# ``bdc_snowflake_explain_flow``.
EXPLAIN_FLOW_TEXT = (
    "Snowflake sharing flow (readiness-only at v0.2):\n"
    "  1. Provider creates an OUTBOUND share using CREATE SHARE.\n"
    "  2. Provider grants USAGE/SELECT on schemas/tables to the share.\n"
    "  3. Provider adds a consumer account: ALTER SHARE ADD ACCOUNTS=...\n"
    "  4. Consumer creates a database from the share: CREATE DATABASE FROM SHARE ....\n"
    "  5. Consumer grants IMPORTED PRIVILEGES on the new database to roles.\n"
    "v0.2 verifies the operator has the credentials + role for steps 1-3; the "
    "actual SQL is documented but not executed by this MCP server. Execution "
    "is deferred to v0.3."
)


class SnowflakeProvider(BDCConnectProvider):
    """Readiness-only Snowflake provider."""

    name = "snowflake"

    def __init__(self, config: BDCConfig) -> None:
        self._config = config

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_preflight=True,
            supports_validate_plan=True,
            supports_dry_run=False,
            supports_execute=False,
            notes=(
                "Readiness-only at v0.2. dry_run_execute and execute raise "
                "ProviderCapabilityError; the share-execute wrapper translates "
                "this into a structured block. Execution is deferred to v0.3."
            ),
        )

    async def preflight(self, ctx: ProviderContext) -> PreflightResult:
        cfg = self._config.snowflake
        checks: List[Dict[str, Any]] = []
        blockers: List[str] = []

        def _add(name: str, ok: bool, detail: str, *, blocker: Optional[str] = None) -> None:
            checks.append({"name": name, "ok": ok, "detail": detail})
            if not ok and blocker:
                blockers.append(blocker)

        account_ok = bool(cfg.account) or ctx.mock_mode
        _add(
            "account_configured",
            account_ok,
            (
                "mock_mode=1; not probed"
                if ctx.mock_mode
                else (f"account={cfg.account}" if cfg.account else "BDC_SNOWFLAKE_ACCOUNT is empty")
            ),
            blocker=None if account_ok else "Set BDC_SNOWFLAKE_ACCOUNT.",
        )

        role_ok = bool(cfg.role) or ctx.mock_mode
        _add(
            "role_configured",
            role_ok,
            (
                "mock_mode=1; not probed"
                if ctx.mock_mode
                else (f"role={cfg.role}" if cfg.role else "BDC_SNOWFLAKE_ROLE is empty")
            ),
            blocker=None if role_ok else "Set BDC_SNOWFLAKE_ROLE.",
        )

        warehouse_ok = bool(cfg.warehouse) or ctx.mock_mode
        _add(
            "warehouse_configured",
            warehouse_ok,
            (
                "mock_mode=1; not probed"
                if ctx.mock_mode
                else (
                    f"warehouse={cfg.warehouse}"
                    if cfg.warehouse
                    else "BDC_SNOWFLAKE_WAREHOUSE is empty"
                )
            ),
            blocker=None if warehouse_ok else "Set BDC_SNOWFLAKE_WAREHOUSE.",
        )

        ok = all(c["ok"] for c in checks)
        return PreflightResult(ok=ok, checks=checks, blockers=blockers)

    async def validate_plan(self, plan: SharePlan, ctx: ProviderContext) -> PlanValidation:
        issues: List[Dict[str, Any]] = []
        if not plan.name or not plan.name.strip():
            issues.append({"code": "INVALID_PLAN_NAME", "message": "plan.name is empty"})
        if not plan.assets:
            issues.append({"code": "EMPTY_PLAN", "message": "plan has no assets"})
        for i, asset in enumerate(plan.assets):
            if not asset.name or not asset.name.strip():
                issues.append(
                    {
                        "code": "INVALID_ASSET_NAME",
                        "asset_index": i,
                        "message": "asset name empty",
                    }
                )
        return PlanValidation(ok=(not issues), issues=issues)

    async def dry_run_execute(self, plan: SharePlan, ctx: ProviderContext) -> ExecutionPreview:
        raise ProviderCapabilityError(
            "Snowflake execution is readiness-only at v0.2; deferred to v0.3."
        )

    async def execute(
        self, plan: SharePlan, ctx: ProviderContext, approval_token: str
    ) -> ExecutionResult:
        raise ProviderCapabilityError(
            "Snowflake execution is readiness-only at v0.2; deferred to v0.3."
        )
