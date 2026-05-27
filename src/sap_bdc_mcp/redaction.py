"""Redaction helpers.

File: src/sap_bdc_mcp/redaction.py
Version: v2

v0.2 adds patterns for signed Delta-share URLs and JWT-shaped tokens, plus
`hash_input()` which is consumed by audit.py to fingerprint inputs without
storing secrets.
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
    "approval_token",
}

# Basic URL credential patterns (defense-in-depth).
_URL_CRED_RE = re.compile(r"(https?://)([^/@:]+):([^/@]+)@")
_BEARER_RE = re.compile(r"(Bearer\s+)([A-Za-z0-9\-\._~\+/]+=*)", re.IGNORECASE)

# v0.2 additions:
# Signed Delta Sharing / generic signed URL — redact the secret portion of the query string.
_SIGNED_URL_RE = re.compile(
    r"((?:token|signature|sig|x-amz-signature)=)([^&\s\"']+)",
    re.IGNORECASE,
)
# JWT-shaped string (eyJ...) — redact the whole thing.
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_\-]{6,}\.[A-Za-z0-9_\-]{6,}\.[A-Za-z0-9_\-]{6,}\b")


def redact_str(value: str) -> str:
    v = _URL_CRED_RE.sub(r"\1***:***@", value)
    v = _BEARER_RE.sub(r"\1***", v)
    v = _SIGNED_URL_RE.sub(r"\1***", v)
    v = _JWT_RE.sub("***", v)
    return v


def redact(obj: Any) -> Any:
    if isinstance(obj, str):
        return redact_str(obj)
    if isinstance(obj, list):
        return [redact(x) for x in obj]
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            if isinstance(k, str) and k.lower() in _SENSITIVE_KEYS:
                out[k] = "***"
            else:
                out[k] = redact(v)
        return out
    return obj
