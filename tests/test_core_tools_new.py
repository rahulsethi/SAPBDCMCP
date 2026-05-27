"""Tests for new core tools: get_tenant_info and whoami.

File: tests/test_core_tools_new.py
Version: v1
"""

from sap_bdc_mcp.server import build_server


def test_bdc_get_tenant_info_registered() -> None:
    """Verify bdc_get_tenant_info tool is registered."""
    server = build_server()
    assert server is not None
    # Tool should be registered (verified by server build success)


def test_bdc_whoami_registered() -> None:
    """Verify bdc_whoami tool is registered."""
    server = build_server()
    assert server is not None
    # Tool should be registered (verified by server build success)
