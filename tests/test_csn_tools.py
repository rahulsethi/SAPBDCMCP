"""CSN tools comprehensive tests.

File: tests/test_csn_tools.py
Version: v1
"""

from sap_bdc_mcp.connectors.csn_client import csn_diff, csn_render_docs, csn_validate
from sap_bdc_mcp.server import build_server


def test_csn_validate_valid() -> None:
    """Test validation of valid CSN."""
    valid_csn = {
        "definitions": {
            "Entity1": {"kind": "entity"},
            "Entity2": {"kind": "entity"},
        }
    }
    result = csn_validate(valid_csn)
    assert result["ok"] is True
    assert len(result["issues"]) == 0


def test_csn_validate_invalid_not_object() -> None:
    """Test validation rejects non-object CSN."""
    result = csn_validate("not an object")
    assert result["ok"] is False
    assert len(result["issues"]) > 0
    assert any("NOT_OBJECT" in issue.get("code", "") for issue in result["issues"])


def test_csn_validate_missing_definitions() -> None:
    """Test validation catches missing definitions."""
    invalid_csn = {"someOtherKey": "value"}
    result = csn_validate(invalid_csn)
    assert result["ok"] is False
    assert len(result["issues"]) > 0
    assert any("MISSING_DEFINITIONS" in issue.get("code", "") for issue in result["issues"])


def test_csn_diff_added_entities() -> None:
    """Test CSN diff detects added entities."""
    old_csn = {"definitions": {"Entity1": {"kind": "entity"}}}
    new_csn = {"definitions": {"Entity1": {"kind": "entity"}, "Entity2": {"kind": "entity"}}}
    
    result = csn_diff(old_csn, new_csn)
    assert "breaking" in result
    assert "non_breaking" in result
    assert "summary" in result
    assert result["summary"]["added_entities"] >= 1


def test_csn_diff_removed_entities() -> None:
    """Test CSN diff detects removed entities."""
    old_csn = {"definitions": {"Entity1": {"kind": "entity"}, "Entity2": {"kind": "entity"}}}
    new_csn = {"definitions": {"Entity1": {"kind": "entity"}}}
    
    result = csn_diff(old_csn, new_csn)
    assert result["summary"]["removed_entities"] >= 1
    assert len(result["breaking"]) >= 1


def test_csn_diff_no_changes() -> None:
    """Test CSN diff with no changes."""
    csn = {"definitions": {"Entity1": {"kind": "entity"}}}
    result = csn_diff(csn, csn)
    assert result["summary"]["added_entities"] == 0
    assert result["summary"]["removed_entities"] == 0


def test_csn_render_docs() -> None:
    """Test CSN rendering to Markdown."""
    csn = {
        "definitions": {
            "Entity1": {"kind": "entity"},
            "Entity2": {"kind": "view"},
        }
    }
    md = csn_render_docs(csn)
    assert isinstance(md, str)
    assert "# CSN Documentation" in md
    assert "Entity1" in md
    assert "Entity2" in md


def test_csn_render_docs_empty() -> None:
    """Test CSN rendering with empty definitions."""
    csn = {"definitions": {}}
    md = csn_render_docs(csn)
    assert isinstance(md, str)
    assert "Entities: 0" in md


def test_csn_tools_server_builds() -> None:
    """Verify server builds successfully with CSN tools."""
    server = build_server()
    assert server is not None
    # Server should build without errors, indicating tools are registered

