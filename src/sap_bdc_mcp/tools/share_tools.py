"""Share planning tools for creating and validating share plans.

File: src/sap_bdc_mcp/tools/share_tools.py
Version: v3
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..config import BDCConfig
from ..models.share_plan import SharePlan, ShareAsset
from ..policy import ToolPolicy, ToolPermission, RiskLevel


# v0.1 share tools are READ-ish (plan/validate only).
SHARE_VALIDATE_POLICY = ToolPolicy(permission=ToolPermission.READ, risk=RiskLevel.MEDIUM)


def register(server: Any, config: BDCConfig) -> None:
    @server.tool()
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

    @server.tool()
    def bdc_share_validate_contract(plan: Dict) -> Dict:
        """Validate a share plan against safety limits + basic contract structure."""
        if not SHARE_VALIDATE_POLICY.is_allowed(config.enable_write_tools):
            return {"ok": False, "error": "Share validation is currently disabled by policy."}

        issues: List[Dict] = []
        try:
            parsed = SharePlan.model_validate(plan)
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "issues": [{"code": "INVALID_PLAN", "message": str(e)}]}

        # Safety: very small limits in v0.1
        if len(parsed.assets) > 50:
            issues.append(
                {
                    "code": "TOO_MANY_ASSETS",
                    "message": "Share plan has > 50 assets; split into multiple shares.",
                }
            )
        
        # Validate asset structure
        for i, asset in enumerate(parsed.assets):
            if not asset.name or not asset.name.strip():
                issues.append({
                    "code": "INVALID_ASSET_NAME",
                    "asset_index": i,
                    "message": f"Asset at index {i} has empty or invalid name",
                })
            
            # Check for duplicate assets
            asset_key = (asset.schema_name or "", asset.name)
            if i > 0:
                prev_assets = [(a.schema_name or "", a.name) for a in parsed.assets[:i]]
                if asset_key in prev_assets:
                    issues.append({
                        "code": "DUPLICATE_ASSET",
                        "asset_index": i,
                        "asset": asset.name,
                        "message": f"Duplicate asset '{asset.name}' in share plan",
                    })
        
        # Note: In a full implementation, we would validate against ORD/CSN:
        # - Check that referenced tables/views exist in CSN
        # - Verify access permissions from ORD data products
        # - Validate schema/namespace consistency
        
        ok = len(issues) == 0
        return {"ok": ok, "issues": issues}
