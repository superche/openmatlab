"""Activation predicates and plugin lifecycle helpers."""

from __future__ import annotations

import importlib.util
import logging
import sys
from enum import Enum
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, List, Optional, Set

from openmatlab.extensions.context import ExtensionContext
from openmatlab.extensions.manifest import PluginManifest

log = logging.getLogger("openmatlab.extensions")


class PluginState(str, Enum):
    DISCOVERED = "discovered"
    LOADED = "loaded"  # contributes registered; not yet activated
    ACTIVE = "active"
    FAULTED = "faulted"
    DISABLED = "disabled"  # engine mismatch etc.
    UNLOADED = "unloaded"


KNOWN_PREDICATE_PREFIXES = (
    "onStartupFinished",
    "onCommand:",
    "onPathExists:",
    "workspaceHasMatlabFiles",
)


def normalize_predicates(raw: List[str]) -> List[str]:
    return list(raw) if raw else ["onStartupFinished"]


def is_known_predicate(pred: str) -> bool:
    if pred == "onStartupFinished" or pred == "workspaceHasMatlabFiles":
        return True
    return pred.startswith("onCommand:") or pred.startswith("onPathExists:")


def predicates_waiting(activation: List[str]) -> List[str]:
    """Return known predicates; unknown ones are ignored with warning elsewhere."""
    return [p for p in activation if is_known_predicate(p)]


def should_activate_on_startup(activation: List[str]) -> bool:
    return "onStartupFinished" in activation


def command_triggers(activation: List[str]) -> Set[str]:
    out: Set[str] = set()
    for pred in activation:
        if pred.startswith("onCommand:"):
            out.add(pred[len("onCommand:") :])
    return out


def import_plugin_main(manif: PluginManifest) -> ModuleType:
    """Import the plugin main module from extension_path / main."""
    if not manif.main:
        raise RuntimeError(f"plugin {manif.id} has no main module")
    main = manif.main
    root = manif.root

    # Relative file path (extension.py or pkg/mod.py)
    candidate = (root / main).resolve()
    if candidate.is_file():
        mod_name = f"openmatlab_plugin_{manif.id.replace('.', '_')}"
        spec = importlib.util.spec_from_file_location(mod_name, candidate)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load plugin main {candidate}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = module
        # Ensure plugin root on path for relative imports
        root_s = str(root)
        if root_s not in sys.path:
            sys.path.insert(0, root_s)
        spec.loader.exec_module(module)
        return module

    # Dotted import (already on sys.path)
    root_s = str(root)
    if root_s not in sys.path:
        sys.path.insert(0, root_s)
    return importlib.import_module(main)


def call_activate(module: ModuleType, context: ExtensionContext) -> None:
    activate = getattr(module, "activate", None)
    if activate is None:
        return
    if not callable(activate):
        raise TypeError(f"{module!r}.activate is not callable")
    activate(context)


def call_deactivate(module: Optional[ModuleType]) -> None:
    if module is None:
        return
    deactivate = getattr(module, "deactivate", None)
    if callable(deactivate):
        try:
            deactivate()
        except Exception:
            log.exception("deactivate() failed")


def path_exists_globs(activation: List[str]) -> List[str]:
    """Extract glob patterns from ``onPathExists:<glob>`` predicates."""
    out: List[str] = []
    for pred in activation:
        if pred.startswith("onPathExists:"):
            out.append(pred[len("onPathExists:") :])
    return out


def wants_workspace_matlab(activation: List[str]) -> bool:
    return "workspaceHasMatlabFiles" in activation
