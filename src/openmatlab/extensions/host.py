"""PluginHost — discover, validate, contribute, activate, unload."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List, Optional, Sequence

from openmatlab.extensions import api_version as HOST_API_VERSION
from openmatlab.extensions.activation import (
    PluginState,
    call_activate,
    call_deactivate,
    command_triggers,
    import_plugin_main,
    is_known_predicate,
    should_activate_on_startup,
)
from openmatlab.extensions.api.commands import CommandsAPI
from openmatlab.extensions.api.path import PathAPI
from openmatlab.extensions.api.window import WindowAPI
from openmatlab.extensions.api.workspace import WorkspaceAPI
from openmatlab.extensions.api import commands as commands_mod
from openmatlab.extensions.api import path as path_mod
from openmatlab.extensions.api import window as window_mod
from openmatlab.extensions.api import workspace as workspace_mod
from openmatlab.extensions.context import ExtensionContext, WorkspaceView
from openmatlab.extensions.discovery import discover_all
from openmatlab.extensions.engines import EngineRangeError, check_compatible, satisfies
from openmatlab.extensions.manifest import PluginManifest
from openmatlab.extensions.slots import SlotRegistry

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
    api_version: str = HOST_API_VERSION


class PluginHost:
    """Orchestrates discovery → contributes → activation → unload."""

    def __init__(
        self,
        *,
        toolbox_path: Any = None,
        session: Any = None,
        api_version: str = HOST_API_VERSION,
    ) -> None:
        self.api_version = api_version
        self.session = session
        self.slots = SlotRegistry.with_core_slots()
        self.commands_api = CommandsAPI()
        self.window_api = WindowAPI()
        self.workspace_api = WorkspaceAPI()
        self.path_api = PathAPI(toolbox_path)
        self.plugins: Dict[str, PluginRecord] = {}
        self._command_to_plugin: Dict[str, str] = {}
        self._pending_command_activation: Dict[str, str] = {}
        self._bound = False

    # --- binding ---------------------------------------------------------

    def bind_apis(self) -> None:
        """Bind module-level Host API to this host instance."""
        commands_mod.bind(self.commands_api)
        window_mod.bind(self.window_api)
        workspace_mod.bind(self.workspace_api)
        path_mod.bind(self.path_api)
        self._bound = True

    def unbind_apis(self) -> None:
        commands_mod.bind(None)
        window_mod.bind(None)
        workspace_mod.bind(None)
        path_mod.bind(None)
        self._bound = False

    def facade(self) -> HostAPIFacade:
        return HostAPIFacade(
            commands=self.commands_api,
            window=self.window_api,
            workspace=self.workspace_api,
            path=self.path_api,
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

        # Warn on unknown predicates
        for pred in rec.manifest.activation:
            if not is_known_predicate(pred):
                log.warning(
                    "plugin %s: unknown activation predicate %r", plugin_id, pred
                )

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
            rec.error = None
        except Exception as exc:
            rec.state = PluginState.FAULTED
            rec.error = f"{type(exc).__name__}: {exc}"
            log.exception("plugin %s activate failed", plugin_id)
        return rec

    def activate_on_startup(self) -> None:
        """Activate plugins that list onStartupFinished."""
        for pid, rec in list(self.plugins.items()):
            if rec.state in (PluginState.DISABLED, PluginState.FAULTED, PluginState.ACTIVE):
                continue
            if should_activate_on_startup(rec.manifest.activation):
                self.activate_plugin(pid)

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
