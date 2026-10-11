"""Toolbox / MATLAB-like search path placeholder.

FunctionResolver consults this after builtins. Entries will be directories
of .m files or package folders — not implemented yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence


@dataclass
class ToolboxPath:
    """Ordered search path for user/toolbox function files."""

    entries: List[Path] = field(default_factory=list)

    def addpath(self, *paths: str | Path, append: bool = False) -> None:
        resolved = [Path(p).expanduser().resolve() for p in paths]
        if append:
            self.entries.extend(resolved)
        else:
            self.entries[0:0] = resolved

    def rmpath(self, *paths: str | Path) -> None:
        remove = {Path(p).expanduser().resolve() for p in paths}
        self.entries = [e for e in self.entries if e not in remove]

    def list(self) -> Sequence[Path]:
        return tuple(self.entries)

    def find_mfile(self, name: str) -> Path | None:
        """Locate name.m on the path — stub returns None."""
        return None
