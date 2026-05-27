"""Gated-tool registration: policy evidence + WRITE/ADMIN enablement + audit + redaction.

File: src/sap_bdc_mcp/tools/_gated.py
Version: v1

Every MCP tool in v0.2 is registered through `gated(server, ctx, meta=...)`. The
wrapper runs three policy gates before the inner function executes, then writes
a JSONL audit event regardless of outcome, then redacts the return value.

Shape contract (for blocked / error cases):
  {"ok": False, "blocked_reason": str | None, "error": str | None, "audit_id": str}
Successful results pass through unchanged (subject to redaction).
"""

from __future__ import annotations

import functools
import inspect
import typing
from dataclasses import dataclass
from typing import Any, Callable, List

from ..audit import AuditWriter
from ..config import BDCConfig
from ..plugin_loader import PluginLoadResult
from ..policy_evidence import check_or_block
from ..redaction import redact
from .metadata import MetadataRegistry, Mutability, ToolMetadata


@dataclass
class ToolContext:
    """Shared runtime context handed to every tool registration function."""

    config: BDCConfig
    audit: AuditWriter
    metadata: MetadataRegistry
    plugin_status: List[PluginLoadResult]
    # Populated by server.py after Phase 3 (provider registry).
    # Typed Any to avoid a circular import during module load; access via
    # `ctx.providers.get(name)` in tools that need it.
    providers: Any = None


def gated(server: Any, ctx: ToolContext, *, meta: ToolMetadata) -> Callable:
    """Decorator factory: register `fn` as an MCP tool wrapped with gates + audit."""
    if ctx.metadata.get(meta.name) is None:
        ctx.metadata.register(meta)

    def decorator(fn: Callable) -> Callable:
        # Pre-resolve PEP-563 string annotations so FastMCP/Pydantic schema build works
        # on the wrapper (which lives in this module, with a different globals scope).
        try:
            hints = typing.get_type_hints(fn)
        except Exception:  # noqa: BLE001
            hints = {}
        orig_sig = inspect.signature(fn)
        resolved_params = [
            p.replace(annotation=hints.get(p.name, p.annotation))
            for p in orig_sig.parameters.values()
        ]
        resolved_return = hints.get("return", orig_sig.return_annotation)
        resolved_sig = orig_sig.replace(
            parameters=resolved_params, return_annotation=resolved_return
        )

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                bound = orig_sig.bind(*args, **kwargs)
                bound.apply_defaults()
                inputs = dict(bound.arguments)
            except TypeError:
                inputs = {"args": list(args), "kwargs": dict(kwargs)}

            dry_run = bool(inputs.get("dry_run", True))

            def _blocked(reason: str) -> dict:
                cid = ctx.audit.write(
                    tool_name=meta.name,
                    mutability=meta.mutability.value,
                    risk=meta.risk.value,
                    provider=meta.provider,
                    dry_run=dry_run,
                    allowed=False,
                    blocked_reason=reason,
                    inputs=inputs,
                    result_status="blocked",
                )
                return {"ok": False, "blocked_reason": reason, "audit_id": cid}

            ev = check_or_block(meta, strict=ctx.config.api_policy_strict)
            if not ev.allowed:
                return _blocked(ev.reason or "policy_evidence: blocked")

            if meta.mutability == Mutability.WRITE and not ctx.config.enable_write_tools:
                return _blocked("BDC_ENABLE_WRITE_TOOLS=0; write tools are disabled.")

            if meta.mutability == Mutability.ADMIN and not ctx.config.enable_admin_tools:
                return _blocked("BDC_ENABLE_ADMIN_TOOLS=0; admin tools are disabled.")

            try:
                result = fn(*args, **kwargs)
            except Exception as e:  # noqa: BLE001
                cid = ctx.audit.write(
                    tool_name=meta.name,
                    mutability=meta.mutability.value,
                    risk=meta.risk.value,
                    provider=meta.provider,
                    dry_run=dry_run,
                    allowed=True,
                    blocked_reason=None,
                    inputs=inputs,
                    result_status="error",
                )
                return {"ok": False, "error": redact(str(e)), "audit_id": cid}

            ctx.audit.write(
                tool_name=meta.name,
                mutability=meta.mutability.value,
                risk=meta.risk.value,
                provider=meta.provider,
                dry_run=dry_run,
                allowed=True,
                blocked_reason=None,
                inputs=inputs,
                result_status="ok",
            )
            if isinstance(result, (dict, list)):
                return redact(result)
            return result

        # Preserve resolved signature for FastMCP schema introspection.
        wrapper.__signature__ = resolved_sig  # type: ignore[attr-defined]
        wrapper.__annotations__ = {
            **{p.name: hints.get(p.name, p.annotation) for p in resolved_params},
            "return": resolved_return,
        }
        # Register with FastMCP.
        server.tool()(wrapper)
        return wrapper

    return decorator
