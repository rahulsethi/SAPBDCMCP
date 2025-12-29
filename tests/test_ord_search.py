from sap_bdc_mcp.connectors.ord_client import load_ord_documents, search_ord_resources

def test_ord_search_fixture(tmp_path, monkeypatch):
    docs = load_ord_documents(
        sources=["fixtures/ord.sample.json"],
        verify_tls=True,
        max_doc_kb=512,
        mock_mode=True,
    )
    hits = search_ord_resources(docs, query="finance", resource_type="dataProduct", limit=10)
    assert len(hits) >= 1
