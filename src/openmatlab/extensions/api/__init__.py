"""Host API submodules bound per PluginHost / ExtensionContext."""

from __future__ import annotations

from openmatlab.extensions.api import commands, extensions, path, window, workspace

__all__ = ["commands", "window", "workspace", "path", "extensions"]
