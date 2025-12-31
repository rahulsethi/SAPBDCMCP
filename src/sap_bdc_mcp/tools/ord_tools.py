"""ORD tools for document fetching, searching, and validation.

File: src/sap_bdc_mcp/tools/ord_tools.py
Version: v2
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..config import BDCConfig
from ..connectors.ord_client import load_ord_documents, search_ord_resources, validate_ord_documents


def register(server: Any, config: BDCConfig) -> None:
    @server.tool()
    def bdc_ord_fetch_documents(sources: Optional[List[str]] = None) -> Dict:
        """Fetch ORD documents from URLs/files.

        If `sources` is omitted, uses BDC_ORD_SOURCES from config.
        """
        docs = load_ord_documents(
            sources=sources or config.ord_sources,
            verify_tls=config.verify_tls,
            max_doc_kb=config.max_doc_kb,
            mock_mode=config.mock_mode,
        )
        return {"count": len(docs), "documents": docs}

    @server.tool()
    def bdc_ord_search(
        query: str,
        resource_type: str = "dataProduct",
        sources: Optional[List[str]] = None,
        limit: int = 25,
    ) -> Dict:
        """Search ORD resources across loaded documents."""
        docs = load_ord_documents(
            sources=sources or config.ord_sources,
            verify_tls=config.verify_tls,
            max_doc_kb=config.max_doc_kb,
            mock_mode=config.mock_mode,
        )
        hits = search_ord_resources(docs, query=query, resource_type=resource_type, limit=limit)
        return {"query": query, "resource_type": resource_type, "count": len(hits), "results": hits}

    @server.tool()
    def bdc_ord_validate(sources: Optional[List[str]] = None) -> Dict:
        """Validate ORD documents and return diagnostics.

        Validates against ORD JSON Schema and checks for structural issues.
        """
        docs = load_ord_documents(
            sources=sources or config.ord_sources,
            verify_tls=config.verify_tls,
            max_doc_kb=config.max_doc_kb,
            mock_mode=config.mock_mode,
        )
        report = validate_ord_documents(docs)
        return report
