"""Policy and risk gating.

File: src/sap_bdc_mcp/policy.py
Version: v1
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


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

    def is_allowed(self, enable_write_tools: bool) -> bool:
        if self.requires_write_enable and not enable_write_tools:
            return False
        return True
