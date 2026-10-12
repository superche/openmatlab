#!/usr/bin/env python3
"""Run Option A stub: entry-point-style discovery."""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from host import boot  # noqa: E402
from plugins.signal_domain import load as load_domain  # noqa: E402
from plugins.signal_panel import load as load_ui  # noqa: E402


def main() -> None:
    # Production would use:
    #   importlib.metadata.entry_points(group="openmatlab.domain")
    entry_table = {
        "openmatlab.domain": [load_domain],
        "openmatlab.ui": [load_ui],
    }
    cmds, shell = boot(entry_table)
    print("=== Option A: entry-point discovery ===")
    print("commands:", sorted(cmds.commands))
    print("fft_demo(sin):", cmds.commands["fft_demo"]("sin"))
    print("panels:", [(p.id, p.title, p.render()) for p in shell.panels])
    print("domain_ux:", shell.domain_ux)
    print("OK")


if __name__ == "__main__":
    main()
