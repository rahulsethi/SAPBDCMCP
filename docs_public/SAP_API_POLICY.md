# SAP API Policy Compliance

**Audience:** SAP architects, security reviewers, enterprise IT, customers performing due diligence on third-party tooling that connects to SAP Business Data Cloud.
**Scope:** sap-bdc-mcp v0.2.0 and forward.

This document explains how `sap-bdc-mcp` is designed to align with SAP's published API usage policies, what it specifically does *not* do, and how an operator can self-audit compliance at any time.

> This document is the product's compliance posture as designed and shipped. It is **not** a legal interpretation of SAP's policies, and it is **not** a substitute for your own contractual review with SAP. When SAP's published policies change, this document is updated within one release cycle.

---

## 1. Design principle: "documented or refused"

The single load-bearing rule for every tool sap-bdc-mcp exposes is:

> A tool that mutates SAP state, or that returns SAP data, **must cite the documented SAP API, SDK, SQL function, or manual flow it relies on**. If no such citation exists, the tool is refused under strict mode (default on).

This is enforced at three layers:

1. **Authoring.** Each tool's metadata declares `api_surface ∈ {published_api, documented_sdk, documented_manual_flow, unknown}` and an `api_evidence` string identifying the source. A tool cannot ship without these fields.
2. **Runtime.** The `policy_evidence` module refuses any `WRITE` or `ADMIN` tool whose `api_surface` is `unknown` when `BDC_API_POLICY_STRICT=1` (default).
3. **Self-audit.** The `bdc_api_policy_check` tool exposes the full evidence catalog so operators can verify compliance themselves at any moment.

## 2. What we never do

These are hard rules baked into the architecture, not just defaults:

| Forbidden behavior | Why |
|---|---|
| Use of undocumented SAP APIs | Violates SAP's API policy and creates upgrade risk; agents cannot rely on what is not published. |
| Bulk extraction / replication of SAP data | Data movement at scale belongs to SAP-supported integration (BDC Connect, Datasphere replication, etc.), not an MCP tool. |
| SAP cockpit / UI scraping or automation | Brittle, off-policy, and creates an unauditable channel. |
| Returning entire data products as agent context | Even where API access exists, sap-bdc-mcp returns metadata and bounded samples — never the data set. |
| Storing customer data outside the operator's boundary | sap-bdc-mcp is stdio-only at v0.2; it does not phone home, does not maintain a server, and the audit log lives on the operator's filesystem. |

Each of these is also enforced by `bulk_data_behavior` metadata on every tool. v0.2 tools are exclusively `none` (no data return) or `metadata_only` (schemas + descriptors). `bounded_sample` is reserved in the enum but **no v0.2 first-party tool uses it**.

## 3. Per-tool evidence

Every tool registered by sap-bdc-mcp v0.2 carries the following metadata:

```python
ToolMetadata(
    name=...,
    category=...,
    mutability=READ | WRITE | ADMIN,
    risk=low | medium | high,
    api_surface=published_api | documented_sdk | documented_manual_flow | unknown,
    api_evidence="<short identifier>",
    api_evidence_url="<optional documentation URL>",
    bulk_data_behavior=none | metadata_only | bounded_sample | blocked,
    ...
)
```

For v0.2's tool surface:

| Tool | Mutability | API surface | Evidence identifier |
|---|---|---|---|
| `bdc_ping` | READ | published_api | `mcp.server.ping` |
| `bdc_diagnostics` | READ | published_api | `mcp.server.diagnostics` |
| `bdc_get_tenant_info` | READ | documented_manual_flow | `sap-bdc.tenant.info` |
| `bdc_whoami` | READ | documented_manual_flow | `sap-bdc.identity.whoami` |
| `bdc_ord_fetch_documents` | READ | published_api | `ord-spec.v1.documents` |
| `bdc_ord_search` | READ | published_api | `ord-spec.v1.search` |
| `bdc_ord_validate` | READ | published_api | `ord-spec.v1.validate` |
| `bdc_csn_validate` | READ | documented_manual_flow | `csn-spec.v2.validation` |
| `bdc_csn_diff` | READ | documented_manual_flow | `csn-spec.v2.diff` |
| `bdc_csn_render_docs` | READ | documented_manual_flow | `csn-spec.v2.render` |
| `bdc_share_plan` | READ | documented_sdk | `bdc-connect-sdk.share.plan_v1` |
| `bdc_share_validate_contract` | READ | documented_sdk | `bdc-connect-sdk.share.validate_v1` |
| `bdc_share_execute_plan` | **WRITE** | documented_sdk | `bdc-connect-sdk.share.execute_v1` |
| `bdc_tool_risk_catalog` | READ | published_api | `sap-bdc-mcp.governance.risk_catalog` |
| `bdc_policy_explain` | READ | published_api | `sap-bdc-mcp.governance.policy_explain` |
| `bdc_api_policy_check` | READ | published_api | `sap-bdc-mcp.governance.api_policy_check` |
| `bdc_audit_tail` | READ | published_api | `sap-bdc-mcp.governance.audit_tail` |
| `bdc_connect_list_providers` | READ | published_api | `sap-bdc-mcp.providers.list` |
| `bdc_connect_diagnostics` | READ | published_api | `sap-bdc-mcp.providers.diagnostics` |
| `bdc_connect_preflight` | READ | published_api | `sap-bdc-mcp.providers.preflight` |
| `bdc_databricks_preflight` | READ | documented_sdk | `bdc-connect-sdk.databricks.preflight` |
| `bdc_databricks_validate_share_readiness` | READ | documented_sdk | `bdc-connect-sdk.databricks.share_readiness` |
| `bdc_databricks_generate_csn_from_share` | READ | documented_sdk | `bdc-connect-sdk.databricks.generate_csn` |
| `bdc_snowflake_preflight` | READ | documented_manual_flow | `bdc-connect-sdk.snowflake.preflight` |
| `bdc_snowflake_explain_flow` | READ | documented_manual_flow | `bdc-connect-sdk.snowflake.explain_flow` |

You can pull this same table at runtime:

```text
agent: please call bdc_tool_risk_catalog
agent: please call bdc_api_policy_check
```

Both tools return the live evidence list. They are themselves classified `READ / published_api / sap-bdc-mcp.governance.*`.

## 4. The strict-mode gate

`BDC_API_POLICY_STRICT=1` (default) gives the policy real teeth: any `WRITE` or `ADMIN` tool with `api_surface=unknown` is refused at runtime *before* the tool body executes. The audit event for the blocked call records `allowed=false, blocked_reason="...api_surface=UNKNOWN..."`.

This is the primary defense against three real risks:

1. **Drift.** A future PR adds a mutating tool but forgets to populate its evidence. Strict mode catches this at first call.
2. **Subprocess plugins.** Any tool exposed by an `npx:`/`uvx:`/`cmd:` upstream MCP server is treated as `api_surface=unknown` by default. Operators promote trust per plugin alias via `BDC_PLUGIN_TRUST=<alias>:<surface>` — explicitly opting in for that specific plugin.
3. **Mistaken upgrades.** A library version bump can change a tool's behavior. The metadata + audit log give you a verifiable trail.

You can disable strict mode (`BDC_API_POLICY_STRICT=0`) — for development, evaluation, or a deliberate emergency override. The default is on, and we recommend keeping it on in production.

## 5. Mutation only via documented SDK

The single mutating tool at v0.2 is `bdc_share_execute_plan`, which is `documented_sdk` (the SAP BDC Connect SDK on PyPI). The execution path:

1. Plan is built and validated through `bdc_share_plan` / `bdc_share_validate_contract` — pure local validation, no SAP calls.
2. The provider (Databricks at v0.2) implements the `BDCConnectProvider` interface: `preflight`, `validate_plan`, `dry_run_execute`, `execute`.
3. The operator must:
   - Enable writes: `BDC_ENABLE_WRITE_TOOLS=1`.
   - Set an approval token: `BDC_APPROVAL_TOKEN=<secret>`.
   - Call `dry_run=True` first to get a `correlation_id`.
   - Then call `dry_run=False, approval_token=<secret>, correlation_id=<from-dry-run>`.
4. The provider then issues the documented SDK call — and only the documented SDK call.
5. The audit log records the call with `provider, mutability, risk, dry_run, allowed, result_status, input_hash, correlation_id`.

At every step, the tool wrapper has the right to refuse. Refusal is the safe default; success requires every gate to pass.

## 6. Audit trail

Every gated tool invocation writes a JSONL event (path: `BDC_AUDIT_LOG_PATH`, default `./.sap_bdc_mcp/audit.jsonl`). The schema (frozen at `event_version: v1`):

```json
{
  "timestamp": "2026-05-27T18:00:00.000+00:00",
  "event_version": "v1",
  "tool_name": "bdc_share_execute_plan",
  "mutability": "WRITE",
  "risk": "high",
  "provider": "databricks",
  "plugin": null,
  "upstream_tool": null,
  "dry_run": true,
  "allowed": true,
  "blocked_reason": null,
  "input_hash": "sha256:<64-hex>",
  "redaction_applied": true,
  "result_status": "ok",
  "correlation_id": "<uuid4>"
}
```

`input_hash` is a sha256 of the *redacted* canonical JSON of the inputs — so secrets cannot be reconstructed from the log even if the redaction layer regresses on a future change.

The audit log is local. v0.2 does not forward audit events anywhere; that's a planned v0.3+ premium feature (SIEM forwarding). The log is yours, lives on your filesystem, and is sized for low-volume tool calls (~500 bytes per event).

You can review the tail at any time via `bdc_audit_tail(limit=50)`.

## 7. Subprocess plugin trust model

`sap-bdc-mcp` v0.2 can act as a fan-out point — registering `npx:`, `uvx:`, and `cmd:` MCP servers as upstream plugins. **Their tools are not implicitly trusted with SAP-policy compliance**:

- A child tool's synthesized metadata defaults to `WRITE / medium / api_surface=unknown / bulk_data_behavior=blocked`.
- Strict mode refuses every `WRITE` call to it.
- Trust is operator-asserted via `BDC_PLUGIN_TRUST=<alias>:<surface>`. The operator takes responsibility for the citation. sap-bdc-mcp does not verify it.
- Every child tool call is audited with `plugin=<alias>` and `upstream_tool=<name>`, so you can see exactly which subprocess saw which input.
- Child env is minimal-by-default. Only env vars listed in `BDC_PLUGIN_ENV_PASSTHROUGH` are forwarded. Parent secrets are NOT leaked.

If a child plugin makes undocumented SAP calls, that's the plugin's choice — and sap-bdc-mcp's strict mode will refuse it unless the operator has explicitly trusted it. The audit trail is the operator's defense.

## 8. Verifying compliance — operator checklist

Before deploying sap-bdc-mcp into a regulated environment:

- [ ] Confirm `BDC_API_POLICY_STRICT=1` is set (it's the default; verify in `bdc_diagnostics`).
- [ ] Confirm `BDC_ENABLE_WRITE_TOOLS=0` unless real execution is needed (and if it is, the team owning the SAP integration approves).
- [ ] Confirm `BDC_AUDIT_ENABLED=1` and `BDC_AUDIT_LOG_PATH` points at a path your retention pipeline can ingest.
- [ ] Run `bdc_api_policy_check` and confirm zero tools report `would_block_under_strict=true` (other than tools that are *supposed* to be blocked — synthetic plugin proxies in untrusted state).
- [ ] Run `bdc_tool_risk_catalog` and review the full surface. Tools you do not need can be disabled by omitting their plugin module from `BDC_PLUGINS` (for plugin-loaded tools) or by removing the relevant install (for first-party).
- [ ] Verify the redaction layer with a smoke test: invoke a tool with a fake bearer token in the input, then `bdc_audit_tail(limit=1)` and confirm the token is `***` in the redacted payload.
- [ ] Review the `LICENSE` and `docs_public/COMMERCIAL_LICENSING.md` — make sure your use is permitted.

## 9. When SAP's API policy changes

When SAP publishes an API policy change (typically via the SAP Architecture Center or BDC Connect SDK release notes):

1. We assess impact within one release cycle.
2. Affected tools' metadata is updated (`api_evidence`, `api_evidence_url`, and `api_surface` if it shifts).
3. Tools that no longer have a documented surface are marked `api_surface=unknown` — strict mode will refuse them, *with* a clear `blocked_reason` pointing operators at the policy change.
4. The next release's CHANGELOG calls out the change.

You can subscribe to the GitHub Releases feed on the repo to be notified.

## 10. Reporting a policy concern

If you believe a tool in sap-bdc-mcp is making an undocumented SAP call or otherwise violating SAP's API policy, please open a GitHub issue with:

- The tool name.
- The `api_evidence` value (visible via `bdc_tool_risk_catalog`).
- The SAP documentation reference you believe is being violated.
- (Optional but helpful) An `audit.jsonl` excerpt showing the problematic call.

We treat these reports as high-priority. The next release will either correct the metadata, remove the tool, or document the resolution.

---

**Last reviewed against SAP policy:** 2026-05-27 (v0.2.0 release).
