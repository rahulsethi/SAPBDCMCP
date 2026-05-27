"""BDC Connect provider registry.

File: src/sap_bdc_mcp/providers/__init__.py
Version: v1

The registry is the single lookup the server + tools consult to obtain a
concrete :class:`BDCConnectProvider` by name. v0.2 ships two built-ins:
``databricks`` and ``snowflake``. The registry is intentionally trivial
(in-memory dict) — provider construction is the responsibility of the
caller (typically ``server.py``).
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .base import (
    BDCConnectProvider,
    ExecutionPreview,
    ExecutionResult,
    PlanValidation,
    PreflightResult,
    ProviderCapabilities,
    ProviderCapabilityError,
    ProviderContext,
)


__all__ = [
    "BDCConnectProvider",
    "ExecutionPreview",
    "ExecutionResult",
    "PlanValidation",
    "PreflightResult",
    "ProviderCapabilities",
    "ProviderCapabilityError",
    "ProviderContext",
    "ProviderRegistry",
    "default_registry",
]


class ProviderRegistry:
    """In-memory registry of :class:`BDCConnectProvider` instances."""

    def __init__(self) -> None:
        self._items: Dict[str, BDCConnectProvider] = {}

    def register(self, provider: BDCConnectProvider) -> None:
        """Register ``provider`` under its ``name``. Duplicate name raises."""
        name = provider.name
        if not name:
            raise ValueError("provider.name must be set on subclass")
        if name in self._items:
            raise ValueError(f"Duplicate provider registration for '{name}'")
        self._items[name] = provider

    def get(self, name: str) -> Optional[BDCConnectProvider]:
        """Return the provider by name, or ``None`` if not registered."""
        return self._items.get(name)

    def list_names(self) -> List[str]:
        """Return all registered provider names, alphabetically sorted."""
        return sorted(self._items.keys())

    def __len__(self) -> int:
        return len(self._items)


def default_registry() -> ProviderRegistry:
    """Return a fresh, empty :class:`ProviderRegistry`.

    Called by ``server.py`` at boot to build the per-process registry. The
    server then registers the built-in providers onto it before tool
    registration runs.
    """
    return ProviderRegistry()
