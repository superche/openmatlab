#!/usr/bin/env python3
"""Run Option C stub: host slots + thin adapters."""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from adapters.signal_adapter import CoreShellAdapter, SignalAdapter  # noqa: E402
from host import create_host  # noqa: E402


def main() -> None:
    host = create_host()
    for adapter in (CoreShellAdapter(), SignalAdapter()):
        adapter.attach(host)

    print("=== Option C: host slots + thin adapters ===")
    print("slots:", sorted(host.slots))
    cmds = host.get("commands").contributions[0][1]
    print("fft(sin):", cmds["fft"]("sin"))
    print(host.render_desktop())
    print("ux_hints:", host.get("ux_hints").contributions)
    print("OK")


if __name__ == "__main__":
    main()
