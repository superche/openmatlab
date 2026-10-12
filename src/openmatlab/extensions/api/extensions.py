"""extensions Host API — inspect loaded plugins (get_extension)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from openmatlab.extensions.host import PluginHost

_active: Optional["ExtensionsAPI"] = None


@dataclass
class ExtensionInfo:
    """Public snapshot of another plugin (Host API get_extension)."""

    id: str
    version: str
    display_name: str
    state: str
    is_active: bool
    exports: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    engine_mismatch: bool = False
    root: str = ""


class ExtensionsAPI:
    """Bound to a PluginHost; returns metadata / exports for plugins."""

    def __init__(self, host: "PluginHost") -> None:
        self._host = host

    def get_extension(self, extension_id: str) -> ExtensionInfo:
        if not isinstance(extension_id, str) or not extension_id:
            raise ValueError("extension id must be a non-empty string")
        rec = self._host.plugins.get(extension_id)
        if rec is None:
            raise KeyError(f"unknown extension: {extension_id!r}")
        from openmatlab.extensions.activation import PluginState
        from openmatlab.extensions.engines import satisfies

        state = rec.state
        exports: Dict[str, Any] = {}
        # Active plugins may publish ``exports`` (dict) or ``__all__``.
        if state == PluginState.ACTIVE and rec.module is not None:
            raw = getattr(rec.module, "exports", None)
            if isinstance(raw, dict):
                exports = dict(raw)
            else:
                names = getattr(rec.module, "__all__", None)
                if isinstance(names, (list, tuple)):
                    for n in names:
                        if hasattr(rec.module, n):
                            exports[str(n)] = getattr(rec.module, n)
        eng = rec.manifest.engines_openmatlab
        mismatch = not rec.engine_ok or not satisfies(eng, self._host.api_version)
        return ExtensionInfo(
            id=extension_id,
            version=rec.manifest.version,
            display_name=rec.manifest.display_name or extension_id,
            state=state.value,
            is_active=state == PluginState.ACTIVE,
            exports=exports,
            error=rec.error,
            engine_mismatch=mismatch,
            root=str(rec.manifest.root),
        )


def bind(api: Optional[ExtensionsAPI]) -> None:
    global _active
    _active = api


def get_extension(extension_id: str) -> ExtensionInfo:
    if _active is None:
        raise RuntimeError("extensions API not bound to a PluginHost")
    return _active.get_extension(extension_id)
