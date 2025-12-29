"""Tool registration.

File: src/sap_bdc_mcp/tools/registry.py
Version: v1
"""

from __future__ import annotations

from typing import Any, List

from ..config import BDCConfig
from ..plugin_loader import PluginLoadResult
from . import core, ord_tools, csn_tools, share_tools


def register_all_tools(server: Any, config: BDCConfig, plugin_status: List[PluginLoadResult]) -> None:
    # Core + diagnostics first
    core.register(server, config, plugin_status)
    # Contract/discovery tools
    ord_tools.register(server, config)
    csn_tools.register(server, config)
    share_tools.register(server, config)
