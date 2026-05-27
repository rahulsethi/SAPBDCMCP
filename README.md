# SAP Business Data Cloud MCP Server (`sap-bdc-mcp`)

An **MCP (Model Context Protocol)** server that exposes **safe, well-scoped SAP Business Data Cloud (BDC)** discovery + contract tooling for AI agents (Cursor, Claude Desktop, LibreChat, etc.) — with **enterprise-first guardrails** (redaction, policy gating, bounded outputs, and read-only defaults).

> **Latest release:** v0.2.0 — *Governed BDC Connect* (Databricks-first execution, Snowflake readiness, audit + policy gates, npx distribution wrapper, subprocess plugin upstreams). See the [v0.2.0 section at the end of this README](#v020--governed-bdc-connect-2026-05-27) and the [CHANGELOG](CHANGELOG.md).
>
> **Previous release:** v0.1.0 — contract-first *open-core* foundation: **ORD discovery**, **CSN contract checks**, **share planning (non-executing)**. The v0.1 content below describes that initial baseline; v0.2 builds on it without breaking compatibility.

---

## Why this exists

Modern enterprises increasingly want **AI agents** to *act* — not just chat. But real enterprise action requires:

- controlled access to systems of record,
- strict governance and auditability,
- safe defaults (no accidental writes),
- predictable, machine-readable tool contracts.

**MCP** provides the standard “tool bus” that lets external clients call tools safely. This project provides that tool bus specifically for **SAP Business Data Cloud** so agents can:

- **discover** data products and resources (ORD),
- **validate and diff** schema contracts (CSN),
- **plan** data sharing contracts before execution (share plans),
- **operate safely** (redaction + permissions + bounded outputs).

---

## Where `sap-bdc-mcp` fits in the enterprise landscape

In most enterprise setups, you’ll have:

- **AI clients** (Cursor, Claude Desktop, LibreChat, internal copilots)
- **MCP servers** (tool providers) running inside a controlled network boundary
- **SAP platforms** (BDC, Datasphere, BW, etc.)
- **Governance** (identity, policies, approvals, logging, DLP)

`SAPBDCMCP` is intended to run **inside your boundary** (developer laptop, jump host, or a controlled runtime) and act as the **policy-gated integration layer** between agentic tooling and SAP BDC.

A typical flow:

1. User asks an AI client to find / validate / plan something.
2. The client calls MCP tools exposed by `sap-bdc-mcp`.
3. The server enforces:
   - output size limits,
   - redaction of secrets,
   - permission levels (READ/WRITE/ADMIN),
   - “no writes by default”.
4. Results are returned to the client in structured form.

> **Important:** v0.1 focuses on *read-only* and *contract-first* operations. It does **not** execute shares or mutate BDC resources.

---

## Architecture (plugin-based, safety-first)

### Component view

```
MCP Client (Cursor / Claude / LibreChat)
            |
            | stdio (v0.1)
            v
+---------------------------+
|  FastMCP Server           |
|  (tool registry)          |
+------------+--------------+
             |
             v
+---------------------------+        +--------------------------+
| Policy + Redaction        |        | Connectors / Parsers     |
| - Permission gates        |------->| - ORD loader + search    |
| - Secret redaction        |        | - JSON Schema validation |
| - Output bounds           |        | - CSN validation + diff  |
+------------+--------------+        +--------------------------+
             |
             v
+---------------------------+
| Tool Packs (v0.1)         |
| - Core                    |
| - ORD                     |
| - CSN                     |
| - Share Plan              |
+---------------------------+
```

### Design principles

- **Safe defaults**: write tools are off unless explicitly enabled.
- **Contract-first**: validate structures before “doing” anything.
- **Composable**: tools are grouped into “packs” that can evolve independently.
- **Enterprise-friendly**: minimal data retention, predictable behavior, and clear boundaries.

---

## What’s included in v0.1

### Core tooling (safe diagnostics)
- Health + wiring checks
- Configuration diagnostics (with redaction)
- Tenant/user “identity” introspection (mock-friendly)

### ORD (Open Resource Discovery)
- Fetch ORD documents from URLs and local files
- Expand ORD Configuration documents (to resolve referenced documents)
- Search resources by type (data products, APIs, events, etc.)
- Validate documents against shipped JSON Schemas

### CSN (Common Schema Notation / contract checks)
- Validate CSN structure for interoperability / tooling assumptions
- Diff CSNs to detect breaking vs non-breaking changes
- Render CSN → Markdown documentation (quick contract docs)

### Share planning (non-executing)
- Build share plan objects with a stable contract shape
- Validate share plans against safety limits (asset limits, duplicates, required fields)
- **No execution in v0.1** (planning + validation only)

---

## Installation

### Install from PyPI (recommended)
```bash
pip install sap-bdc-mcp
```

### Install from source (development)
```bash
git clone https://github.com/rahulsethi/SAPBDCMCP.git
cd SAPBDCMCP
python -m venv .venv
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### Prerequisites

- Python **3.11+**
- `pip`

### Install from source (recommended for v0.1)
```bash
git clone https://github.com/rahulsethi/SAPBDCMCP.git
cd SAPBDCMCP

python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# macOS/Linux
# source .venv/bin/activate

pip install -e ".[dev]"
```

### Environment file (optional)
```bash
cp .env.example .env
```

---

## Configuration

The server is configured via environment variables (or a `.env` file).

### Required (for v0.1)
Nothing is strictly required — **mock mode** supports local development without a BDC tenant.

### Common settings

| Variable | Default | Purpose |
|---|---:|---|
| `BDC_MODE` | `local` | Runtime mode label (local/dev/prod) |
| `BDC_MOCK_MODE` | `1` | Use fixtures/local inputs instead of calling external endpoints |
| `BDC_VERIFY_TLS` | `1` | Verify TLS certificates for HTTPS fetches |
| `BDC_MAX_DOC_KB` | `512` | Max size for fetched ORD docs (prevents “LLM ate my RAM” moments) |
| `BDC_ORD_SOURCES` | *(empty)* | Comma-separated list of ORD sources (URLs or file paths) |
| `BDC_PLUGINS` | *(empty)* | Comma-separated plugin module paths to load |
| `BDC_ENABLE_WRITE_TOOLS` | `0` | Enables write tools (**keep OFF in v0.1**) |

### Optional tenant identity (informational in v0.1)

| Variable | Purpose |
|---|---|
| `BDC_TENANT_ID` | Tenant identifier (redacted in outputs) |
| `BDC_REGION` | Region label |
| `BDC_BASE_URL` | Base URL label (redacted where appropriate) |
| `BDC_USER` | User label (redacted) |
| `BDC_SERVICE_ACCOUNT` | Service account label (redacted) |

---

## Running the server

### Stdio mode (default)
```bash
sap-bdc-mcp
```

This starts the MCP server on **stdio**, suitable for:
- Cursor MCP integration
- Claude Desktop MCP servers
- LibreChat MCP connectors
- custom MCP clients

### Alternative entry (useful for debugging)
```bash
python -m sap_bdc_mcp
```

---

## Using from MCP clients

### Cursor
This repo includes a Cursor MCP configuration file at `.cursor/mcp.json`.

Typical workflow:
1. Open the repository in Cursor
2. Ensure your venv is active and dependencies are installed
3. Cursor will detect MCP config and can start the server automatically

### Claude Desktop
Add an MCP server entry (stdio) and point it to your environment’s `sap-bdc-mcp` executable.

### LibreChat
Configure an MCP server as a stdio tool provider and run it inside the same host/container boundary as LibreChat.

> Exact configuration formats differ by client; the important invariant is: **this server speaks MCP over stdio in v0.1**.

---

## Tool catalog (v0.1)

This section is intentionally detailed so you can:
- understand expected inputs/outputs,
- write deterministic agent prompts,
- validate behavior without a BDC tenant.

### Core tools

#### `bdc_ping`
**Purpose:** lightweight health check for server wiring and config surface.

**Returns (example):**
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

**Test prompts:**
- “Call `bdc_ping` and tell me whether write tools are enabled.”
- “Check if the SAP BDC MCP server is alive and report version + mode.”

---

#### `bdc_diagnostics`
**Purpose:** structured readiness report (all sensitive values redacted).

**Returns (high level):**
- runtime mode, TLS settings, limits
- ORD source configuration
- plugin status
- redacted environment summary

**Test prompts:**
- “Run `bdc_diagnostics` and summarize what is configured vs missing.”
- “Show me current safety limits and plugin status.”

---

#### `bdc_get_tenant_info`
**Purpose:** returns configured tenant labels (redacted), useful for client sanity checks.

**Returns (high level):**
- tenant id, region, base url (if configured)
- mode + mock mode

**Test prompts:**
- “Use `bdc_get_tenant_info` and confirm whether a tenant is configured.”
- “Show tenant metadata (redacted) and current mode.”

---

#### `bdc_whoami`
**Purpose:** returns identity labels (mock identity in mock mode).

**Returns (high level):**
- user / service account identity (redacted)
- mock identity when `BDC_MOCK_MODE=1`

**Test prompts:**
- “Call `bdc_whoami` and tell me who this server thinks it is.”
- “Show identity info, but ensure secrets are not displayed.”

---

### ORD tools (Open Resource Discovery)

#### `bdc_ord_fetch_documents`
**Purpose:** fetch ORD documents from sources (URLs or local files). Supports ORD **Configuration** expansion.

**Parameters:**
- `sources` *(optional)*: list of URLs/file paths. If omitted, uses `BDC_ORD_SOURCES`.

**Returns:**
- document count
- full ORD documents (expanded if configuration docs are used)

**Test prompts:**
- “Fetch ORD docs from the configured sources, then summarize how many documents were loaded.”
- “Load the local ORD sample fixture and list the available resource types.”

---

#### `bdc_ord_search`
**Purpose:** search across loaded ORD documents.

**Parameters:**
- `query` *(required)*: search query string
- `resource_type` *(optional)*: default `dataProduct`  
  (e.g., `apiResource`, `eventResource`, `entityType`, `capability`)
- `sources` *(optional)*: override sources (defaults to config)
- `limit` *(optional)*: default `25`

**Returns:**
- query + resource_type
- count
- matching resources (ordId, title, description, metadata)

**Test prompts:**
- “Search ORD for data products matching ‘finance’ and show top 5.”
- “Search for ‘sales’ in `apiResource` and summarize results.”
- “Find entity types containing ‘Customer’ and list ordIds.”

---

#### `bdc_ord_validate`
**Purpose:** validate ORD documents against JSON Schema.

**Parameters:**
- `sources` *(optional)*: list of sources to validate (defaults to config)

**Returns:**
- ok/not ok
- issues with paths + messages (capped per document)

**Test prompts:**
- “Validate the currently configured ORD sources and report any schema errors.”
- “Validate the ORD fixture and show me the first 10 issues (if any).”

---

### CSN tools (Common Schema Notation)

#### `bdc_csn_validate`
**Purpose:** validate a CSN object for tooling compatibility.

**Parameters:**
- `csn` *(required)*: CSN JSON object

**Returns:**
- ok/not ok
- issues with codes + messages

**Test prompts:**
- “Validate this CSN and explain what’s missing or malformed.”
- “Check whether this CSN is safe to publish as a contract.”

---

#### `bdc_csn_diff`
**Purpose:** compare two CSNs and classify changes.

**Parameters:**
- `old_csn` *(required)*
- `new_csn` *(required)*

**Returns:**
- breaking changes: removals, incompatible type changes, kind changes
- non-breaking changes: additive changes
- summary stats

**Test prompts:**
- “Diff these two CSNs and list breaking changes first, then non-breaking.”
- “Tell me if upgrading from old_csn to new_csn is backward compatible.”

---

#### `bdc_csn_render_docs`
**Purpose:** render CSN → Markdown documentation (contract docs).

**Parameters:**
- `csn` *(required)*

**Returns:**
- Markdown string describing entities, fields, types, constraints

**Test prompts:**
- “Generate Markdown docs for this CSN and include entity + field summaries.”
- “Create a compact schema reference for this CSN.”

---

### Share planning tools (non-executing in v0.1)

#### `bdc_share_plan`
**Purpose:** create a share plan object (does not execute anything).

**Parameters:**
- `share_name` *(required)*
- `assets` *(required)*: list of assets:
  - `type`: `table` | `view` | `file`
  - `name`: asset identifier
  - `schema` *(optional)*: namespace/schema
  - `comment` *(optional)*
- `description` *(optional)*
- `provider` *(optional)*: default `sap-bdc`

**Returns:**
- normalized, validated share plan object

**Test prompts:**
- “Create a share plan called ‘demo_share’ with 2 tables in schema ‘FIN’.”
- “Generate a share plan for these assets and return the resulting JSON.”

---

#### `bdc_share_validate_contract`
**Purpose:** validate a share plan contract and safety limits.

**Parameters:**
- `plan` *(required)*: share plan JSON

**Validations:**
- required fields + structure
- max asset count (50)
- duplicate asset detection
- asset naming/shape checks

**Returns:**
- ok/not ok
- issues list (if any)

**Test prompts:**
- “Validate this share plan and tell me what I need to fix.”
- “Check whether this plan exceeds safety limits or contains duplicates.”

---

## Testing & quality

### Run tests
```bash
pytest
```

### Run with coverage
```bash
pytest --cov=src/sap_bdc_mcp --cov-report=term-missing
```

**Test coverage (v0.1): 100%** statement coverage for `src/sap_bdc_mcp` is the quality bar for this repo (and should remain enforced as changes land).  
If you ever see lower numbers, treat it as a regression and tighten tests before merging.

---

## Safety, security, and governance notes

This project is designed to be safe by default, but **enterprise safety is a system property**, not a single feature. Recommended posture:

### Safe defaults baked in
- **Write tools disabled** by default (`BDC_ENABLE_WRITE_TOOLS=0`)
- **Automatic secret redaction** across tool outputs
- **Bounded outputs** to prevent oversized data egress
- **Mock mode** to develop without connecting to production

### Data handling expectations
- v0.1 tools focus on **discovery + contract validation**, not data movement.
- The server is intended to run **within your controlled boundary**.
- When future versions add live BDC operations, they should be deployed with:
  - least-privileged service accounts,
  - strict network controls,
  - centralized logging/monitoring,
  - approvals for write actions (where appropriate).

### Redaction scope
The server automatically redacts common sensitive patterns including:
- API keys, secrets, passwords
- bearer tokens
- credentials embedded in URLs
- fields with sensitive key names

> If you are deploying this inside an enterprise, treat this as one layer of defense-in-depth, not a substitute for DLP, IAM, and network security.

---

## Contributing
Contributions are welcome. Please see `CONTRIBUTING.md`.

---

## License

`sap-bdc-mcp` is licensed under the **PolyForm Noncommercial License 1.0.0** from v0.2.0 onward. (v0.1.0 was MIT; that version remains MIT-licensed for code already in use.) See [`LICENSE`](LICENSE) for the full text.

- **Free for noncommercial use** — personal, evaluation, research, academic, and use by charitable / educational / public / government institutions.
- **Commercial / for-profit use requires a separate license.** See [`docs_public/COMMERCIAL_LICENSING.md`](docs_public/COMMERCIAL_LICENSING.md) to inquire.

---

## v0.2.0 — *Governed BDC Connect* (2026-05-27)

v0.2.0 turns sap-bdc-mcp from a contract-first discovery server (v0.1) into a **governed-execution** server. Three deltas land:

1. **Provider-neutral execution layer** — `BDCConnectProvider` ABC with `DatabricksProvider` (real provider) and `SnowflakeProvider` (readiness-only at v0.2; mutation deferred to v0.3 per ADR-002).
2. **Policy + audit teeth** — tool risk metadata, SAP API policy evidence, dry-run + approval-token gating, JSONL audit log.
3. **Multi-runtime reach** — `BDC_PLUGINS` now accepts `npx:` / `uvx:` / `cmd:` upstream MCP servers as subprocess plugins. sap-bdc-mcp itself can now be launched via `npx -y sap-bdc-mcp@0.2.0` thanks to a Node bootstrap wrapper that bridges to `uvx`.

### What's new — tool surface

8 new MCP tools land at v0.2 on top of the 12 from v0.1:

| Tool | Category | Mutability | Risk | Notes |
|---|---|---|---|---|
| `bdc_tool_risk_catalog` | governance | READ | low | All registered tools + their risk metadata |
| `bdc_policy_explain` | governance | READ | low | Which gates apply to a tool and would they pass now |
| `bdc_api_policy_check` | governance | READ | low | SAP API evidence summary per tool |
| `bdc_audit_tail` | governance | READ | low | Recent audit events (redacted, capped) |
| `bdc_connect_list_providers` | providers | READ | low | Configured providers + capabilities |
| `bdc_connect_diagnostics` | providers | READ | low | Provider configuration health |
| `bdc_connect_preflight` | providers | READ | low | Run a provider's preflight |
| `bdc_databricks_preflight` | databricks | READ | medium | Databricks share-readiness preflight |
| `bdc_databricks_validate_share_readiness` | databricks | READ | medium | Per-share readiness check |
| `bdc_databricks_generate_csn_from_share` | databricks | READ | low | CSN from a Databricks share (primitives only — see D-006) |
| `bdc_snowflake_preflight` | snowflake | READ | low | Snowflake readiness checks (no mutation at v0.2) |
| `bdc_snowflake_explain_flow` | snowflake | READ | low | Documented publish flow text |
| `bdc_share_execute_plan` | sharing | **WRITE** | **high** | Governed execution. Requires dry-run + approval token |

All 12 v0.1 tools are still registered and identical in behavior — they now also produce audit events.

### Two install routes

**Python (recommended for production):**
```bash
pip install sap-bdc-mcp==0.2.0
sap-bdc-mcp --help
```

**Node / npx (no Python toolchain to manage):**
```bash
npx -y sap-bdc-mcp@0.2.0 --help
```
The wrapper bootstraps Python via [`uv`](https://docs.astral.sh/uv/) automatically. If `uvx` isn't on your PATH, the wrapper prints a one-screen install hint and exits.

### Configure in your MCP client

`claude_desktop_config.json` (Python install):
```json
{
  "mcpServers": {
    "sap-bdc-mcp": {
      "command": "sap-bdc-mcp",
      "env": { "BDC_MODE": "local", "BDC_MOCK_MODE": "1" }
    }
  }
}
```

`claude_desktop_config.json` (npx install):
```json
{
  "mcpServers": {
    "sap-bdc-mcp": {
      "command": "npx",
      "args": ["-y", "sap-bdc-mcp@0.2.0"],
      "env": { "BDC_MODE": "local", "BDC_MOCK_MODE": "1" }
    }
  }
}
```

### Safe defaults (unchanged spirit, more teeth)

- `BDC_ENABLE_WRITE_TOOLS=0` and `BDC_ENABLE_ADMIN_TOOLS=0` by default — every mutating tool is refused until you opt in.
- `BDC_REQUIRE_DRY_RUN=1` — high-risk tools must dry-run first; the dry-run returns a `correlation_id` you replay on real execute.
- `BDC_REQUIRE_APPROVAL_TOKEN=1` + `BDC_APPROVAL_TOKEN=<your-secret>` — every real execution must pass a constant-time-compare token (per [D-003](docs/release/v0.2.0/03_Decisions/D-003-approval-token-mechanism.md)).
- `BDC_API_POLICY_STRICT=1` — WRITE/ADMIN tools with `api_surface=UNKNOWN` are refused. This is what gates subprocess plugin proxies by default.
- `BDC_AUDIT_ENABLED=1` — every tool call writes a JSONL audit event (sha256-hashed inputs after redaction). Tail via `bdc_audit_tail`.

Full env-var reference + troubleshooting + the upgrade path from v0.1 is in the [CHANGELOG](CHANGELOG.md).

### Subprocess plugin upstreams (npx / uvx / cmd)

```bash
BDC_PLUGINS="gh=npx:@modelcontextprotocol/server-github@latest,sentry=uvx:mcp-server-sentry"
BDC_PLUGIN_TRUST="gh:documented_sdk"          # operator-asserted trust
BDC_PLUGIN_ENV_PASSTHROUGH="GITHUB_TOKEN"     # secrets to forward
```

Child MCP server tools are proxied as `plug_<alias>__<tool>`, treated as `WRITE / UNKNOWN-surface` by default, gated through the same audit + policy chain. Trust is operator-asserted; sap-bdc-mcp never blindly trusts a child's metadata.

### Publishing

PyPI + npm + GitHub Releases. Publishing is a deliberate, manual step performed by the maintainer. The artifacts to upload are:

- PyPI: `dist/sap_bdc_mcp-0.2.0-py3-none-any.whl` and `dist/sap_bdc_mcp-0.2.0.tar.gz` (produced by `python -m build`)
- npm: `npx-wrapper/` (`cd npx-wrapper && npm publish --access public`)
- GitHub Release: tag `v0.2.0` with the [CHANGELOG](CHANGELOG.md) v0.2.0 section as the body

### Full changelog

See [`CHANGELOG.md`](CHANGELOG.md) — the canonical record of what's in v0.2.0.
