"""Toolbox / MATLAB-like search path."""

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
        """Locate name.m (or name.M) on the path; first match wins."""
        base = Path(name).name
        if base.lower().endswith(".m"):
            base = base[:-2]
        parts = base.split(".")  # pkg.sub.name -> +pkg/+sub/name.m (M8 O-E5)
        if any(not p for p in parts):
            return None
        sub = Path(*["+" + p for p in parts[:-1]]) if len(parts) > 1 else Path()
        base = parts[-1]
        candidates = (f"{base}.m", f"{base}.M")
        for entry in self.entries:
            if not entry.is_dir():
                continue
            for cand in candidates:
                hit = entry / sub / cand
                if hit.is_file():
                    return hit.resolve()
                hit = entry / sub / ("@" + base) / cand  # class folder (#766)
                if hit.is_file():
                    return hit.resolve()
        return None
