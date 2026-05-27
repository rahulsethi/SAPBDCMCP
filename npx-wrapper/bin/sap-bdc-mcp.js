#!/usr/bin/env node
// Version: v1
// Thin bootstrapper for sap-bdc-mcp. All MCP server logic lives in the
// Python package `sap-bdc-mcp` on PyPI. This script:
//   1. Verifies `uvx` is on PATH (from astral.sh/uv).
//   2. If missing, prints a one-screen install hint and exits 2.
//   3. If present, spawns `uvx --python 3.11 sap-bdc-mcp@<PIN> <user args>`
//      with stdio inherited, and forwards the child's exit code.
//
// See docs/release/v0.2.0/03_Decisions/D-002-npx-distribution-wrapper.md
// and docs/release/v0.2.0/02_Design.md §4 for the full rationale.

const { spawn, spawnSync } = require("node:child_process");

const PIN = "0.2.0";
const REQ_PY = "3.11";

function hasUvx() {
  const probe = process.platform === "win32" ? "where" : "which";
  const r = spawnSync(probe, ["uvx"], { stdio: "ignore" });
  return r.status === 0;
}

if (!hasUvx()) {
  process.stderr.write(
    [
      "",
      "sap-bdc-mcp requires 'uvx' (from astral.sh/uv) to bootstrap its Python runtime.",
      "",
      "Install uv with one of:",
      "  pipx install uv",
      "  brew install uv                                   # macOS",
      "  scoop install uv                                  # Windows",
      "  curl -LsSf https://astral.sh/uv/install.sh | sh   # Linux / macOS",
      "  irm https://astral.sh/uv/install.ps1 | iex        # Windows PowerShell",
      "",
      "Then re-run:",
      "  npx -y sap-bdc-mcp",
      "",
      "Docs: https://docs.astral.sh/uv/",
      "",
    ].join("\n"),
  );
  process.exit(2);
}

const args = ["--python", REQ_PY, `sap-bdc-mcp@${PIN}`, ...process.argv.slice(2)];
const child = spawn("uvx", args, { stdio: "inherit", env: process.env });

child.on("error", (err) => {
  process.stderr.write(`sap-bdc-mcp: failed to launch uvx: ${err.message}\n`);
  process.exit(1);
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.stderr.write(`sap-bdc-mcp: uvx terminated by signal ${signal}\n`);
    process.exit(1);
  }
  process.exit(code ?? 1);
});
