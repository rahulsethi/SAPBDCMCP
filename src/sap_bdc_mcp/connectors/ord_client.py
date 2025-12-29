"""ORD client.

File: src/sap_bdc_mcp/connectors/ord_client.py
Version: v2

Implements:
- Loading ORD Documents from files / URLs
- Expanding ORD Configuration into its referenced Documents
- Searching across ORD resources (incl. Data Products)
- Validating payloads against the ORD JSON Schemas (vendored)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
from urllib.parse import urljoin, urlparse

import httpx
from jsonschema import Draft202012Validator

from .ord_schema import load_configuration_schema, load_document_schema


@dataclass(frozen=True)
class OrdLoadIssue:
    source: str
    message: str


def _repo_root() -> Path:
    # .../src/sap_bdc_mcp/connectors/ord_client.py -> repo root
    return Path(__file__).resolve().parents[3]


def _load_fixture() -> List[Dict[str, Any]]:
    # Used in tests and local mock mode.
    p = _repo_root() / "fixtures" / "ord.sample.json"
    return [json.loads(p.read_text(encoding="utf-8"))]


def _read_json_file(path: Path, max_doc_kb: int) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    size = path.stat().st_size
    if size > max_doc_kb * 1024:
        raise ValueError(f"ORD payload too large: {size} bytes (limit {max_doc_kb} KB)")
    return json.loads(path.read_text(encoding="utf-8"))


def _fetch_json(url: str, verify_tls: bool, max_doc_kb: int) -> Dict[str, Any]:
    with httpx.Client(verify=verify_tls, follow_redirects=True, timeout=15.0) as client:
        r = client.get(url)
        r.raise_for_status()

        # Protect memory: enforce a hard cap even if server doesn't send Content-Length.
        content = r.content
        if len(content) > max_doc_kb * 1024:
            raise ValueError(f"ORD payload too large: {len(content)} bytes (limit {max_doc_kb} KB)")
        return r.json()


def _is_configuration(payload: Dict[str, Any]) -> bool:
    return isinstance(payload.get("openResourceDiscoveryV1"), dict) and "documents" in payload["openResourceDiscoveryV1"]


def _expand_configuration(
    config_url: str,
    payload: Dict[str, Any],
    verify_tls: bool,
    max_doc_kb: int,
) -> List[Dict[str, Any]]:
    cfg_schema = load_configuration_schema()
    cfg_validator = Draft202012Validator(cfg_schema)
    cfg_errors = sorted(cfg_validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
    if cfg_errors:
        raise ValueError(f"Invalid ORD Configuration: {cfg_errors[0].message}")

    base_url = (payload.get("baseUrl") or "").strip()
    if not base_url:
        # Fallback: origin of the configuration URL
        parsed = urlparse(config_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

    docs: List[Dict[str, Any]] = []
    for d in payload.get("openResourceDiscoveryV1", {}).get("documents", []):
        doc_url = d.get("url") if isinstance(d, dict) else None
        if not doc_url:
            continue
        full_url = doc_url if doc_url.startswith("http") else urljoin(base_url + "/", doc_url.lstrip("/"))
        docs.append(_fetch_json(full_url, verify_tls=verify_tls, max_doc_kb=max_doc_kb))
    return docs


def load_ord_documents(
    sources: List[str],
    verify_tls: bool,
    max_doc_kb: int,
    mock_mode: bool,
) -> List[Dict[str, Any]]:
    """Load ORD documents from file paths or URLs.

    If the payload is an ORD Configuration file, referenced documents are fetched and returned.
    """
    if mock_mode and not sources:
        return _load_fixture()

    docs: List[Dict[str, Any]] = []
    for src in sources:
        src = src.strip()
        if not src:
            continue

        if src.startswith("http://") or src.startswith("https://"):
            payload = _fetch_json(src, verify_tls=verify_tls, max_doc_kb=max_doc_kb)
            if _is_configuration(payload):
                docs.extend(_expand_configuration(src, payload, verify_tls=verify_tls, max_doc_kb=max_doc_kb))
            else:
                docs.append(payload)
            continue

        # File path (relative paths resolved against cwd, then repo root as fallback)
        p = Path(src)
        if not p.is_absolute() and not p.exists():
            p = _repo_root() / src

        payload = _read_json_file(p, max_doc_kb=max_doc_kb)
        if _is_configuration(payload):
            # Local configuration file: expand using baseUrl (no file-relative expansion by spec).
            config_base = payload.get("baseUrl") or ""
            if not config_base:
                raise ValueError("Configuration file missing baseUrl; cannot expand document URLs")
            docs.extend(_expand_configuration(config_base, payload, verify_tls=verify_tls, max_doc_kb=max_doc_kb))
        else:
            docs.append(payload)

    return docs


def _iter_resources(doc: Dict[str, Any]) -> Iterable[Tuple[str, Dict[str, Any]]]:
    """Yield (resource_type, resource_obj) pairs from an ORD Document.

    ORD uses separate top-level arrays for each resource kind; we normalize them into a single stream.
    """
    section_map = {
        "dataProduct": "dataProducts",
        "apiResource": "apiResources",
        "eventResource": "eventResources",
        "entityType": "entityTypes",
        "capability": "capabilities",
        "integrationDependency": "integrationDependencies",
        "package": "packages",
        "product": "products",
        "vendor": "vendors",
        "consumptionBundle": "consumptionBundles",
        "group": "groups",
        "groupType": "groupTypes",
        "tombstone": "tombstones",
    }

    for rtype, key in section_map.items():
        items = doc.get(key) or []
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict):
                    yield rtype, it


def _matches_query(resource: Dict[str, Any], query: str) -> bool:
    if not query:
        return True

    q = query.lower()

    parts: List[str] = []
    for k in ("ordId", "localId", "title", "shortDescription", "description"):
        v = resource.get(k)
        if isinstance(v, str) and v:
            parts.append(v)

    tags = resource.get("tags")
    if isinstance(tags, list):
        parts.extend([str(t) for t in tags if t])

    labels = resource.get("labels")
    if isinstance(labels, dict):
        parts.extend([f"{k}:{v}" for k, v in labels.items() if v is not None])

    haystack = " ".join(parts).lower()
    return q in haystack


def search_ord_resources(
    docs: List[Dict[str, Any]],
    query: str,
    resource_type: str = "dataProduct",
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Search resources across ORD documents."""
    hits: List[Dict[str, Any]] = []
    rtype_norm = (resource_type or "").strip()

    # Accept a few handy aliases.
    alias = {
        "api": "apiResource",
        "event": "eventResource",
        "entity": "entityType",
        "dataproduct": "dataProduct",
        "data_product": "dataProduct",
    }
    if rtype_norm:
        rtype_norm = alias.get(rtype_norm, rtype_norm)

    for doc in docs:
        for rtype, r in _iter_resources(doc):
            if rtype_norm and rtype != rtype_norm:
                continue
            if not _matches_query(r, query):
                continue
            hits.append(
                {
                    "type": rtype,
                    "ordId": r.get("ordId"),
                    "title": r.get("title"),
                    "shortDescription": r.get("shortDescription"),
                    "description": r.get("description"),
                }
            )
            if len(hits) >= limit:
                return hits
    return hits


def validate_ord_documents(docs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate each document against the ORD Document schema.

    We treat documents as ORD Documents, not configuration objects (those should be expanded first).
    """
    schema = load_document_schema()
    validator = Draft202012Validator(schema)

    issues: List[Dict[str, Any]] = []
    for i, doc in enumerate(docs):
        for err in validator.iter_errors(doc):
            issues.append(
                {
                    "index": i,
                    "path": "/".join([str(p) for p in err.absolute_path]),
                    "message": err.message,
                }
            )
            if len(issues) >= 50:
                break
        if len(issues) >= 50:
            break

    return {"ok": len(issues) == 0, "issues": issues}
