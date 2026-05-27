"""Policy evidence — gate writes/admin actions on documented API surface.

File: src/sap_bdc_mcp/policy_evidence.py
Version: v1

A tool with `api_surface == UNKNOWN` cannot mutate when strict mode is on.
This is the practical enforcement of the SAP API policy at the per-tool level.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .tools.metadata import APISurface, Mutability, ToolMetadata


@dataclass(frozen=True)
class PolicyEvidenceResult:
    allowed: bool
    reason: Optional[str] = None


def check_or_block(meta: ToolMetadata, *, strict: bool) -> PolicyEvidenceResult:
    """Return blocked when a WRITE/ADMIN tool lacks an evidenced API surface."""
    if meta.mutability == Mutability.READ:
        return PolicyEvidenceResult(allowed=True)
    if meta.api_surface == APISurface.UNKNOWN and strict:
        return PolicyEvidenceResult(
            allowed=False,
            reason=(
                f"Tool '{meta.name}' is {meta.mutability.value} but api_surface is UNKNOWN; "
                f"refusing under BDC_API_POLICY_STRICT=1."
            ),
        )
    return PolicyEvidenceResult(allowed=True)
