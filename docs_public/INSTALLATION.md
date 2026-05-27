# sap-bdc-mcp — Installation & Configuration

This guide covers installing `sap-bdc-mcp`, wiring it into your MCP client (Claude Desktop, Cursor, LibreChat, custom), configuring environment variables, and troubleshooting.

> Licensing note: `sap-bdc-mcp` is **not** under a permissive open-source license. See [`LICENSE`](../LICENSE) and [`COMMERCIAL_LICENSING.md`](COMMERCIAL_LICENSING.md) for permitted use.

---

## 1. Prerequisites

- Operating system: Windows 10+ / macOS 12+ / any modern Linux.
- One of these toolchains on PATH:
  - **Python** 3.11, 3.12, or 3.13 (for the PyPI install route), **or**
  - **Node** 18+ **and** [`uv`](https://docs.astral.sh/uv/) (for the `npx` route — `uv` provides the `uvx` Python bootstrapper used by the wrapper).

You only need one route. Pick whichever fits your environment.

---

## 2. Install

### 2.1 PyPI route (recommended for production)

```bash
pip install sap-bdc-mcp==0.2.0
sap-bdc-mcp --help
```

Or with `uv` (faster + isolated, no global Python pollution):

```bash
uvx --python 3.11 sap-bdc-mcp@0.2.0 --help
```

### 2.2 npx route (no Python toolchain required to manage)

```bash
npx -y sap-bdc-mcp@0.2.0 --help
```

The wrapper is a ~60-line Node script. On first run it:

1. Checks for `uvx` on your PATH.
2. If missing, prints a one-screen install hint and exits with code 2.
3. If present, exec's `uvx --python 3.11 sap-bdc-mcp@0.2.0 <your args>` with stdio inherited.

The server you run is the same Python package as in 2.1. The wrapper has no MCP logic — it bootstraps Python via `uv` so Node-first environments can still launch it.

If `uvx` is missing, install `uv` with one of:

```bash
pipx install uv                                   # cross-platform
brew install uv                                   # macOS
scoop install uv                                  # Windows
curl -LsSf https://astral.sh/uv/install.sh | sh   # Linux / macOS
irm https://astral.sh/uv/install.ps1 | iex        # Windows PowerShell
```

### 2.3 Source install (for contributors / forks)

```bash
git clone https://github.com/rahulsethi/SAPBDCMCP.git
cd SAPBDCMCP
python -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .\.venv\Scripts\Activate.ps1     # Windows PowerShell
pip install -e ".[dev]"
sap-bdc-mcp --help
```

---

## 3. Wire it into your MCP client

### 3.1 Claude Desktop

File:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

PyPI install:

```json
{
  "mcpServers": {
    "sap-bdc-mcp": {
      "command": "sap-bdc-mcp",
      "args": [],
      "env": {
        "BDC_MODE": "local",
        "BDC_MOCK_MODE": "1"
      }
    }
  }
}
```

npx install:

```json
{
  "mcpServers": {
    "sap-bdc-mcp": {
      "command": "npx",
      "args": ["-y", "sap-bdc-mcp@0.2.0"],
      "env": {
        "BDC_MODE": "local",
        "BDC_MOCK_MODE": "1"
      }
    }
  }
}
```

Restart Claude Desktop after editing.

### 3.2 Cursor

In your workspace's `.cursor/mcp.json`:

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

### 3.3 LibreChat

In `librechat.yaml`:

```yaml
mcpServers:
  sap-bdc-mcp:
    type: stdio
    command: sap-bdc-mcp
    env:
      BDC_MODE: local
      BDC_MOCK_MODE: "1"
```

### 3.4 Custom Python client

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

params = StdioServerParameters(
    command="sap-bdc-mcp",
    env={"BDC_MODE": "local", "BDC_MOCK_MODE": "1"},
)
async with stdio_client(params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        # ...
```

---

## 4. Environment variables — full reference

### 4.1 Carried over from v0.1

```
BDC_MODE=local                # label only: local | dev | prod
BDC_MOCK_MODE=0               # 1 = use fixtures, never call out
BDC_VERIFY_TLS=1
BDC_MAX_DOC_KB=512            # max fetched ORD document size
BDC_ORD_SOURCES=              # comma-separated URLs / file paths
BDC_PLUGINS=                  # see §5 below
BDC_ENABLE_WRITE_TOOLS=0      # default OFF — required for any WRITE tool
BDC_TENANT_ID=                # label only; redacted in output
BDC_REGION=                   # label only; redacted in output
BDC_BASE_URL=                 # label only; redacted in output
BDC_USER=                     # label only; redacted in output
BDC_SERVICE_ACCOUNT=          # label only; redacted in output
```

### 4.2 New in v0.2

```
BDC_ENABLE_ADMIN_TOOLS=0      # default OFF — required for any ADMIN tool
BDC_REQUIRE_DRY_RUN=1         # high-risk tools must dry-run first
BDC_REQUIRE_APPROVAL_TOKEN=1  # high-risk tools require a matching approval token
BDC_APPROVAL_TOKEN=           # opaque secret; required when real execution is desired
BDC_AUDIT_ENABLED=1           # write JSONL audit events on every gated tool call
BDC_AUDIT_LOG_PATH=.sap_bdc_mcp/audit.jsonl
BDC_API_POLICY_STRICT=1       # if 1, WRITE/ADMIN tools with UNKNOWN api_surface are refused
BDC_MAX_RESULT_ITEMS=50       # caps audit_tail and similar list-returning tools
BDC_PLUGIN_ENV_PASSTHROUGH=   # comma-list of env var names to forward to subprocess plugins
BDC_PLUGIN_TRUST=             # alias1:surface,alias2:surface — operator-asserted plugin trust
BDC_DATABRICKS_HOST=
BDC_DATABRICKS_TOKEN=
BDC_DATABRICKS_RECIPIENT=
BDC_DATABRICKS_WAREHOUSE=
BDC_SNOWFLAKE_ACCOUNT=
BDC_SNOWFLAKE_ROLE=
BDC_SNOWFLAKE_WAREHOUSE=
```

All `*_TOKEN`, `*_HOST` (when it contains credentials), JWT-shaped strings, signed share URLs, and the `approval_token` itself are **automatically redacted** in every tool output and audit-log line.

---

## 5. Plugin entries — `BDC_PLUGINS`

v0.2 accepts four entry forms, comma-separated:

| Form | Behavior |
|---|---|
| `module.path` | Python plugin imported in-process (v0.1 contract — unchanged) |
| `python:module.path` | Same as above, explicit |
| `[alias=]npx:<npm-spec>[ -- arg1 arg2]` | Spawn `npx -y <npm-spec> args...` and proxy its tools |
| `[alias=]uvx:<pypi-spec>[ -- arg1 arg2]` | Spawn `uvx <pypi-spec> args...` |
| `[alias=]cmd:<absolute-path>[ -- arg1 arg2]` | Spawn an arbitrary binary |

Example:

```
BDC_PLUGINS="sap_bdc_mcp.plugins.internal,gh=npx:@modelcontextprotocol/server-github@latest,sentry=uvx:mcp-server-sentry"
BDC_PLUGIN_TRUST="gh:documented_sdk"
BDC_PLUGIN_ENV_PASSTHROUGH="GITHUB_TOKEN"
```

Tools from subprocess plugins appear as `plug_<alias>__<tool>` in your MCP client. They are **distrusted by default** (treated as `WRITE / UNKNOWN-surface`) until you list them in `BDC_PLUGIN_TRUST`. Every cross-process call is audited.

---

## 6. Enabling real execution (use with care)

By default `sap-bdc-mcp` is as safe as v0.1 — every mutating tool is blocked. To execute real share operations against Databricks:

1. Provide credentials:
   ```
   BDC_DATABRICKS_HOST=...
   BDC_DATABRICKS_TOKEN=...
   BDC_DATABRICKS_RECIPIENT=...
   ```
2. Enable write tools:
   ```
   BDC_ENABLE_WRITE_TOOLS=1
   ```
3. Set an approval token (any opaque secret you control):
   ```
   BDC_APPROVAL_TOKEN=<random-uuid-or-passphrase>
   ```
4. In your agent:
   - Build a share plan with `bdc_share_plan`.
   - Validate with `bdc_share_validate_contract`.
   - Dry-run with `bdc_share_execute_plan(plan, provider="databricks", dry_run=True)` — review the preview.
   - Re-call with `dry_run=False, approval_token="<value>"`.
5. Inspect what happened: `bdc_audit_tail(limit=10)`.

If anything in the chain fails (wrong token, missing dry-run, unrecognized provider, unmet API policy), the tool returns a `{"ok": false, "blocked_reason": "..."}` dict — the server never crashes.

---

## 7. Upgrading from v0.1.0

No breaking changes to existing tools. Steps:

1. `pip install --upgrade sap-bdc-mcp` (or bump your npx version pin to `@0.2.0`).
2. Restart your MCP client.
3. In your agent, ask for `bdc_diagnostics` — the result now includes `audit_enabled`, `providers`, plugin status, and version `0.2.0`.
4. (Optional) Set `BDC_AUDIT_LOG_PATH` to a directory you control. Default is `./.sap_bdc_mcp/audit.jsonl` relative to the working directory at startup.

Existing `BDC_PLUGINS=module.path` entries continue to work unchanged.

---

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `sap-bdc-mcp: command not found` after `pip install` | venv not activated, or PATH not refreshed | Activate venv or re-open shell |
| `npx ... uvx not found` | `uv` is not installed on the host | Install per <https://docs.astral.sh/uv/> |
| `bdc_share_execute_plan` returns `blocked_reason: "BDC_ENABLE_WRITE_TOOLS=0"` | Safe default | Set the env var (only if you mean it) |
| `bdc_share_execute_plan` returns `blocked_reason: "dry-run required"` | First call must be `dry_run=True` | Run dry-run first; the result returns a `correlation_id` you can pass back |
| `bdc_share_execute_plan` returns `blocked_reason: "approval token invalid"` | Token mismatch | Confirm `BDC_APPROVAL_TOKEN` and the `approval_token` argument match exactly |
| Plugin from npx not appearing | Wrong package name, npm not installed, or child failed to initialize | Check `bdc_diagnostics` — failed plugins are listed with their error |
| Audit log not written | `BDC_AUDIT_ENABLED=0` or unwritable path | Set `BDC_AUDIT_ENABLED=1` and a writable `BDC_AUDIT_LOG_PATH` |
| Secret leaks into output | bug — report immediately | All secrets are supposed to be redacted; file an issue with a redacted repro |

---

## 9. Where to go next

- [`RELEASE_NOTES_v0.2.0.md`](RELEASE_NOTES_v0.2.0.md) — plain-language overview of what v0.2.0 added.
- [`SAP_API_POLICY.md`](SAP_API_POLICY.md) — how this server respects SAP's API policy and how you can self-audit.
- [`COMMERCIAL_LICENSING.md`](COMMERCIAL_LICENSING.md) — licensing terms for enterprise / commercial use.
- Root [`CHANGELOG.md`](../CHANGELOG.md) — full version history.
- Issues: <https://github.com/rahulsethi/SAPBDCMCP/issues>.
