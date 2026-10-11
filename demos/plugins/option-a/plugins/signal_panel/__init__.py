"""Example UI plugin: spectrum panel contributed to the shell."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow importing host.Panel from sibling package layout
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from host import Panel  # noqa: E402


class SpectrumPanelUi:
    id = "signal.spectrum"
    label = "Spectrum Panel"

    def contribute_panels(self, shell) -> None:
        shell.add_panel(
            Panel(
                id=self.id,
                title="Spectrum",
                render=lambda: "[SpectrumPanel] FFT magnitude placeholder",
            )
        )


def load():
    return SpectrumPanelUi()
