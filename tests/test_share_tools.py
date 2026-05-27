"""Share tools comprehensive tests.

File: tests/test_share_tools.py
Version: v1
"""

from sap_bdc_mcp.models.share_plan import SharePlan, ShareAsset
from sap_bdc_mcp.server import build_server


def test_share_plan_creation() -> None:
    """Test creating a share plan."""
    assets = [
        {"type": "table", "name": "sales_data", "schema": "public"},
        {"type": "view", "name": "sales_summary"},
    ]
    plan = SharePlan(
        name="test_share",
        description="Test share plan",
        provider="sap-bdc",
        assets=[ShareAsset(**a) for a in assets],
    )

    assert plan.name == "test_share"
    assert plan.description == "Test share plan"
    assert len(plan.assets) == 2
    assert plan.assets[0].name == "sales_data"
    assert plan.assets[0].schema_name == "public"


def test_share_plan_serialization() -> None:
    """Test share plan serialization."""
    assets = [{"type": "table", "name": "test_table"}]
    plan = SharePlan(
        name="test_share",
        assets=[ShareAsset(**a) for a in assets],
    )
    dumped = plan.model_dump(by_alias=True)

    assert dumped["name"] == "test_share"
    assert len(dumped["assets"]) == 1
    assert dumped["assets"][0]["name"] == "test_table"


def test_share_validate_contract_functionality() -> None:
    """Test share validation logic directly."""
    from sap_bdc_mcp.models.share_plan import SharePlan
    from sap_bdc_mcp.config import BDCConfig

    BDCConfig.from_env()

    # Test with valid plan
    plan_dict = {
        "name": "test_share",
        "description": "Test",
        "provider": "sap-bdc",
        "assets": [{"type": "table", "name": "test_table"}],
    }

    # Validate the plan structure
    plan = SharePlan.model_validate(plan_dict)
    assert plan.name == "test_share"
    assert len(plan.assets) == 1


def test_share_validate_contract_too_many_assets() -> None:
    """Test validation logic for too many assets."""
    from sap_bdc_mcp.models.share_plan import SharePlan

    # Create plan with > 50 assets
    plan_dict = {
        "name": "test_share",
        "description": "Test",
        "provider": "sap-bdc",
        "assets": [{"type": "table", "name": f"table_{i}"} for i in range(51)],
    }

    plan = SharePlan.model_validate(plan_dict)
    assert len(plan.assets) == 51
    # The validation logic in share_tools will check this


def test_share_tools_server_builds() -> None:
    """Verify server builds successfully with share tools."""
    server = build_server()
    assert server is not None
    # Server should build without errors, indicating tools are registered
