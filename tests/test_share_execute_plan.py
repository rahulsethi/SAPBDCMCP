"""bdc_share_execute_plan tests — full 9-row matrix per 06_TestPlan §7.1.

File: tests/test_share_execute_plan.py
Version: v1

The fixture pattern builds a server with the env vars each row needs.
Provider state is reset between tests so the in-memory correlation map does
not leak between scenarios.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

from sap_bdc_mcp.audit import AuditWriter
from sap_bdc_mcp.config import BDCConfig, DatabricksConfig, SnowflakeConfig
from sap_bdc_mcp.providers import default_registry
from sap_bdc_mcp.providers.base import (
    BDCConnectProvider,
    ExecutionPreview,
    ExecutionResult,
    PlanValidation,
    PreflightResult,
    ProviderCapabilities,
    ProviderContext,
)
from sap_bdc_mcp.providers.databricks import DatabricksProvider
from sap_bdc_mcp.providers.snowflake import SnowflakeProvider
from sap_bdc_mcp.tools import share_tools
from sap_bdc_mcp.tools._gated import ToolContext
from sap_bdc_mcp.tools.metadata import MetadataRegistry


_VALID_PLAN: Dict = {
    "name": "simple_share",
    "description": "test",
    "provider": "databricks",
    "assets": [{"type": "table", "name": "sales", "schema": "finance"}],
}


_INVALID_PLAN: Dict = {
    "name": "bad",
    "description": "",
    "provider": "databricks",
    "assets": [{"type": "table", "name": ""}],
}


class FakeServer:
    def __init__(self) -> None:
        self.registered: List[Callable] = []

    def tool(self) -> Callable:
        def decorator(fn: Callable) -> Callable:
            self.registered.append(fn)
            return fn

        return decorator


class _PluginProviderUnknown(BDCConnectProvider):
    """Synthetic plugin-style provider with UNKNOWN api_surface (row #9)."""

    name = "plug_dummy"
    api_surface = "unknown"

    def __init__(self) -> None:
        pass

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_preflight=True,
            supports_validate_plan=True,
            supports_dry_run=True,
            supports_execute=True,
        )

    async def preflight(self, ctx: ProviderContext) -> PreflightResult:
        return PreflightResult(ok=True)

    async def validate_plan(self, plan, ctx):  # type: ignore[no-untyped-def]
        return PlanValidation(ok=True)

    async def dry_run_execute(self, plan, ctx):  # type: ignore[no-untyped-def]
        return ExecutionPreview(ok=True, planned_operations=[{"op": "noop"}])

    async def execute(self, plan, ctx, approval_token):  # type: ignore[no-untyped-def]
        return ExecutionResult(ok=True, status="ok")


def _build_ctx(
    tmp_path,
    *,
    write_enabled: bool = True,
    strict: bool = True,
    require_dry_run: bool = True,
    require_approval_token: bool = True,
    approval_token: str = "topsecret",
    extra_providers: Optional[List[BDCConnectProvider]] = None,
) -> ToolContext:
    config = BDCConfig(
        mode="local",
        mock_mode=True,
        verify_tls=False,
        max_doc_kb=512,
        ord_sources=[],
        plugins=[],
        enable_write_tools=write_enabled,
        enable_admin_tools=False,
        require_dry_run=require_dry_run,
        require_approval_token=require_approval_token,
        approval_token=approval_token,
        audit_enabled=True,
        audit_log_path=str(tmp_path / "audit.jsonl"),
        api_policy_strict=strict,
        max_result_items=50,
        plugin_env_passthrough=[],
        plugin_trust={},
        databricks=DatabricksConfig(),
        snowflake=SnowflakeConfig(),
    )
    audit = AuditWriter(config.audit_log_path, enabled=True)
    providers = default_registry()
    providers.register(DatabricksProvider(config))
    providers.register(SnowflakeProvider(config))
    for p in extra_providers or []:
        providers.register(p)
    return ToolContext(
        config=config,
        audit=audit,
        metadata=MetadataRegistry(),
        plugin_status=[],
        providers=providers,
    )


def _register(ctx: ToolContext):
    """Re-register share tools against a fresh server + clear correlation map."""
    # Important: the dry-run correlation map is module-level state. Reset it
    # between tests so prior rows can't leak into row #2/3/4 expectations.
    share_tools._DRY_RUN_CORRELATIONS.clear()
    server = FakeServer()
    share_tools.register(server, ctx)
    # The third registered fn is bdc_share_execute_plan (after plan + validate).
    by_name: Dict[str, Callable] = {fn.__name__: fn for fn in server.registered}
    return by_name["bdc_share_execute_plan"]


def _last_audit(ctx: ToolContext) -> Dict:
    events = ctx.audit.tail()
    assert events, "expected at least one audit event"
    return events[-1]


# ----------------------------------------------------------------------------
# Row 1: dry_run=True, valid plan, mock provider -> preview + audit
# ----------------------------------------------------------------------------


def test_row1_dry_run_returns_preview_and_correlation_id(tmp_path) -> None:
    ctx = _build_ctx(tmp_path)
    fn = _register(ctx)
    out = fn(plan=_VALID_PLAN, provider="databricks", dry_run=True)
    assert out["ok"] is True
    assert out["dry_run"] is True
    assert out["correlation_id"]
    assert out["planned_operations"]
    ev = _last_audit(ctx)
    assert ev["result_status"] == "ok"
    assert ev["dry_run"] is True


# ----------------------------------------------------------------------------
# Row 2: dry_run=False without prior dry_run -> blocked
# ----------------------------------------------------------------------------


def test_row2_real_execute_without_prior_dry_run_blocked(tmp_path) -> None:
    ctx = _build_ctx(tmp_path)
    fn = _register(ctx)
    out = fn(
        plan=_VALID_PLAN,
        provider="databricks",
        dry_run=False,
        approval_token="topsecret",
    )
    assert out["ok"] is False
    assert "dry-run" in out["blocked_reason"].lower()


# ----------------------------------------------------------------------------
# Row 3: prior dry_run, missing token -> blocked
# ----------------------------------------------------------------------------


def test_row3_missing_approval_token_blocked(tmp_path) -> None:
    ctx = _build_ctx(tmp_path)
    fn = _register(ctx)
    dry = fn(plan=_VALID_PLAN, provider="databricks", dry_run=True)
    out = fn(
        plan=_VALID_PLAN,
        provider="databricks",
        dry_run=False,
        approval_token=None,
        correlation_id=dry["correlation_id"],
    )
    assert out["ok"] is False
    assert "approval" in out["blocked_reason"].lower()


# ----------------------------------------------------------------------------
# Row 4: prior dry_run, wrong token -> blocked (constant-time compare)
# ----------------------------------------------------------------------------


def test_row4_wrong_approval_token_blocked(tmp_path) -> None:
    ctx = _build_ctx(tmp_path)
    fn = _register(ctx)
    dry = fn(plan=_VALID_PLAN, provider="databricks", dry_run=True)
    out = fn(
        plan=_VALID_PLAN,
        provider="databricks",
        dry_run=False,
        approval_token="wrong",
        correlation_id=dry["correlation_id"],
    )
    assert out["ok"] is False
    assert "approval token invalid" in out["blocked_reason"].lower()


# ----------------------------------------------------------------------------
# Row 5: prior dry_run, valid token -> ExecutionResult + audit allowed=true
# ----------------------------------------------------------------------------


def test_row5_valid_token_executes_and_audits(tmp_path) -> None:
    ctx = _build_ctx(tmp_path)
    fn = _register(ctx)
    dry = fn(plan=_VALID_PLAN, provider="databricks", dry_run=True)
    out = fn(
        plan=_VALID_PLAN,
        provider="databricks",
        dry_run=False,
        approval_token="topsecret",
        correlation_id=dry["correlation_id"],
    )
    assert out["ok"] is True
    assert out["dry_run"] is False
    assert out["status"] == "ok"
    ev = _last_audit(ctx)
    assert ev["allowed"] is True
    assert ev["dry_run"] is False


# ----------------------------------------------------------------------------
# Row 6: WRITE disabled -> blocked
# ----------------------------------------------------------------------------


def test_row6_write_disabled_blocks_dry_run(tmp_path) -> None:
    ctx = _build_ctx(tmp_path, write_enabled=False)
    fn = _register(ctx)
    out = fn(plan=_VALID_PLAN, provider="databricks", dry_run=True)
    assert out["ok"] is False
    assert "BDC_ENABLE_WRITE_TOOLS" in out["blocked_reason"]


# ----------------------------------------------------------------------------
# Row 7: snowflake -> ProviderCapabilityError -> structured block
# ----------------------------------------------------------------------------


def test_row7_snowflake_dry_run_blocked_with_capability_reason(tmp_path) -> None:
    ctx = _build_ctx(tmp_path)
    fn = _register(ctx)
    out = fn(plan=_VALID_PLAN, provider="snowflake", dry_run=True)
    assert out["ok"] is False
    # Either provider_capability flag (from caps.supports_dry_run=False) or the
    # raised ProviderCapabilityError. Both are acceptable per the design.
    assert (
        "capability" in out["blocked_reason"].lower()
        or "readiness" in out["blocked_reason"].lower()
    )


# ----------------------------------------------------------------------------
# Row 8: invalid asset -> blocked with validate_contract reason
# ----------------------------------------------------------------------------


def test_row8_invalid_asset_blocked_with_share_validate_contract_reason(tmp_path) -> None:
    ctx = _build_ctx(tmp_path)
    fn = _register(ctx)
    out = fn(plan=_INVALID_PLAN, provider="databricks", dry_run=True)
    assert out["ok"] is False
    assert "validate_contract" in out["blocked_reason"]
    assert any(i["code"] == "INVALID_ASSET_NAME" for i in out["issues"])


# ----------------------------------------------------------------------------
# Row 9: strict + synthetic plugin provider with UNKNOWN surface -> blocked
# ----------------------------------------------------------------------------


def test_row9_strict_plugin_unknown_surface_blocked(tmp_path) -> None:
    ctx = _build_ctx(
        tmp_path,
        strict=True,
        extra_providers=[_PluginProviderUnknown()],
    )
    fn = _register(ctx)
    out = fn(plan=_VALID_PLAN, provider="plug_dummy", dry_run=True)
    assert out["ok"] is False
    assert "UNKNOWN" in out["blocked_reason"]


# ----------------------------------------------------------------------------
# Sanity: unknown provider name surfaces structured block, no raise
# ----------------------------------------------------------------------------


def test_unknown_provider_returns_structured_block(tmp_path) -> None:
    ctx = _build_ctx(tmp_path)
    fn = _register(ctx)
    out = fn(plan=_VALID_PLAN, provider="not_a_real_provider", dry_run=True)
    assert out["ok"] is False
    assert "not_a_real_provider" in out["blocked_reason"]


# ----------------------------------------------------------------------------
# Sanity: every gate writes exactly one audit event per call
# ----------------------------------------------------------------------------


def test_each_call_writes_exactly_one_audit_event(tmp_path) -> None:
    ctx = _build_ctx(tmp_path)
    fn = _register(ctx)
    fn(plan=_VALID_PLAN, provider="databricks", dry_run=True)
    fn(plan=_INVALID_PLAN, provider="databricks", dry_run=True)
    events = ctx.audit.tail(limit=100)
    # Each call writes one event regardless of allowed/blocked status.
    assert len(events) == 2
