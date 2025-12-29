"""Share plan model (v0.1 scaffold).

File: src/sap_bdc_mcp/models/share_plan.py
Version: v2
"""

from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict


class ShareAsset(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: Literal["table", "view", "file"] = "table"
    name: str = Field(..., description="Asset identifier (table/view/file name)")

    # Avoid shadowing BaseModel.schema while keeping external contract key = "schema"
    schema_name: Optional[str] = Field(
        default=None,
        alias="schema",
        serialization_alias="schema",
        description="Optional schema / namespace",
    )

    comment: Optional[str] = None


class SharePlan(BaseModel):
    name: str
    description: str = ""
    provider: str = "sap-bdc"
    assets: List[ShareAsset] = Field(default_factory=list)
