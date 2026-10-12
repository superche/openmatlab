"""Shell that mounts isolated UI bundles and routes messages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List


@dataclass
class MessageBus:
    handlers: Dict[str, List[Callable[[dict], None]]] = field(default_factory=dict)

    def on(self, topic: str, handler: Callable[[dict], None]) -> None:
        self.handlers.setdefault(topic, []).append(handler)

    def emit(self, topic: str, payload: dict) -> None:
        for h in self.handlers.get(topic, []):
            h(payload)


@dataclass
class Bundle:
    id: str
    mount: Callable[["Shell"], str]


@dataclass
class Shell:
    bus: MessageBus = field(default_factory=MessageBus)
    mounts: List[str] = field(default_factory=list)
    domain_cmds: Dict[str, Callable[..., Any]] = field(default_factory=dict)

    def mount_bundle(self, bundle: Bundle) -> None:
        self.mounts.append(bundle.mount(self))

    def register_command(self, name: str, fn: Callable[..., Any]) -> None:
        self.domain_cmds[name] = fn
