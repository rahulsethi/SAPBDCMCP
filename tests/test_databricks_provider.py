"""Databricks provider tests — mock mode only, no network.

File: tests/test_databricks_provider.py
Version: v1

Covers 06_TestPlan §5.2.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from sap_bdc_mcp.config import BDCConfig, DatabricksConfig, SnowflakeConfig
from sap_bdc_mcp.models.share_plan import ShareAsset, SharePlan
from sap_bdc_mcp.providers.base import ProviderContext
from sap_bdc_mcp.providers.databricks import DatabricksProvider


def _config(*, mock: bool = True, **dbx_kwargs) -> BDCConfig:
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
        databricks=DatabricksConfig(**dbx_kwargs),
        snowflake=SnowflakeConfig(),
    )


def _ctx(mock: bool = True) -> ProviderContext:
    return ProviderContext(mock_mode=mock, config_snapshot={})


def _sample_plan() -> SharePlan:
    return SharePlan(
        name="simple_share",
        provider="databricks",
        assets=[
            ShareAsset(type="table", name="sales"),
            ShareAsset(type="table", name="products"),
        ],
    )


def test_capabilities_supports_full_lifecycle() -> None:
    p = DatabricksProvider(_config())
    caps = p.capabilities()
    assert caps.supports_preflight is True
    assert caps.supports_validate_plan is True
    assert caps.supports_dry_run is True
    assert caps.supports_execute is True


async def test_preflight_mock_mode_passes_all() -> None:
    p = DatabricksProvider(_config())
    result = await p.preflight(_ctx(mock=True))
    assert result.ok is True
    names = [c["name"] for c in result.checks]
    for expected in (
        "host_reachable",
        "token_shape_valid",
        "recipient_registered",
        "warehouse_accessible",
    ):
        assert expected in names
    assert result.blockers == []


async def test_preflight_real_mode_missing_env_returns_blockers_not_exception() -> None:
    # No env values set + mock_mode=False on the ctx -> structured blockers.
    p = DatabricksProvider(_config(mock=False))
    result = await p.preflight(_ctx(mock=False))
    assert result.ok is False
    assert any("BDC_DATABRICKS_HOST" in b for b in result.blockers)
    # No exception escaped — that's the contract.


async def test_validate_plan_ok_for_simple_plan() -> None:
    p = DatabricksProvider(_config())
    res = await p.validate_plan(_sample_plan(), _ctx())
    assert res.ok is True
    assert res.issues == []


async def test_validate_plan_rejects_empty_asset_name() -> None:
    bad_plan = SharePlan(
        name="bad",
        assets=[ShareAsset(type="table", name=" ")],
    )
    p = DatabricksProvider(_config())
    res = await p.validate_plan(bad_plan, _ctx())
    assert res.ok is False
    assert any(i["code"] == "INVALID_ASSET_NAME" for i in res.issues)


async def test_validate_plan_rejects_empty_plan() -> None:
    plan = SharePlan(name="x", assets=[])
    p = DatabricksProvider(_config())
    res = await p.validate_plan(plan, _ctx())
    assert res.ok is False
    assert any(i["code"] == "EMPTY_PLAN" for i in res.issues)


def _fixture_path() -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / "databricks_share_mock.json"


async def test_dry_run_execute_returns_preview_no_mutation() -> None:
    fixture = _fixture_path()
    before = hashlib.sha256(fixture.read_bytes()).hexdigest()
    p = DatabricksProvider(_config())
    preview = await p.dry_run_execute(_sample_plan(), _ctx())
    after = hashlib.sha256(fixture.read_bytes()).hexdigest()
    assert preview.ok is True
    assert len(preview.planned_operations) == 2
    assert preview.planned_operations[0]["op"] == "create_or_update_share_asset"
    assert before == after  # fixture unchanged


async def test_execute_returns_ok_in_mock_mode() -> None:
    p = DatabricksProvider(_config())
    result = await p.execute(_sample_plan(), _ctx(), approval_token="dummy")
    assert result.ok is True
    assert result.status == "ok"
    assert "Mock execute" in result.summary
    assert result.next_steps


async def test_dry_run_execute_real_mode_raises_clearly() -> None:
    """Real mode either raises NotImplementedError (SDK installed) or
    BDCConnectSDKNotInstalled (SDK missing). Both are acceptable; both point
    operators to v0.3 or to mock mode."""
    from sap_bdc_mcp.connectors.bdc_connect_sdk_client import (
        BDCConnectSDKNotInstalled,
    )

    p = DatabricksProvider(_config(mock=False))
    with pytest.raises((NotImplementedError, BDCConnectSDKNotInstalled)):
        await p.dry_run_execute(_sample_plan(), _ctx(mock=False))


async def test_execute_real_mode_raises_clearly() -> None:
    from sap_bdc_mcp.connectors.bdc_connect_sdk_client import (
        BDCConnectSDKNotInstalled,
    )

    p = DatabricksProvider(_config(mock=False))
    with pytest.raises((NotImplementedError, BDCConnectSDKNotInstalled)):
        await p.execute(_sample_plan(), _ctx(mock=False), approval_token="x")
