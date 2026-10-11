"""Host-owned contribution slots."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

CORE_SLOTS: Tuple[Tuple[str, str], ...] = (
    ("commands", "Command id → callable (+ metadata)"),
    ("panels", "Dockable / tab panel descriptors"),
    ("menus", "Menu path contributions"),
    ("toolbar", "Toolbar actions"),
    ("status", "Status-bar items"),
    ("ux_hints", "Domain-driven UX preferences"),
    ("configuration", "Setting contributions"),
    ("path", "Extra .m search path entries"),
)


@dataclass
class Slot:
    name: str
    description: str
    # (plugin_id, payload)
    contributions: List[Tuple[str, Any]] = field(default_factory=list)

    def contribute(self, plugin_id: str, payload: Any) -> None:
        self.contributions.append((plugin_id, payload))

    def payloads(self) -> List[Any]:
        return [p for _, p in self.contributions]

    def by_plugin(self, plugin_id: str) -> List[Any]:
        return [p for pid, p in self.contributions if pid == plugin_id]


@dataclass
class SlotRegistry:
    """Registry of named slots; unload removes contributions by plugin id."""

    slots: Dict[str, Slot] = field(default_factory=dict)

    @classmethod
    def with_core_slots(cls) -> "SlotRegistry":
        reg = cls()
        for name, desc in CORE_SLOTS:
            reg.define(name, desc)
        return reg

    def define(self, name: str, description: str) -> Slot:
        if name in self.slots:
            raise ValueError(f"slot already defined: {name}")
        slot = Slot(name=name, description=description)
        self.slots[name] = slot
        return slot

    def get(self, name: str) -> Slot:
        try:
            return self.slots[name]
        except KeyError as exc:
            raise KeyError(f"unknown slot: {name}") from exc

    def contribute(self, slot_name: str, plugin_id: str, payload: Any) -> None:
        self.get(slot_name).contribute(plugin_id, payload)

    def unload(self, plugin_id: str) -> int:
        """Remove all contributions tagged with ``plugin_id``. Return count."""
        removed = 0
        for slot in self.slots.values():
            before = len(slot.contributions)
            slot.contributions = [
                (pid, payload)
                for pid, payload in slot.contributions
                if pid != plugin_id
            ]
            removed += before - len(slot.contributions)
        return removed

    def names(self) -> List[str]:
        return sorted(self.slots)
