#!/usr/bin/env python3
"""Run Option D stub: micro-frontend-ish UI composition."""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from bundles import control_mfe, shell as shell_bundle, signal_mfe  # noqa: E402
from host import Bundle, Shell  # noqa: E402


def main() -> None:
    shell = Shell()
    layout_log: list[dict] = []
    shell.bus.on("ui.layout", layout_log.append)

    for b in (
        Bundle("shell", shell_bundle.mount),
        Bundle("signal", signal_mfe.mount),
        Bundle("control", control_mfe.mount),
    ):
        shell.mount_bundle(b)

    print("=== Option D: micro-frontend-ish UI ===")
    print("mounts:", shell.mounts)
    print("fft(sin):", shell.domain_cmds["fft"]("sin"))
    shell.bus.emit("domain.signal.fft", {"x": "sin"})
    print("after fft event mounts:", shell.mounts)
    print("layout prefs:", layout_log)
    print("OK")


if __name__ == "__main__":
    main()
