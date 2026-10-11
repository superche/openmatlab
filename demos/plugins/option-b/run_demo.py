#!/usr/bin/env python3
"""Run Option B stub: manifest YAML + ToolboxPath-like load path."""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from host import load_path  # noqa: E402


def main() -> None:
    roots = [HERE / "toolboxes"]
    commands, panels, ux = load_path(roots)
    print("=== Option B: manifest YAML + load path ===")
    print("path:", [str(r) for r in roots])
    print("commands:", sorted(commands))
    print("bode(G):", commands["bode"]("G"))
    print("tf([1],[1 1]):", commands["tf"]([1], [1, 1]))
    print("panels:", panels)
    print("ux:", ux)
    print("OK")


if __name__ == "__main__":
    main()
