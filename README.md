<!-- SAP Business Data Cloud MCP Server -->
<!-- File: README.md -->
<!-- Version: v1 -->

# SAP Business Data Cloud MCP Server (sap-bdc-mcp)

An MCP (Model Context Protocol) server that exposes SAP Business Data Cloud (BDC) discovery and contract validation as safe, well-scoped tools for AI agents.

**v0.1 theme:** contract-first open-core (ORD + CSN + share planning scaffolding).

## Quickstart (local, mock mode)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1

pip install -e ".[dev]"

cp .env.example .env
sap-bdc-mcp
```

## Tools (scaffolded)

- `bdc_ping`
- `bdc_diagnostics`
- `bdc_ord_fetch_documents`
- `bdc_ord_search`
- `bdc_ord_validate`
- `bdc_csn_validate`
- `bdc_csn_diff`
- `bdc_csn_render_docs`
- `bdc_share_plan`
- `bdc_share_validate_contract`

> In this scaffold, most tools return **stub responses** with TODO markers.
> Next we’ll implement v0.1 properly, version-by-version.

## Cursor integration

This repo includes a project-local MCP config: `.cursor/mcp.json`.  
Once dependencies are installed, Cursor can start the server as a stdio MCP server.

See `docs/` for v0.1 planning and tracking.
