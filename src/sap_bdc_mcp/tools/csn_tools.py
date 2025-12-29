"""CSN tools (scaffold).

File: src/sap_bdc_mcp/tools/csn_tools.py
Version: v1
"""

from __future__ import annotations

from typing import Any, Dict

from ..config import BDCConfig
from ..connectors.csn_client import csn_diff, csn_render_docs, csn_validate


def register(server: Any, config: BDCConfig) -> None:
    @server.tool()
    def bdc_csn_validate(csn: Dict) -> Dict:
        """Validate a CSN (Interop-focused) and return diagnostics."""
        return csn_validate(csn)

    @server.tool()
    def bdc_csn_diff(old_csn: Dict, new_csn: Dict) -> Dict:
        """Diff two CSNs and highlight breaking vs non-breaking changes.

        v0.1 scaffold: minimal diff (keys + entity changes).
        """
        return csn_diff(old_csn, new_csn)

    @server.tool()
    def bdc_csn_render_docs(csn: Dict) -> Dict:
        """Render CSN into Markdown documentation."""
        md = csn_render_docs(csn)
        return {"markdown": md}
