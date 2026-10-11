"""Example domain plugin: signal processing commands + UX hint."""

from __future__ import annotations


class SignalDomain:
    id = "signal"
    label = "Signal Processing"

    def register_commands(self, registry) -> None:
        registry.add("fft_demo", lambda x: f"fft({x})")
        registry.add("filter_demo", lambda x: f"filter({x})")

    def customize_ux(self, shell) -> None:
        shell.set_domain_ux(
            self.id,
            "Signal UX: prefer spectrum panel; default colormap = viridis",
        )


def load():
    return SignalDomain()
