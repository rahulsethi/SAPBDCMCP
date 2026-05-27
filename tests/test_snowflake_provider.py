"""Snowflake provider tests — readiness only at v0.2.

File: tests/test_snowflake_provider.py
Version: v1

Covers 06_TestPlan §6.1.
"""

from __future__ import annotations

import pytest

from sap_bdc_mcp.config import BDCConfig, DatabricksConfig, SnowflakeConfig
from sap_bdc_mcp.models.share_plan import ShareAsset, SharePlan
from sap_bdc_mcp.providers.base import ProviderCapabilityError, ProviderContext
from sap_bdc_mcp.providers.snowflake import SnowflakeProvider


def _config(*, mock: bool = True, **sf_kwargs) -> BDCConfig:
    return BDCConfig(
        mode="local",
        mock_mode=mock,
        verify_tls=False,
        max_doc_kb=512,
        ord_sources=[],
        plugins=[],
        enable_write_tools=True,
        enable_admin_tools=False,
        require_dry_run=True,
        require_approval_token=True,
        approval_token="",
        audit_enabled=False,
        audit_log_path=".audit.jsonl",
        api_policy_strict=True,
        max_result_items=50,
        plugin_env_passthrough=[],
        plugin_trust={},
        databricks=DatabricksConfig(),
        snowflake=SnowflakeConfig(**sf_kwargs),
    )


def _ctx(mock: bool = True) -> ProviderContext:
    return ProviderContext(mock_mode=mock, config_snapshot={})


def _plan() -> SharePlan:
    return SharePlan(
        name="sf_test",
        assets=[ShareAsset(type="table", name="orders")],
    )


def test_capabilities_readiness_only() -> None:
    p = SnowflakeProvider(_config())
    caps = p.capabilities()
    assert caps.supports_preflight is True
    assert caps.supports_validate_plan is True
    assert caps.supports_dry_run is False
    assert caps.supports_execute is False


async def test_preflight_mock_mode_passes() -> None:
    p = SnowflakeProvider(_config())
    res = await p.preflight(_ctx(mock=True))
    assert res.ok is True
    assert res.blockers == []


async def test_preflight_real_mode_missing_env_blockers() -> None:
    p = SnowflakeProvider(_config(mock=False))
    res = await p.preflight(_ctx(mock=False))
    assert res.ok is False
    assert any("BDC_SNOWFLAKE_ACCOUNT" in b for b in res.blockers)


async def test_validate_plan_ok() -> None:
    p = SnowflakeProvider(_config())
    res = await p.validate_plan(_plan(), _ctx())
    assert res.ok is True


async def test_dry_run_execute_raises_capability_error() -> None:
    p = SnowflakeProvider(_config())
    with pytest.raises(ProviderCapabilityError) as exc:
        await p.dry_run_execute(_plan(), _ctx())
    assert "readiness-only" in str(exc.value).lower() or "v0.3" in str(exc.value).lower()


async def test_execute_raises_capability_error() -> None:
    p = SnowflakeProvider(_config())
    with pytest.raises(ProviderCapabilityError) as exc:
        await p.execute(_plan(), _ctx(), approval_token="tok")
    assert "readiness-only" in str(exc.value).lower() or "v0.3" in str(exc.value).lower()
