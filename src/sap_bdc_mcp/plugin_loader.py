"""Plugin loader.

File: src/sap_bdc_mcp/plugin_loader.py
Version: v1
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any, Callable, List

from .config import BDCConfig


@dataclass(frozen=True)
class PluginLoadResult:
    name: str
    ok: bool
    error: str | None = None


def load_plugins(server: Any, config: BDCConfig) -> List[PluginLoadResult]:
    results: List[PluginLoadResult] = []
    for module_path in config.plugins:
        try:
            mod = importlib.import_module(module_path)
            register = getattr(mod, "register_tools", None)
            if not callable(register):
                results.append(
                    PluginLoadResult(
                        name=module_path,
                        ok=False,
                        error="No callable register_tools(server, config) found",
                    )
                )
                continue

            register(server, config)
            results.append(PluginLoadResult(name=module_path, ok=True))
        except Exception as e:  # noqa: BLE001
            results.append(PluginLoadResult(name=module_path, ok=False, error=str(e)))
    return results
