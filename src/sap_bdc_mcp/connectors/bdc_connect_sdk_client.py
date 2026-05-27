"""Thin wrapper around the SAP BDC Connect SDK (lazy import).

File: src/sap_bdc_mcp/connectors/bdc_connect_sdk_client.py
Version: v1

At v0.2 this module is the only place the rest of the codebase reaches for
the external ``sap-bdc-connect-sdk`` package. The import is lazy: the server
boots even when the SDK is not installed; tools running in mock mode never
attempt the import. Real-mode tools call :func:`client` which raises a clear
error if the SDK is missing.

Phase 3 covers mock paths only; the real implementation is wired in v0.3
once the SDK contract stabilises.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any, Optional


logger = logging.getLogger(__name__)


_SDK_MODULE_NAME = "sap_bdc_connect_sdk"


class BDCConnectSDKNotInstalled(RuntimeError):
    """Raised when real-mode code requires the SDK but it is not importable."""


def is_available() -> bool:
    """Return True if the SAP BDC Connect SDK can be imported.

    The import is attempted exactly once; the result is *not* cached because
    ``bdc_diagnostics`` is allowed to reflect SDK installation changes during
    a server's lifetime (rare, but cheap to recompute).
    """
    try:
        importlib.import_module(_SDK_MODULE_NAME)
    except ImportError:
        return False
    return True


def client() -> Any:
    """Return an SDK client instance (real mode).

    v0.2 raises :class:`NotImplementedError` even when the SDK is importable:
    the real wiring is deferred to v0.3 per ADR-002 + Plan/05. Mock-mode
    callers must not reach this function — see ``DatabricksProvider`` for the
    mock branch.
    """
    if not is_available():
        raise BDCConnectSDKNotInstalled(
            "sap-bdc-connect-sdk is not installed; install it or set "
            "BDC_MOCK_MODE=1 to use the v0.2 mock provider."
        )
    raise NotImplementedError(
        "Real bdc-connect-sdk client wiring is deferred to v0.3. Use mock "
        "mode (BDC_MOCK_MODE=1) at v0.2; see "
        "docs/release/v0.2.0/03_Decisions/D-008-hybrid-worker-contract.md."
    )


def info() -> dict:
    """Return a small dict describing SDK availability — safe for diagnostics."""
    available = is_available()
    return {
        "module": _SDK_MODULE_NAME,
        "installed": available,
        "v02_real_mode_supported": False,
        "note": (
            "Real-mode execution is deferred to v0.3. v0.2 uses mock mode (BDC_MOCK_MODE=1) only."
        ),
    }


def _reset_for_tests(sdk_module: Optional[Any] = None) -> None:  # pragma: no cover
    """Test hook: install or remove a stub SDK module under the expected name.

    Not used by production code. Kept here so tests can simulate an
    installed SDK without altering ``sys.modules`` directly in many places.
    """
    import sys

    if sdk_module is None:
        sys.modules.pop(_SDK_MODULE_NAME, None)
    else:
        sys.modules[_SDK_MODULE_NAME] = sdk_module
