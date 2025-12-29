"""Redaction helpers.

File: src/sap_bdc_mcp/redaction.py
Version: v1
"""

from __future__ import annotations

import re
from typing import Any, Dict


_SENSITIVE_KEYS = {
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "password",
    "secret",
    "client_secret",
    "apikey",
    "api_key",
}

# Basic URL credential patterns (defense-in-depth).
_URL_CRED_RE = re.compile(r"(https?://)([^/@:]+):([^/@]+)@")
_BEARER_RE = re.compile(r"(Bearer\s+)([A-Za-z0-9\-\._~\+/]+=*)", re.IGNORECASE)


def redact_str(value: str) -> str:
    v = _URL_CRED_RE.sub(r"\1***:***@", value)
    v = _BEARER_RE.sub(r"\1***", v)
    return v


def redact(obj: Any) -> Any:
    if isinstance(obj, str):
        return redact_str(obj)
    if isinstance(obj, list):
        return [redact(x) for x in obj]
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            if k.lower() in _SENSITIVE_KEYS:
                out[k] = "***"
            else:
                out[k] = redact(v)
        return out
    return obj
