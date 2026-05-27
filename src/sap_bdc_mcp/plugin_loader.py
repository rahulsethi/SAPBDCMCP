"""Plugin loader with import + subprocess (npx/uvx/cmd) MCP plugin support.

File: src/sap_bdc_mcp/plugin_loader.py
Version: v2

Phase 6 (v0.2.0): in addition to the v0.1 import-based plugins, BDC_PLUGINS
entries may now use scheme prefixes to spawn upstream MCP servers as
subprocesses. Each subprocess child is initialized over stdio (MCP
``initialize`` + ``tools/list``) and every child tool is registered in the
parent under a namespaced name ``plug_<alias>__<tool>``, gated by the same
policy/audit machinery as first-party tools.

See ``docs/release/v0.2.0/02_Design.md`` section 3, plus
``docs/release/v0.2.0/03_Decisions/D-001-npx-upstream-plugins.md`` for the
trust model. Subprocess plugin tools default to
``mutability=WRITE / api_surface=UNKNOWN / bulk_data_behavior=BLOCKED`` and
are blocked under ``BDC_API_POLICY_STRICT=1`` unless the operator promotes
them via ``BDC_PLUGIN_TRUST=<alias>:<surface>``.
"""

from __future__ import annotations

import asyncio
import atexit
import importlib
import logging
import os
import shlex
import shutil
import sys
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .tools._gated import ToolContext


# ---------------------------------------------------------------------------
# Result + spec dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PluginLoadResult:
    """Outcome of loading a single plugin entry from BDC_PLUGINS."""

    name: str
    ok: bool
    error: Optional[str] = None
    scheme: Optional[str] = None
    alias: Optional[str] = None
    tools: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class PluginSpec:
    """Parsed BDC_PLUGINS entry."""

    alias: str
    scheme: str  # "python" | "npx" | "uvx" | "cmd"
    target: str
    args: List[str] = field(default_factory=list)


_VALID_SCHEMES: Set[str] = {"python", "npx", "uvx", "cmd"}


class PluginParseError(ValueError):
    """Raised when an entry cannot be parsed into a :class:`PluginSpec`."""


def _derive_alias_from_target(scheme: str, target: str) -> str:
    """Best-effort alias derivation when the operator did not supply one."""
    raw = target.strip()
    if scheme == "python":
        # last dotted segment
        return raw.rsplit(".", 1)[-1] or "plugin"
    if scheme == "cmd":
        base = os.path.basename(raw.split()[0]) if raw else "cmd"
        for ext in (".exe", ".cmd", ".bat", ".py", ".js"):
            if base.lower().endswith(ext):
                base = base[: -len(ext)]
                break
        return base or "cmd"
    # npx / uvx packages: keep last path segment, strip version pin.
    # Examples:
    #   "@scope/name@1.2.3"     -> "name"
    #   "@scope/name"           -> "name"
    #   "mcp-server-sentry==0.1.4" -> "mcp-server-sentry"
    #   "pkg@2.0.0"             -> "pkg"
    spec = raw.split()[0] if raw else ""
    # 1) Strip version pin.
    if "==" in spec:
        spec = spec.split("==", 1)[0]
    elif spec.startswith("@"):
        # Scoped npm package: pin (if any) is the second `@`.
        head, _, _ = spec[1:].partition("@")
        spec = "@" + head
    elif "@" in spec:
        # Unscoped pin "pkg@1.2.3" — strip everything from the @.
        spec = spec.split("@", 1)[0]
    # 2) For scoped packages, drop the @scope/ prefix.
    if spec.startswith("@") and "/" in spec:
        spec = spec.split("/", 1)[1]
    return spec or scheme


def parse_plugin_entry(raw: str) -> PluginSpec:
    """Parse one ``BDC_PLUGINS`` entry into a :class:`PluginSpec`.

    Grammar (whitespace tolerant):

        [<alias>=]<scheme>:<target>[ -- arg1 arg2 ...]
        <python.module.path>            # back-compat: bare module path

    Schemes: python | npx | uvx | cmd. Unknown schemes raise
    :class:`PluginParseError`; the caller is expected to surface this as a
    :class:`PluginLoadResult` with ``ok=False``.
    """
    if raw is None:
        raise PluginParseError("plugin entry is None")
    text = raw.strip()
    if not text:
        raise PluginParseError("plugin entry is empty")

    # Split optional alias prefix `<alias>=`.
    alias: Optional[str] = None
    if "=" in text:
        head, _, tail = text.partition("=")
        # Only treat as alias= if head looks like a bare identifier and tail
        # contains a scheme/module (defensive: avoids splitting on '=' inside args).
        if head and head.strip().replace("_", "").replace("-", "").isalnum() and tail:
            alias = head.strip()
            text = tail.strip()

    # Split body / args on " -- ".
    body = text
    args: List[str] = []
    if " -- " in text:
        body, _, arg_str = text.partition(" -- ")
        body = body.strip()
        try:
            args = _shlex_split_windows_safe(arg_str)
        except ValueError as exc:
            raise PluginParseError(f"failed to parse args for plugin entry: {exc}") from exc

    # Bare module path back-compat: no scheme prefix.
    scheme: str
    target: str
    if ":" not in body or body.split(":", 1)[0] not in _VALID_SCHEMES:
        # Treat the whole body as a python module path. Reject obviously
        # invalid schemes (e.g. "something:invalid") loudly.
        if ":" in body:
            bad_scheme = body.split(":", 1)[0].strip()
            if bad_scheme and bad_scheme not in _VALID_SCHEMES:
                raise PluginParseError(
                    f"unknown plugin scheme '{bad_scheme}'; "
                    f"expected one of {sorted(_VALID_SCHEMES)} or a bare module path"
                )
        scheme = "python"
        target = body
    else:
        scheme, _, target = body.partition(":")
        scheme = scheme.strip()
        target = target.strip()

    if not target:
        raise PluginParseError(f"plugin entry '{raw}' has empty target")

    if alias is None:
        alias = _derive_alias_from_target(scheme, target)

    return PluginSpec(alias=alias, scheme=scheme, target=target, args=args)


# ---------------------------------------------------------------------------
# Subprocess plugin runtime
# ---------------------------------------------------------------------------


def _shlex_split_windows_safe(text: str) -> List[str]:
    """Split a command line tolerantly across platforms.

    Backslashes inside Windows paths must not be treated as escape characters,
    so we run shlex with ``posix=False`` (which preserves quote characters on
    each token) and strip a single layer of surrounding double-quotes.
    """
    if not text:
        return []
    tokens = shlex.split(text, posix=False)
    out: List[str] = []
    for tok in tokens:
        if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in ('"', "'"):
            tok = tok[1:-1]
        out.append(tok)
    return out


def _build_subprocess_env(passthrough: List[str]) -> Dict[str, str]:
    """Build a minimal env for the child process.

    Always include standard system vars (PATH, HOME/USERPROFILE, TMP, ...).
    Anything else must be opted-in via BDC_PLUGIN_ENV_PASSTHROUGH.
    """
    keep_keys = {
        "PATH",
        "PATHEXT",
        "SYSTEMROOT",
        "SYSTEMDRIVE",
        "TEMP",
        "TMP",
        "HOME",
        "HOMEDRIVE",
        "HOMEPATH",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
        "USER",
        "USERNAME",
        "LOGNAME",
        "SHELL",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
    }
    env: Dict[str, str] = {}
    for k in keep_keys:
        v = os.environ.get(k)
        if v is not None:
            env[k] = v
    for k in passthrough:
        k = k.strip()
        if not k:
            continue
        v = os.environ.get(k)
        if v is not None:
            env[k] = v
    return env


def _resolve_subprocess_command(spec: PluginSpec) -> tuple[str, List[str]]:
    """Translate a PluginSpec into (command, args) for ``stdio_client``."""
    if spec.scheme == "npx":
        return "npx", ["-y", spec.target, *spec.args]
    if spec.scheme == "uvx":
        return "uvx", [spec.target, *spec.args]
    if spec.scheme == "cmd":
        # For cmd:<abs_path> the target itself is the executable; args follow.
        # Tolerate the convenience of `cmd:python tests/_helpers/dummy.py`
        # (i.e. target may include the first arg separated by spaces).
        parts = _shlex_split_windows_safe(spec.target) if spec.target else []
        if not parts:
            raise PluginParseError(f"cmd plugin '{spec.alias}' has empty target")
        cmd, *rest = parts
        return cmd, [*rest, *spec.args]
    raise PluginParseError(f"unsupported subprocess scheme: {spec.scheme}")


class SubprocessPlugin:
    """Manages the lifecycle of one subprocess MCP server.

    Each instance runs a dedicated background thread that hosts an asyncio
    event loop. The loop holds the ``stdio_client`` + ``ClientSession``
    context manager open for the lifetime of the plugin. Synchronous calls
    from the parent are scheduled onto that loop via
    ``asyncio.run_coroutine_threadsafe``.

    This is the most robust shape for v0.2: simple, isolating each plugin
    from the others, and avoids forcing the parent server's event loop to
    become asyncio-aware (the parent currently runs FastMCP synchronously).
    """

    def __init__(self, spec: PluginSpec, env_passthrough: List[str]) -> None:
        self.spec = spec
        self.env_passthrough = list(env_passthrough)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._ready = threading.Event()
        self._stopped = threading.Event()
        self._start_error: Optional[BaseException] = None
        self._tools: List[Dict[str, Any]] = []
        self._session: Any = None  # mcp.ClientSession (typed Any to avoid hard dep at import)
        self._stop_request: Optional[asyncio.Event] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start(self, *, timeout: float = 15.0) -> None:
        """Spawn the child, run initialize + tools/list, return when ready."""
        thr = threading.Thread(
            target=self._thread_main,
            name=f"sap-bdc-plugin[{self.spec.alias}]",
            daemon=True,
        )
        self._thread = thr
        thr.start()
        if not self._ready.wait(timeout=timeout):
            self.stop()
            raise RuntimeError(
                f"plugin '{self.spec.alias}' ({self.spec.scheme}:{self.spec.target}) "
                f"did not initialize within {timeout}s"
            )
        if self._start_error is not None:
            self.stop()
            raise self._start_error

    def stop(self, *, timeout: float = 5.0) -> None:
        """Signal the background loop to exit and join the thread."""
        if self._loop is None or self._stop_request is None:
            self._stopped.set()
            return
        loop = self._loop
        evt = self._stop_request
        if not loop.is_closed():
            try:
                loop.call_soon_threadsafe(evt.set)
            except RuntimeError:
                pass
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def listed_tools(self) -> List[Dict[str, Any]]:
        """List of dicts: ``{"name", "description", "input_schema"}`` per child tool."""
        return list(self._tools)

    def call_sync(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        *,
        timeout: float = 60.0,
    ) -> Dict[str, Any]:
        """Forward a tool call to the child synchronously."""
        if self._loop is None or self._session is None:
            return {
                "ok": False,
                "error": f"plugin '{self.spec.alias}' is not running",
            }
        coro = self._call(tool_name, arguments)
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        try:
            return fut.result(timeout=timeout)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"plugin call failed: {exc}"}

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    async def _call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        session = self._session
        if session is None:  # pragma: no cover - guarded above
            return {"ok": False, "error": "session unavailable"}
        try:
            result = await session.call_tool(tool_name, arguments or {})
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        # Normalize result to a JSON-friendly dict.
        out: Dict[str, Any] = {"ok": not bool(getattr(result, "isError", False))}
        struct = getattr(result, "structuredContent", None)
        if struct is not None:
            out["structured"] = struct
        contents = getattr(result, "content", None)
        if contents:
            text_chunks: List[str] = []
            for chunk in contents:
                text = getattr(chunk, "text", None)
                if text is not None:
                    text_chunks.append(text)
            if text_chunks:
                out["text"] = "\n".join(text_chunks)
        return out

    def _thread_main(self) -> None:
        try:
            loop = asyncio.new_event_loop()
        except Exception as exc:  # pragma: no cover
            self._start_error = exc
            self._ready.set()
            return
        self._loop = loop
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._run())
        except BaseException as exc:  # noqa: BLE001
            if not self._ready.is_set():
                self._start_error = exc
                self._ready.set()
            else:  # pragma: no cover - post-ready failure
                logger.warning("plugin '%s' background loop crashed: %s", self.spec.alias, exc)
        finally:
            try:
                loop.close()
            except Exception:  # pragma: no cover
                pass
            self._stopped.set()

    async def _run(self) -> None:
        # Local imports keep ``mcp`` out of the import path until a subprocess
        # plugin is actually requested.
        from mcp import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client

        self._stop_request = asyncio.Event()

        command, args = _resolve_subprocess_command(self.spec)
        env = _build_subprocess_env(self.env_passthrough)

        # On Windows, ``npx``/``uvx`` are typically batch shims; resolving via
        # PATH is sufficient because StdioServerParameters honors PATHEXT.
        resolved = shutil.which(command)
        if resolved is None and command not in ("npx", "uvx"):
            # cmd: scheme needs a real path; npx/uvx may still be resolvable
            # by the OS even if shutil.which fails on some shims.
            self._start_error = FileNotFoundError(
                f"plugin '{self.spec.alias}': command '{command}' not found on PATH"
            )
            self._ready.set()
            return

        params = StdioServerParameters(
            command=resolved or command,
            args=args,
            env=env,
        )

        try:
            async with stdio_client(params, errlog=sys.stderr) as (read, write):
                async with ClientSession(read, write) as session:
                    self._session = session
                    try:
                        await session.initialize()
                        tools_result = await session.list_tools()
                    except Exception as exc:  # noqa: BLE001
                        self._start_error = exc
                        self._ready.set()
                        return
                    self._tools = [
                        {
                            "name": t.name,
                            "description": t.description or "",
                            "input_schema": getattr(t, "inputSchema", None),
                        }
                        for t in tools_result.tools
                    ]
                    self._ready.set()
                    await self._stop_request.wait()
                    # Falling out of the context managers shuts the child down
                    # via stdio_client's documented SIGTERM/SIGKILL escalation.
        except BaseException as exc:  # noqa: BLE001
            if not self._ready.is_set():
                self._start_error = exc
                self._ready.set()
            else:  # pragma: no cover
                logger.warning("plugin '%s' stdio loop ended: %s", self.spec.alias, exc)
        finally:
            self._session = None


# ---------------------------------------------------------------------------
# Synthesized metadata for child tools
# ---------------------------------------------------------------------------


def _surface_from_trust(raw: Optional[str]) -> Any:
    """Translate the operator's ``BDC_PLUGIN_TRUST`` value to an APISurface."""
    from .tools.metadata import APISurface

    if not raw:
        return APISurface.UNKNOWN
    raw = raw.strip().lower()
    for s in APISurface:
        if s.value == raw:
            return s
    return APISurface.UNKNOWN


def _synthesize_metadata(
    alias: str,
    upstream_tool: Dict[str, Any],
    *,
    trust: Dict[str, str],
) -> Any:
    """Build a :class:`ToolMetadata` for one child tool.

    Defaults follow Design §3.3 + D-001 + D-007:
      mutability=WRITE, risk=MEDIUM, api_surface=UNKNOWN, category="plugin",
      bulk_data_behavior=BLOCKED. Operator-supplied trust upgrades
      ``api_surface`` and (implicitly) flips ``bulk_data_behavior`` to NONE
      because the operator has vouched that the plugin is not a bulk
      extractor.
    """
    from .tools.metadata import (
        APISurface,
        BulkDataBehavior,
        Mutability,
        Risk,
        ToolMetadata,
    )

    surface = _surface_from_trust(trust.get(alias))
    name = upstream_tool["name"]
    desc = upstream_tool.get("description") or f"Proxy for upstream plugin tool {name}."
    bulk = BulkDataBehavior.NONE if surface != APISurface.UNKNOWN else BulkDataBehavior.BLOCKED
    return ToolMetadata(
        name=f"plug_{alias}__{name}",
        category="plugin",
        mutability=Mutability.WRITE,
        risk=Risk.MEDIUM,
        provider=None,
        api_surface=surface,
        api_evidence=f"plugin.{alias}.{name}",
        api_evidence_url=None,
        requires_dry_run=False,
        requires_approval=False,
        requires_write_enable=True,
        requires_admin_enable=False,
        bulk_data_behavior=bulk,
        description=desc,
    )


def _make_proxy(plugin: SubprocessPlugin, upstream_name: str, proxy_name: str) -> Any:
    """Build the synchronous callable that ``gated()`` will wrap + register."""

    def proxy(arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return plugin.call_sync(upstream_name, arguments or {})

    proxy.__name__ = proxy_name
    proxy.__qualname__ = proxy_name
    proxy.__doc__ = f"Proxy to upstream plugin tool '{upstream_name}'."
    return proxy


# ---------------------------------------------------------------------------
# Top-level entry: load_plugins
# ---------------------------------------------------------------------------


_LIVE_SUBPROCESS_PLUGINS: List[SubprocessPlugin] = []


def _atexit_shutdown() -> None:  # pragma: no cover - lifecycle hook
    for plugin in list(_LIVE_SUBPROCESS_PLUGINS):
        try:
            plugin.stop()
        except Exception:
            pass


atexit.register(_atexit_shutdown)


def _load_python_plugin(server: Any, ctx: "ToolContext", spec: PluginSpec) -> PluginLoadResult:
    """v0.1 import-based plugin path: ``register_tools(server, config)``."""
    try:
        mod = importlib.import_module(spec.target)
        register = getattr(mod, "register_tools", None)
        if not callable(register):
            return PluginLoadResult(
                name=spec.target,
                ok=False,
                error="No callable register_tools(server, config) found",
                scheme=spec.scheme,
                alias=spec.alias,
            )
        register(server, ctx.config)
        return PluginLoadResult(name=spec.target, ok=True, scheme=spec.scheme, alias=spec.alias)
    except Exception as exc:  # noqa: BLE001
        return PluginLoadResult(
            name=spec.target,
            ok=False,
            error=str(exc),
            scheme=spec.scheme,
            alias=spec.alias,
        )


def _load_subprocess_plugin(server: Any, ctx: "ToolContext", spec: PluginSpec) -> PluginLoadResult:
    """Spawn subprocess, list child tools, register namespaced proxies."""
    # Local imports keep gated() optional for callers that don't use it.
    from .tools._gated import gated

    plugin = SubprocessPlugin(spec, env_passthrough=ctx.config.plugin_env_passthrough)
    try:
        plugin.start()
    except Exception as exc:  # noqa: BLE001
        return PluginLoadResult(
            name=f"{spec.scheme}:{spec.target}",
            ok=False,
            error=str(exc),
            scheme=spec.scheme,
            alias=spec.alias,
        )

    _LIVE_SUBPROCESS_PLUGINS.append(plugin)
    registered_names: List[str] = []
    for tool in plugin.listed_tools():
        meta = _synthesize_metadata(spec.alias, tool, trust=ctx.config.plugin_trust)
        proxy_name = meta.name
        proxy_fn = _make_proxy(plugin, tool["name"], proxy_name)
        try:
            gated(server, ctx, meta=meta)(proxy_fn)
            registered_names.append(proxy_name)
        except Exception as exc:  # noqa: BLE001
            logger.warning("failed to register plugin tool %s: %s", proxy_name, exc)

    return PluginLoadResult(
        name=f"{spec.scheme}:{spec.target}",
        ok=True,
        scheme=spec.scheme,
        alias=spec.alias,
        tools=registered_names,
    )


def load_plugins(server: Any, ctx: "ToolContext") -> List[PluginLoadResult]:
    """Load every entry in ``ctx.config.plugins``.

    Each entry is parsed via :func:`parse_plugin_entry`. ``python:`` (and bare
    module paths) call the v0.1 ``register_tools(server, config)`` hook.
    Subprocess schemes (``npx`` / ``uvx`` / ``cmd``) spawn the child MCP
    server, list its tools, and register namespaced proxy tools under
    ``plug_<alias>__<tool>`` via the gated() wrapper so audit + redaction +
    policy enforcement applies uniformly.

    The function NEVER raises for a malformed entry — failures are reported
    as :class:`PluginLoadResult` with ``ok=False`` so the server can still
    boot and surface the warning via ``bdc_diagnostics``.
    """
    results: List[PluginLoadResult] = []
    for raw in ctx.config.plugins:
        try:
            spec = parse_plugin_entry(raw)
        except PluginParseError as exc:
            results.append(PluginLoadResult(name=raw, ok=False, error=str(exc)))
            continue

        if spec.scheme == "python":
            results.append(_load_python_plugin(server, ctx, spec))
        elif spec.scheme in {"npx", "uvx", "cmd"}:
            results.append(_load_subprocess_plugin(server, ctx, spec))
        else:  # pragma: no cover - parse_plugin_entry already rejects others
            results.append(
                PluginLoadResult(
                    name=raw,
                    ok=False,
                    error=f"unsupported plugin scheme: {spec.scheme}",
                    scheme=spec.scheme,
                    alias=spec.alias,
                )
            )
    return results
