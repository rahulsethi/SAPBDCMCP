"""ToolMetadata model + registry tests.

File: tests/test_metadata.py
Version: v1
"""

from __future__ import annotations

import pytest

from sap_bdc_mcp.tools.metadata import (
    APISurface,
    BulkDataBehavior,
    MetadataRegistry,
    Mutability,
    Risk,
    ToolMetadata,
    register_v01_metadata,
    v01_metadata_list,
)


def _sample_meta(name: str = "x") -> ToolMetadata:
    return ToolMetadata(
        name=name,
        category="core",
        mutability=Mutability.READ,
        risk=Risk.LOW,
        api_surface=APISurface.PUBLISHED_API,
        api_evidence="test.evidence",
    )


def test_registry_register_and_get() -> None:
    r = MetadataRegistry()
    m = _sample_meta("a")
    r.register(m)
    assert r.get("a") is m
    assert r.get("missing") is None


def test_registry_duplicate_raises() -> None:
    r = MetadataRegistry()
    r.register(_sample_meta("dup"))
    with pytest.raises(ValueError):
        r.register(_sample_meta("dup"))


def test_registry_all_filter_by_category() -> None:
    r = MetadataRegistry()
    r.register(_sample_meta("a"))
    other = ToolMetadata(
        name="b",
        category="ord",
        mutability=Mutability.READ,
        risk=Risk.LOW,
        api_surface=APISurface.PUBLISHED_API,
        api_evidence="ord-spec.v1.x",
    )
    r.register(other)
    assert [m.name for m in r.all()] == ["a", "b"]
    assert [m.name for m in r.all(category="ord")] == ["b"]


def test_registry_len() -> None:
    r = MetadataRegistry()
    assert len(r) == 0
    r.register(_sample_meta("a"))
    assert len(r) == 1


def test_v01_metadata_covers_all_twelve() -> None:
    metas = v01_metadata_list()
    names = {m.name for m in metas}
    expected = {
        "bdc_ping",
        "bdc_diagnostics",
        "bdc_get_tenant_info",
        "bdc_whoami",
        "bdc_ord_fetch_documents",
        "bdc_ord_search",
        "bdc_ord_validate",
        "bdc_csn_validate",
        "bdc_csn_diff",
        "bdc_csn_render_docs",
        "bdc_share_plan",
        "bdc_share_validate_contract",
    }
    assert names == expected


def test_v01_tools_are_all_read() -> None:
    for m in v01_metadata_list():
        assert m.mutability == Mutability.READ, f"{m.name} is not READ"


def test_v01_tools_have_known_surface() -> None:
    for m in v01_metadata_list():
        assert m.api_surface != APISurface.UNKNOWN, f"{m.name} has UNKNOWN surface"


def test_v01_tools_have_evidence_strings() -> None:
    for m in v01_metadata_list():
        assert m.api_evidence and m.api_evidence.strip(), f"{m.name} missing api_evidence"


def test_register_v01_metadata_idempotent() -> None:
    r = MetadataRegistry()
    register_v01_metadata(r)
    n = len(r)
    register_v01_metadata(r)  # should not raise nor duplicate
    assert len(r) == n


def test_bulk_data_behavior_defaults_to_none() -> None:
    m = _sample_meta()
    assert m.bulk_data_behavior == BulkDataBehavior.NONE
