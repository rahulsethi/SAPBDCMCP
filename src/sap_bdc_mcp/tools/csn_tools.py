"""CSN tools for validation, diffing, and documentation.

File: src/sap_bdc_mcp/tools/csn_tools.py
Version: v3
"""

from __future__ import annotations

from typing import Any, Dict

from ..connectors.csn_client import csn_diff, csn_render_docs, csn_validate
from ._gated import ToolContext, gated
from .metadata import v01_metadata_list


_META = {m.name: m for m in v01_metadata_list()}


def register(server: Any, ctx: ToolContext) -> None:
    @gated(server, ctx, meta=_META["bdc_csn_validate"])
    def bdc_csn_validate(csn: Dict) -> Dict:
        """Validate a CSN (Interop-focused) and return diagnostics."""
        return csn_validate(csn)

    @gated(server, ctx, meta=_META["bdc_csn_diff"])
    def bdc_csn_diff(old_csn: Dict, new_csn: Dict) -> Dict:
        """Diff two CSNs and highlight breaking vs non-breaking changes."""
        return csn_diff(old_csn, new_csn)

    @gated(server, ctx, meta=_META["bdc_csn_render_docs"])
    def bdc_csn_render_docs(csn: Dict) -> Dict:
        """Render CSN into Markdown documentation."""
        md = csn_render_docs(csn)
        return {"markdown": md}
