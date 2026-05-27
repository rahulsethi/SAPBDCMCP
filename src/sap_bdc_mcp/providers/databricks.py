"""Databricks BDC Connect provider — full impl, mock-driven at v0.2.

File: src/sap_bdc_mcp/providers/databricks.py
Version: v1

Mock mode (``BDC_MOCK_MODE=1``) is the only path exercised at v0.2; tests
assert it is deterministic and never touches the network. Real mode lazily
imports :mod:`sap_bdc_mcp.connectors.bdc_connect_sdk_client` and currently
raises :class:`NotImplementedError` pointing to v0.3.

Implements:
  - :meth:`capabilities` — supports_execute=True, supports_dry_run=True, etc.
  - :meth:`preflight` — checks env shape; returns structured blockers (no raise).
  - :meth:`validate_plan` — light structural checks on top of share_validate_contract.
  - :meth:`dry_run_execute` — returns ExecutionPreview built from fixture metadata.
  - :meth:`execute` — returns ExecutionResult that documents the (mock) actions.

CSN generation helpers live in this module too because they share the same
fixture lookup. The tool wrapper in ``tools/databricks_tools.py`` calls
:func:`generate_csn_from_share` (free function) — keeps the provider focused
on share lifecycle and isolates the D-006 logic for testing.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..config import BDCConfig
from ..models.share_plan import SharePlan
from .base import (
    BDCConnectProvider,
    ExecutionPreview,
    ExecutionResult,
    PlanValidation,
    PreflightResult,
    ProviderCapabilities,
    ProviderContext,
)


_FIXTURE_DIR = Path(__file__).resolve().parents[3] / "fixtures"
_SHARE_FIXTURE = _FIXTURE_DIR / "databricks_share_mock.json"
_RECIPIENT_FIXTURE = _FIXTURE_DIR / "databricks_recipient_mock.json"


CSN_DISCLAIMER = (
    "Generated CSN is approximate. Review every entity definition before "
    "publishing. Tool: bdc_databricks_generate_csn_from_share, evidence: "
    "bdc-connect-sdk.share.read_metadata, v0.2."
)
CSN_REFUSAL_DISCLAIMER = (
    "v0.2 generates CSN for primitive Delta columns only. Complex types "
    "are deferred to v0.3. See docs/release/v0.2.0/03_Decisions/"
    "D-006-csn-generation-scope.md"
)


# ---------------------------------------------------------------------------
# Type mapping (D-006)
# ---------------------------------------------------------------------------


_PRIMITIVE_TO_CSN: Dict[str, Tuple[str, Dict[str, Any]]] = {
    "string": ("cds.String", {}),
    "varchar": ("cds.String", {}),
    "char": ("cds.String", {}),
    "bigint": ("cds.Integer", {}),
    "int": ("cds.Integer", {}),
    "integer": ("cds.Integer", {}),
    "smallint": ("cds.Integer", {}),
    "tinyint": ("cds.Integer", {}),
    "double": ("cds.Double", {}),
    "float": ("cds.Double", {}),
    "boolean": ("cds.Boolean", {}),
    "bool": ("cds.Boolean", {}),
    "date": ("cds.Date", {}),
    "timestamp": ("cds.Timestamp", {}),
    "timestamp_ntz": ("cds.Timestamp", {}),
    "binary": ("cds.Binary", {}),
}

_COMPLEX_PREFIXES = ("struct<", "array<", "map<")


def _classify_column(col_type: str) -> Tuple[str, Dict[str, Any], bool]:
    """Return (csn_type, extras, is_supported).

    Decimal precision/scale is parsed out of ``decimal(p,s)``.
    Complex types return (raw, {}, False).
    """
    lt = col_type.strip().lower()
    if lt.startswith(_COMPLEX_PREFIXES):
        return (col_type, {}, False)
    m = re.fullmatch(r"decimal\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)", lt)
    if m:
        precision, scale = int(m.group(1)), int(m.group(2))
        return ("cds.Decimal", {"precision": precision, "scale": scale}, True)
    primary = lt.split("(", 1)[0].strip()
    mapping = _PRIMITIVE_TO_CSN.get(primary)
    if mapping is None:
        return (col_type, {}, False)
    csn_type, extras = mapping
    return (csn_type, dict(extras), True)


# ---------------------------------------------------------------------------
# Fixture loaders
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ShareMock:
    share_name: str
    recipient: str
    comment: str
    schemas: List[Dict[str, Any]]


def _load_shares() -> Dict[str, _ShareMock]:
    if not _SHARE_FIXTURE.exists():
        return {}
    raw = json.loads(_SHARE_FIXTURE.read_text(encoding="utf-8"))
    out: Dict[str, _ShareMock] = {}
    for name, entry in raw.get("shares", {}).items():
        out[name] = _ShareMock(
            share_name=entry.get("share_name", name),
            recipient=entry.get("recipient", ""),
            comment=entry.get("comment", ""),
            schemas=entry.get("schemas", []),
        )
    return out


def _load_recipients() -> Dict[str, Dict[str, Any]]:
    if not _RECIPIENT_FIXTURE.exists():
        return {}
    raw = json.loads(_RECIPIENT_FIXTURE.read_text(encoding="utf-8"))
    return dict(raw.get("recipients", {}))


# ---------------------------------------------------------------------------
# CSN generation (D-006)
# ---------------------------------------------------------------------------


def _entity_name(share: str, schema: str, table: str) -> str:
    return f"db.{schema}.{table}" if schema else f"db.{table}"


def _generate_csn_dict(share: _ShareMock) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, str]]]:
    """Build a CSN dict from a share mock. Returns (csn, unsupported_columns)."""
    unsupported: List[Dict[str, str]] = []
    definitions: Dict[str, Any] = {}
    for schema in share.schemas:
        schema_name = schema.get("schema_name", "")
        for table in schema.get("tables", []):
            table_name = table.get("table_name", "")
            elements: Dict[str, Any] = {}
            for col in table.get("columns", []):
                name = col.get("name", "")
                raw_type = col.get("type", "")
                csn_type, extras, supported = _classify_column(raw_type)
                if not supported:
                    unsupported.append({"name": name, "type": raw_type})
                    continue
                element: Dict[str, Any] = {"type": csn_type}
                element.update(extras)
                if col.get("nullable") is False:
                    element["notNull"] = True
                elements[name] = element
            if unsupported:
                # Don't bother building the rest — refusal will dominate.
                continue
            definitions[_entity_name(share.share_name, schema_name, table_name)] = {
                "kind": "entity",
                "elements": elements,
            }
    if unsupported:
        return None, unsupported
    csn: Dict[str, Any] = {"$version": "2.0", "definitions": definitions}
    return csn, []


def _render_cds(csn: Dict[str, Any]) -> str:
    """Render a CSN dict to a minimal CDS DDL string."""
    lines: List[str] = []
    for entity_name, body in csn.get("definitions", {}).items():
        if body.get("kind") != "entity":
            continue
        lines.append(f"entity {entity_name} {{")
        for name, element in body.get("elements", {}).items():
            t = element["type"]
            if t == "cds.Decimal":
                precision = element.get("precision")
                scale = element.get("scale")
                if precision is not None and scale is not None:
                    t = f"Decimal({precision}, {scale})"
                else:
                    t = "Decimal"
            elif t.startswith("cds."):
                t = t.split(".", 1)[1]
            suffix = " not null" if element.get("notNull") else ""
            lines.append(f"  {name}: {t}{suffix};")
        lines.append("}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_draft(share: _ShareMock, csn: Dict[str, Any]) -> str:
    """Plain-English summary."""
    entity_count = len(csn.get("definitions", {}))
    parts: List[str] = [
        f"Draft CSN for Databricks share '{share.share_name}':",
        f"  recipient: {share.recipient or '(unknown)'}",
        f"  entities: {entity_count}",
    ]
    for entity_name, body in csn.get("definitions", {}).items():
        col_count = len(body.get("elements", {}))
        parts.append(f"   - {entity_name} ({col_count} columns)")
    parts.append("Review required: every entity definition before publishing.")
    return "\n".join(parts)


def generate_csn_from_share(share_name: str, format: str = "json") -> Dict[str, Any]:
    """Generate a CSN-ish artifact from a Databricks share (mock-driven).

    D-006 scope: primitive Delta columns only. Any complex column yields a
    refusal dict with the disclaimer; success dicts always carry the
    standard disclaimer too.
    """
    if format not in {"json", "cds", "draft"}:
        return {
            "ok": False,
            "reason": "invalid_format",
            "supported_formats": ["json", "cds", "draft"],
            "disclaimer": CSN_DISCLAIMER,
        }
    shares = _load_shares()
    share = shares.get(share_name)
    if share is None:
        return {
            "ok": False,
            "reason": "share_not_found",
            "share_name": share_name,
            "disclaimer": CSN_DISCLAIMER,
        }
    csn, unsupported = _generate_csn_dict(share)
    if csn is None:
        return {
            "ok": False,
            "reason": "complex_types_not_supported",
            "share_name": share_name,
            "unsupported_columns": unsupported,
            "disclaimer": CSN_REFUSAL_DISCLAIMER,
        }
    result: Dict[str, Any] = {
        "ok": True,
        "share_name": share_name,
        "format": format,
        "disclaimer": CSN_DISCLAIMER,
    }
    if format == "json":
        result["csn"] = csn
    elif format == "cds":
        result["cds"] = _render_cds(csn)
    else:  # "draft"
        result["draft"] = _render_draft(share, csn)
    return result


def lookup_share(share_name: str) -> Optional[_ShareMock]:
    """Return the share mock by name, or None."""
    return _load_shares().get(share_name)


def lookup_recipient(name: str) -> Optional[Dict[str, Any]]:
    """Return the recipient mock by name, or None."""
    return _load_recipients().get(name)


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class DatabricksProvider(BDCConnectProvider):
    """Databricks BDC Connect provider.

    Construction never raises. Methods consume mock fixtures when
    ``ctx.mock_mode`` is True; real mode raises :class:`NotImplementedError`
    via :mod:`sap_bdc_mcp.connectors.bdc_connect_sdk_client`.
    """

    name = "databricks"

    def __init__(self, config: BDCConfig) -> None:
        self._config = config

    # -- capability declaration -------------------------------------------------
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_preflight=True,
            supports_validate_plan=True,
            supports_dry_run=True,
            supports_execute=True,
            notes=(
                "Mock mode is the only path exercised at v0.2; real SDK wiring is deferred to v0.3."
            ),
        )

    # -- preflight --------------------------------------------------------------
    async def preflight(self, ctx: ProviderContext) -> PreflightResult:
        cfg = self._config.databricks
        checks: List[Dict[str, Any]] = []
        blockers: List[str] = []

        def _add(name: str, ok: bool, detail: str, *, blocker: Optional[str] = None) -> None:
            checks.append({"name": name, "ok": ok, "detail": detail})
            if not ok and blocker:
                blockers.append(blocker)

        host_ok = bool(cfg.host) or ctx.mock_mode
        _add(
            "host_reachable",
            host_ok,
            (
                "mock_mode=1; not probed"
                if ctx.mock_mode
                else (f"host={cfg.host}" if cfg.host else "BDC_DATABRICKS_HOST is empty")
            ),
            blocker=(
                None if host_ok else "Set BDC_DATABRICKS_HOST to your Databricks workspace URL."
            ),
        )

        token_ok = bool(cfg.token) or ctx.mock_mode
        _add(
            "token_shape_valid",
            token_ok,
            (
                "mock_mode=1; not probed"
                if ctx.mock_mode
                else ("token present" if cfg.token else "BDC_DATABRICKS_TOKEN is empty")
            ),
            blocker=None if token_ok else "Set BDC_DATABRICKS_TOKEN.",
        )

        recipient_ok = bool(cfg.recipient) or ctx.mock_mode
        _add(
            "recipient_registered",
            recipient_ok,
            (
                "mock_mode=1; not probed"
                if ctx.mock_mode
                else (
                    f"recipient={cfg.recipient}"
                    if cfg.recipient
                    else "BDC_DATABRICKS_RECIPIENT is empty"
                )
            ),
            blocker=None if recipient_ok else "Set BDC_DATABRICKS_RECIPIENT.",
        )

        warehouse_ok = bool(cfg.warehouse) or ctx.mock_mode
        _add(
            "warehouse_accessible",
            warehouse_ok,
            (
                "mock_mode=1; not probed"
                if ctx.mock_mode
                else (
                    f"warehouse={cfg.warehouse}"
                    if cfg.warehouse
                    else "BDC_DATABRICKS_WAREHOUSE is empty"
                )
            ),
            blocker=None if warehouse_ok else "Set BDC_DATABRICKS_WAREHOUSE.",
        )

        ok = all(c["ok"] for c in checks)
        return PreflightResult(ok=ok, checks=checks, blockers=blockers)

    # -- validate_plan ----------------------------------------------------------
    async def validate_plan(self, plan: SharePlan, ctx: ProviderContext) -> PlanValidation:
        issues: List[Dict[str, Any]] = []
        if not plan.name or not plan.name.strip():
            issues.append({"code": "INVALID_PLAN_NAME", "message": "plan.name is empty"})
        if not plan.assets:
            issues.append({"code": "EMPTY_PLAN", "message": "plan has no assets"})
        for i, asset in enumerate(plan.assets):
            if not asset.name or not asset.name.strip():
                issues.append(
                    {
                        "code": "INVALID_ASSET_NAME",
                        "asset_index": i,
                        "message": "asset name empty",
                    }
                )
        return PlanValidation(ok=(not issues), issues=issues)

    # -- dry_run_execute --------------------------------------------------------
    async def dry_run_execute(self, plan: SharePlan, ctx: ProviderContext) -> ExecutionPreview:
        if not ctx.mock_mode:
            # Real-mode wiring deferred to v0.3.
            from ..connectors.bdc_connect_sdk_client import client as _client

            _client()  # raises NotImplementedError pointing to v0.3
        # Build a synthetic operation list — one per asset.
        planned_operations: List[Dict[str, Any]] = []
        for asset in plan.assets:
            planned_operations.append(
                {
                    "op": "create_or_update_share_asset",
                    "share": plan.name,
                    "asset": asset.name,
                    "asset_type": asset.type,
                    "schema": asset.schema_name,
                }
            )
        warnings: List[str] = []
        recipient_name = self._config.databricks.recipient
        if recipient_name and lookup_recipient(recipient_name) is None and ctx.mock_mode:
            warnings.append(
                f"recipient '{recipient_name}' not present in mock fixtures; "
                "fixture-driven dry-run still proceeds."
            )
        return ExecutionPreview(
            ok=True,
            planned_operations=planned_operations,
            warnings=warnings,
            estimated_impact={
                "asset_count": len(plan.assets),
                "recipient": recipient_name or "(unset)",
            },
        )

    # -- execute ----------------------------------------------------------------
    async def execute(
        self, plan: SharePlan, ctx: ProviderContext, approval_token: str
    ) -> ExecutionResult:
        if not ctx.mock_mode:
            from ..connectors.bdc_connect_sdk_client import client as _client

            _client()  # raises NotImplementedError pointing to v0.3
        # Mock-mode "execute": fixture is read-only, so nothing happens. We
        # report success for every asset so the caller can audit the result.
        return ExecutionResult(
            ok=True,
            status="ok",
            summary=(
                f"Mock execute applied {len(plan.assets)} asset(s) to share "
                f"'{plan.name}'. No real Databricks calls were made."
            ),
            next_steps=[
                "Run bdc_databricks_validate_share_readiness to confirm the "
                "share is consumable by the recipient.",
                "Generate consumer-side CSN via bdc_databricks_generate_csn_from_share.",
            ],
        )
