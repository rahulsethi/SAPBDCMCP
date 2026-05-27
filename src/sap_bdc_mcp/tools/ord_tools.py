"""ORD tools for document fetching, searching, and validation.

File: src/sap_bdc_mcp/tools/ord_tools.py
Version: v3
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..connectors.ord_client import load_ord_documents, search_ord_resources, validate_ord_documents
from ._gated import ToolContext, gated
from .metadata import v01_metadata_list


_META = {m.name: m for m in v01_metadata_list()}


def register(server: Any, ctx: ToolContext) -> None:
    config = ctx.config

    @gated(server, ctx, meta=_META["bdc_ord_fetch_documents"])
    def bdc_ord_fetch_documents(sources: Optional[List[str]] = None) -> Dict:
        """Fetch ORD documents from URLs/files."""
        docs = load_ord_documents(
            sources=sources or config.ord_sources,
            verify_tls=config.verify_tls,
            max_doc_kb=config.max_doc_kb,
            mock_mode=config.mock_mode,
        )
        return {"count": len(docs), "documents": docs}

    @gated(server, ctx, meta=_META["bdc_ord_search"])
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

    @gated(server, ctx, meta=_META["bdc_ord_validate"])
    def bdc_ord_validate(sources: Optional[List[str]] = None) -> Dict:
        """Validate ORD documents and return diagnostics."""
        docs = load_ord_documents(
            sources=sources or config.ord_sources,
            verify_tls=config.verify_tls,
            max_doc_kb=config.max_doc_kb,
            mock_mode=config.mock_mode,
        )
        report = validate_ord_documents(docs)
        return report
