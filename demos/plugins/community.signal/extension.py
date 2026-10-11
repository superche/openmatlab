"""Community Signal sample plugin — clean-room demo (not a MathWorks toolbox)."""

from __future__ import annotations

from typing import Any


def activate(context: Any) -> None:
    host = context.host
    plugin_id = context.plugin_id

    def _demo(*_args: Any, **_kwargs: Any) -> str:
        msg = f"{plugin_id}: demo OK (path={context.extension_path})"
        host.window.show_information_message(msg)
        return msg

    host.commands.register_command("community.signal.demo", _demo)
    host.window.register_panel(
        "community.signal.panel",
        lambda: {"title": "Signal", "plugin": plugin_id},
    )


def deactivate() -> None:
    pass
