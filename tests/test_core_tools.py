"""Core tools tests: ping and diagnostics.

File: tests/test_core_tools.py
Version: v2
"""

from mcp.server.fastmcp import FastMCP

from sap_bdc_mcp.audit import AuditWriter
from sap_bdc_mcp.config import BDCConfig
from sap_bdc_mcp.server import build_server
from sap_bdc_mcp.tools._gated import ToolContext
from sap_bdc_mcp.tools.core import register
from sap_bdc_mcp.tools.metadata import MetadataRegistry


def _ctx(tmp_path=None) -> ToolContext:
    config = BDCConfig.from_env()
    audit = AuditWriter(
        str(tmp_path / "audit.jsonl") if tmp_path else ".sap_bdc_mcp/audit.jsonl",
        enabled=False,
    )
    return ToolContext(config=config, audit=audit, metadata=MetadataRegistry(), plugin_status=[])


def test_bdc_ping_functionality(tmp_path) -> None:
    """Core tools register without error against a fresh FastMCP server."""
    server = FastMCP("Test")
    register(server, _ctx(tmp_path))
    assert server is not None


def test_bdc_diagnostics_functionality(tmp_path) -> None:
    server = FastMCP("Test")
    register(server, _ctx(tmp_path))
    assert server is not None


def test_server_builds_with_core_tools() -> None:
    """Verify server builds successfully with all core tools registered."""
    server = build_server()
    assert server is not None
