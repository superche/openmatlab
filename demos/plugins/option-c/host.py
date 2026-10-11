"""Host with explicit extension slots."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol


SlotHandler = Callable[..., Any]


@dataclass
class Slot:
    name: str
    description: str
    # each contribution: (plugin_id, payload)
    contributions: List[tuple[str, Any]] = field(default_factory=list)

    def contribute(self, plugin_id: str, payload: Any) -> None:
        self.contributions.append((plugin_id, payload))


@dataclass
class Host:
    """Workbench shell: slots are the only extension API."""

    slots: Dict[str, Slot] = field(default_factory=dict)

    def define_slot(self, name: str, description: str) -> Slot:
        slot = Slot(name=name, description=description)
        self.slots[name] = slot
        return slot

    def get(self, name: str) -> Slot:
        return self.slots[name]

    def render_desktop(self) -> str:
        lines = ["[Desktop]"]
        for name in ("menus", "toolbar", "panels", "status"):
            slot = self.slots.get(name)
            if not slot:
                continue
            lines.append(f"  slot:{name}")
            for pid, payload in slot.contributions:
                lines.append(f"    - {pid}: {payload}")
        return "\n".join(lines)


class Adapter(Protocol):
    plugin_id: str

    def attach(self, host: Host) -> None: ...


def create_host() -> Host:
    host = Host()
    host.define_slot("commands", "Callable registry name → fn")
    host.define_slot("panels", "Dockable / tab panels")
    host.define_slot("menus", "Menu contributions")
    host.define_slot("toolbar", "Toolbar actions")
    host.define_slot("status", "Status-bar items")
    host.define_slot("ux_hints", "Domain-driven UX preferences")
    return host
