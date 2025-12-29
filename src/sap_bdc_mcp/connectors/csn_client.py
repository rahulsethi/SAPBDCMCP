"""CSN client (scaffold).

File: src/sap_bdc_mcp/connectors/csn_client.py
Version: v1
"""

from __future__ import annotations

from typing import Any, Dict, List
import json


def csn_validate(csn: Dict[str, Any]) -> Dict[str, Any]:
    issues: List[Dict[str, str]] = []
    if not isinstance(csn, dict):
        return {"ok": False, "issues": [{"code": "NOT_OBJECT", "message": "CSN must be a JSON object"}]}

    # Minimal expectations for scaffold; real CSN interop checks come in v0.1 implementation.
    if "definitions" not in csn:
        issues.append({"code": "MISSING_DEFINITIONS", "message": "CSN missing 'definitions' key"})
    return {"ok": len(issues) == 0, "issues": issues}


def csn_diff(old_csn: Dict[str, Any], new_csn: Dict[str, Any]) -> Dict[str, Any]:
    old_defs = set((old_csn.get("definitions") or {}).keys())
    new_defs = set((new_csn.get("definitions") or {}).keys())

    removed = sorted(list(old_defs - new_defs))
    added = sorted(list(new_defs - old_defs))

    breaking: List[Dict[str, Any]] = []
    non_breaking: List[Dict[str, Any]] = []

    for name in removed:
        breaking.append({"code": "ENTITY_REMOVED", "entity": name})
    for name in added:
        non_breaking.append({"code": "ENTITY_ADDED", "entity": name})

    return {
        "breaking": breaking,
        "non_breaking": non_breaking,
        "summary": {
            "removed_entities": len(removed),
            "added_entities": len(added),
        },
    }


def csn_render_docs(csn: Dict[str, Any]) -> str:
    defs = csn.get("definitions") or {}
    lines = ["# CSN Documentation (scaffold)", ""]
    lines.append(f"- Entities: {len(defs)}")
    lines.append("")
    for name, body in list(defs.items())[:50]:
        kind = body.get("kind", "unknown") if isinstance(body, dict) else "unknown"
        lines.append(f"## {name}")
        lines.append(f"- kind: {kind}")
        lines.append("")
    if len(defs) > 50:
        lines.append("> Truncated at 50 entities.")
    return "\n".join(lines)
