"""Hybrid worker client — skeleton (v0.2).

File: src/sap_bdc_mcp/connectors/hybrid_worker_client.py
Version: v1

This module is a placeholder. At v0.2, no hybrid worker is wired. The class
signatures here match the expected v0.3/v0.4 contract sketched in
``docs/release/v0.2.0/03_Decisions/D-008-hybrid-worker-contract.md``.

All execute-shaped methods raise :class:`HybridWorkerNotConfigured`. Do not
import this module from any v0.2 tool that runs against real backends.
:func:`HybridWorkerClient.health` is safe and is consumed by
``bdc_diagnostics`` to report the slot's status.
"""

from __future__ import annotations

from typing import Any, Dict


class HybridWorkerNotConfigured(RuntimeError):
    """Raised when calling into the worker before it has been wired (v0.2)."""


class HybridWorkerClient:
    """Skeleton hybrid-worker client.

    Construction never raises. Calling :meth:`execute` raises immediately so
    no v0.2 tool can accidentally rely on the worker.
    """

    def __init__(self, base_url: str = "", token: str = "") -> None:
        self.base_url = base_url
        self.token = token
        self.configured = False

    async def execute(
        self,
        tool_name: str,
        payload: Dict[str, Any],
        correlation_id: str,
    ) -> Dict[str, Any]:
        """Stub. Always raises :class:`HybridWorkerNotConfigured` at v0.2."""
        raise HybridWorkerNotConfigured(
            "hybrid worker is skeleton-only at v0.2; see "
            "docs/release/v0.2.0/03_Decisions/D-008-hybrid-worker-contract.md"
        )

    async def health(self) -> Dict[str, Any]:
        """Return a small dict describing the worker's wiring state."""
        return {"configured": False, "reason": "skeleton only at v0.2"}
