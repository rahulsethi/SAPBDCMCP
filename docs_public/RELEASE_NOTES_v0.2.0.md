# Release Notes — v0.2.0 — *Governed BDC Connect*

**Release date:** 2026-05-27
**Audience:** End users, agent operators, architects, security reviewers.
**One-liner:** Discovery server grows execution muscle — Databricks-first share execution, Snowflake readiness, every tool call gated and audited, and a Node `npx` install route.

> Looking for the engineering changelog? See [`../CHANGELOG.md`](../CHANGELOG.md).

---

## What changed at a glance

v0.1 was contract-first: read the catalog, validate schemas, plan shares — but never *do* anything. v0.2 keeps every v0.1 promise *and* adds a small, carefully gated execution surface.

Three pillars land:

1. **Provider-neutral execution.** A `BDCConnectProvider` interface with two concrete providers:
   - **Databricks** — full provider surface with `preflight`, `validate_plan`, `dry_run_execute`, `execute`. Mock mode is the exercised path at v0.2; real execution wires through the SAP BDC Connect SDK in v0.3 (real mode currently raises a clear `NotImplementedError` pointing there).
   - **Snowflake** — *readiness-only* at v0.2 (preflight + plan validation). Real Snowflake execution lands in v0.3.
2. **Policy + audit teeth.** Every tool now carries risk metadata (`mutability`, `risk`, `api_surface`, `api_evidence`, `bulk_data_behavior`). High-risk tools must dry-run first, then supply a constant-time-compared approval token. Every invocation writes a JSONL audit event with sha256-hashed inputs (post-redaction). Inspect via the new `bdc_audit_tail` tool.
3. **Multi-runtime reach.** `BDC_PLUGINS` now accepts subprocess MCP servers via `npx:`, `uvx:`, or `cmd:` schemes. The Python-only v0.1 plugin path still works. Subprocess plugin tools are distrusted by default — an operator must opt in via `BDC_PLUGIN_TRUST`. Separately, `sap-bdc-mcp` itself can now be launched via `npx -y sap-bdc-mcp@0.2.0` (the Node wrapper bootstraps Python via `uv`).

## Tool surface

**v0.1 tools (12)** — unchanged in name, signature, and return shape. They now also produce audit events.

| Category | v0.1 tools |
|---|---|
| Core | `bdc_ping`, `bdc_diagnostics`, `bdc_get_tenant_info`, `bdc_whoami` |
| ORD | `bdc_ord_fetch_documents`, `bdc_ord_search`, `bdc_ord_validate` |
| CSN | `bdc_csn_validate`, `bdc_csn_diff`, `bdc_csn_render_docs` |
| Sharing | `bdc_share_plan`, `bdc_share_validate_contract` |

**v0.2 additions (13 new tools)**

| Category | Tool | Mutability | Risk |
|---|---|---|---|
| Governance | `bdc_tool_risk_catalog` | READ | low |
| Governance | `bdc_policy_explain` | READ | low |
| Governance | `bdc_api_policy_check` | READ | low |
| Governance | `bdc_audit_tail` | READ | low |
| Providers | `bdc_connect_list_providers` | READ | low |
| Providers | `bdc_connect_diagnostics` | READ | low |
| Providers | `bdc_connect_preflight` | READ | low |
| Databricks | `bdc_databricks_preflight` | READ | medium |
| Databricks | `bdc_databricks_validate_share_readiness` | READ | medium |
| Databricks | `bdc_databricks_generate_csn_from_share` | READ | low |
| Snowflake | `bdc_snowflake_preflight` | READ | low |
| Snowflake | `bdc_snowflake_explain_flow` | READ | low |
| Sharing | **`bdc_share_execute_plan`** | **WRITE** | **high** |

`bdc_share_execute_plan` is the only mutating tool. It enforces the full gate chain: WRITE-enable → API policy evidence → plan validation → provider preflight → `validate_plan` → capability check → prior-dry-run correlation → constant-time approval-token compare → provider call. Audit event written on every outcome (block, dry-run, real, error).

## Safe defaults (same spirit, more teeth)

| Setting | Default | What it does |
|---|---|---|
| `BDC_ENABLE_WRITE_TOOLS` | `0` | Every WRITE tool refused until you opt in |
| `BDC_ENABLE_ADMIN_TOOLS` | `0` | Every ADMIN tool refused until you opt in |
| `BDC_REQUIRE_DRY_RUN` | `1` | High-risk tools must dry-run first |
| `BDC_REQUIRE_APPROVAL_TOKEN` | `1` | Real execute requires a matching `BDC_APPROVAL_TOKEN` |
| `BDC_API_POLICY_STRICT` | `1` | WRITE/ADMIN tools with `api_surface=UNKNOWN` are refused — gates subprocess plugin proxies by default |
| `BDC_AUDIT_ENABLED` | `1` | Every tool call writes a JSONL audit event |

These are explicit defaults — not implicit. Read [`INSTALLATION.md §4`](INSTALLATION.md#4-environment-variables--full-reference) for the complete env-var reference.

## Compatibility

v0.1 → v0.2 is **backward compatible**:

- All 12 v0.1 tools are still registered with identical signatures and return shapes.
- All v0.1 environment variables retain their meaning.
- All v0.1 `BDC_PLUGINS=module.path` entries continue to work unchanged.

Upgrading is `pip install --upgrade sap-bdc-mcp` (or bumping your npx version pin) plus a client restart. See [`INSTALLATION.md §7`](INSTALLATION.md#7-upgrading-from-v010) for the full upgrade walkthrough.

## What's *not* in v0.2 (intentionally)

- **Live share execution (Databricks *and* Snowflake).** v0.2 ships the full governance + gate chain against **mock** execution; real provider mutation (Databricks SDK wiring, Snowflake) lands in v0.3.
- **HTTP / SSE transport.** stdio only at v0.2; HTTP lands in v0.4.
- **JWT / time-bound approval tokens.** Plain shared-secret + constant-time compare at v0.2; JWT in v0.4.
- **Audit log rotation.** Manual at v0.2; controls in v0.4.
- **SIEM forwarding, central policy, RBAC, dashboards.** Premium / post-v1.
- **Hybrid worker live REST contract.** Skeleton ships at v0.2; wired in v0.3.

These are *deliberate* deferrals — the design notes for each live in our internal release workspace.

## Two install routes

```bash
# Python route
pip install sap-bdc-mcp==0.2.0

# Node / npx route (bootstraps Python via uv)
npx -y sap-bdc-mcp@0.2.0
```

Pick one. They run the same Python server underneath. See [`INSTALLATION.md`](INSTALLATION.md) for client configuration.

## License + commercial use

`sap-bdc-mcp` v0.2.0 is licensed under the **Business Source License 1.1 (BSL 1.1)** — the same license as its sibling read-only server [SAPDatasphereMCP](https://github.com/rahulsethi/SAPDatasphereMCP). It is **not** a permissive open-source license today, but it **converts automatically to Apache 2.0 on 2029-01-01**. Personal, evaluation, research, academic, and internal-evaluation use is free under the [`LICENSE`](../LICENSE) at the repo root; commercial / for-profit use requires a separate agreement — see [`COMMERCIAL_LICENSING.md`](COMMERCIAL_LICENSING.md) (a 2-for-1 discount covers both family servers). *(v0.1.0 remains MIT for code already in use.)*

## SAP API policy

Every v0.2 tool cites the documented SAP API, SDK, or manual flow it relies on via the `api_evidence` field on its metadata. The `bdc_api_policy_check` tool lets you self-audit this at any time. Read [`SAP_API_POLICY.md`](SAP_API_POLICY.md) for the full policy posture.

## Verifying the install

After install + client restart, ask your agent to call `bdc_diagnostics`. You should see something like:

```json
{
  "mode": "local",
  "mock_mode": true,
  "write_enabled": false,
  "admin_enabled": false,
  "audit_enabled": true,
  "audit_log_path": ".sap_bdc_mcp/audit.jsonl",
  "api_policy_strict": true,
  "tool_count": 25,
  "plugins": [...]
}
```

`tool_count: 25` indicates all v0.1 + v0.2 tools are registered.

## Reporting bugs

GitHub issues: <https://github.com/rahulsethi/SAPBDCMCP/issues>.

When reporting:
- Include `bdc_diagnostics` output (it's auto-redacted).
- Include the failing `bdc_audit_tail` event(s) (also redacted).
- Do **not** paste raw `BDC_APPROVAL_TOKEN`, share URLs, or Databricks tokens. The audit log shape strips these — please mirror that discipline in issue reports.

---

Thanks for using `sap-bdc-mcp`.
