"""ORD JSON Schema loaders.

File: src/sap_bdc_mcp/connectors/ord_schema.py
Version: v1

Purpose:
- Keep schema loading logic isolated from the ORD client.
- Load JSON Schemas shipped under `sap_bdc_mcp.schemas.ord`.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from typing import Any, Dict

import sap_bdc_mcp.schemas.ord as ord_schema_pkg


@lru_cache
def load_document_schema() -> Dict[str, Any]:
    """Load ORD Document schema as a dict."""
    raw = files(ord_schema_pkg).joinpath("Document.schema.json").read_text(encoding="utf-8")
    return json.loads(raw)


@lru_cache
def load_configuration_schema() -> Dict[str, Any]:
    """Load ORD Configuration schema as a dict."""
    raw = files(ord_schema_pkg).joinpath("Configuration.schema.json").read_text(encoding="utf-8")
    return json.loads(raw)
