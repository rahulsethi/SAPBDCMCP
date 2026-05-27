# sap-bdc-mcp (npx wrapper)

A thin Node bootstrapper for [`sap-bdc-mcp`](https://pypi.org/project/sap-bdc-mcp/), a
Model Context Protocol (MCP) server for SAP Business Data Cloud (BDC).

**This package contains no MCP logic.** It is a ~50-line Node script that
detects [`uvx`](https://docs.astral.sh/uv/) on your `PATH` and delegates to the
Python package, ensuring you always run the matching, isolated Python runtime.

## What it does

When invoked, the wrapper:

1. Checks for `uvx` on your `PATH`.
2. If missing, prints install hints for `uv` and exits with code `2`.
3. If present, runs `uvx --python 3.11 sap-bdc-mcp@0.2.0 <your args>` with
   stdio inherited and forwards the exit code.

The npm version is pinned in lockstep with the PyPI version. npm `0.2.0`
always points at PyPI `0.2.0`.

## Install / run

You typically do not install this package — `npx` runs it directly:

```bash
npx -y sap-bdc-mcp
```

Prerequisite: install `uv` once. Any of:

```bash
pipx install uv
brew install uv                                   # macOS
scoop install uv                                  # Windows
curl -LsSf https://astral.sh/uv/install.sh | sh   # Linux / macOS
irm https://astral.sh/uv/install.ps1 | iex        # Windows PowerShell
```

## MCP client configuration

For Claude Desktop, Cursor, or any MCP client that supports stdio servers:

```json
{
  "mcpServers": {
    "sap-bdc": {
      "command": "npx",
      "args": ["-y", "sap-bdc-mcp"]
    }
  }
}
```

Environment variables are forwarded to the Python server unchanged. See the
full end-user documentation for the supported variables, gating model, and
audit log:

- **End-user instructions:** [docs/release/v0.2.0/08_EndUserInstructions.md](https://github.com/rahulsethi/sap-bdc-mcp/blob/main/docs/release/v0.2.0/08_EndUserInstructions.md)
- **Architecture:** [docs/release/v0.2.0/01_Architecture.md](https://github.com/rahulsethi/sap-bdc-mcp/blob/main/docs/release/v0.2.0/01_Architecture.md)
- **Decision record (this wrapper):** [docs/release/v0.2.0/03_Decisions/D-002-npx-distribution-wrapper.md](https://github.com/rahulsethi/sap-bdc-mcp/blob/main/docs/release/v0.2.0/03_Decisions/D-002-npx-distribution-wrapper.md)

## Alternatives

If you already have Python tooling, you can skip this wrapper:

```bash
pip install sap-bdc-mcp
sap-bdc-mcp
# or, isolated:
uvx --python 3.11 sap-bdc-mcp
```

The wrapper exists solely to make the Node-first MCP install path
(`npx -y ...`) work without asking users to install Python themselves.

## Requirements

- Node.js 18 or newer.
- `uvx` (from `uv`) on `PATH`. `uv` handles fetching an isolated Python 3.11.

## License

MIT — see [LICENSE](./LICENSE).
