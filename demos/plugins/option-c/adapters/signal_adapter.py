"""Thin adapter: signal domain + its preferred UX into host slots."""

from __future__ import annotations


class SignalAdapter:
    plugin_id = "domain.signal"

    def attach(self, host) -> None:
        host.get("commands").contribute(self.plugin_id, {"fft": lambda x: f"fft({x})"})
        host.get("panels").contribute(
            self.plugin_id, {"id": "spectrum", "title": "Spectrum", "body": "[Spectrum]"}
        )
        host.get("menus").contribute(self.plugin_id, "Analyze/Signal/FFT")
        host.get("toolbar").contribute(self.plugin_id, "btn:FFT")
        # Domain customizes UX without owning the shell
        host.get("ux_hints").contribute(
            self.plugin_id, "open panel=spectrum when fft runs; theme=viridis"
        )


class CoreShellAdapter:
    """Optional: full-shell replacement still goes through slots (demo)."""

    plugin_id = "ui.core_shell"

    def attach(self, host) -> None:
        host.get("status").contribute(self.plugin_id, "Ready | Option-C slots")
        host.get("menus").contribute(self.plugin_id, "File/Open")
