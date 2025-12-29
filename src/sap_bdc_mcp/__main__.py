"""CLI entrypoint.

File: src/sap_bdc_mcp/__main__.py
Version: v2
"""

from __future__ import annotations

from .server import build_server


def main() -> None:
    server = build_server()
    try:
        # FastMCP defaults to stdio when no transport is specified.
        server.run()
    except KeyboardInterrupt:
        # Quiet shutdown when run manually from a terminal.
        return


if __name__ == "__main__":
    main()

