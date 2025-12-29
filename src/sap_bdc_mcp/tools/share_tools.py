"""Share planning tools (scaffold).

File: src/sap_bdc_mcp/tools/share_tools.py
Version: v2
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

        # Safety: very small limits in v0.1 scaffold
        if len(parsed.assets) > 50:
            issues.append(
                {
                    "code": "TOO_MANY_ASSETS",
                    "message": "Share plan has > 50 assets; split into multiple shares.",
                }
            )

        # TODO(v0.1): tie validation to ORD/CSN constraints.
        ok = len(issues) == 0
        return {"ok": ok, "issues": issues}
