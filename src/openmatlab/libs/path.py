"""Toolbox / MATLAB-like search path."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
import stat as _stat
import time
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple

_LISTINGS: Dict[str, Tuple[int, FrozenSet[str]]] = {}


def _listing(d: str) -> Optional[FrozenSet[str]]:
    """Names in directory ``d`` (None if not a directory), cached on its mtime (#797);
    a directory modified in the last 2 s is re-listed every time (coarse mtime clocks):
    adding, removing or renaming a file changes the directory mtime, so new files are seen."""
    try:
        st = os.stat(d)
    except OSError:
        return None
    if not _stat.S_ISDIR(st.st_mode):
        return None
    hit = _LISTINGS.get(d)
    if hit is not None and hit[0] == st.st_mtime_ns:
        return hit[1]
    try:
        names = frozenset(os.listdir(d))
    except OSError:
        return None
    if time.time_ns() - st.st_mtime_ns > 2_000_000_000:  # racy-git rule: never cache a just-touched dir
        _LISTINGS[d] = (st.st_mtime_ns, names)
    return names


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
            top = _listing(str(entry))
            if top is None:
                continue
            d = entry / sub if parts[:-1] else entry
            names = _listing(str(d)) if parts[:-1] else top
            cls = None
            for cand in candidates:
                if names is not None and cand in names:
                    hit = d / cand
                    if hit.is_file():
                        return hit.resolve()
                if names is not None and ("@" + base) in names:
                    if cls is None:
                        cls = _listing(str(d / ("@" + base))) or frozenset()
                    if cand in cls:
                        hit = d / ("@" + base) / cand  # class folder (#766)
                        if hit.is_file():
                            return hit.resolve()
        return None
