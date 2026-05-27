"""CSN generation tests — D-006 acceptance.

File: tests/test_csn_generation.py
Version: v1

Covers 06_TestPlan §5.4.
"""

from __future__ import annotations

from sap_bdc_mcp.providers.databricks import (
    CSN_DISCLAIMER,
    CSN_REFUSAL_DISCLAIMER,
    generate_csn_from_share,
)


def test_primitive_table_maps_types() -> None:
    out = generate_csn_from_share("simple_share", format="json")
    assert out["ok"] is True
    defs = out["csn"]["definitions"]
    # Locate the 'sales' entity by suffix.
    sales_entity = next(v for k, v in defs.items() if k.endswith("sales"))
    elements = sales_entity["elements"]
    assert elements["id"]["type"] == "cds.Integer"
    assert elements["id"]["notNull"] is True
    assert elements["customer"]["type"] == "cds.String"
    assert elements["amount"]["type"] == "cds.Decimal"
    assert elements["amount"]["precision"] == 18
    assert elements["amount"]["scale"] == 2
    assert elements["is_paid"]["type"] == "cds.Boolean"
    assert elements["ordered_at"]["type"] == "cds.Timestamp"
    products_entity = next(v for k, v in defs.items() if k.endswith("products"))
    products_elements = products_entity["elements"]
    assert products_elements["price"]["type"] == "cds.Double"
    assert products_elements["launched_on"]["type"] == "cds.Date"


def test_complex_share_refuses_with_unsupported_columns() -> None:
    out = generate_csn_from_share("complex_share", format="json")
    assert out["ok"] is False
    assert out["reason"] == "complex_types_not_supported"
    cols = {c["name"] for c in out["unsupported_columns"]}
    assert "address" in cols
    assert "tags" in cols
    assert out["disclaimer"] == CSN_REFUSAL_DISCLAIMER


def test_all_complex_share_refuses() -> None:
    out = generate_csn_from_share("all_complex_share", format="json")
    assert out["ok"] is False
    assert out["reason"] == "complex_types_not_supported"
    names = {c["name"] for c in out["unsupported_columns"]}
    assert "payload" in names
    assert "samples" in names


def test_format_cds_returns_ddl_text() -> None:
    out = generate_csn_from_share("simple_share", format="cds")
    assert out["ok"] is True
    assert out["format"] == "cds"
    assert "entity" in out["cds"]
    assert "Decimal(18, 2)" in out["cds"] or "Decimal" in out["cds"]
    assert "Timestamp" in out["cds"]


def test_format_draft_returns_summary_text() -> None:
    out = generate_csn_from_share("simple_share", format="draft")
    assert out["ok"] is True
    assert out["format"] == "draft"
    assert "Draft CSN" in out["draft"]
    assert "Review required" in out["draft"]


def test_disclaimer_present_on_success() -> None:
    for fmt in ("json", "cds", "draft"):
        out = generate_csn_from_share("simple_share", format=fmt)
        assert out["disclaimer"] == CSN_DISCLAIMER


def test_missing_share_returns_structured_error() -> None:
    out = generate_csn_from_share("nope_share")
    assert out["ok"] is False
    assert out["reason"] == "share_not_found"


def test_invalid_format_returns_structured_error() -> None:
    out = generate_csn_from_share("simple_share", format="yaml")
    assert out["ok"] is False
    assert out["reason"] == "invalid_format"
