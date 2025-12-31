<!-- SAP Business Data Cloud MCP Server -->
<!-- File: ImplementationTracker_v0.1.md -->
<!-- Version: v1 -->

# Implementation Tracker – SAP Business Data Cloud MCP Server v0.1

Tracks implementation progress for **v0.1** only.

---

## Legend

- **Status:** ⏳ Planned | 🔨 In Progress | ✅ Done | ⏹ Deferred
- **Priority:** [P0] must-have | [P1] nice-to-have | [P2] stretch/v0.2+

---

## Release goals

- Open-core MCP server skeleton (stdio).
- Stable, testable **ORD + CSN contract tooling**.
- Safety primitives: policy gating, redaction, bounded outputs.
- Mock mode and first MCP test prompts.

---

### Phase A – Core server skeleton

| Task | Status | Notes |
|---|---:|---|
| Stdio entrypoint `sap-bdc-mcp` | ✅ Done | [P0] |
| `BDCConfig.from_env()` + validation | ✅ Done | [P0] |
| Redaction helpers | ✅ Done | [P0] |
| Policy gating (READ/WRITE/ADMIN) | ✅ Done | [P0] |
| Tool: `bdc_ping` | ✅ Done | [P0] |
| Tool: `bdc_diagnostics` | ✅ Done | [P1] |

---

### Phase B – ORD tools

| Task | Status | Notes |
|---|---:|---|
| ORD client interface + fixtures | ✅ Done | [P0] |
| `bdc_ord_fetch_documents` | ✅ Done | [P0] |
| `bdc_ord_search` | ✅ Done | [P0] |
| `bdc_ord_validate` | ✅ Done | [P0] |
| Tests for ORD tools | ✅ Done | [P0] |

---

### Phase C – CSN tools

| Task | Status | Notes |
|---|---:|---|
| CSN validation utilities + fixtures | ✅ Done | [P0] |
| `bdc_csn_validate` | ✅ Done | [P0] |
| `bdc_csn_diff` | ✅ Done | [P1] |
| `bdc_csn_render_docs` | ✅ Done | [P1] |
| Tests for CSN tools | ✅ Done | [P0] |

---

### Phase D – Share scaffolding

| Task | Status | Notes |
|---|---:|---|
| Share plan JSON schema | ✅ Done | [P0] |
| `bdc_share_plan` | ✅ Done | [P0] |
| `bdc_share_validate_contract` | ✅ Done | [P0] |
| Tests for share scaffolding | ✅ Done | [P0] |
