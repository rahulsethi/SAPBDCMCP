# Changelog

All notable changes to `sap-bdc-mcp` are documented here.
Format adapted from [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [SemVer](https://semver.org/) — `0.x` is pre-1.0 and may still introduce contract changes between minors.

---

## [0.2.0] — 2026-05-27 — *Governed BDC Connect*

The first **execution-capable** release. v0.2.0 turns sap-bdc-mcp from a contract-first discovery server into a governed-execution server, with Databricks as the first production provider and Snowflake as a readiness-only adapter.

### Added

- **Tool risk metadata** (`tools/metadata.py`) — every MCP tool carries `mutability`, `risk`, `api_surface`, `api_evidence`, `bulk_data_behavior`. Backfilled for all 12 v0.1 tools; required for every new tool.
- **API policy evidence gate** (`policy_evidence.py`) — WRITE/ADMIN tools with `api_surface = UNKNOWN` are refused under `BDC_API_POLICY_STRICT=1` (default on).
- **JSONL audit log** (`audit.py`) — every gated tool invocation writes an event with sha256-hashed inputs (post-redaction). Tail via `bdc_audit_tail`. Path configurable via `BDC_AUDIT_LOG_PATH`.
- **Gated tool wrapper** (`tools/_gated.py`) — single decorator that runs policy gates, captures inputs, calls the tool, writes audit, redacts output.
- **Provider-neutral adapter layer** (`providers/`):
  - `BDCConnectProvider` ABC with `preflight`, `validate_plan`, `dry_run_execute`, `execute`.
  - `DatabricksProvider` — mock + real modes; real-mode execution raises `NotImplementedError` pointing to v0.3 wiring of the BDC Connect SDK.
  - `SnowflakeProvider` — readiness-only; `dry_run_execute` / `execute` raise `ProviderCapabilityError` (Snowflake mutation deferred to v0.3).
- **Subprocess plugin upstream support** (`plugin_loader.py`) — `BDC_PLUGINS` now accepts `npx:`, `uvx:`, `cmd:` schemes in addition to the v0.1 Python `module.path`. Child MCP server tools are proxied as `plug_<alias>__<tool>`, treated as `WRITE / UNKNOWN-surface` by default, and gated through the same audit + policy chain as first-party tools. Operator promotes trust via `BDC_PLUGIN_TRUST=<alias>:<surface>`. Child env is minimal-by-default; pass extras via `BDC_PLUGIN_ENV_PASSTHROUGH`.
- **Governance tools** (4):
  - `bdc_tool_risk_catalog` — every tool's risk metadata.
  - `bdc_policy_explain` — which gates apply to a tool and current pass/fail status.
  - `bdc_api_policy_check` — per-tool SAP API evidence summary; flags UNKNOWN-surface mutators.
  - `bdc_audit_tail` — recent audit events, capped, redacted.
- **Provider introspection tools** (3):
  - `bdc_connect_list_providers`
  - `bdc_connect_diagnostics`
  - `bdc_connect_preflight`
- **Databricks tools** (3):
  - `bdc_databricks_preflight`
  - `bdc_databricks_validate_share_readiness`
  - `bdc_databricks_generate_csn_from_share` — primitive Delta columns only; complex types refused with a disclaimer.
- **Snowflake tools** (2):
  - `bdc_snowflake_preflight`
  - `bdc_snowflake_explain_flow`
- **Controlled execution tool** (1):
  - `bdc_share_execute_plan(plan, provider, dry_run=True, approval_token=None, correlation_id=None)` — full gate chain: WRITE-enable → API policy evidence → plan validation → provider preflight → provider.validate_plan → capability check → prior-dry-run correlation → constant-time approval-token compare → provider call. Audit event written on every outcome (block / dry-run / real / error).
- **Approval token mechanism** (`policy.approval_token_valid`) — plain shared secret + `hmac.compare_digest`. JWT path deferred to v0.4.
- **npx distribution wrapper** (`npx-wrapper/`) — Node package that bootstraps the Python server via `uvx`. Run via `npx -y sap-bdc-mcp@0.2.0`. The wrapper has no MCP logic; it pins the Python version and forwards stdio.
- **Redaction patterns** (new in `redaction.py`): signed Delta-share URLs (`token=`, `signature=`, `sig=` query params), JWT-shaped strings, `approval_token` dict key.
- **CI** — added `mypy` step + `npx-smoke` job (Node 20 on Ubuntu + Windows) that boots the wrapper.

### Changed

- `BDCConfig` extended with `enable_admin_tools`, `require_dry_run`, `require_approval_token`, `approval_token`, `audit_enabled`, `audit_log_path`, `api_policy_strict`, `max_result_items`, `plugin_env_passthrough`, `plugin_trust`, `databricks` (sub-config), `snowflake` (sub-config). All new env vars have safe defaults.
- `ToolPolicy.is_allowed()` extended with optional `enable_admin_tools`, `dry_run`, `prior_dry_run_correlation`, `approval_token_valid` parameters (backward-compatible — old single-arg call sites still work).
- `plugin_loader.load_plugins()` signature changed from `(server, config)` to `(server, ctx)` to allow proxy tools to register through the same audit + metadata path as first-party tools.
- `register_all_tools()` signature changed from `(server, config, plugin_status)` to `(server, ctx)`.
- All 12 v0.1 tools are now registered through the `gated()` wrapper — they still behave identically but produce audit events.
- `pyproject.toml` adds `types-jsonschema` and `pytest-asyncio` as dev dependencies; adds `asyncio_mode = "auto"` to `[tool.pytest.ini_options]`.

### Fixed

- Pre-existing ruff `F401` / `F841` warnings in `tests/test_share_tools.py` and `src/sap_bdc_mcp/plugin_loader.py` cleaned up.
- mypy now passes cleanly across all 35 source files (`types-jsonschema` stubs added).

### Deferred (not in v0.2.0)

- Snowflake share execution → v0.3.
- HTTP / SSE transport → v0.4.
- JWT / time-bound approval tokens → v0.4.
- Audit log rotation / retention → v0.4.
- SIEM forwarding, central policy, RBAC, dashboards → premium / post-v1.
- Hybrid worker live REST contract → wired in v0.3 (skeleton ships at v0.2).
- Live `npm publish` + GitHub release automation → manual.

### Migration notes

- **Existing v0.1 tools are unchanged** in behavior, signature, and return shape.
- **Existing env vars retain their meaning.** New env vars default to safe values: writes off, dry-run required, audit enabled, strict API policy.
- **Existing Python plugins keep working** — bare module paths in `BDC_PLUGINS` are treated as v0.1 import-based plugins. To opt in to subprocess plugins, prefix with `npx:`, `uvx:`, or `cmd:`.
- **First time invoking any tool** now creates `./.sap_bdc_mcp/audit.jsonl`. Set `BDC_AUDIT_LOG_PATH` to relocate, or `BDC_AUDIT_ENABLED=0` to disable.

---

## [0.1.0] — 2026-01

Initial public release. Contract-first, read-safe MCP server for SAP Business Data Cloud.

### Added
- 12 MCP tools: `bdc_ping`, `bdc_diagnostics`, `bdc_get_tenant_info`, `bdc_whoami`, `bdc_ord_fetch_documents`, `bdc_ord_search`, `bdc_ord_validate`, `bdc_csn_validate`, `bdc_csn_diff`, `bdc_csn_render_docs`, `bdc_share_plan`, `bdc_share_validate_contract`.
- Redaction helpers (bearer tokens, basic-auth URLs, sensitive key names).
- Plugin loader (Python module imports via `BDC_PLUGINS`).
- ORD + CSN JSON Schemas for validation.
- Mock mode (`BDC_MOCK_MODE=1`) with fixture-driven responses.
- pytest test suite covering all 12 tools + connectors.
