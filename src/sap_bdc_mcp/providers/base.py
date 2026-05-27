"""Provider abstract base class + result dataclasses.

File: src/sap_bdc_mcp/providers/base.py
Version: v1

The :class:`BDCConnectProvider` ABC is the seam between provider-neutral MCP
tools (``bdc_share_execute_plan`` etc.) and the concrete provider
implementations (Databricks, Snowflake, future plugin-supplied providers).

Design contract: 02_Design.md §1.4. Method shapes are fixed at v0.2 — provider
implementations must return one of the dataclasses defined here; raising is
reserved for **capability** errors (see :class:`ProviderCapabilityError`).
Network / SDK failures should be reported as ``ok=False`` results so the
``share_execute_plan`` wrapper can translate them to structured blocks.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..models.share_plan import SharePlan


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ProviderCapabilityError(RuntimeError):
    """Raised when a method is called on a provider that does not support it.

    Snowflake at v0.2 raises this from :meth:`BDCConnectProvider.dry_run_execute`
    and :meth:`BDCConnectProvider.execute`; the share-execute wrapper translates
    the exception into a structured block so no raise reaches the MCP caller.
    """


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProviderCapabilities:
    """Static feature flags declared by a provider."""

    supports_preflight: bool
    supports_validate_plan: bool
    supports_dry_run: bool
    supports_execute: bool
    notes: str = ""


@dataclass
class ProviderContext:
    """Per-call context handed to provider methods.

    ``config_snapshot`` is a redacted view of the operator config — never
    contains secrets. ``correlation_id`` ties a dry-run to its subsequent
    real execute (Phase 5).
    """

    mock_mode: bool
    config_snapshot: Dict[str, Any]
    correlation_id: Optional[str] = None


@dataclass
class PreflightResult:
    """Outcome of :meth:`BDCConnectProvider.preflight`.

    ``checks`` lists each individual probe in shape
    ``{"name": str, "ok": bool, "detail": str}``. ``blockers`` lists
    human-readable strings naming the remediation steps the operator must take.
    """

    ok: bool
    checks: List[Dict[str, Any]] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)


@dataclass
class PlanValidation:
    """Outcome of :meth:`BDCConnectProvider.validate_plan`."""

    ok: bool
    issues: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ExecutionPreview:
    """Outcome of :meth:`BDCConnectProvider.dry_run_execute`.

    ``planned_operations`` is provider-specific in content but typed as a list
    of dicts. Each entry should be safe to redact (no secrets).
    """

    ok: bool
    planned_operations: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    estimated_impact: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Outcome of :meth:`BDCConnectProvider.execute`."""

    ok: bool
    status: str  # "ok" | "partial" | "error"
    summary: str = ""
    next_steps: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class BDCConnectProvider(ABC):
    """Base class every provider implements.

    Subclasses MUST set the class-level :attr:`name` attribute. The method
    suite mirrors the gate chain a real execute traverses:
    ``preflight`` → ``validate_plan`` → ``dry_run_execute`` → ``execute``.

    :attr:`api_surface` is the policy-evidence label the share-execute gate
    consults under ``BDC_API_POLICY_STRICT=1``. Built-in providers declare
    ``"documented_sdk"``; plugin-supplied providers default to ``"unknown"``
    and are blocked from write paths until the operator promotes them via
    ``BDC_PLUGIN_TRUST``.
    """

    name: str = ""
    # String form keeps providers/base.py free of a circular dep on
    # tools/metadata.py. The share-execute gate accepts either form.
    api_surface: str = "documented_sdk"

    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Return the static capability flags for this provider."""

    @abstractmethod
    async def preflight(self, ctx: ProviderContext) -> PreflightResult:
        """Probe configuration + reachability. Never raises on missing env."""

    @abstractmethod
    async def validate_plan(self, plan: SharePlan, ctx: ProviderContext) -> PlanValidation:
        """Validate that ``plan`` is shaped for this provider's expectations."""

    @abstractmethod
    async def dry_run_execute(self, plan: SharePlan, ctx: ProviderContext) -> ExecutionPreview:
        """Compute the operations a real execute would perform. No mutation.

        May raise :class:`ProviderCapabilityError` if the provider does not
        support execute previews at this version.
        """

    @abstractmethod
    async def execute(
        self, plan: SharePlan, ctx: ProviderContext, approval_token: str
    ) -> ExecutionResult:
        """Apply the plan. Caller is expected to have presented a valid token.

        May raise :class:`ProviderCapabilityError` if the provider does not
        support execute at this version.
        """
