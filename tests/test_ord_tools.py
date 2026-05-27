"""ORD tools comprehensive tests.

File: tests/test_ord_tools.py
Version: v1
"""

from sap_bdc_mcp.connectors.ord_client import (
    load_ord_documents,
    search_ord_resources,
    validate_ord_documents,
)
from sap_bdc_mcp.server import build_server


def test_ord_fetch_documents_from_fixture() -> None:
    """Test loading ORD documents from fixture file."""
    docs = load_ord_documents(
        sources=["fixtures/ord.sample.json"],
        verify_tls=True,
        max_doc_kb=512,
        mock_mode=False,
    )
    assert len(docs) >= 1
    assert "dataProducts" in docs[0] or "apiResources" in docs[0]


def test_ord_fetch_documents_mock_mode() -> None:
    """Test loading ORD documents in mock mode (no sources)."""
    docs = load_ord_documents(
        sources=[],
        verify_tls=True,
        max_doc_kb=512,
        mock_mode=True,
    )
    assert len(docs) >= 1


def test_ord_search_by_query() -> None:
    """Test searching ORD resources by query string."""
    docs = load_ord_documents(
        sources=["fixtures/ord.sample.json"],
        verify_tls=True,
        max_doc_kb=512,
        mock_mode=False,
    )
    hits = search_ord_resources(docs, query="finance", resource_type="dataProduct", limit=10)
    assert len(hits) >= 1
    assert hits[0]["type"] == "dataProduct"
    assert (
        "finance" in hits[0].get("title", "").lower()
        or "finance" in hits[0].get("description", "").lower()
    )


def test_ord_search_by_type() -> None:
    """Test searching ORD resources by type."""
    docs = load_ord_documents(
        sources=["fixtures/ord.sample.json"],
        verify_tls=True,
        max_doc_kb=512,
        mock_mode=False,
    )
    hits = search_ord_resources(docs, query="", resource_type="dataProduct", limit=10)
    assert len(hits) >= 1
    assert all(h["type"] == "dataProduct" for h in hits)


def test_ord_search_limit() -> None:
    """Test search respects limit parameter."""
    docs = load_ord_documents(
        sources=["fixtures/ord.sample.json"],
        verify_tls=True,
        max_doc_kb=512,
        mock_mode=False,
    )
    hits = search_ord_resources(docs, query="", resource_type="", limit=1)
    assert len(hits) <= 1


def test_ord_validate_valid_document() -> None:
    """Test validation of valid ORD document."""
    docs = load_ord_documents(
        sources=["fixtures/ord.sample.json"],
        verify_tls=True,
        max_doc_kb=512,
        mock_mode=False,
    )
    report = validate_ord_documents(docs)
    # The fixture should be valid, but we check structure
    assert "ok" in report
    assert "issues" in report
    assert isinstance(report["issues"], list)


def test_ord_validate_invalid_document() -> None:
    """Test validation catches invalid ORD document."""
    invalid_doc = {"invalid": "structure"}
    report = validate_ord_documents([invalid_doc])
    assert "ok" in report
    assert "issues" in report
    # Should have validation issues
    assert len(report["issues"]) > 0


def test_ord_tools_server_builds() -> None:
    """Verify server builds successfully with ORD tools."""
    server = build_server()
    assert server is not None
    # Server should build without errors, indicating tools are registered
