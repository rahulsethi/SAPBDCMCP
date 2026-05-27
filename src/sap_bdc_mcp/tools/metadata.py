"""Tool metadata model + registry.

File: src/sap_bdc_mcp/tools/metadata.py
Version: v1

v0.2 introduces a central, queryable registry of every MCP tool the server
exposes. Each entry carries the policy + SAP-API-policy facts that the
governance + execution gates use.

Backfill for v0.1 tools is performed by `register_v01_metadata()` and called
during server boot. New v0.2 tools register their own metadata at the same
time they register their tool functions.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class Mutability(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    ADMIN = "ADMIN"


class Risk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class APISurface(str, Enum):
    PUBLISHED_API = "published_api"
    DOCUMENTED_SDK = "documented_sdk"
    DOCUMENTED_MANUAL_FLOW = "documented_manual_flow"
    UNKNOWN = "unknown"


class BulkDataBehavior(str, Enum):
    NONE = "none"
    METADATA_ONLY = "metadata_only"
    BOUNDED_SAMPLE = "bounded_sample"
    BLOCKED = "blocked"


class ToolMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    category: str
    mutability: Mutability
    risk: Risk
    provider: Optional[str] = None
    api_surface: APISurface
    api_evidence: str
    api_evidence_url: Optional[str] = None
    requires_dry_run: bool = False
    requires_approval: bool = False
    requires_write_enable: bool = False
    requires_admin_enable: bool = False
    bulk_data_behavior: BulkDataBehavior = BulkDataBehavior.NONE
    description: str = ""


class MetadataRegistry:
    """In-memory registry of tool metadata. One per server instance."""

    def __init__(self) -> None:
        self._items: Dict[str, ToolMetadata] = {}

    def register(self, meta: ToolMetadata) -> None:
        if meta.name in self._items:
            raise ValueError(f"Duplicate tool metadata for '{meta.name}'")
        self._items[meta.name] = meta

    def get(self, name: str) -> Optional[ToolMetadata]:
        return self._items.get(name)

    def all(self, category: Optional[str] = None) -> List[ToolMetadata]:
        items = list(self._items.values())
        if category is not None:
            items = [m for m in items if m.category == category]
        return sorted(items, key=lambda m: m.name)

    def names(self) -> List[str]:
        return sorted(self._items.keys())

    def __len__(self) -> int:
        return len(self._items)


# ------------------------- v0.1 backfill -------------------------

_V01_METADATA: List[ToolMetadata] = [
    ToolMetadata(
        name="bdc_ping",
        category="core",
        mutability=Mutability.READ,
        risk=Risk.LOW,
        api_surface=APISurface.PUBLISHED_API,
        api_evidence="mcp.server.ping",
        bulk_data_behavior=BulkDataBehavior.NONE,
        description="Lightweight health check.",
    ),
    ToolMetadata(
        name="bdc_diagnostics",
        category="core",
        mutability=Mutability.READ,
        risk=Risk.LOW,
        api_surface=APISurface.PUBLISHED_API,
        api_evidence="mcp.server.diagnostics",
        bulk_data_behavior=BulkDataBehavior.NONE,
        description="Structured environment + readiness report.",
    ),
    ToolMetadata(
        name="bdc_get_tenant_info",
        category="core",
        mutability=Mutability.READ,
        risk=Risk.LOW,
        api_surface=APISurface.DOCUMENTED_MANUAL_FLOW,
        api_evidence="sap-bdc.tenant.info",
        bulk_data_behavior=BulkDataBehavior.NONE,
        description="Tenant labels from environment (redacted).",
    ),
    ToolMetadata(
        name="bdc_whoami",
        category="core",
        mutability=Mutability.READ,
        risk=Risk.LOW,
        api_surface=APISurface.DOCUMENTED_MANUAL_FLOW,
        api_evidence="sap-bdc.identity.whoami",
        bulk_data_behavior=BulkDataBehavior.NONE,
        description="Current user/identity labels (redacted).",
    ),
    ToolMetadata(
        name="bdc_ord_fetch_documents",
        category="ord",
        mutability=Mutability.READ,
        risk=Risk.LOW,
        api_surface=APISurface.PUBLISHED_API,
        api_evidence="ord-spec.v1.documents",
        api_evidence_url="https://sap.github.io/open-resource-discovery/spec-v1/",
        bulk_data_behavior=BulkDataBehavior.METADATA_ONLY,
        description="Fetch ORD documents from configured sources.",
    ),
    ToolMetadata(
        name="bdc_ord_search",
        category="ord",
        mutability=Mutability.READ,
        risk=Risk.LOW,
        api_surface=APISurface.PUBLISHED_API,
        api_evidence="ord-spec.v1.search",
        api_evidence_url="https://sap.github.io/open-resource-discovery/spec-v1/",
        bulk_data_behavior=BulkDataBehavior.METADATA_ONLY,
        description="Search ORD resources by keyword and type.",
    ),
    ToolMetadata(
        name="bdc_ord_validate",
        category="ord",
        mutability=Mutability.READ,
        risk=Risk.LOW,
        api_surface=APISurface.PUBLISHED_API,
        api_evidence="ord-spec.v1.validate",
        api_evidence_url="https://sap.github.io/open-resource-discovery/spec-v1/",
        bulk_data_behavior=BulkDataBehavior.METADATA_ONLY,
        description="Validate ORD documents against JSON Schema.",
    ),
    ToolMetadata(
        name="bdc_csn_validate",
        category="csn",
        mutability=Mutability.READ,
        risk=Risk.LOW,
        api_surface=APISurface.DOCUMENTED_MANUAL_FLOW,
        api_evidence="csn-spec.v2.validation",
        api_evidence_url="https://cap.cloud.sap/docs/cds/csn",
        bulk_data_behavior=BulkDataBehavior.METADATA_ONLY,
        description="Validate CSN structure.",
    ),
    ToolMetadata(
        name="bdc_csn_diff",
        category="csn",
        mutability=Mutability.READ,
        risk=Risk.MEDIUM,
        api_surface=APISurface.DOCUMENTED_MANUAL_FLOW,
        api_evidence="csn-spec.v2.diff",
        api_evidence_url="https://cap.cloud.sap/docs/cds/csn",
        bulk_data_behavior=BulkDataBehavior.METADATA_ONLY,
        description="Diff two CSN documents.",
    ),
    ToolMetadata(
        name="bdc_csn_render_docs",
        category="csn",
        mutability=Mutability.READ,
        risk=Risk.LOW,
        api_surface=APISurface.DOCUMENTED_MANUAL_FLOW,
        api_evidence="csn-spec.v2.render",
        api_evidence_url="https://cap.cloud.sap/docs/cds/csn",
        bulk_data_behavior=BulkDataBehavior.METADATA_ONLY,
        description="Render CSN to Markdown documentation.",
    ),
    ToolMetadata(
        name="bdc_share_plan",
        category="sharing",
        mutability=Mutability.READ,
        risk=Risk.LOW,
        api_surface=APISurface.DOCUMENTED_SDK,
        api_evidence="bdc-connect-sdk.share.plan_v1",
        bulk_data_behavior=BulkDataBehavior.METADATA_ONLY,
        description="Create a share plan object (no mutation).",
    ),
    ToolMetadata(
        name="bdc_share_validate_contract",
        category="sharing",
        mutability=Mutability.READ,
        risk=Risk.MEDIUM,
        api_surface=APISurface.DOCUMENTED_SDK,
        api_evidence="bdc-connect-sdk.share.validate_v1",
        bulk_data_behavior=BulkDataBehavior.METADATA_ONLY,
        description="Validate a share plan against contract structure + safety limits.",
    ),
]


def register_v01_metadata(registry: MetadataRegistry) -> None:
    """Register metadata for all v0.1 tools. Idempotent-safe by tracking names."""
    for meta in _V01_METADATA:
        if registry.get(meta.name) is None:
            registry.register(meta)


def v01_metadata_list() -> List[ToolMetadata]:
    """Read-only view of the v0.1 metadata catalog (for tests)."""
    return list(_V01_METADATA)
