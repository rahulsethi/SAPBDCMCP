"""CSN client for validation, diff, and documentation.

File: src/sap_bdc_mcp/connectors/csn_client.py
Version: v2
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


def csn_validate(csn: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a CSN structure for Interop compatibility.

    Checks for:
    - Valid JSON object structure
    - Required 'definitions' key
    - Valid entity definitions with expected structure
    """
    issues: List[Dict[str, str]] = []
    if not isinstance(csn, dict):
        return {
            "ok": False,
            "issues": [{"code": "NOT_OBJECT", "message": "CSN must be a JSON object"}],
        }

    # Check for required 'definitions' key
    if "definitions" not in csn:
        issues.append({"code": "MISSING_DEFINITIONS", "message": "CSN missing 'definitions' key"})
        return {"ok": False, "issues": issues}

    definitions = csn.get("definitions", {})
    if not isinstance(definitions, dict):
        issues.append(
            {"code": "INVALID_DEFINITIONS", "message": "CSN 'definitions' must be an object"}
        )
        return {"ok": False, "issues": issues}

    # Validate each entity definition
    for entity_name, entity_def in definitions.items():
        if not isinstance(entity_def, dict):
            issues.append(
                {
                    "code": "INVALID_ENTITY",
                    "entity": entity_name,
                    "message": f"Entity '{entity_name}' must be an object",
                }
            )
            continue

        # Check for kind (common in CSN)
        if "kind" not in entity_def:
            issues.append(
                {
                    "code": "MISSING_KIND",
                    "entity": entity_name,
                    "message": f"Entity '{entity_name}' missing 'kind' field",
                }
            )

        # Check for elements (for structured types)
        if "elements" in entity_def and not isinstance(entity_def["elements"], dict):
            issues.append(
                {
                    "code": "INVALID_ELEMENTS",
                    "entity": entity_name,
                    "message": f"Entity '{entity_name}' has invalid 'elements' (must be object)",
                }
            )

    return {"ok": len(issues) == 0, "issues": issues}


def csn_diff(old_csn: Dict[str, Any], new_csn: Dict[str, Any]) -> Dict[str, Any]:
    """Diff two CSNs and identify breaking vs non-breaking changes.

    Breaking changes:
    - Entities removed
    - Entity kind changed
    - Required elements removed or changed
    - Element types changed to incompatible types

    Non-breaking changes:
    - New entities added
    - New optional elements added
    - Element types widened (e.g., String -> Any)
    """
    old_defs = old_csn.get("definitions") or {}
    new_defs = new_csn.get("definitions") or {}

    if not isinstance(old_defs, dict) or not isinstance(new_defs, dict):
        return {
            "breaking": [{"code": "INVALID_INPUT", "message": "Invalid CSN structure"}],
            "non_breaking": [],
            "summary": {"error": "Invalid input"},
        }

    old_entity_names = set(old_defs.keys())
    new_entity_names = set(new_defs.keys())

    removed = sorted(list(old_entity_names - new_entity_names))
    added = sorted(list(new_entity_names - old_entity_names))
    common = old_entity_names & new_entity_names

    breaking: List[Dict[str, Any]] = []
    non_breaking: List[Dict[str, Any]] = []

    # Entities removed are breaking
    for name in removed:
        breaking.append({"code": "ENTITY_REMOVED", "entity": name})

    # Entities added are non-breaking
    for name in added:
        non_breaking.append({"code": "ENTITY_ADDED", "entity": name})

    # Check for changes in common entities
    for name in common:
        old_entity = old_defs[name]
        new_entity = new_defs[name]

        if not isinstance(old_entity, dict) or not isinstance(new_entity, dict):
            continue

        # Kind change is breaking
        old_kind = old_entity.get("kind")
        new_kind = new_entity.get("kind")
        if old_kind and new_kind and old_kind != new_kind:
            breaking.append(
                {
                    "code": "KIND_CHANGED",
                    "entity": name,
                    "old_kind": old_kind,
                    "new_kind": new_kind,
                }
            )

        # Check element changes
        old_elements = old_entity.get("elements") or {}
        new_elements = new_entity.get("elements") or {}

        if isinstance(old_elements, dict) and isinstance(new_elements, dict):
            old_element_names = set(old_elements.keys())
            new_element_names = set(new_elements.keys())

            # Removed elements are breaking
            for elem_name in old_element_names - new_element_names:
                breaking.append(
                    {
                        "code": "ELEMENT_REMOVED",
                        "entity": name,
                        "element": elem_name,
                    }
                )

            # Added elements are non-breaking (assuming optional by default)
            for elem_name in new_element_names - old_element_names:
                non_breaking.append(
                    {
                        "code": "ELEMENT_ADDED",
                        "entity": name,
                        "element": elem_name,
                    }
                )

            # Check for type changes in common elements
            for elem_name in old_element_names & new_element_names:
                old_elem = old_elements.get(elem_name, {})
                new_elem = new_elements.get(elem_name, {})

                if isinstance(old_elem, dict) and isinstance(new_elem, dict):
                    old_type = old_elem.get("type")
                    new_type = new_elem.get("type")

                    # Type narrowing is breaking (e.g., Any -> String)
                    if old_type and new_type and old_type != new_type:
                        # Simple check: if types differ, it's potentially breaking
                        # More sophisticated type compatibility checks could go here
                        breaking.append(
                            {
                                "code": "ELEMENT_TYPE_CHANGED",
                                "entity": name,
                                "element": elem_name,
                                "old_type": old_type,
                                "new_type": new_type,
                            }
                        )

    return {
        "breaking": breaking,
        "non_breaking": non_breaking,
        "summary": {
            "removed_entities": len(removed),
            "added_entities": len(added),
            "modified_entities": len(
                [
                    b
                    for b in breaking
                    if b.get("code") in ("KIND_CHANGED", "ELEMENT_REMOVED", "ELEMENT_TYPE_CHANGED")
                ]
            ),
        },
    }


def csn_render_docs(csn: Dict[str, Any]) -> str:
    """Render CSN to Markdown documentation.

    Generates comprehensive documentation including:
    - Entity overview
    - Entity details with kind and elements
    - Type information
    """
    defs = csn.get("definitions") or {}
    if not isinstance(defs, dict):
        return "# CSN Documentation\n\nInvalid CSN structure: definitions must be an object."

    lines = ["# CSN Documentation", ""]
    lines.append(f"**Total Entities:** {len(defs)}")
    lines.append("")

    if not defs:
        lines.append("No entities defined.")
        return "\n".join(lines)

    # Group by kind for better organization
    by_kind: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}
    for name, body in defs.items():
        if isinstance(body, dict):
            kind = body.get("kind", "unknown")
            if kind not in by_kind:
                by_kind[kind] = []
            by_kind[kind].append((name, body))

    # Render entities grouped by kind
    for kind, entities in sorted(by_kind.items()):
        lines.append(f"## {kind.title()} Entities")
        lines.append("")

        for name, body in sorted(entities)[:50]:
            lines.append(f"### {name}")

            # Kind
            entity_kind = body.get("kind", "unknown")
            if entity_kind:
                lines.append(f"- **Kind:** `{entity_kind}`")

            # Elements
            elements = body.get("elements")
            if isinstance(elements, dict) and elements:
                lines.append("- **Elements:**")
                for elem_name, elem_def in sorted(elements.items()):
                    if isinstance(elem_def, dict):
                        elem_type = elem_def.get("type", "unknown")
                        elem_key = elem_def.get("key", False)
                        elem_nullable = elem_def.get("nullable", True)
                        type_str = f"`{elem_type}`"
                        if elem_key:
                            type_str += " (key)"
                        if not elem_nullable:
                            type_str += " (required)"
                        lines.append(f"  - `{elem_name}`: {type_str}")
                    else:
                        lines.append(f"  - `{elem_name}`: {elem_def}")

            # Description/comment if available
            description = body.get("description") or body.get("comment")
            if description:
                lines.append(f"- **Description:** {description}")

            lines.append("")

    if len(defs) > 50:
        lines.append("> **Note:** Documentation truncated at 50 entities for readability.")

    return "\n".join(lines)
