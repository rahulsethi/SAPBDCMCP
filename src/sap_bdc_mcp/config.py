"""Configuration loading and validation.

File: src/sap_bdc_mcp/config.py
Version: v1
"""

from __future__ import annotations

from dataclasses import dataclass
from os import getenv
from typing import List

from dotenv import load_dotenv


@dataclass(frozen=True)
class BDCConfig:
    """Configuration for the BDC MCP server.

    Values are loaded from env (.env supported).
    Keep this small and explicit — it becomes a contract for deployments.
    """

    mode: str
    mock_mode: bool
    verify_tls: bool
    max_doc_kb: int
    ord_sources: List[str]
    plugins: List[str]
    enable_write_tools: bool

    @staticmethod
    def from_env() -> "BDCConfig":
        load_dotenv()

        mode = getenv("BDC_MODE", "local").strip()
        mock_mode = getenv("BDC_MOCK_MODE", "0").strip() in ("1", "true", "TRUE", "yes", "YES")
        verify_tls = getenv("BDC_VERIFY_TLS", "1").strip() in ("1", "true", "TRUE", "yes", "YES")

        max_doc_kb_raw = getenv("BDC_MAX_DOC_KB", "512").strip()
        try:
            max_doc_kb = int(max_doc_kb_raw)
        except ValueError as e:
            raise ValueError(f"BDC_MAX_DOC_KB must be an integer, got: {max_doc_kb_raw}") from e

        ord_sources_raw = getenv("BDC_ORD_SOURCES", "").strip()
        ord_sources = [s.strip() for s in ord_sources_raw.split(",") if s.strip()]

        plugins_raw = getenv("BDC_PLUGINS", "").strip()
        plugins = [p.strip() for p in plugins_raw.split(",") if p.strip()]

        enable_write_tools = getenv("BDC_ENABLE_WRITE_TOOLS", "0").strip() in (
            "1",
            "true",
            "TRUE",
            "yes",
            "YES",
        )

        return BDCConfig(
            mode=mode,
            mock_mode=mock_mode,
            verify_tls=verify_tls,
            max_doc_kb=max_doc_kb,
            ord_sources=ord_sources,
            plugins=plugins,
            enable_write_tools=enable_write_tools,
        )
