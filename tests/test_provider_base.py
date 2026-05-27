"""Provider base + registry tests.

File: tests/test_provider_base.py
Version: v1
"""

from __future__ import annotations

import pytest

from sap_bdc_mcp.providers import ProviderRegistry, default_registry
from sap_bdc_mcp.providers.base import (
    BDCConnectProvider,
    ExecutionPreview,
    ExecutionResult,
    PlanValidation,
    PreflightResult,
    ProviderCapabilities,
    ProviderContext,
)


class _FakeProvider(BDCConnectProvider):
    name = "fake"

    def __init__(self, name: str = "fake") -> None:
        self.name = name

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_preflight=True,
            supports_validate_plan=True,
            supports_dry_run=False,
            supports_execute=False,
        )

    async def preflight(self, ctx: ProviderContext) -> PreflightResult:
        return PreflightResult(ok=True, checks=[], blockers=[])

    async def validate_plan(self, plan, ctx):  # type: ignore[no-untyped-def]
        return PlanValidation(ok=True)

    async def dry_run_execute(self, plan, ctx):  # type: ignore[no-untyped-def]
        return ExecutionPreview(ok=True)

    async def execute(self, plan, ctx, approval_token):  # type: ignore[no-untyped-def]
        return ExecutionResult(ok=True, status="ok")


def test_default_registry_is_empty() -> None:
    r = default_registry()
    assert isinstance(r, ProviderRegistry)
    assert r.list_names() == []
    assert len(r) == 0


def test_register_and_get() -> None:
    r = ProviderRegistry()
    p = _FakeProvider("p1")
    r.register(p)
    assert r.get("p1") is p
    assert r.get("nope") is None


def test_register_duplicate_raises() -> None:
    r = ProviderRegistry()
    r.register(_FakeProvider("dup"))
    with pytest.raises(ValueError):
        r.register(_FakeProvider("dup"))


def test_register_missing_name_raises() -> None:
    r = ProviderRegistry()
    p = _FakeProvider()
    p.name = ""
    with pytest.raises(ValueError):
        r.register(p)


def test_list_names_sorted_alphabetically() -> None:
    r = ProviderRegistry()
    r.register(_FakeProvider("zeta"))
    r.register(_FakeProvider("alpha"))
    r.register(_FakeProvider("mu"))
    assert r.list_names() == ["alpha", "mu", "zeta"]


def test_len_reflects_registrations() -> None:
    r = ProviderRegistry()
    assert len(r) == 0
    r.register(_FakeProvider("a"))
    r.register(_FakeProvider("b"))
    assert len(r) == 2


def test_dataclasses_default_construction() -> None:
    pr = PreflightResult(ok=True)
    assert pr.checks == []
    assert pr.blockers == []
    pv = PlanValidation(ok=True)
    assert pv.issues == []
    ep = ExecutionPreview(ok=True)
    assert ep.planned_operations == []
    assert ep.warnings == []
    assert ep.estimated_impact == {}
    er = ExecutionResult(ok=True, status="ok")
    assert er.next_steps == []
    assert er.summary == ""
