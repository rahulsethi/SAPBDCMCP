from sap_bdc_mcp.server import build_server

def test_server_builds():
    server = build_server()
    assert server is not None
