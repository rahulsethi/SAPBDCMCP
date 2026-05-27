"""Policy and risk gating.

File: src/sap_bdc_mcp/policy.py
Version: v2

v0.2 extends `is_allowed()` to factor in:
  - admin tools enablement
  - dry-run requirement (high-risk tools must dry-run before real execute)
  - approval token validity (constant-time compare, supplied by caller)

The v0.1 single-arg call site continues to work via a default-args path.
"""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ToolPermission(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    ADMIN = "ADMIN"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class ToolPolicy:
    permission: ToolPermission
    risk: RiskLevel
    requires_write_enable: bool = False
    requires_admin_enable: bool = False
    requires_dry_run: bool = False
    requires_approval: bool = False

    def is_allowed(
        self,
        enable_write_tools: bool,
        *,
        enable_admin_tools: bool = False,
        dry_run: bool = True,
        prior_dry_run_correlation: Optional[str] = None,
        approval_token_valid: bool = False,
    ) -> bool:
        if self.requires_write_enable and not enable_write_tools:
            return False
        if self.requires_admin_enable and not enable_admin_tools:
            return False
        if self.requires_dry_run and not dry_run and prior_dry_run_correlation is None:
            return False
        if self.requires_approval and not dry_run and not approval_token_valid:
            return False
        return True


def approval_token_valid(provided: Optional[str], expected: str) -> bool:
    """Constant-time approval-token compare. Empty expected => never valid."""
    if not expected:
        return False
    if provided is None:
        return False
    return hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))
