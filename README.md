<!-- SAP Business Data Cloud MCP Server -->
<!-- File: README.md -->
<!-- Version: v2 -->

# SAP Business Data Cloud MCP Server (sap-bdc-mcp)

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server that exposes SAP Business Data Cloud (BDC) discovery and contract validation as safe, well-scoped tools for AI agents.

**Version:** 0.1.0 (in progress)

**Theme:** Contract-first open-core (ORD + CSN + share planning scaffolding)

---

## Overview

The SAP Business Data Cloud MCP Server provides AI agents with secure, policy-gated access to BDC capabilities including:

- **ORD Discovery**: Fetch, search, and validate Open Resource Discovery documents
- **CSN Validation**: Validate, diff, and document CSN (Common Schema Notation) contracts
- **Share Planning**: Create and validate share plans without execution (read-only in v0.1)
- **Core Diagnostics**: Health checks, diagnostics, and tenant information

All tools are designed with safety-first principles: secrets are redacted, outputs are bounded, and write operations are disabled by default.

---

## Features

### 🔒 Safety & Security
- **Automatic secret redaction** - Sensitive data is automatically redacted from outputs
- **Policy gating** - READ/WRITE/ADMIN permission levels with safe defaults
- **Bounded outputs** - Configurable limits on document sizes and result sets
- **Mock mode** - Test and develop without live BDC connections

### 📊 ORD (Open Resource Discovery) Tools
- Fetch ORD documents from URLs, files, or registries
- Search across ORD resources (data products, APIs, events, etc.)
- Validate ORD documents against JSON Schema
- Support for ORD Configuration expansion

### 🔍 CSN (Common Schema Notation) Tools
- Validate CSN structures for Interop compatibility
- Diff two CSNs to identify breaking vs non-breaking changes
- Generate comprehensive Markdown documentation from CSN

### 📦 Share Planning Tools
- Create share plan objects (no mutation in v0.1)
- Validate share plans against safety limits and contract structure
- Detect duplicate assets and validate asset structure

### 🛠️ Core Tools
- Health checks and diagnostics
- Tenant information retrieval
- Identity/user information (where supported)

---

## Installation

### Prerequisites
- Python 3.11 or higher
- pip

### Setup

```bash
# Clone the repository
git clone https://github.com/rahulsethi/SAPBDCMCP.git
cd sap-bdc-mcp

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.\.venv\Scripts\Activate.ps1
# On Linux/Mac:
source .venv/bin/activate

# Install package with dev dependencies
pip install -e ".[dev]"

# Copy environment template (optional)
cp .env.example .env
```

---

## Configuration

Configure the server using environment variables or a `.env` file:

```bash
# Server mode: local, dev, or prod
BDC_MODE=local

# Enable mock mode (uses fixtures instead of real API calls)
BDC_MOCK_MODE=1

# Verify TLS certificates
BDC_VERIFY_TLS=1

# Maximum document size in KB
BDC_MAX_DOC_KB=512

# Comma-separated list of ORD document sources (URLs or file paths)
BDC_ORD_SOURCES=

# Comma-separated list of plugin modules to load
BDC_PLUGINS=

# Enable write tools (disabled by default for safety)
BDC_ENABLE_WRITE_TOOLS=0

# Optional: Tenant information
BDC_TENANT_ID=
BDC_REGION=
BDC_BASE_URL=
BDC_USER=
BDC_SERVICE_ACCOUNT=
```

---

## Usage

### Running the Server

```bash
# Start the MCP server (stdio mode)
sap-bdc-mcp
```

The server runs in stdio mode by default, suitable for integration with MCP clients like Cursor, Claude Desktop, or custom applications.

### Cursor Integration

This repository includes MCP configuration for Cursor. Once installed, Cursor can automatically start the server as a stdio MCP server.

---

## Tools Reference

### Core Tools

#### `bdc_ping`
Lightweight health check for configuration and server wiring.

**Returns:**
- Server status and version
- Current mode and mock mode status
- Write tools enabled status

**Example:**
```json
{
  "ok": true,
  "server": "sap-bdc-mcp",
  "version": "0.1.0",
  "mode": "local",
  "mock_mode": true,
  "write_enabled": false
}
```

#### `bdc_diagnostics`
Structured environment and readiness report with automatic secret redaction.

**Returns:**
- Configuration details (mode, TLS settings, limits)
- ORD sources configuration
- Plugin status
- All sensitive data automatically redacted

#### `bdc_get_tenant_info`
Get tenant information from environment/config with automatic redaction.

**Returns:**
- Tenant ID, region, base URL (if configured)
- Mode and mock status
- All sensitive values redacted

#### `bdc_whoami`
Get current user/identity information (where supported) with automatic redaction.

**Returns:**
- User/service account information
- Mock identity in mock mode
- All sensitive data redacted

---

### ORD (Open Resource Discovery) Tools

#### `bdc_ord_fetch_documents`
Fetch ORD documents from URLs, files, or registries.

**Parameters:**
- `sources` (optional): List of URLs or file paths. If omitted, uses `BDC_ORD_SOURCES` from config.

**Returns:**
- Document count
- Full ORD documents (supports ORD Configuration expansion)

**Features:**
- Supports both ORD Documents and ORD Configuration files
- Automatically expands Configuration files to fetch referenced documents
- Enforces size limits for security
- Works with local files, HTTP/HTTPS URLs

#### `bdc_ord_search`
Search ORD resources across loaded documents.

**Parameters:**
- `query` (required): Search query string
- `resource_type` (optional): Filter by resource type (default: "dataProduct")
  - Supported types: dataProduct, apiResource, eventResource, entityType, capability, etc.
- `sources` (optional): ORD document sources (uses config if omitted)
- `limit` (optional): Maximum results (default: 25)

**Returns:**
- Query and resource type used
- Result count
- Matching resources with metadata (ordId, title, description, etc.)

**Search covers:**
- Resource IDs (ordId, localId)
- Titles and descriptions
- Tags and labels

#### `bdc_ord_validate`
Validate ORD documents against JSON Schema.

**Parameters:**
- `sources` (optional): ORD document sources to validate

**Returns:**
- Validation status (ok/not ok)
- List of validation issues with paths and messages
- Up to 50 issues reported per document

**Validates:**
- JSON structure
- Required fields
- Field types and formats
- ORD schema compliance

---

### CSN (Common Schema Notation) Tools

#### `bdc_csn_validate`
Validate a CSN structure for Interop compatibility.

**Parameters:**
- `csn` (required): CSN object to validate

**Returns:**
- Validation status
- List of issues with codes and messages

**Validates:**
- JSON object structure
- Required "definitions" key
- Entity structure (kind, elements)
- Element structure and types

#### `bdc_csn_diff`
Diff two CSNs and identify breaking vs non-breaking changes.

**Parameters:**
- `old_csn` (required): Previous CSN version
- `new_csn` (required): New CSN version

**Returns:**
- Breaking changes (entity removals, kind changes, element removals, type changes)
- Non-breaking changes (new entities, new elements)
- Summary statistics

**Detects:**
- Entity additions/removals
- Entity kind changes
- Element additions/removals
- Element type changes
- Type compatibility issues

#### `bdc_csn_render_docs`
Render CSN to comprehensive Markdown documentation.

**Parameters:**
- `csn` (required): CSN object to document

**Returns:**
- Markdown documentation string

**Includes:**
- Entity overview and count
- Entities grouped by kind
- Element details with types
- Key and nullable constraints
- Descriptions and comments

---

### Share Planning Tools

#### `bdc_share_plan`
Create a share plan object (read-only, no mutation in v0.1).

**Parameters:**
- `share_name` (required): Name of the share
- `assets` (required): List of asset objects
  - `type`: "table", "view", or "file"
  - `name`: Asset identifier
  - `schema` (optional): Schema/namespace
  - `comment` (optional): Asset description
- `description` (optional): Share description
- `provider` (optional): Provider name (default: "sap-bdc")

**Returns:**
- Complete share plan object with validated structure

#### `bdc_share_validate_contract`
Validate a share plan against safety limits and contract structure.

**Parameters:**
- `plan` (required): Share plan object to validate

**Returns:**
- Validation status
- List of issues (if any)

**Validates:**
- Plan structure and required fields
- Asset count limits (max 50 assets)
- Asset name validity
- Duplicate asset detection
- Asset structure compliance

**Note:** In v0.1, this is a read-only validation. Share execution is planned for v0.2+.

---

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/sap_bdc_mcp --cov-report=term-missing

# Run specific test file
pytest tests/test_ord_tools.py -v
```

### Test Coverage

Current test coverage: **72%+** with 36+ tests covering:
- All core tools
- ORD document operations
- CSN validation, diffing, and rendering
- Share plan creation and validation
- Integration tests

### Project Structure

```
sap-bdc-mcp/
├── src/sap_bdc_mcp/
│   ├── connectors/      # ORD and CSN clients
│   ├── models/          # Pydantic models
│   ├── schemas/         # JSON schemas (ORD)
│   ├── tools/           # MCP tool implementations
│   ├── config.py        # Configuration management
│   ├── policy.py        # Policy and permission gating
│   ├── redaction.py     # Secret redaction utilities
│   └── server.py        # Server construction
├── tests/               # Test suite
├── fixtures/            # Test fixtures (ORD samples)
└── docs/                # Documentation
```

---

## Safety & Security

### Default Safety Settings

- **Write tools disabled by default** - Set `BDC_ENABLE_WRITE_TOOLS=1` to enable
- **Automatic secret redaction** - All outputs are scanned and redacted
- **Bounded outputs** - Document size limits enforced
- **Policy gating** - Tools require appropriate permissions

### Redaction

The server automatically redacts:
- API keys and tokens
- Passwords and secrets
- Bearer tokens in strings
- Credentials in URLs
- Any field matching sensitive key patterns

---

## Roadmap

### v0.1 (Current - In Progress)
- ✅ Core server skeleton
- ✅ ORD discovery tools
- ✅ CSN validation tools
- ✅ Share planning scaffolding
- ✅ Comprehensive test suite
- ✅ Safety primitives (redaction, policy gating)

### v0.2 (Planned)
- Share execution (Databricks/Delta Sharing)
- BDC Connect SDK integration
- Plugin registry
- Enhanced ORD/CSN constraint validation

### v0.3+ (Future)
- Catalog/governance tools
- Enterprise deployment bundles
- Metrics and monitoring
- Premium features

---

## Contributing

Contributions are welcome! Please see `CONTRIBUTING.md` for guidelines.

---

## License

MIT License - see `LICENSE` file for details.

---

## Documentation

Additional documentation is available in the `docs/` directory:

- `ImplementationTracker_v0.1.md` - Implementation progress tracking
- `VersionPlan_v0.1.md` - Version planning and scope
- `ProjectPlan_v0.1.md` - Project plan and release criteria
- `ToolCatalog.md` - Complete tool catalog
- `TestPrompts_v0.1.md` - Example test prompts for MCP clients

---

## Support

For issues, questions, or contributions, please use the GitHub Issues page.

---

**Status:** Version 0.1.0 (in progress) - Contract-first open-core implementation
