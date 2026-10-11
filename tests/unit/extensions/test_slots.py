"""P03: Slot registry contribute / unload by plugin id."""

from __future__ import annotations

import pytest

from openmatlab.extensions.slots import SlotRegistry

pytestmark = pytest.mark.unit


def test_core_slots_exist():
    reg = SlotRegistry.with_core_slots()
    for name in (
        "commands",
        "panels",
        "menus",
        "toolbar",
        "status",
        "ux_hints",
        "configuration",
        "path",
    ):
        assert name in reg.slots


def test_contribute_and_unload_scoped():
    reg = SlotRegistry.with_core_slots()
    reg.contribute("commands", "plug.a", {"command": "a.run"})
    reg.contribute("commands", "plug.b", {"command": "b.run"})
    reg.contribute("panels", "plug.a", {"id": "a.panel"})
    assert len(reg.get("commands").contributions) == 2
    removed = reg.unload("plug.a")
    assert removed == 2
    assert reg.get("commands").payloads() == [{"command": "b.run"}]
    assert reg.get("panels").payloads() == []


def test_unknown_slot_raises():
    reg = SlotRegistry.with_core_slots()
    with pytest.raises(KeyError, match="unknown slot"):
        reg.get("nope")
