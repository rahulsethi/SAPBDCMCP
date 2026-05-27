"""JSONL audit writer for tool invocations.

File: src/sap_bdc_mcp/audit.py
Version: v1

Schema is `event_version: v1` — frozen at v0.2.0.
Retention is manual at v0.2 (see docs/release/v0.2.0/03_Decisions/D-004).
"""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .redaction import redact


EVENT_VERSION = "v1"


@dataclass(frozen=True)
class AuditEvent:
    tool_name: str
    mutability: str
    risk: str
    provider: Optional[str]
    dry_run: bool
    allowed: bool
    blocked_reason: Optional[str]
    input_hash: str
    result_status: str
    correlation_id: str
    timestamp: str
    event_version: str = EVENT_VERSION
    plugin: Optional[str] = None
    upstream_tool: Optional[str] = None
    redaction_applied: bool = True


def hash_inputs(payload: Any) -> str:
    """sha256 of canonical JSON of the *redacted* payload."""
    redacted = redact(payload)
    canon = json.dumps(redacted, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(canon.encode("utf-8")).hexdigest()


class AuditWriter:
    """Append-only JSONL writer. Thread-safe append; per-process file handle reopened on each write."""

    def __init__(self, log_path: str, enabled: bool = True) -> None:
        self.path = Path(log_path)
        self.enabled = enabled
        self._lock = threading.Lock()
        if self.enabled:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        *,
        tool_name: str,
        mutability: str,
        risk: str,
        provider: Optional[str],
        dry_run: bool,
        allowed: bool,
        blocked_reason: Optional[str],
        inputs: Any,
        result_status: str,
        correlation_id: Optional[str] = None,
        plugin: Optional[str] = None,
        upstream_tool: Optional[str] = None,
    ) -> str:
        cid = correlation_id or str(uuid.uuid4())
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_version": EVENT_VERSION,
            "tool_name": tool_name,
            "mutability": mutability,
            "risk": risk,
            "provider": provider,
            "plugin": plugin,
            "upstream_tool": upstream_tool,
            "dry_run": dry_run,
            "allowed": allowed,
            "blocked_reason": blocked_reason,
            "input_hash": hash_inputs(inputs),
            "redaction_applied": True,
            "result_status": result_status,
            "correlation_id": cid,
        }
        if self.enabled:
            with self._lock, self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        return cid

    def tail(self, limit: int = 50, since_timestamp: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return the last `limit` events (most-recent last), optionally filtered by timestamp."""
        if not self.path.exists():
            return []
        events: List[Dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if since_timestamp is not None and ev.get("timestamp", "") < since_timestamp:
                    continue
                events.append(ev)
        return events[-limit:]
