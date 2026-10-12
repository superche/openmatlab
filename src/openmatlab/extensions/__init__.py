"""Extension Host API — VS Code–style plugin surface (contract v0).

Public imports for plugin authors::

    from openmatlab.extensions import commands, window, workspace, path, extensions
    from openmatlab.extensions import api_version

See ``docs/design/PLUGIN-CONTRACT.md``.
"""

from __future__ import annotations

from openmatlab.extensions import api as _api_pkg
from openmatlab.extensions.api import commands, extensions, path, window, workspace

# Host API SemVer (independent of package openmatlab version when needed).
api_version: str = "0.1.0"

__all__ = [
    "api_version",
    "commands",
    "window",
    "workspace",
    "path",
    "extensions",
    "PluginHost",
]

def __getattr__(name: str):
    if name == "PluginHost":
        from openmatlab.extensions.host import PluginHost

        return PluginHost
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
