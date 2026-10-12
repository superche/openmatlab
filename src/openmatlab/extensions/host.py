"""PluginHost — discover, validate, contribute, activate, unload."""

from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Dict, List, Optional, Sequence

from openmatlab.extensions import api_version as HOST_API_VERSION
from openmatlab.extensions.activation import (
    PluginState,
    call_activate,
    call_deactivate,
    command_triggers,
    import_plugin_main,
    is_known_predicate,
    path_exists_globs,
    should_activate_on_startup,
    wants_workspace_matlab,
)
from openmatlab.extensions.api.commands import CommandsAPI
from openmatlab.extensions.api.extensions import ExtensionInfo, ExtensionsAPI
from openmatlab.extensions.api.path import PathAPI
from openmatlab.extensions.api.window import WindowAPI
from openmatlab.extensions.api.workspace import WorkspaceAPI
from openmatlab.extensions.api import commands as commands_mod
from openmatlab.extensions.api import extensions as extensions_mod
from openmatlab.extensions.api import path as path_mod
from openmatlab.extensions.api import window as window_mod
from openmatlab.extensions.api import workspace as workspace_mod
from openmatlab.extensions.context import ExtensionContext, WorkspaceView
from openmatlab.extensions.discovery import discover_all
from openmatlab.extensions.engines import EngineRangeError, check_compatible, satisfies
from openmatlab.extensions.manifest import PluginManifest
from openmatlab.extensions.slots import SlotRegistry
from openmatlab.extensions.when import any_matlab_files, evaluate_when, glob_matches

log = logging.getLogger("openmatlab.extensions")


@dataclass
class PluginRecord:
    manifest: PluginManifest
    state: PluginState = PluginState.DISCOVERED
    module: Optional[ModuleType] = None
    context: Optional[ExtensionContext] = None
    error: Optional[str] = None
    engine_ok: bool = True


@dataclass
class HostAPIFacade:
    """Bound surface handed to ExtensionContext.host."""

    commands: CommandsAPI
    window: WindowAPI
    workspace: WorkspaceAPI
    path: PathAPI
    extensions: ExtensionsAPI
    api_version: str = HOST_API_VERSION


def resolve_builtin_factory(manif: PluginManifest, factory_spec: str) -> Callable[..., Any]:
    """Resolve ``module:attr`` factory relative to the plugin root."""
    if not isinstance(factory_spec, str) or ":" not in factory_spec:
        raise ValueError(
            f"builtin factory must be 'module:attr', got {factory_spec!r}"
        )
    mod_name, attr = factory_spec.split(":", 1)
    if not mod_name or not attr:
        raise ValueError(
            f"builtin factory must be 'module:attr', got {factory_spec!r}"
        )
    root = manif.root
    candidate = (root / f"{mod_name}.py").resolve()
    if candidate.is_file():
        mod_id = f"openmatlab_plugin_{manif.id.replace('.', '_')}_builtin_{mod_name}"
        spec = importlib.util.spec_from_file_location(mod_id, candidate)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load builtin factory module {candidate}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[mod_id] = module
        root_s = str(root)
        if root_s not in sys.path:
            sys.path.insert(0, root_s)
        spec.loader.exec_module(module)
    else:
        root_s = str(root)
        if root_s not in sys.path:
            sys.path.insert(0, root_s)
        module = importlib.import_module(mod_name)
    try:
        obj = getattr(module, attr)
    except AttributeError as exc:
        raise AttributeError(
            f"builtin factory {factory_spec!r}: {mod_name!r} has no attr {attr!r}"
        ) from exc
    if not callable(obj):
        raise TypeError(f"builtin factory {factory_spec!r} is not callable")
    return obj


class PluginHost:
    """Orchestrates discovery → contributes → activation → unload."""

    def __init__(
        self,
        *,
        toolbox_path: Any = None,
        session: Any = None,
        function_resolver: Any = None,
        api_version: str = HOST_API_VERSION,
    ) -> None:
        self.api_version = api_version
        self.session = session
        self.slots = SlotRegistry.with_core_slots()
        self.commands_api = CommandsAPI()
        self.window_api = WindowAPI()
        self.workspace_api = WorkspaceAPI()
        self.path_api = PathAPI(toolbox_path)
        self.extensions_api = ExtensionsAPI(self)
        self.plugins: Dict[str, PluginRecord] = {}
        self._command_to_plugin: Dict[str, str] = {}
        self._pending_command_activation: Dict[str, str] = {}
        self._plugin_builtins: Dict[str, List[str]] = {}
        self._bound = False
        # Prefer explicit resolver; else Session.functions when present.
        if function_resolver is not None:
            self.function_resolver = function_resolver
        elif session is not None and getattr(session, "functions", None) is not None:
            self.function_resolver = session.functions
        else:
            self.function_resolver = None

    # --- binding ---------------------------------------------------------

    def bind_apis(self) -> None:
        """Bind module-level Host API to this host instance."""
        commands_mod.bind(self.commands_api)
        window_mod.bind(self.window_api)
        workspace_mod.bind(self.workspace_api)
        path_mod.bind(self.path_api)
        extensions_mod.bind(self.extensions_api)
        self._bound = True

    def unbind_apis(self) -> None:
        commands_mod.bind(None)
        window_mod.bind(None)
        workspace_mod.bind(None)
        path_mod.bind(None)
        extensions_mod.bind(None)
        self._bound = False

    def facade(self) -> HostAPIFacade:
        return HostAPIFacade(
            commands=self.commands_api,
            window=self.window_api,
            workspace=self.workspace_api,
            path=self.path_api,
            extensions=self.extensions_api,
            api_version=self.api_version,
        )

    # --- discovery / load ------------------------------------------------

    def discover(
        self,
        *,
        extra: Optional[Sequence[Path | str]] = None,
        env: Optional[str] = None,
        include_user_dir: bool = True,
        include_entry_points: bool = True,
    ) -> List[str]:
        """Discover plugins and register records. Return warning strings."""
        manifests, warns = discover_all(
            extra=extra,
            env=env,
            include_user_dir=include_user_dir,
            include_entry_points=include_entry_points,
        )
        for manif in manifests:
            if manif.id in self.plugins:
                msg = f"duplicate plugin id {manif.id!r} ignored on re-discover"
                warns.append(msg)
                continue
            self.plugins[manif.id] = PluginRecord(manifest=manif)
        return warns

    def register_manifest(self, manif: PluginManifest) -> PluginRecord:
        """Register a single already-validated manifest (tests / demos)."""
        if manif.id in self.plugins:
            raise ValueError(f"plugin already registered: {manif.id}")
        rec = PluginRecord(manifest=manif)
        self.plugins[manif.id] = rec
        return rec

    def load_plugin(self, plugin_id: str) -> PluginRecord:
        """Validate engines, register declarative contributes (not activate)."""
        rec = self.plugins[plugin_id]
        manif = rec.manifest
        try:
            check_compatible(manif.engines_openmatlab, self.api_version)
            rec.engine_ok = True
        except EngineRangeError as exc:
            rec.engine_ok = False
            rec.state = PluginState.DISABLED
            rec.error = str(exc)
            log.warning("plugin %s disabled: %s", plugin_id, exc)
            return rec

        for w in manif.warnings:
            log.warning("plugin %s: %s", plugin_id, w)

        self._apply_contributes(rec)
        rec.state = PluginState.LOADED

        # Track onCommand activation
        for cmd in command_triggers(manif.activation):
            self._pending_command_activation[cmd] = plugin_id
            self._command_to_plugin[cmd] = plugin_id

        return rec

    def load_all(self) -> None:
        for pid in list(self.plugins):
            if self.plugins[pid].state == PluginState.DISCOVERED:
                self.load_plugin(pid)

    def _apply_contributes(self, rec: PluginRecord) -> None:
        manif = rec.manifest
        pid = manif.id
        contrib = manif.contributes

        for cmd in contrib.get("commands") or []:
            if isinstance(cmd, dict) and "command" in cmd:
                self.slots.contribute("commands", pid, dict(cmd))
                # Stub until activate registers handler
                cid = cmd["command"]
                self._command_to_plugin[cid] = pid
                if not self.commands_api.has(cid):

                    def _stub(*_a: Any, _cid=cid, **_k: Any) -> None:
                        raise RuntimeError(
                            f"command {_cid} not yet activated "
                            f"(plugin handler missing)"
                        )

                    self.commands_api.register_command(cid, _stub)

        for item in contrib.get("menus") or []:
            self.slots.contribute("menus", pid, item)
        for item in contrib.get("toolbar") or []:
            self.slots.contribute("toolbar", pid, item)
        for item in contrib.get("panels") or []:
            self.slots.contribute("panels", pid, item)
        for item in contrib.get("status") or []:
            self.slots.contribute("status", pid, item)

        ux = contrib.get("uxHints")
        if ux:
            self.slots.contribute("ux_hints", pid, ux)

        cfg = contrib.get("configuration")
        if cfg and isinstance(cfg, dict):
            self.slots.contribute("configuration", pid, cfg)
            self.workspace_api.merge_contributed(cfg)

        for entry in contrib.get("pathEntries") or []:
            if isinstance(entry, str):
                rel = entry
            elif isinstance(entry, dict):
                rel = entry.get("relative") or entry.get("path")
            else:
                continue
            if not rel:
                continue
            abs_path = (manif.root / rel).resolve()
            self.slots.contribute("path", pid, str(abs_path))
            try:
                self.path_api.addpath(abs_path)
            except RuntimeError:
                # No toolbox bound yet — slot still records the entry
                pass

        for builtin in contrib.get("builtins") or []:
            self.slots.contribute("commands", pid, {"builtin": builtin})
            self._register_builtin_contribution(rec, builtin)

    def _register_builtin_contribution(
        self, rec: PluginRecord, builtin: Any
    ) -> None:
        """Resolve ``factory: module:attr`` and install into FunctionResolver."""
        if not isinstance(builtin, dict):
            log.warning(
                "plugin %s: builtins entry must be a mapping, got %r",
                rec.manifest.id,
                type(builtin).__name__,
            )
            return
        name = builtin.get("name")
        factory_spec = builtin.get("factory")
        if not name or not factory_spec:
            log.warning(
                "plugin %s: builtins entry requires name+factory, got %r",
                rec.manifest.id,
                builtin,
            )
            return
        resolver = self.function_resolver
        if resolver is None:
            log.warning(
                "plugin %s: builtins %r skipped (no FunctionResolver bound)",
                rec.manifest.id,
                name,
            )
            return
        try:
            factory = resolve_builtin_factory(rec.manifest, str(factory_spec))
            builtin_fn = factory()
            if not callable(builtin_fn):
                raise TypeError(
                    f"factory {factory_spec!r} must return a callable, "
                    f"got {type(builtin_fn).__name__}"
                )
            resolver.register_builtin(str(name), builtin_fn)
            self._plugin_builtins.setdefault(rec.manifest.id, []).append(
                str(name).lower()
            )
        except Exception as exc:
            log.warning(
                "plugin %s: failed to register builtin %r: %s",
                rec.manifest.id,
                name,
                exc,
            )
            rec.error = f"builtin {name!r}: {type(exc).__name__}: {exc}"

    # --- activation ------------------------------------------------------

    def _make_context(self, rec: PluginRecord) -> ExtensionContext:
        path_entries: List[Path] = []
        try:
            path_entries = list(self.path_api.list())
        except Exception:
            path_entries = []
        ws = WorkspaceView(cwd=Path.cwd(), path_entries=path_entries)
        return ExtensionContext(
            plugin_id=rec.manifest.id,
            extension_path=rec.manifest.root,
            workspace=ws,
            host=self.facade(),
        )

    def _warn_unknown_predicates(self, plugin_id: str, activation: List[str]) -> None:
        for pred in activation:
            if not is_known_predicate(pred):
                log.warning(
                    "plugin %s: unknown activation predicate %r", plugin_id, pred
                )

    def activate_plugin(self, plugin_id: str) -> PluginRecord:
        """Import main and call activate(context). Faults are isolated."""
        rec = self.plugins[plugin_id]
        if rec.state == PluginState.DISABLED:
            return rec
        if rec.state == PluginState.ACTIVE:
            return rec
        if rec.state == PluginState.DISCOVERED:
            self.load_plugin(plugin_id)
            if rec.state == PluginState.DISABLED:
                return rec

        self._warn_unknown_predicates(plugin_id, rec.manifest.activation)

        if not rec.manifest.main:
            # Declarative-only
            rec.state = PluginState.ACTIVE
            return rec

        if not self._bound:
            self.bind_apis()

        ctx = self._make_context(rec)
        rec.context = ctx
        try:
            module = import_plugin_main(rec.manifest)
            rec.module = module
            call_activate(module, ctx)
            rec.state = PluginState.ACTIVE
            # Preserve builtin registration errors; clear unrelated ones
            if not (rec.error and str(rec.error).startswith("builtin ")):
                rec.error = None
        except Exception as exc:
            rec.state = PluginState.FAULTED
            rec.error = f"{type(exc).__name__}: {exc}"
            log.exception("plugin %s activate failed", plugin_id)
        return rec

    def activate_on_startup(self) -> None:
        """Activate plugins that list onStartupFinished; then poll path preds."""
        for pid, rec in list(self.plugins.items()):
            if rec.state in (PluginState.DISABLED, PluginState.FAULTED, PluginState.ACTIVE):
                continue
            if should_activate_on_startup(rec.manifest.activation):
                self.activate_plugin(pid)
        # Best-effort path / workspace predicates after startup wiring
        self.poll_path_activation()

    def ensure_command_activated(self, command_id: str) -> None:
        """If a plugin waits on onCommand:id, activate it first."""
        pid = self._pending_command_activation.get(command_id)
        if not pid:
            return
        rec = self.plugins.get(pid)
        if rec and rec.state not in (
            PluginState.ACTIVE,
            PluginState.FAULTED,
            PluginState.DISABLED,
        ):
            self.activate_plugin(pid)

    def execute_command(self, command_id: str, *args: Any, **kwargs: Any) -> Any:
        self.ensure_command_activated(command_id)
        return self.commands_api.execute_command(command_id, *args, **kwargs)

    # --- path / workspace activation (#360) ------------------------------

    def activation_roots(self) -> List[Path]:
        """Roots scanned for path / workspace activation predicates."""
        roots: List[Path] = [Path.cwd()]
        try:
            roots.extend(Path(p) for p in self.path_api.list())
        except Exception:
            pass
        return roots

    def _path_predicates_match(
        self, activation: List[str], roots: Sequence[Path]
    ) -> bool:
        if wants_workspace_matlab(activation) and any_matlab_files(roots):
            return True
        for pattern in path_exists_globs(activation):
            if glob_matches(roots, pattern):
                return True
        return False

    def poll_path_activation(self) -> List[str]:
        """Best-effort activate plugins waiting on path/workspace predicates.

        Returns plugin ids newly activated. Safe to call after addpath or
        filesystem changes; does not replace a full watch service.
        """
        roots = self.activation_roots()
        activated: List[str] = []
        for pid, rec in list(self.plugins.items()):
            if rec.state in (
                PluginState.ACTIVE,
                PluginState.FAULTED,
                PluginState.DISABLED,
                PluginState.UNLOADED,
            ):
                continue
            preds = rec.manifest.activation
            # Warn unknowns even when we only poll
            self._warn_unknown_predicates(pid, preds)
            # Skip if only waiting on onCommand / onStartupFinished without path
            has_path = wants_workspace_matlab(preds) or bool(path_exists_globs(preds))
            if not has_path:
                continue
            if self._path_predicates_match(preds, roots):
                self.activate_plugin(pid)
                if self.plugins[pid].state == PluginState.ACTIVE:
                    activated.append(pid)
        return activated

    # --- when clauses (#362) ---------------------------------------------

    def list_menus(self, *, evaluate: bool = True) -> List[Any]:
        """Menu contributions, optionally filtered by ``when`` clauses."""
        payloads = list(self.slots.get("menus").payloads())
        if not evaluate:
            return payloads
        has_m = any_matlab_files(self.activation_roots())
        out: List[Any] = []
        for item in payloads:
            if isinstance(item, dict):
                if evaluate_when(item.get("when"), has_matlab_files=has_m):
                    out.append(item)
            else:
                out.append(item)
        return out

    def list_panel_contributions(self, *, evaluate: bool = True) -> List[Any]:
        """Panel slot contributions, optionally filtered by ``when``."""
        payloads = list(self.slots.get("panels").payloads())
        if not evaluate:
            return payloads
        has_m = any_matlab_files(self.activation_roots())
        out: List[Any] = []
        for item in payloads:
            if isinstance(item, dict):
                if evaluate_when(item.get("when"), has_matlab_files=has_m):
                    out.append(item)
            else:
                out.append(item)
        return out

    def get_extension(self, extension_id: str) -> ExtensionInfo:
        """Host API convenience: inspect another plugin."""
        return self.extensions_api.get_extension(extension_id)

    # --- unload ----------------------------------------------------------

    def unload(self, plugin_id: str) -> None:
        rec = self.plugins.get(plugin_id)
        if rec is None:
            return
        if rec.context is not None:
            rec.context.dispose_subscriptions()
        call_deactivate(rec.module)
        # Capture path entries before slot unload so ToolboxPath can drop them
        path_payloads = list(self.slots.get("path").by_plugin(plugin_id))
        self.slots.unload(plugin_id)
        # Drop command handlers owned by this plugin
        for cid, owner in list(self._command_to_plugin.items()):
            if owner == plugin_id:
                self.commands_api.unregister(cid)
                self._command_to_plugin.pop(cid, None)
                self._pending_command_activation.pop(cid, None)
        # Drop builtins registered from contributes.builtins
        names = self._plugin_builtins.pop(plugin_id, [])
        resolver = self.function_resolver
        if resolver is not None and names:
            for n in names:
                resolver.builtins.pop(n, None)
        if self.path_api._path is not None:
            for payload in path_payloads:
                try:
                    self.path_api._path.rmpath(payload)
                except Exception:
                    log.debug("rmpath failed for %s", payload, exc_info=True)
        rec.state = PluginState.UNLOADED
        rec.module = None
        rec.context = None

    # --- listing ---------------------------------------------------------

    def list_plugins(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for pid, rec in sorted(self.plugins.items()):
            eng = rec.manifest.engines_openmatlab
            mismatch = not rec.engine_ok or not satisfies(eng, self.api_version)
            rows.append(
                {
                    "id": pid,
                    "version": rec.manifest.version,
                    "displayName": rec.manifest.display_name or pid,
                    "state": rec.state.value,
                    "engines": eng,
                    "engine_mismatch": mismatch,
                    "error": rec.error,
                    "root": str(rec.manifest.root),
                }
            )
        return rows
