"""ExtensionContext passed to plugin activate()."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Protocol


class Disposable(Protocol):
    def dispose(self) -> None: ...


@dataclass
class WorkspaceView:
    """Read-only workspace snapshot for plugins."""

    cwd: Path
    path_entries: List[Path] = field(default_factory=list)


@dataclass
class ExtensionContext:
    plugin_id: str
    extension_path: Path
    subscriptions: List[Any] = field(default_factory=list)
    workspace: Optional[WorkspaceView] = None
    host: Any = None  # bound Host API facade

    def dispose_subscriptions(self) -> None:
        for sub in list(self.subscriptions):
            dispose = getattr(sub, "dispose", None)
            if callable(dispose):
                try:
                    dispose()
                except Exception:
                    pass
        self.subscriptions.clear()
