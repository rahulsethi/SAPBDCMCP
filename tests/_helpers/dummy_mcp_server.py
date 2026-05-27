"""Minimal stdio MCP server used by Phase 6 subprocess plugin tests.

File: tests/_helpers/dummy_mcp_server.py
Version: v1

Standalone: ``python tests/_helpers/dummy_mcp_server.py``.

Exposes a single tool ``dummy_echo(message: str) -> dict`` that returns the
input. This file deliberately depends only on ``mcp.server.fastmcp`` so the
subprocess plugin loader has a tiny, deterministic upstream to drive.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP


def build() -> FastMCP:
    server = FastMCP("dummy-mcp", instructions="Echo server for plugin loader tests.")

    @server.tool()
    def dummy_echo(message: str) -> dict:
        """Return the message verbatim, plus an ``ok`` flag."""
        return {"ok": True, "message": message}

    return server


def main() -> None:
    build().run()


if __name__ == "__main__":
    main()
