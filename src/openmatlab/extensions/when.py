"""``when`` clause evaluation for menus / panels (v0 subset).

Documented subset (see PLUGIN-CONTRACT.md):

- omitted / empty / ``true`` → always show
- ``false`` → never show
- ``workspaceHasMatlabFiles`` → any ``*.m`` under cwd or ToolboxPath roots

Unknown identifiers → warning and treat as false. Boolean algebra deferred.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Sequence

log = logging.getLogger("openmatlab.extensions")

SUPPORTED_WHEN = frozenset({"", "true", "false", "workspaceHasMatlabFiles"})


def any_matlab_files(roots: Sequence[Path]) -> bool:
    """Best-effort: True if any ``*.m`` exists under the given roots."""
    for root in roots:
        try:
            p = Path(root)
        except TypeError:
            continue
        try:
            if p.is_file() and p.suffix.lower() == ".m":
                return True
            if p.is_dir() and next(p.rglob("*.m"), None) is not None:
                return True
        except OSError:
            continue
    return False


def glob_matches(roots: Sequence[Path], pattern: str) -> bool:
    """Return True if ``pattern`` matches any path under ``roots``."""
    if not pattern:
        return False
    for root in roots:
        try:
            p = Path(root)
        except TypeError:
            continue
        try:
            if p.is_file():
                if p.match(pattern) or p.name == pattern or str(p) == pattern:
                    return True
                continue
            if not p.is_dir():
                continue
            if next(p.glob(pattern), None) is not None:
                return True
            if next(p.rglob(pattern), None) is not None:
                return True
        except (OSError, ValueError):
            continue
    return False


def evaluate_when(
    expr: Optional[str],
    *,
    has_matlab_files: bool,
    unknown_as: bool = False,
) -> bool:
    """Evaluate a v0 ``when`` expression.

    Unknown identifiers log a warning and return ``unknown_as`` (default False).
    """
    if expr is None:
        return True
    text = str(expr).strip()
    if text == "" or text == "true":
        return True
    if text == "false":
        return False
    if text == "workspaceHasMatlabFiles":
        return bool(has_matlab_files)
    log.warning("unknown when clause %r; treating as %s", text, unknown_as)
    return unknown_as
