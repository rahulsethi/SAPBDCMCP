"""ORD client (scaffold).

File: src/sap_bdc_mcp/connectors/ord_client.py
Version: v1
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import httpx


def _load_fixture() -> List[Dict[str, Any]]:
    fixture = Path("fixtures/ord.sample.json")
    if fixture.exists():
        return [json.loads(fixture.read_text(encoding="utf-8"))]
    return []


def load_ord_documents(
    sources: List[str],
    verify_tls: bool,
    max_doc_kb: int,
    mock_mode: bool,
) -> List[Dict[str, Any]]:
    """Load ORD documents from sources (URL or file path)."""
    if mock_mode:
        docs = _load_fixture()
        if docs:
            return docs

    docs: List[Dict[str, Any]] = []
    for src in sources:
        if src.startswith("http://") or src.startswith("https://"):
            with httpx.Client(verify=verify_tls, timeout=20.0) as client:
                r = client.get(src)
                r.raise_for_status()
                content = r.content
        else:
            content = Path(src).read_bytes()

        if len(content) > max_doc_kb * 1024:
            raise ValueError(f"ORD doc too large: {src} ({len(content)} bytes)")

        docs.append(json.loads(content.decode("utf-8")))
    return docs


def search_ord_resources(
    docs: List[Dict[str, Any]],
    query: str,
    resource_type: str,
    limit: int,
) -> List[Dict[str, Any]]:
    q = query.lower().strip()
    hits: List[Dict[str, Any]] = []

    for doc in docs:
        resources = doc.get("resources") or doc.get("openResourceDiscovery", {}).get("resources") or []
        if isinstance(resources, dict):
            resources = list(resources.values())

        for r in resources:
            rtype = (r.get("type") or "").lower()
            if resource_type and resource_type.lower() not in rtype:
                continue
            hay = " ".join(
                [
                    str(r.get("title", "")),
                    str(r.get("description", "")),
                    " ".join(r.get("labels", []) if isinstance(r.get("labels"), list) else []),
                ]
            ).lower()
            if q in hay:
                hits.append(
                    {
                        "id": r.get("id") or r.get("name"),
                        "type": r.get("type"),
                        "title": r.get("title"),
                        "description": r.get("description"),
                        "labels": r.get("labels", []),
                    }
                )
                if len(hits) >= limit:
                    return hits
    return hits


def validate_ord_documents(docs: List[Dict[str, Any]]) -> Dict[str, Any]:
    issues: List[Dict[str, str]] = []
    for i, doc in enumerate(docs):
        if not isinstance(doc, dict):
            issues.append({"doc": str(i), "code": "NOT_OBJECT", "message": "ORD doc must be JSON object"})
            continue
        # Very lightweight checks for scaffolding
        if "resources" not in doc and "openResourceDiscovery" not in doc:
            issues.append(
                {
                    "doc": str(i),
                    "code": "MISSING_RESOURCES",
                    "message": "ORD doc missing resources/openResourceDiscovery.resources",
                }
            )
    return {"ok": len(issues) == 0, "issue_count": len(issues), "issues": issues}
