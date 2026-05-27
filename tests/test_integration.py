"""Integration tests for MCP server.

File: tests/test_integration.py
Version: v1
"""

from sap_bdc_mcp.server import build_server
from sap_bdc_mcp.config import BDCConfig


def test_server_builds_and_configures() -> None:
    """Test that server builds with proper configuration."""
    server = build_server()
    assert server is not None

    # Verify config can be loaded
    config = BDCConfig.from_env()
    assert config is not None
    assert config.mode in ("local", "dev", "prod")
    assert isinstance(config.mock_mode, bool)
    assert isinstance(config.verify_tls, bool)
    assert config.max_doc_kb > 0


def test_server_with_mock_mode() -> None:
    """Test server works in mock mode."""
    import os
    from unittest.mock import patch

    # Temporarily set mock mode
    with patch.dict(os.environ, {"BDC_MOCK_MODE": "1"}):
        config = BDCConfig.from_env()
        assert config.mock_mode is True

        server = build_server()
        assert server is not None
