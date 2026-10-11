"""Minimal host: discover entry-point-like plugins and activate them."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Protocol


class DomainPlugin(Protocol):
    id: str
    label: str

    def register_commands(self, registry: "CommandRegistry") -> None: ...


class UiPlugin(Protocol):
    id: str
    label: str

    def contribute_panels(self, shell: "Shell") -> None: ...


@dataclass
class CommandRegistry:
    commands: Dict[str, Callable[..., Any]] = field(default_factory=dict)

    def add(self, name: str, fn: Callable[..., Any]) -> None:
        self.commands[name] = fn


@dataclass
class Panel:
    id: str
    title: str
    render: Callable[[], str]


@dataclass
class Shell:
    """Desktop shell stub — panels + active domain UX hooks."""

    panels: List[Panel] = field(default_factory=list)
    domain_ux: Dict[str, str] = field(default_factory=dict)

    def add_panel(self, panel: Panel) -> None:
        self.panels.append(panel)

    def set_domain_ux(self, domain_id: str, blurb: str) -> None:
        self.domain_ux[domain_id] = blurb


def discover_entry_points(group: str, table: Dict[str, List[Callable[[], Any]]]) -> List[Any]:
    """Stand-in for importlib.metadata.entry_points(group=...).load()."""
    return [factory() for factory in table.get(group, [])]


def boot(entry_table: Dict[str, List[Callable[[], Any]]]) -> tuple[CommandRegistry, Shell]:
    cmds = CommandRegistry()
    shell = Shell()
    for domain in discover_entry_points("openmatlab.domain", entry_table):
        domain.register_commands(cmds)
        # Domains may customize UX via the same entry-point load
        if hasattr(domain, "customize_ux"):
            domain.customize_ux(shell)
    for ui in discover_entry_points("openmatlab.ui", entry_table):
        ui.contribute_panels(shell)
    return cmds, shell
