"""Smoke test: server builds.

File: tests/test_ping.py
Version: v1
"""

from sap_bdc_mcp.server import build_server


def test_server_builds() -> None:
    server = build_server()
    assert server is not None
